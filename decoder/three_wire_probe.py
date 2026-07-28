#!/usr/bin/env python3
"""Probe 3-wire shift-register-like interpretations on Sigrok captures.

The tool scans candidate (clock, data, latch) channel triplets and evaluates
whether a capture can be interpreted as deterministic framed serial transfer,
which is typical for LED/LCD driver chains with a latch/strobe line.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import statistics
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import load_logic_capture


@dataclass(frozen=True)
class ComboScore:
    """Quality score for one interpretation combo."""

    clock_bit: int
    data_bit: int
    latch_bit: int
    clock_edge: str
    latch_edge: str
    frames: int
    bits_mode: int
    bits_mean: float
    bits_std: float
    mode_ratio: float
    bit_ones_ratio: float
    bit_entropy: float
    score: float


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Rank 3-wire protocol interpretations (clock/data/latch)."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input .sr files")
    parser.add_argument(
        "--min-frames",
        type=int,
        default=20,
        help="Minimum frame count per combo.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=12,
        help="Top combinations to print per file.",
    )
    return parser.parse_args()


def channel_transitions(samples: bytes, bit: int) -> int:
    """Count transitions for one digital channel."""
    if not samples:
        return 0
    prev = (samples[0] >> bit) & 0x01
    transitions = 0
    for raw in samples[1:]:
        cur = (raw >> bit) & 0x01
        if cur != prev:
            transitions += 1
        prev = cur
    return transitions


def edge_positions(samples: bytes, bit: int, edge: str) -> list[int]:
    """Return sample indices where the selected edge occurs."""
    if not samples:
        return []
    prev = (samples[0] >> bit) & 0x01
    pos: list[int] = []
    for index, raw in enumerate(samples[1:], start=1):
        cur = (raw >> bit) & 0x01
        if edge == "rising" and prev == 0 and cur == 1:
            pos.append(index)
        elif edge == "falling" and prev == 1 and cur == 0:
            pos.append(index)
        prev = cur
    return pos


def bit_entropy(bit_ones_ratio: float) -> float:
    """Return binary entropy in bits."""
    probability = min(max(bit_ones_ratio, 1e-9), 1.0 - 1e-9)
    return -probability * math.log2(probability) - (1.0 - probability) * math.log2(1.0 - probability)


def evaluate_combo(
    samples: bytes,
    clock_bit: int,
    data_bit: int,
    latch_bit: int,
    clock_edge: str,
    latch_edge: str,
    min_frames: int,
) -> ComboScore | None:
    """Evaluate one (clock, data, latch) interpretation."""
    latch_marks = edge_positions(samples, latch_bit, latch_edge)
    if len(latch_marks) < min_frames + 1:
        return None

    clock_marks = edge_positions(samples, clock_bit, clock_edge)
    if not clock_marks:
        return None

    bits_per_frame: list[int] = []
    sampled_bits: list[int] = []
    clock_index = 0
    for start, end in zip(latch_marks, latch_marks[1:]):
        while clock_index < len(clock_marks) and clock_marks[clock_index] <= start:
            clock_index += 1
        local_index = clock_index
        local_count = 0
        while local_index < len(clock_marks) and clock_marks[local_index] <= end:
            sample_index = clock_marks[local_index]
            sampled_bits.append((samples[sample_index] >> data_bit) & 0x01)
            local_count += 1
            local_index += 1
        bits_per_frame.append(local_count)

    valid = [value for value in bits_per_frame if value > 0]
    if len(valid) < min_frames:
        return None

    mode_counts: dict[int, int] = {}
    for value in valid:
        mode_counts[value] = mode_counts.get(value, 0) + 1
    bits_mode, mode_hits = max(mode_counts.items(), key=lambda item: item[1])

    bits_mean = statistics.mean(valid)
    bits_std = statistics.pstdev(valid) if len(valid) > 1 else 0.0
    mode_ratio = mode_hits / len(valid)

    ones = sum(sampled_bits)
    bit_ratio = ones / len(sampled_bits) if sampled_bits else 0.0
    entropy = bit_entropy(bit_ratio) if sampled_bits else 0.0

    # Favor consistent frame widths and non-trivial data entropy.
    if bits_mean <= 0.0:
        return None
    consistency = max(0.0, 1.0 - (bits_std / bits_mean))
    width_bonus = min(bits_mode / 256.0, 1.0)
    frame_bonus = min(len(valid) / 600.0, 1.0)
    score = (3.0 * mode_ratio) + (2.0 * consistency) + (1.5 * entropy) + width_bonus + frame_bonus

    return ComboScore(
        clock_bit=clock_bit,
        data_bit=data_bit,
        latch_bit=latch_bit,
        clock_edge=clock_edge,
        latch_edge=latch_edge,
        frames=len(valid),
        bits_mode=bits_mode,
        bits_mean=bits_mean,
        bits_std=bits_std,
        mode_ratio=mode_ratio,
        bit_ones_ratio=bit_ratio,
        bit_entropy=entropy,
        score=score,
    )


def probe_file(path: Path, min_frames: int) -> list[ComboScore]:
    """Probe all channel combinations for one capture."""
    samples, samplerate_hz = load_logic_capture(path)
    if samplerate_hz is None:
        samplerate_hz = 2_000_000

    # Restrict to channels with enough transitions to avoid static lines.
    transitions = {bit: channel_transitions(samples, bit) for bit in range(8)}
    active = [bit for bit in range(8) if transitions[bit] > 10]
    if len(active) < 3:
        return []

    results: list[ComboScore] = []
    for clock_bit in active:
        for data_bit in active:
            if data_bit == clock_bit:
                continue
            for latch_bit in active:
                if latch_bit == clock_bit or latch_bit == data_bit:
                    continue
                for clock_edge in ("rising", "falling"):
                    for latch_edge in ("rising", "falling"):
                        score = evaluate_combo(
                            samples=samples,
                            clock_bit=clock_bit,
                            data_bit=data_bit,
                            latch_bit=latch_bit,
                            clock_edge=clock_edge,
                            latch_edge=latch_edge,
                            min_frames=min_frames,
                        )
                        if score is not None:
                            results.append(score)

    results.sort(
        key=lambda item: (
            item.score,
            item.mode_ratio,
            item.frames,
            item.bits_mode,
        ),
        reverse=True,
    )
    return results


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    for path in args.inputs:
        if not path.exists():
            raise FileNotFoundError(path)

    for path in args.inputs:
        results = probe_file(path, min_frames=args.min_frames)
        print(f"=== 3-Wire Probe: {path.name} ===")
        if not results:
            print("No valid clock/data/latch combos found.")
            print()
            continue

        for item in results[: args.max_results]:
            print(
                "combo="
                f"clk=D{item.clock_bit}({item.clock_edge}) "
                f"data=D{item.data_bit} "
                f"latch=D{item.latch_bit}({item.latch_edge}) "
                f"score={item.score:.3f} frames={item.frames} "
                f"mode_bits={item.bits_mode} mean_bits={item.bits_mean:.2f} "
                f"std_bits={item.bits_std:.2f} mode_ratio={item.mode_ratio:.3f} "
                f"bit_ones={item.bit_ones_ratio:.3f} entropy={item.bit_entropy:.3f}"
            )

        top = results[0]
        print(
            "best_guess="
            f"clk=D{top.clock_bit} data=D{top.data_bit} latch=D{top.latch_bit} "
            f"mode_bits={top.bits_mode} mode_ratio={top.mode_ratio:.3f}"
        )
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
