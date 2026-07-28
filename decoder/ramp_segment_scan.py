#!/usr/bin/env python3
"""Scan one ramp capture for display-segment transitions.

The tool extracts a symbol stream, builds slot-dominance states per sliding
window, and reports window-to-window change points with slot and bank summaries.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import extract_symbols, load_logic_capture, parse_data_bits


@dataclass(frozen=True)
class WindowState:
    """Dominant slot state in one symbol window."""

    start_symbol: int
    end_symbol: int
    center_symbol: int
    center_seconds: float
    approx_temp: float | None
    dominant: tuple[int, ...]
    confidence: tuple[float, ...]


@dataclass(frozen=True)
class ChangeEvent:
    """One transition between two neighboring window states."""

    left_index: int
    right_index: int
    center_seconds: float
    approx_temp: float | None
    changed_slots: tuple[int, ...]
    bank_counts: tuple[int, ...]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Detect slot-level transition events in one ramp capture "
            "using sliding-window dominance."
        )
    )
    parser.add_argument("input", type=Path, help="Input .sr file")
    parser.add_argument(
        "--clock-bit",
        type=int,
        default=5,
        help="Clock channel bit index (default: 5 for D5).",
    )
    parser.add_argument(
        "--data-bits",
        default="4,7",
        help="Comma-separated data bit indices (default: 4,7).",
    )
    parser.add_argument(
        "--edge",
        choices=("rising", "falling"),
        default="rising",
        help="Clock edge used for symbol extraction.",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=192,
        help="Assumed scan period in symbols.",
    )
    parser.add_argument(
        "--window-periods",
        type=int,
        default=24,
        help="Periods per state window.",
    )
    parser.add_argument(
        "--step-periods",
        type=int,
        default=6,
        help="Period step between neighboring windows.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.42,
        help="Minimum dominance confidence in both windows.",
    )
    parser.add_argument(
        "--min-changed-slots",
        type=int,
        default=4,
        help="Minimum changed-slot count to report one event.",
    )
    parser.add_argument(
        "--top-events",
        type=int,
        default=24,
        help="Maximum number of strongest events printed.",
    )
    parser.add_argument(
        "--temp-start",
        type=float,
        default=None,
        help="Optional ramp start temperature for approximate mapping.",
    )
    parser.add_argument(
        "--temp-end",
        type=float,
        default=None,
        help="Optional ramp end temperature for approximate mapping.",
    )
    parser.add_argument(
        "--banks",
        type=int,
        default=4,
        help="Number of equally sized banks for slot summaries.",
    )
    return parser.parse_args()


def dominant_slot_state(
    symbols: tuple[int, ...],
    start_symbol: int,
    end_symbol: int,
    period: int,
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """Compute dominant symbol and confidence for each slot."""
    counters = [Counter() for _ in range(period)]
    for absolute_index in range(start_symbol, end_symbol):
        slot = absolute_index % period
        counters[slot][symbols[absolute_index]] += 1

    dominant: list[int] = []
    confidence: list[float] = []
    for slot_counter in counters:
        if not slot_counter:
            dominant.append(-1)
            confidence.append(0.0)
            continue
        value, count = slot_counter.most_common(1)[0]
        total = sum(slot_counter.values())
        dominant.append(value)
        confidence.append((count / total) if total else 0.0)

    return tuple(dominant), tuple(confidence)


def approx_temperature(
    center_symbol: int,
    total_symbols: int,
    temp_start: float | None,
    temp_end: float | None,
) -> float | None:
    """Map symbol position to approximate ramp temperature."""
    if temp_start is None or temp_end is None or total_symbols <= 1:
        return None
    progress = center_symbol / (total_symbols - 1)
    return temp_start + ((temp_end - temp_start) * progress)


def scan_runs(slots: tuple[int, ...], max_gap: int = 2) -> tuple[tuple[int, int], ...]:
    """Compact sorted slot ids into nearly contiguous runs."""
    if not slots:
        return tuple()

    runs: list[tuple[int, int]] = []
    start = slots[0]
    end = slots[0]
    for slot in slots[1:]:
        if slot <= end + max_gap:
            end = slot
            continue
        runs.append((start, end))
        start = slot
        end = slot
    runs.append((start, end))
    return tuple(runs)


def bank_distribution(
    changed_slots: tuple[int, ...],
    period: int,
    banks: int,
) -> tuple[int, ...]:
    """Count changed slots per equally sized bank."""
    if banks < 1:
        raise ValueError("--banks must be at least 1.")

    counts = [0 for _ in range(banks)]
    bank_size = period / banks
    for slot in changed_slots:
        index = int(slot / bank_size)
        if index >= banks:
            index = banks - 1
        counts[index] += 1
    return tuple(counts)


def format_temp(temp: float | None) -> str:
    """Render optional temperature."""
    if temp is None:
        return "n/a"
    return f"{temp:.2f}"


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)
    if (args.temp_start is None) ^ (args.temp_end is None):
        raise ValueError("Set both --temp-start and --temp-end, or neither.")

    data_bits = parse_data_bits(args.data_bits)

    samples, samplerate_hz = load_logic_capture(args.input)
    effective_samplerate = samplerate_hz if samplerate_hz is not None else 2_000_000
    symbols = extract_symbols(samples, args.clock_bit, data_bits, args.edge)
    if not symbols:
        print("No symbols extracted with the selected decode parameters.")
        return 0

    duration_s = len(samples) / float(effective_samplerate)
    symbol_rate = len(symbols) / duration_s if duration_s > 0.0 else 0.0

    window_symbols = args.window_periods * args.period
    step_symbols = args.step_periods * args.period
    if window_symbols < args.period:
        raise ValueError("--window-periods is too small for the selected period.")
    if step_symbols < 1:
        raise ValueError("--step-periods must produce a positive symbol step.")

    states: list[WindowState] = []
    for start_symbol in range(0, len(symbols) - window_symbols + 1, step_symbols):
        end_symbol = start_symbol + window_symbols
        center_symbol = (start_symbol + end_symbol - 1) // 2
        center_seconds = center_symbol / symbol_rate if symbol_rate > 0.0 else 0.0
        temp = approx_temperature(
            center_symbol=center_symbol,
            total_symbols=len(symbols),
            temp_start=args.temp_start,
            temp_end=args.temp_end,
        )
        dominant, confidence = dominant_slot_state(
            symbols=symbols,
            start_symbol=start_symbol,
            end_symbol=end_symbol,
            period=args.period,
        )
        states.append(
            WindowState(
                start_symbol=start_symbol,
                end_symbol=end_symbol,
                center_symbol=center_symbol,
                center_seconds=center_seconds,
                approx_temp=temp,
                dominant=dominant,
                confidence=confidence,
            )
        )

    events: list[ChangeEvent] = []
    for left_index in range(len(states) - 1):
        right_index = left_index + 1
        left_state = states[left_index]
        right_state = states[right_index]

        changed: list[int] = []
        for slot in range(args.period):
            if left_state.dominant[slot] < 0 or right_state.dominant[slot] < 0:
                continue
            if left_state.dominant[slot] == right_state.dominant[slot]:
                continue
            if left_state.confidence[slot] < args.min_confidence:
                continue
            if right_state.confidence[slot] < args.min_confidence:
                continue
            changed.append(slot)

        if len(changed) < args.min_changed_slots:
            continue

        changed_slots = tuple(sorted(changed))
        events.append(
            ChangeEvent(
                left_index=left_index,
                right_index=right_index,
                center_seconds=right_state.center_seconds,
                approx_temp=right_state.approx_temp,
                changed_slots=changed_slots,
                bank_counts=bank_distribution(changed_slots, args.period, args.banks),
            )
        )

    print("=== Ramp Segment Scan ===")
    print(
        f"file={args.input.name} samplerate={effective_samplerate}Hz "
        f"samples={len(samples)} symbols={len(symbols)} symbol_rate={symbol_rate:.2f}/s"
    )
    print(
        f"decode clock=D{args.clock_bit} data={','.join(f'D{bit}' for bit in data_bits)} "
        f"edge={args.edge} period={args.period}"
    )
    print(
        f"window_periods={args.window_periods} step_periods={args.step_periods} "
        f"min_conf={args.min_confidence:.2f} min_changed_slots={args.min_changed_slots}"
    )
    print(f"windows={len(states)} events={len(events)}")

    if not events:
        print("No transition events matched the current thresholds.")
        return 0

    ranked = sorted(
        events,
        key=lambda item: (
            -len(item.changed_slots),
            -sum(item.bank_counts),
            item.right_index,
        ),
    )

    print("\n=== Top transition events ===")
    for event in ranked[: args.top_events]:
        runs = scan_runs(event.changed_slots)
        print(
            f"event {event.left_index:03d}->{event.right_index:03d} "
            f"t={event.center_seconds:7.3f}s temp~{format_temp(event.approx_temp)} "
            f"changed={len(event.changed_slots):3d} banks={list(event.bank_counts)}"
        )
        print(f"  slots={list(event.changed_slots)}")
        print(f"  runs={list(runs)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
