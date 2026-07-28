#!/usr/bin/env python3
"""Decode Sundance panel frames using a 96-bit latched scan model.

Protocol model (empirical):
- Clock: D7 rising edge
- Latch/Frame boundary: D6 rising edge
- Frame width: 96 sampled symbols
- Data plane: D4 (primary), optional D5 secondary plane

This is not standard I2C/SPI/UART traffic. It behaves like a proprietary
latched scan-bus for panel/display state transfer.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import load_logic_capture
from decoder.frame96_mapper import edge_positions


PROTOCOL_NAME = "Sundance Panel96 Latched Scan"
PROTOCOL_SHORT = "panel96-latched"


@dataclass(frozen=True)
class PanelFrame:
    """One decoded 96-bit panel frame."""

    time_s: float
    d4_bits: tuple[int, ...]
    d5_bits: tuple[int, ...] | None


@dataclass(frozen=True)
class StableRun:
    """One stable frame-signature run."""

    label: str
    start_s: float
    end_s: float
    frames: int


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Decode proprietary Sundance panel96 latched scan frames."
    )
    parser.add_argument("input", type=Path, help="Input .sr capture")
    parser.add_argument("--clock-bit", type=int, default=7)
    parser.add_argument("--latch-bit", type=int, default=6)
    parser.add_argument("--data-bit", type=int, default=4)
    parser.add_argument("--data-bit-2", type=int, default=5)
    parser.add_argument("--clock-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--latch-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--frame-bits", type=int, default=96)
    parser.add_argument(
        "--min-run-frames",
        type=int,
        default=10,
        help="Minimum run size for stable state output.",
    )
    parser.add_argument(
        "--show-top-signatures",
        type=int,
        default=8,
        help="How many dominant signatures to print.",
    )
    return parser.parse_args()


def sample_bits(raw: int, bits: tuple[int, ...]) -> int:
    """Sample and pack selected bit lines into one symbol."""
    value = 0
    for bit in bits:
        value = (value << 1) | ((raw >> bit) & 0x01)
    return value


def decode_frames(
    samples: bytes,
    samplerate_hz: int,
    clock_bit: int,
    latch_bit: int,
    data_bit: int,
    data_bit_2: int | None,
    clock_edge: str,
    latch_edge: str,
    frame_bits: int,
) -> list[PanelFrame]:
    """Decode capture into fixed-size panel frames."""
    latch = edge_positions(samples, latch_bit, latch_edge)
    clock = edge_positions(samples, clock_bit, clock_edge)
    if len(latch) < 2 or not clock:
        return []

    frames: list[PanelFrame] = []
    clock_index = 0
    for start, end in zip(latch, latch[1:]):
        while clock_index < len(clock) and clock[clock_index] <= start:
            clock_index += 1

        local_index = clock_index
        d4_list: list[int] = []
        d5_list: list[int] = []
        while local_index < len(clock) and clock[local_index] <= end:
            sample_index = clock[local_index]
            raw = samples[sample_index]
            d4_list.append(sample_bits(raw, (data_bit,)))
            if data_bit_2 is not None:
                d5_list.append(sample_bits(raw, (data_bit_2,)))
            local_index += 1

        if len(d4_list) != frame_bits:
            continue

        center = (start + end) / 2.0
        frames.append(
            PanelFrame(
                time_s=center / float(samplerate_hz),
                d4_bits=tuple(d4_list),
                d5_bits=tuple(d5_list) if data_bit_2 is not None else None,
            )
        )
    return frames


def majority_smooth(labels: list[str], radius: int = 8) -> list[str]:
    """Apply simple majority smoothing to frame labels."""
    if not labels:
        return labels
    output: list[str] = []
    for index in range(len(labels)):
        start = max(0, index - radius)
        end = min(len(labels), index + radius + 1)
        output.append(Counter(labels[start:end]).most_common(1)[0][0])
    return output


def compress_runs(labels: list[str], times: list[float], min_frames: int) -> list[StableRun]:
    """Compress smoothed labels into stable runs."""
    if not labels:
        return []

    runs: list[StableRun] = []
    start = 0
    current = labels[0]
    for index, label in enumerate(labels[1:], start=1):
        if label == current:
            continue
        width = index - start
        if width >= min_frames:
            runs.append(
                StableRun(
                    label=current,
                    start_s=times[start],
                    end_s=times[index - 1],
                    frames=width,
                )
            )
        start = index
        current = label

    width = len(labels) - start
    if width >= min_frames:
        runs.append(
            StableRun(
                label=current,
                start_s=times[start],
                end_s=times[-1],
                frames=width,
            )
        )
    return runs


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)

    samples, samplerate_hz = load_logic_capture(args.input)
    if samplerate_hz is None:
        samplerate_hz = 2_000_000

    frames = decode_frames(
        samples=samples,
        samplerate_hz=samplerate_hz,
        clock_bit=args.clock_bit,
        latch_bit=args.latch_bit,
        data_bit=args.data_bit,
        data_bit_2=args.data_bit_2,
        clock_edge=args.clock_edge,
        latch_edge=args.latch_edge,
        frame_bits=args.frame_bits,
    )

    print("=== Panel96 Decoder ===")
    print(f"protocol={PROTOCOL_NAME} ({PROTOCOL_SHORT})")
    print(f"file={args.input.name} samplerate={samplerate_hz}Hz")
    print(
        f"wiring=clk:D{args.clock_bit}({args.clock_edge}) "
        f"latch:D{args.latch_bit}({args.latch_edge}) "
        f"data:D{args.data_bit}" + (f",D{args.data_bit_2}" if args.data_bit_2 is not None else "")
    )

    if not frames:
        print("frames=0 (no valid fixed-size frames found)")
        return 1

    d4_counts = Counter(frame.d4_bits for frame in frames)
    print(f"frames={len(frames)} valid_frame_bits={args.frame_bits}")
    print("top_signatures_d4:")
    for index, (signature, count) in enumerate(d4_counts.most_common(args.show_top_signatures), start=1):
        prefix = "".join(str(bit) for bit in signature[:24])
        print(f"  s{index}: count={count} prefix24={prefix}")

    # Convert dominant signatures to symbolic state labels.
    prototypes = [sig for sig, _ in d4_counts.most_common(args.show_top_signatures)]
    raw_labels: list[str] = []
    times: list[float] = []
    for frame in frames:
        best = min(
            range(len(prototypes)),
            key=lambda idx: sum(
                1 for a, b in zip(frame.d4_bits, prototypes[idx]) if a != b
            ),
        )
        raw_labels.append(f"S{best}")
        times.append(frame.time_s)

    smoothed = majority_smooth(raw_labels, radius=8)
    runs = compress_runs(smoothed, times, min_frames=args.min_run_frames)

    print("stable_runs:")
    if not runs:
        print("  none")
    else:
        for run in runs:
            duration = max(0.0, run.end_s - run.start_s)
            print(
                f"  {run.label} t=[{run.start_s:.3f},{run.end_s:.3f}] "
                f"dur~{duration:.3f}s frames={run.frames}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
