#!/usr/bin/env python3
"""Probe slot-to-digit relationships for Sundance display decoding.

This tool uses labeled time windows (for example 40.0C, 34.2C, 31.4C, 31.3C)
from one or more captures and ranks scan slots by mutual information with each
numeric digit position (tens, ones, tenths).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import math
from pathlib import Path
import re
import sys
from typing import Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import extract_symbols, load_logic_capture


@dataclass(frozen=True)
class TimeWindow:
    """One labeled state window."""

    label: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class SlotState:
    """Dominant symbol and confidence for one slot in one state."""

    dominant: int
    confidence: float


DEFAULT_WINDOWS = (
    TimeWindow("40.0C", 2.00, 2.50),
    TimeWindow("34.2C", 3.75, 4.25),
    TimeWindow("31.4C", 4.25, 5.75),
    TimeWindow("31.3C", 6.00, 7.25),
)

TEMP_RANGE_PATTERN = re.compile(r"(\d+)-(\d+)")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Rank scan slots by information about numeric display digits."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input .sr files")
    parser.add_argument(
        "--clock-bit",
        type=int,
        default=7,
        help="Clock bit index (default: 7).",
    )
    parser.add_argument(
        "--data-bits",
        default="4,5",
        help="Comma-separated data bit indices (default: 4,5).",
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
        help="Window as label:start-end, e.g. 31.4C:4.25-5.75.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.55,
        help="Minimum dominant confidence per slot/state to count as reliable.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Top N slots per digit position.",
    )
    parser.add_argument(
        "--auto-from-filename",
        action="store_true",
        help=(
            "Infer labels from filename ranges like 26-27 and build "
            "start/end windows automatically."
        ),
    )
    parser.add_argument(
        "--auto-window-seconds",
        type=float,
        default=0.80,
        help="Window size in seconds for auto start/end labels.",
    )
    return parser.parse_args()


def parse_data_bits(text: str) -> tuple[int, ...]:
    """Parse comma-separated data bits."""
    parts = [item.strip() for item in text.split(",") if item.strip()]
    values = tuple(int(item) for item in parts)
    if not values:
        raise ValueError("--data-bits must contain at least one bit index")
    if any(value < 0 or value > 7 for value in values):
        raise ValueError("data bits must be in range 0..7")
    return values


def parse_window(spec: str) -> TimeWindow:
    """Parse one window specification label:start-end."""
    if ":" not in spec:
        raise ValueError(f"Invalid window spec: {spec!r}")
    label, tail = spec.split(":", maxsplit=1)
    if "-" not in tail:
        raise ValueError(f"Invalid window range: {spec!r}")
    start_text, end_text = tail.split("-", maxsplit=1)
    start_s = float(start_text)
    end_s = float(end_text)
    if end_s <= start_s:
        raise ValueError(f"Window end must be greater than start: {spec!r}")
    return TimeWindow(label=label, start_s=start_s, end_s=end_s)


def parse_windows(specs: list[str]) -> tuple[TimeWindow, ...]:
    """Use explicit windows or defaults."""
    if not specs:
        return DEFAULT_WINDOWS
    return tuple(parse_window(item) for item in specs)


def parse_label_value(label: str) -> tuple[int, int, int]:
    """Convert labels like '34.2C' into (tens, ones, tenths)."""
    raw = label.strip().upper().replace("C", "")
    if "." not in raw:
        raise ValueError(f"Label {label!r} must include one decimal digit")
    left, right = raw.split(".", maxsplit=1)
    if len(right) < 1:
        raise ValueError(f"Label {label!r} must include tenths")
    value10 = int(round(float(raw) * 10.0))
    tens = value10 // 100
    ones = (value10 // 10) % 10
    tenths = value10 % 10
    return tens, ones, tenths


def parse_file_temp_range(path: Path) -> tuple[int, int] | None:
    """Extract (from_temp, to_temp) from filename when available."""
    match = TEMP_RANGE_PATTERN.search(path.name)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def entropy(values: Iterable[int]) -> float:
    """Compute entropy in bits for a discrete variable."""
    counts: dict[int, int] = defaultdict(int)
    total = 0
    for value in values:
        counts[value] += 1
        total += 1
    if total == 0:
        return 0.0
    result = 0.0
    for count in counts.values():
        probability = count / total
        result -= probability * math.log2(probability)
    return result


def mutual_information(x_values: list[int], y_values: list[int]) -> float:
    """Compute mutual information I(X;Y) in bits."""
    if len(x_values) != len(y_values):
        raise ValueError("x and y lengths must match")
    if not x_values:
        return 0.0

    xy_counts: dict[tuple[int, int], int] = defaultdict(int)
    x_counts: dict[int, int] = defaultdict(int)
    y_counts: dict[int, int] = defaultdict(int)

    total = len(x_values)
    for x_value, y_value in zip(x_values, y_values):
        xy_counts[(x_value, y_value)] += 1
        x_counts[x_value] += 1
        y_counts[y_value] += 1

    value = 0.0
    for (x_value, y_value), joint_count in xy_counts.items():
        p_xy = joint_count / total
        p_x = x_counts[x_value] / total
        p_y = y_counts[y_value] / total
        value += p_xy * math.log2(p_xy / (p_x * p_y))
    return value


def slot_dominants_for_window(
    symbols: tuple[int, ...],
    period: int,
    start_idx: int,
    end_idx: int,
    alphabet_size: int,
) -> tuple[SlotState, ...]:
    """Compute dominant symbol/confidence for each slot in one window."""
    counts = [[0 for _ in range(alphabet_size)] for _ in range(period)]
    totals = [0 for _ in range(period)]

    for index in range(start_idx, end_idx):
        slot = index % period
        symbol = symbols[index]
        counts[slot][symbol] += 1
        totals[slot] += 1

    states: list[SlotState] = []
    for slot in range(period):
        total = totals[slot]
        if total == 0:
            states.append(SlotState(dominant=-1, confidence=0.0))
            continue
        dominant = max(range(alphabet_size), key=lambda item: counts[slot][item])
        confidence = counts[slot][dominant] / total
        states.append(SlotState(dominant=dominant, confidence=confidence))
    return tuple(states)


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    data_bits = parse_data_bits(args.data_bits)
    windows = parse_windows(args.window)
    alphabet_size = 1 << len(data_bits)

    for path in args.inputs:
        if not path.exists():
            raise FileNotFoundError(path)

    labels = [window.label for window in windows]
    numeric = {label: parse_label_value(label) for label in labels}

    # Samples for MI: per slot we collect one dominant-symbol sample per
    # (capture, window) pair when confidence is high enough.
    slot_samples: list[list[tuple[int, int, int]]] = [[] for _ in range(args.period)]

    print("=== Capture Summary ===")
    for path in args.inputs:
        samples, samplerate_hz = load_logic_capture(path)
        if samplerate_hz is None:
            samplerate_hz = 2_000_000
        symbols = extract_symbols(samples, args.clock_bit, data_bits, args.edge)
        duration_s = len(samples) / float(samplerate_hz)
        symbol_rate = len(symbols) / duration_s if duration_s > 0.0 else 0.0
        print(
            f"{path.name}: samplerate={samplerate_hz}Hz samples={len(samples)} "
            f"symbols={len(symbols)} symbol_rate={symbol_rate:.2f}/s"
        )

        if args.auto_from_filename:
            temp_range = parse_file_temp_range(path)
            if temp_range is None:
                continue
            from_temp, to_temp = temp_range
            file_windows = (
                TimeWindow(
                    label=f"{from_temp}.0C",
                    start_s=0.0,
                    end_s=args.auto_window_seconds,
                ),
                TimeWindow(
                    label=f"{to_temp}.0C",
                    start_s=max(0.0, duration_s - args.auto_window_seconds),
                    end_s=duration_s,
                ),
            )
            for window in file_windows:
                numeric.setdefault(window.label, parse_label_value(window.label))
        else:
            file_windows = windows

        for window in file_windows:
            start_idx = int(round(window.start_s * symbol_rate))
            end_idx = int(round(window.end_s * symbol_rate))
            if end_idx <= start_idx:
                continue
            end_idx = min(end_idx, len(symbols))
            states = slot_dominants_for_window(
                symbols=symbols,
                period=args.period,
                start_idx=max(0, start_idx),
                end_idx=end_idx,
                alphabet_size=alphabet_size,
            )
            tens, ones, tenths = numeric[window.label]
            for slot in range(args.period):
                state = states[slot]
                if state.dominant < 0 or state.confidence < args.min_confidence:
                    continue
                slot_samples[slot].append((state.dominant, tens, ones, tenths))

    results: dict[str, list[tuple[int, float, int]]] = {
        "tens": [],
        "ones": [],
        "tenths": [],
    }

    for slot, samples in enumerate(slot_samples):
        if len(samples) < 4:
            continue

        x_vals = [entry[0] for entry in samples]
        tens_vals = [entry[1] for entry in samples]
        ones_vals = [entry[2] for entry in samples]
        tenths_vals = [entry[3] for entry in samples]

        mi_tens = mutual_information(x_vals, tens_vals)
        mi_ones = mutual_information(x_vals, ones_vals)
        mi_tenths = mutual_information(x_vals, tenths_vals)

        results["tens"].append((slot, mi_tens, len(samples)))
        results["ones"].append((slot, mi_ones, len(samples)))
        results["tenths"].append((slot, mi_tenths, len(samples)))

    for key in ("tens", "ones", "tenths"):
        results[key].sort(key=lambda item: (item[1], item[2]), reverse=True)

    print()
    print("=== Slot Information Ranking ===")
    for key in ("tens", "ones", "tenths"):
        print(f"{key}:")
        top = results[key][: args.top]
        if not top:
            print("  none")
            continue
        for slot, value, count in top:
            print(f"  slot={slot:3d} mi={value:.4f} samples={count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
