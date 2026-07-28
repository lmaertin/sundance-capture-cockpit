#!/usr/bin/env python3
"""Decode display states using learned 96-bit signature subsets.

The decoder learns state signatures from labeled captures (filename tokens) and
applies nearest-signature matching to a target capture.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import load_logic_capture
from decoder.frame96_mapper import extract_frames, filename_labels

TEMP_TOKEN = re.compile(r"^\d{1,2}\.\dC$")


@dataclass(frozen=True)
class Signature:
    """Label signature on selected bit positions."""

    label: str
    values: tuple[int, ...]


@dataclass(frozen=True)
class Run:
    """One decoded stable run."""

    label: str
    start_s: float
    end_s: float
    frames: int
    confidence: float


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Decode states from 96-bit signatures.")
    parser.add_argument(
        "--train",
        nargs="+",
        type=Path,
        required=True,
        help="Labeled training captures.",
    )
    parser.add_argument("--predict", type=Path, required=True, help="Target capture.")
    parser.add_argument("--clock-bit", type=int, default=7)
    parser.add_argument("--latch-bit", type=int, default=6)
    parser.add_argument("--data-bit", type=int, default=4)
    parser.add_argument("--clock-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--latch-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--expected-bits", type=int, default=96)
    parser.add_argument("--min-frames", type=int, default=20)
    parser.add_argument("--smooth", type=int, default=8, help="Majority smooth window radius.")
    parser.add_argument(
        "--min-run-frames",
        type=int,
        default=8,
        help="Minimum run length after smoothing; shorter runs are suppressed.",
    )
    parser.add_argument(
        "--only-temp",
        action="store_true",
        help="Only report labels in temperature-like xx.yC format.",
    )
    return parser.parse_args()


def signature_from_bits(bits: tuple[int, ...], positions: list[int]) -> tuple[int, ...]:
    """Project full bit frame onto selected positions."""
    return tuple(bits[index] for index in positions)


def top_two_patterns(frames_bits: list[tuple[int, ...]], min_frames: int) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    """Return top two frame patterns with count threshold."""
    counts = Counter(frames_bits)
    top = counts.most_common(2)
    if len(top) < 2:
        return None
    if top[0][1] < min_frames or top[1][1] < min_frames:
        return None
    return top[0][0], top[1][0]


def hamming(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    """Return Hamming distance for equal-length tuples."""
    return sum(1 for a, b in zip(left, right) if a != b)


def majority_smooth(labels: list[str], radius: int) -> list[str]:
    """Apply majority smoothing over labels."""
    result: list[str] = []
    for index in range(len(labels)):
        start = max(0, index - radius)
        end = min(len(labels), index + radius + 1)
        result.append(Counter(labels[start:end]).most_common(1)[0][0])
    return result


def compress_runs(labels: list[str], times: list[float]) -> list[Run]:
    """Compress frame labels into runs with confidence proxy."""
    if not labels:
        return []

    runs: list[Run] = []
    start = 0
    current = labels[0]
    for index, value in enumerate(labels[1:], start=1):
        if value == current:
            continue
        width = index - start
        start_s = times[start]
        end_s = times[index - 1]
        runs.append(Run(label=current, start_s=start_s, end_s=end_s, frames=width, confidence=1.0))
        start = index
        current = value

    width = len(labels) - start
    runs.append(
        Run(
            label=current,
            start_s=times[start],
            end_s=times[-1],
            frames=width,
            confidence=1.0,
        )
    )
    return runs


def suppress_short_runs(labels: list[str], min_run_frames: int) -> list[str]:
    """Replace short isolated runs by neighboring labels."""
    if min_run_frames <= 1 or not labels:
        return labels

    current = list(labels)
    changed = True
    while changed:
        changed = False
        runs: list[tuple[int, int, str]] = []
        start = 0
        value = current[0]
        for index, item in enumerate(current[1:], start=1):
            if item == value:
                continue
            runs.append((start, index - 1, value))
            start = index
            value = item
        runs.append((start, len(current) - 1, value))

        for run_index, (run_start, run_end, run_value) in enumerate(runs):
            width = run_end - run_start + 1
            if width >= min_run_frames:
                continue

            left_value = runs[run_index - 1][2] if run_index > 0 else None
            right_value = runs[run_index + 1][2] if run_index + 1 < len(runs) else None

            replacement = None
            if left_value is not None and right_value is not None:
                replacement = left_value if left_value == right_value else right_value
            elif left_value is not None:
                replacement = left_value
            elif right_value is not None:
                replacement = right_value

            if replacement is None or replacement == run_value:
                continue

            for index in range(run_start, run_end + 1):
                current[index] = replacement
            changed = True

        if not changed:
            break

    return current


def main() -> int:
    """CLI entry point."""
    args = parse_args()

    for path in args.train + [args.predict]:
        if not path.exists():
            raise FileNotFoundError(path)

    train_maps: list[tuple[str, tuple[int, ...], tuple[int, ...]]] = []
    diff_intersection: set[int] | None = None

    for path in args.train:
        labels = filename_labels(path)
        if len(labels) < 2:
            continue

        samples, samplerate_hz = load_logic_capture(path)
        if samplerate_hz is None:
            samplerate_hz = 2_000_000

        frames = extract_frames(
            samples=samples,
            samplerate_hz=samplerate_hz,
            clock_bit=args.clock_bit,
            latch_bit=args.latch_bit,
            data_bits=(args.data_bit,),
            clock_edge=args.clock_edge,
            latch_edge=args.latch_edge,
            expected_bits=args.expected_bits,
        )
        if len(frames) < args.min_frames * 2:
            continue

        bits_only = [frame.bits for frame in frames]
        pair = top_two_patterns(bits_only, args.min_frames)
        if pair is None:
            continue

        # Order by first appearance in stream, then map to filename label order.
        first_index = bits_only.index(pair[0])
        second_index = bits_only.index(pair[1])
        if first_index <= second_index:
            pattern_a, pattern_b = pair[0], pair[1]
        else:
            pattern_a, pattern_b = pair[1], pair[0]

        train_maps.append((labels[0], pattern_a, pattern_b))
        train_maps.append((labels[1], pattern_b, pattern_a))

        diffs = {i for i, (a, b) in enumerate(zip(pattern_a, pattern_b)) if a != b}
        if diff_intersection is None:
            diff_intersection = set(diffs)
        else:
            diff_intersection &= diffs

    if not train_maps or diff_intersection is None:
        print("No valid training maps generated.")
        return 1

    positions = sorted(diff_intersection)
    signatures: list[Signature] = []
    seen: set[tuple[str, tuple[int, ...]]] = set()
    for label, pattern, _other in train_maps:
        projected = signature_from_bits(pattern, positions)
        key = (label, projected)
        if key in seen:
            continue
        seen.add(key)
        signatures.append(Signature(label=label, values=projected))

    samples, samplerate_hz = load_logic_capture(args.predict)
    if samplerate_hz is None:
        samplerate_hz = 2_000_000

    frames = extract_frames(
        samples=samples,
        samplerate_hz=samplerate_hz,
        clock_bit=args.clock_bit,
        latch_bit=args.latch_bit,
        data_bits=(args.data_bit,),
        clock_edge=args.clock_edge,
        latch_edge=args.latch_edge,
        expected_bits=args.expected_bits,
    )
    if not frames:
        print("No 96-bit frames found in predict capture.")
        return 2

    labels: list[str] = []
    times: list[float] = []
    for frame in frames:
        projected = signature_from_bits(frame.bits, positions)
        ranked: list[tuple[int, str]] = []
        for signature in signatures:
            ranked.append((hamming(projected, signature.values), signature.label))
        ranked.sort(key=lambda item: item[0])
        labels.append(ranked[0][1])
        times.append(frame.time_s)

    smoothed = majority_smooth(labels, args.smooth)
    stabilized = suppress_short_runs(smoothed, args.min_run_frames)
    runs = compress_runs(stabilized, times)

    print("=== Frame96 State Decoder ===")
    print(f"predict={args.predict.name} frames={len(frames)}")
    print("selected_positions=" + ",".join(str(item) for item in positions))
    print("runs:")
    for run in runs:
        if args.only_temp and not TEMP_TOKEN.match(run.label):
            continue
        duration = max(0.0, run.end_s - run.start_s)
        print(
            f"  {run.label} t=[{run.start_s:.3f},{run.end_s:.3f}] "
            f"dur~{duration:.3f}s frames={run.frames}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
