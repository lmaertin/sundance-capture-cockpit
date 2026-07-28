"""Report slot-wise symbol differences across aligned boot phases.

This tool builds on the boot alignment logic and aggregates symbol streams into
one scan period, making it easier to identify segment-related slot changes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import (
    CaptureSymbols,
    LagResult,
    best_lag,
    common_reference_range,
    extract_symbols,
    load_logic_samples,
    parse_data_bits,
    select_change_points,
)


@dataclass(frozen=True)
class SlotPhaseSummary:
    """Dominant slot value and confidence for one phase."""

    dominant: int
    confidence: float
    counts: tuple[int, ...]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate aligned boot captures into scan slots and report phase "
            "differences."
        )
    )
    parser.add_argument("inputs", nargs="+", help="Input .sr files")
    parser.add_argument(
        "--clock-bit",
        type=int,
        default=7,
        help="Clock channel bit index (default: 7 for D7).",
    )
    parser.add_argument(
        "--data-bits",
        default="4,5",
        help="Comma-separated data channel bit indices (default: 4,5).",
    )
    parser.add_argument(
        "--edge",
        choices=("rising", "falling"),
        default="rising",
        help="Clock edge used for sampling symbols.",
    )
    parser.add_argument(
        "--max-lag",
        type=int,
        default=6000,
        help="Maximum lag (in symbols) to scan for alignment.",
    )
    parser.add_argument(
        "--align-window",
        type=int,
        default=45000,
        help="Maximum symbols used for lag estimation.",
    )
    parser.add_argument(
        "--phases",
        type=int,
        default=4,
        help="Number of boot phases to segment (default: 4).",
    )
    parser.add_argument(
        "--change-window",
        type=int,
        default=1200,
        help="Half-window in symbols for change-point scoring.",
    )
    parser.add_argument(
        "--min-gap",
        type=int,
        default=6000,
        help="Minimum gap between phase boundaries.",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=192,
        help="Assumed scan period in symbols (default: 192).",
    )
    parser.add_argument(
        "--compare-phases",
        default="2,4",
        help="Two 1-based phase indices to compare, e.g. 2,4.",
    )
    parser.add_argument(
        "--top-slots",
        type=int,
        default=24,
        help="Maximum number of changed slots to print.",
    )
    return parser.parse_args()


def parse_compare_phases(spec: str, max_phases: int) -> tuple[int, int]:
    """Parse two 1-based phase indices."""
    parts = [int(item.strip()) for item in spec.split(",") if item.strip()]
    if len(parts) != 2:
        raise ValueError("--compare-phases must contain exactly two values.")
    if any(item < 1 or item > max_phases for item in parts):
        raise ValueError("--compare-phases values are out of range.")
    return parts[0] - 1, parts[1] - 1


def dominant_summary(counter: Counter[int], alphabet_size: int) -> SlotPhaseSummary:
    """Return dominant slot value, confidence, and full counts."""
    if not counter:
        return SlotPhaseSummary(dominant=-1, confidence=0.0, counts=tuple(0 for _ in range(alphabet_size)))

    counts = tuple(counter.get(symbol, 0) for symbol in range(alphabet_size))
    dominant, dominant_count = counter.most_common(1)[0]
    total = sum(counts)
    confidence = dominant_count / total if total else 0.0
    return SlotPhaseSummary(dominant=dominant, confidence=confidence, counts=counts)


def build_captures(
    input_paths: tuple[Path, ...],
    clock_bit: int,
    data_bits: tuple[int, ...],
    edge: str,
) -> tuple[CaptureSymbols, ...]:
    """Load all captures and extract their symbol streams."""
    captures: list[CaptureSymbols] = []
    for path in input_paths:
        samples = load_logic_samples(path)
        symbols = extract_symbols(samples, clock_bit, data_bits, edge)
        captures.append(CaptureSymbols(path=path, symbols=symbols))
    return tuple(captures)


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    input_paths = tuple(Path(item) for item in args.inputs)
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(path)

    data_bits = parse_data_bits(args.data_bits)
    alphabet_size = 1 << len(data_bits)
    captures = build_captures(input_paths, args.clock_bit, data_bits, args.edge)
    reference = captures[0]

    lag_map: dict[Path, LagResult] = {
        reference.path: LagResult(
            lag=0,
            score=1.0,
            compared=min(len(reference.symbols), args.align_window),
        )
    }
    for capture in captures[1:]:
        lag_map[capture.path] = best_lag(
            reference.symbols,
            capture.symbols,
            max_lag=args.max_lag,
            align_window=args.align_window,
        )

    common_start, common_end = common_reference_range(captures, lag_map)
    reference_common = reference.symbols[common_start:common_end]
    boundaries = select_change_points(
        reference_common,
        phases=args.phases,
        window=args.change_window,
        min_gap=args.min_gap,
        alphabet_size=alphabet_size,
    )
    phase_points = (0, *boundaries, len(reference_common))
    left_phase, right_phase = parse_compare_phases(args.compare_phases, len(phase_points) - 1)

    phase_slot_counts: list[list[Counter[int]]] = []
    for _ in range(len(phase_points) - 1):
        phase_slot_counts.append([Counter() for _ in range(args.period)])

    for capture in captures:
        lag = lag_map[capture.path].lag
        aligned = capture.symbols[common_start + lag : common_end + lag]
        for phase_index, (start, end) in enumerate(zip(phase_points, phase_points[1:])):
            phase_segment = aligned[start:end]
            for index, symbol in enumerate(phase_segment):
                slot = index % args.period
                phase_slot_counts[phase_index][slot][symbol] += 1

    print("=== Slot Diff Summary ===")
    print(
        f"reference={reference.path.name} period={args.period} "
        f"compare_phases={left_phase + 1}->{right_phase + 1}"
    )
    print(f"common_range=[{common_start}, {common_end}) boundaries={list(boundaries)}")
    print()

    changed_rows: list[tuple[float, int, SlotPhaseSummary, SlotPhaseSummary]] = []
    for slot in range(args.period):
        left_summary = dominant_summary(phase_slot_counts[left_phase][slot], alphabet_size)
        right_summary = dominant_summary(phase_slot_counts[right_phase][slot], alphabet_size)
        if left_summary.dominant < 0 or right_summary.dominant < 0:
            continue
        if left_summary.dominant == right_summary.dominant:
            continue
        score = (left_summary.confidence + right_summary.confidence) / 2.0
        changed_rows.append((score, slot, left_summary, right_summary))

    changed_rows.sort(reverse=True)
    if not changed_rows:
        print("No dominant slot changes found between the selected phases.")
        return 0

    print("Top changed slots:")
    for score, slot, left_summary, right_summary in changed_rows[: args.top_slots]:
        print(
            f"slot={slot:3d} score={score:.3f} "
            f"phase{left_phase + 1}={left_summary.dominant} "
            f"phase{right_phase + 1}={right_summary.dominant} "
            f"conf=({left_summary.confidence:.3f},{right_summary.confidence:.3f}) "
            f"counts_left={left_summary.counts} counts_right={right_summary.counts}"
        )

    print()
    print("Changed slot runs:")
    changed_slots = sorted(slot for _, slot, _, _ in changed_rows)
    run_start = changed_slots[0]
    run_end = changed_slots[0]
    for slot in changed_slots[1:]:
        if slot <= run_end + 2:
            run_end = slot
            continue
        print(f"[{run_start}, {run_end}]")
        run_start = slot
        run_end = slot
    print(f"[{run_start}, {run_end}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())