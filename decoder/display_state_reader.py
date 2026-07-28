#!/usr/bin/env python3
"""Read two alternating display states from one Sigrok capture.

This tool is intended for captures where the panel toggles between two major
screen contents (for example temperature and time). It builds stable runs from
burst-level signatures and maps the two dominant states to user-provided names.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import parse_data_bits
from decoder.swap_state_timeline import (
    StableRun,
    build_stable_runs,
    hamming,
    load_bursts,
    smooth_labels,
)


@dataclass(frozen=True)
class NamedRun:
    """One stable run with mapped human-readable state name."""

    name: str
    start_time_s: float
    end_time_s: float
    width: int


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Map two dominant display states in one capture to names."
    )
    parser.add_argument("input", type=Path, help="Input .sr file")
    parser.add_argument(
        "--state-names",
        default="29.9C,12:45",
        help="Comma-separated names for state A and B in first-appearance order.",
    )
    parser.add_argument(
        "--clock-bit",
        type=int,
        default=7,
        help="Clock bit index (default: 7).",
    )
    parser.add_argument(
        "--gate-bit",
        type=int,
        default=6,
        help="Gate bit index (default: 6).",
    )
    parser.add_argument(
        "--gate-active",
        type=int,
        choices=(0, 1),
        default=0,
        help="Gate active level (default: 0).",
    )
    parser.add_argument(
        "--data-bits",
        default="5,7",
        help="Comma-separated data bit indices (default: 5,7).",
    )
    parser.add_argument(
        "--symbols-per-burst",
        type=int,
        default=192,
        help="Expected symbol count per burst (default: 192).",
    )
    parser.add_argument(
        "--top-prototypes",
        type=int,
        default=8,
        help="Number of dominant signatures used as prototypes.",
    )
    parser.add_argument(
        "--smooth-radius",
        type=int,
        default=5,
        help="Half-window for majority smoothing.",
    )
    parser.add_argument(
        "--min-stable-width",
        type=int,
        default=18,
        help="Minimum burst count for a stable run.",
    )
    return parser.parse_args()


def parse_state_names(spec: str) -> tuple[str, str]:
    """Parse exactly two state names."""
    parts = [item.strip() for item in spec.split(",") if item.strip()]
    if len(parts) != 2:
        raise ValueError("--state-names must contain exactly two names")
    return parts[0], parts[1]


def dominant_two_labels(runs: list[StableRun]) -> tuple[int, int] | None:
    """Return the two dominant stable labels by accumulated run width."""
    if not runs:
        return None

    widths: Counter[int] = Counter()
    for run in runs:
        widths[run.label] += run.width

    top = widths.most_common(2)
    if len(top) < 2:
        return None
    return top[0][0], top[1][0]


def first_appearance_order(runs: list[StableRun], left: int, right: int) -> tuple[int, int]:
    """Order two labels by first appearance in the stable run list."""
    for run in runs:
        if run.label == left:
            return left, right
        if run.label == right:
            return right, left
    return left, right


def map_runs_to_names(
    runs: list[StableRun],
    label_a: int,
    label_b: int,
    name_a: str,
    name_b: str,
) -> list[NamedRun]:
    """Map stable runs to two named states and ignore short transient labels."""
    mapped: list[NamedRun] = []
    for run in runs:
        if run.label == label_a:
            mapped.append(
                NamedRun(
                    name=name_a,
                    start_time_s=run.start_time_s,
                    end_time_s=run.end_time_s,
                    width=run.width,
                )
            )
        elif run.label == label_b:
            mapped.append(
                NamedRun(
                    name=name_b,
                    start_time_s=run.start_time_s,
                    end_time_s=run.end_time_s,
                    width=run.width,
                )
            )
    return mapped


def build_labels(
    bursts: list[tuple[int, ...]],
    top_prototypes: int,
) -> list[int]:
    """Assign each burst to the nearest prototype label."""
    counts = Counter(bursts)
    prototypes = [signature for signature, _ in counts.most_common(top_prototypes)]
    labels: list[int] = []
    for burst in bursts:
        distances = [hamming(burst, prototype) for prototype in prototypes]
        best_label = min(range(len(distances)), key=lambda index: distances[index])
        labels.append(best_label)
    return labels


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)

    state_a_name, state_b_name = parse_state_names(args.state_names)
    data_bits = parse_data_bits(args.data_bits)
    bursts, times, samplerate_hz = load_bursts(
        path=args.input,
        clock_bit=args.clock_bit,
        gate_bit=args.gate_bit,
        gate_active=args.gate_active,
        data_bits=data_bits,
        symbols_per_burst=args.symbols_per_burst,
    )
    if not bursts:
        print("No usable bursts found.")
        return 1

    raw_labels = build_labels(bursts=bursts, top_prototypes=args.top_prototypes)
    smoothed = smooth_labels(raw_labels, args.smooth_radius)
    stable_runs = build_stable_runs(smoothed, times, args.min_stable_width)

    dominant = dominant_two_labels(stable_runs)
    if dominant is None:
        print("Could not identify two dominant stable states.")
        return 2

    first_label, second_label = first_appearance_order(
        stable_runs,
        dominant[0],
        dominant[1],
    )
    named_runs = map_runs_to_names(
        runs=stable_runs,
        label_a=first_label,
        label_b=second_label,
        name_a=state_a_name,
        name_b=state_b_name,
    )

    if not named_runs:
        print("No named stable runs after filtering transients.")
        return 3

    print("=== Display State Reader ===")
    print(
        f"file={args.input.name} samplerate={samplerate_hz}Hz "
        f"usable_bursts={len(bursts)} data={','.join(f'D{bit}' for bit in data_bits)}"
    )
    print(
        f"state_map: label{first_label}->{state_a_name}, "
        f"label{second_label}->{state_b_name}"
    )
    print("runs:")
    for index, run in enumerate(named_runs, start=1):
        duration = max(0.0, run.end_time_s - run.start_time_s)
        print(
            f"  run{index}: {run.name} "
            f"t=[{run.start_time_s:.3f},{run.end_time_s:.3f}] "
            f"dur~{duration:.3f}s width={run.width}"
        )

    print("transitions:")
    last_name = named_runs[0].name
    for run in named_runs[1:]:
        if run.name != last_name:
            print(f"  {last_name} -> {run.name} at {run.start_time_s:.3f}s")
        last_name = run.name

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
