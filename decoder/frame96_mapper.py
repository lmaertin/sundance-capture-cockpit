#!/usr/bin/env python3
"""Extract 96-bit frames and map discriminative bit positions per display state.

Assumed wiring model:
- clock: D7 rising edge
- latch/frame boundary: D6 rising edge
- data: D4 (main), optional D5 as second plane
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

TIME_TOKEN = re.compile(r"(?<!\d)(\d{1,2})-(\d{2})(?!\d)")
TEMP_TOKEN = re.compile(r"(?<!\d)(\d{1,2}\.\d)(?!\d)")
POOL_TOKEN = re.compile(r"pool_(\d{1,2})-(\d{1,2})", re.IGNORECASE)


@dataclass(frozen=True)
class Frame:
    """One sampled frame between two latch edges."""

    time_s: float
    bits: tuple[int, ...]


@dataclass(frozen=True)
class FileStateMap:
    """Two-state representation for one labeled file."""

    path: Path
    label_a: str
    label_b: str
    pattern_a: tuple[int, ...]
    pattern_b: tuple[int, ...]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build first-pass 96-bit state mapping from labeled captures."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input .sr files")
    parser.add_argument("--clock-bit", type=int, default=7, help="Clock bit index")
    parser.add_argument("--latch-bit", type=int, default=6, help="Latch bit index")
    parser.add_argument("--data-bit", type=int, default=4, help="Primary data bit index")
    parser.add_argument(
        "--second-data-bit",
        type=int,
        default=None,
        help="Optional second data bit index for a second plane.",
    )
    parser.add_argument(
        "--clock-edge",
        choices=("rising", "falling"),
        default="rising",
        help="Clock edge for bit sampling.",
    )
    parser.add_argument(
        "--latch-edge",
        choices=("rising", "falling"),
        default="rising",
        help="Latch edge for frame boundaries.",
    )
    parser.add_argument(
        "--expected-bits",
        type=int,
        default=96,
        help="Expected bits per frame.",
    )
    parser.add_argument(
        "--min-label-frames",
        type=int,
        default=20,
        help="Minimum number of frames per discovered state.",
    )
    return parser.parse_args()


def edge_positions(samples: bytes, bit: int, edge: str) -> list[int]:
    """Return indices for selected edge transitions."""
    if not samples:
        return []
    previous = (samples[0] >> bit) & 0x01
    positions: list[int] = []
    for index, raw in enumerate(samples[1:], start=1):
        current = (raw >> bit) & 0x01
        if edge == "rising" and previous == 0 and current == 1:
            positions.append(index)
        elif edge == "falling" and previous == 1 and current == 0:
            positions.append(index)
        previous = current
    return positions


def extract_frames(
    samples: bytes,
    samplerate_hz: int,
    clock_bit: int,
    latch_bit: int,
    data_bits: tuple[int, ...],
    clock_edge: str,
    latch_edge: str,
    expected_bits: int,
) -> list[Frame]:
    """Extract frames with exactly expected bit count."""
    latch = edge_positions(samples, latch_bit, latch_edge)
    clock = edge_positions(samples, clock_bit, clock_edge)
    if len(latch) < 2 or not clock:
        return []

    frames: list[Frame] = []
    clock_index = 0
    for start, end in zip(latch, latch[1:]):
        while clock_index < len(clock) and clock[clock_index] <= start:
            clock_index += 1

        local_index = clock_index
        bits: list[int] = []
        while local_index < len(clock) and clock[local_index] <= end:
            raw = samples[clock[local_index]]
            value = 0
            for bit in data_bits:
                value = (value << 1) | ((raw >> bit) & 0x01)
            bits.append(value)
            local_index += 1

        if len(bits) != expected_bits:
            continue

        center = (start + end) / 2.0
        frames.append(Frame(time_s=center / float(samplerate_hz), bits=tuple(bits)))

    return frames


def filename_labels(path: Path) -> list[str]:
    """Extract ordered labels from filename."""
    stem = path.stem
    pool = POOL_TOKEN.search(stem)
    if pool is not None:
        return [f"{int(pool.group(1))}.0C", f"{int(pool.group(2))}.0C"]

    entries: list[tuple[int, str]] = []

    for match in TEMP_TOKEN.finditer(stem):
        entries.append((match.start(), f"{match.group(1)}C"))

    for match in TIME_TOKEN.finditer(stem):
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour <= 23 and minute <= 59:
            entries.append((match.start(), f"{hour}:{minute:02d}"))

    entries.sort(key=lambda item: item[0])
    labels = [value for _, value in entries]

    unique: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label in seen:
            continue
        seen.add(label)
        unique.append(label)
    return unique[:2]


def two_main_patterns(frames: list[Frame], min_count: int) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    """Return two most common patterns when both are represented."""
    counts = Counter(frame.bits for frame in frames)
    top = counts.most_common(2)
    if len(top) < 2:
        return None
    if top[0][1] < min_count or top[1][1] < min_count:
        return None
    return top[0][0], top[1][0]


def diff_positions(left: tuple[int, ...], right: tuple[int, ...]) -> list[int]:
    """Return bit indices that differ between two patterns."""
    return [index for index, (a, b) in enumerate(zip(left, right)) if a != b]


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    for path in args.inputs:
        if not path.exists():
            raise FileNotFoundError(path)

    data_bits = (args.data_bit,) if args.second_data_bit is None else (args.data_bit, args.second_data_bit)

    state_maps: list[FileStateMap] = []
    for path in args.inputs:
        labels = filename_labels(path)
        if len(labels) < 2:
            print(f"skip {path.name}: less than 2 labels in filename")
            continue

        samples, samplerate_hz = load_logic_capture(path)
        if samplerate_hz is None:
            samplerate_hz = 2_000_000

        frames = extract_frames(
            samples=samples,
            samplerate_hz=samplerate_hz,
            clock_bit=args.clock_bit,
            latch_bit=args.latch_bit,
            data_bits=data_bits,
            clock_edge=args.clock_edge,
            latch_edge=args.latch_edge,
            expected_bits=args.expected_bits,
        )
        if not frames:
            print(f"skip {path.name}: no frames with {args.expected_bits} bits")
            continue

        pair = two_main_patterns(frames, min_count=args.min_label_frames)
        if pair is None:
            print(f"skip {path.name}: no two dominant patterns above threshold")
            continue

        state_maps.append(
            FileStateMap(
                path=path,
                label_a=labels[0],
                label_b=labels[1],
                pattern_a=pair[0],
                pattern_b=pair[1],
            )
        )

        diffs = diff_positions(pair[0], pair[1])
        print(f"=== {path.name} ===")
        print(
            f"labels={labels[0]} vs {labels[1]} frames={len(frames)} "
            f"diff_bits={len(diffs)}"
        )
        print("diff_positions=" + ",".join(str(index) for index in diffs[:80]))
        if len(diffs) > 80:
            print("diff_positions_truncated=true")
        print()

    if len(state_maps) < 2:
        print("Need at least two mapped files for cross-file intersection.")
        return 0

    # Cross-file intersection of state-difference positions.
    intersections: set[int] | None = None
    per_file: dict[str, set[int]] = {}
    for item in state_maps:
        diffs = set(diff_positions(item.pattern_a, item.pattern_b))
        per_file[item.path.name] = diffs
        if intersections is None:
            intersections = set(diffs)
        else:
            intersections &= diffs

    common = sorted(intersections or set())
    print("=== Cross-File Common Diff Bits ===")
    print("files=" + ",".join(item.path.name for item in state_maps))
    print(f"common_diff_count={len(common)}")
    print("common_diff_positions=" + ",".join(str(index) for index in common))

    # Print a compact bit-state table for common positions.
    if common:
        print()
        print("=== Common Bit State Table ===")
        header = "bit " + " ".join(
            f"{item.path.name}:{item.label_a}/{item.label_b}" for item in state_maps
        )
        print(header)
        for bit_index in common:
            cells: list[str] = []
            for item in state_maps:
                cells.append(f"{item.pattern_a[bit_index]}->{item.pattern_b[bit_index]}")
            print(f"{bit_index:3d} " + " ".join(cells))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
