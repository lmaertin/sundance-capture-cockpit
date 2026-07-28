#!/usr/bin/env python3
"""Build a slot-level mapping hypothesis for Sundance boot captures.

The tool uses fixed time windows with known display values and computes
slot-wise symbol dominance for each state. It then compares all state pairs,
reports stable changed-slot intersections across captures, and summarizes
slot-role candidates for digit mapping.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import extract_symbols, load_logic_capture


@dataclass(frozen=True)
class TimeWindow:
    """One labeled display state within capture time."""

    label: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class SlotDominant:
    """Dominant value information for one slot in one state."""

    value: int
    confidence: float
    counts: tuple[int, ...]


@dataclass(frozen=True)
class PairChange:
    """One slot change between two states."""

    slot: int
    score: float
    left_value: int
    right_value: int


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Compute slot-level mapping candidates from known display windows "
            "in boot captures."
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
        help="Clock edge for symbol extraction.",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=192,
        help="Assumed scan period in symbols (default: 192).",
    )
    parser.add_argument(
        "--window",
        action="append",
        default=[],
        help=(
            "State window as label:start-end in seconds, e.g. "
            "31.4C:4.25-5.75. Can be repeated."
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=12,
        help="Top N rows per comparison and ranking output.",
    )
    return parser.parse_args()


def parse_data_bits(spec: str) -> tuple[int, ...]:
    """Parse comma-separated data bit list."""
    values = tuple(int(item.strip()) for item in spec.split(",") if item.strip())
    if not values:
        raise ValueError("--data-bits must contain at least one bit index.")
    if any(item < 0 or item > 7 for item in values):
        raise ValueError("--data-bits supports only indices 0..7.")
    return values


def parse_window(spec: str) -> TimeWindow:
    """Parse one window spec label:start-end."""
    if ":" not in spec:
        raise ValueError(f"Invalid --window format: {spec!r}")
    label, range_spec = spec.split(":", maxsplit=1)
    if "-" not in range_spec:
        raise ValueError(f"Invalid --window range: {spec!r}")
    start_text, end_text = range_spec.split("-", maxsplit=1)
    start_s = float(start_text)
    end_s = float(end_text)
    if end_s <= start_s:
        raise ValueError(f"Window end must be larger than start: {spec!r}")
    return TimeWindow(label=label, start_s=start_s, end_s=end_s)


def windows_from_args(specs: list[str]) -> tuple[TimeWindow, ...]:
    """Parse all window specs and keep original order."""
    if not specs:
        return (
            TimeWindow("40.0C", 2.00, 2.50),
            TimeWindow("34.2C", 3.75, 4.25),
            TimeWindow("31.4C", 4.25, 5.75),
            TimeWindow("31.3C", 6.00, 7.25),
        )
    return tuple(parse_window(item) for item in specs)


def dominant(counter: Counter[int], alphabet_size: int) -> SlotDominant:
    """Return dominant slot value, confidence and full counts."""
    if not counter:
        return SlotDominant(
            value=-1,
            confidence=0.0,
            counts=tuple(0 for _ in range(alphabet_size)),
        )
    counts = tuple(counter.get(index, 0) for index in range(alphabet_size))
    top_value, top_count = counter.most_common(1)[0]
    total = sum(counts)
    confidence = top_count / total if total else 0.0
    return SlotDominant(value=top_value, confidence=confidence, counts=counts)


def scan_runs(slots: Iterable[int], max_gap: int = 2) -> tuple[tuple[int, int], ...]:
    """Compact slot indices into contiguous runs."""
    sorted_slots = sorted(set(slots))
    if not sorted_slots:
        return tuple()

    runs: list[tuple[int, int]] = []
    start = sorted_slots[0]
    end = sorted_slots[0]
    for slot in sorted_slots[1:]:
        if slot <= end + max_gap:
            end = slot
            continue
        runs.append((start, end))
        start = slot
        end = slot
    runs.append((start, end))
    return tuple(runs)


def state_slot_dominants(
    symbols: tuple[int, ...],
    windows: tuple[TimeWindow, ...],
    period: int,
    symbol_rate: float,
    alphabet_size: int,
) -> dict[str, tuple[SlotDominant, ...]]:
    """Compute dominant slot values for each labeled time window."""
    by_state: dict[str, tuple[SlotDominant, ...]] = {}
    for window in windows:
        start = int(round(window.start_s * symbol_rate))
        end = int(round(window.end_s * symbol_rate))
        counters = [Counter() for _ in range(period)]
        for index, symbol in enumerate(symbols[start:end]):
            counters[index % period][symbol] += 1
        by_state[window.label] = tuple(
            dominant(counter, alphabet_size) for counter in counters
        )
    return by_state


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    data_bits = parse_data_bits(args.data_bits)
    alphabet_size = 1 << len(data_bits)
    windows = windows_from_args(args.window)

    paths = tuple(Path(item) for item in args.inputs)
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)

    per_capture: dict[str, dict[str, tuple[SlotDominant, ...]]] = {}
    print("=== Capture State Extraction ===")
    for path in paths:
        samples, samplerate_hz = load_logic_capture(path)
        symbols = extract_symbols(samples, args.clock_bit, data_bits, args.edge)
        effective_samplerate = samplerate_hz if samplerate_hz is not None else 2_000_000
        duration_s = len(samples) / float(effective_samplerate)
        symbol_rate = len(symbols) / duration_s if duration_s > 0.0 else 0.0
        per_capture[path.name] = state_slot_dominants(
            symbols=symbols,
            windows=windows,
            period=args.period,
            symbol_rate=symbol_rate,
            alphabet_size=alphabet_size,
        )
        print(
            f"{path.name}: samples={len(samples)} symbols={len(symbols)} "
            f"samplerate={effective_samplerate}Hz symbol_rate={symbol_rate:.2f}/s"
        )
    print()

    labels = tuple(window.label for window in windows)
    pair_intersections: dict[tuple[str, str], set[int]] = {}
    pair_top_rows: dict[tuple[str, str], list[PairChange]] = {}

    for left_index in range(len(labels)):
        for right_index in range(left_index + 1, len(labels)):
            left_label = labels[left_index]
            right_label = labels[right_index]
            key = (left_label, right_label)
            intersection: set[int] | None = None
            aggregate_scores: dict[int, list[float]] = {}

            for name in per_capture:
                left = per_capture[name][left_label]
                right = per_capture[name][right_label]
                changed: set[int] = set()
                for slot in range(args.period):
                    left_slot = left[slot]
                    right_slot = right[slot]
                    if left_slot.value < 0 or right_slot.value < 0:
                        continue
                    if left_slot.value == right_slot.value:
                        continue
                    changed.add(slot)
                    score = (left_slot.confidence + right_slot.confidence) / 2.0
                    aggregate_scores.setdefault(slot, []).append(score)

                if intersection is None:
                    intersection = changed
                else:
                    intersection &= changed

            stable_slots = intersection if intersection is not None else set()
            pair_intersections[key] = stable_slots
            rows: list[PairChange] = []
            for slot in stable_slots:
                score_list = aggregate_scores.get(slot, [0.0])
                mean_score = sum(score_list) / len(score_list)
                ref_left = per_capture[next(iter(per_capture))][left_label][slot]
                ref_right = per_capture[next(iter(per_capture))][right_label][slot]
                rows.append(
                    PairChange(
                        slot=slot,
                        score=mean_score,
                        left_value=ref_left.value,
                        right_value=ref_right.value,
                    )
                )
            rows.sort(key=lambda item: (item.score, -item.slot), reverse=True)
            pair_top_rows[key] = rows

    print("=== Stable Pairwise Slot Changes (intersection across captures) ===")
    for key in pair_intersections:
        left_label, right_label = key
        slots = sorted(pair_intersections[key])
        print(f"{left_label} -> {right_label}: slots={slots}")
        print(f"  runs={list(scan_runs(slots))}")
        for row in pair_top_rows[key][: args.top]:
            print(
                f"  slot={row.slot:3d} score={row.score:.3f} "
                f"{row.left_value}->{row.right_value}"
            )
    print()

    slot_hits: dict[int, list[str]] = {}
    for (left_label, right_label), slots in pair_intersections.items():
        pair_name = f"{left_label}->{right_label}"
        for slot in sorted(slots):
            slot_hits.setdefault(slot, []).append(pair_name)

    print("=== Slot Role Ranking ===")
    ranked = sorted(
        slot_hits.items(),
        key=lambda item: (len(item[1]), -item[0]),
        reverse=True,
    )
    for slot, pairs in ranked:
        print(f"slot={slot:3d} pairs={pairs}")
    print()

    print("=== 192-Slot Heatmap (dominant symbols per state, capture 1) ===")
    reference_name = next(iter(per_capture))
    reference = per_capture[reference_name]
    header = "slot " + " ".join(f"{label:>8}" for label in labels)
    print(f"reference={reference_name}")
    print(header)
    for slot in range(args.period):
        values = []
        for label in labels:
            item = reference[label][slot]
            values.append(f"{item.value}:{item.confidence:.2f}")
        if slot in slot_hits:
            print(f"{slot:03d} " + " ".join(f"{value:>8}" for value in values))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())