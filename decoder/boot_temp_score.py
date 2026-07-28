#!/usr/bin/env python3
"""Classify known display temperature states from segment-slot features.

The script uses preselected slot groups from reverse-engineering and computes
state templates from labeled windows. It then predicts each window state and
prints accuracy plus confusion details.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import extract_symbols, load_logic_capture


@dataclass(frozen=True)
class TimeWindow:
    """One labeled state window in seconds."""

    label: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class StateTemplate:
    """A template vector representing one display state."""

    label: str
    vector: tuple[float, ...]


DEFAULT_WINDOWS = (
    TimeWindow("40.0C", 2.00, 2.50),
    TimeWindow("34.2C", 3.75, 4.25),
    TimeWindow("31.4C", 4.25, 5.75),
    TimeWindow("31.3C", 6.00, 7.25),
)

# Derived from boot_digit_map analysis.
DEFAULT_SLOTS = (
    64,
    66,
    65,
    63,
    22,
    76,
    36,
    70,
    172,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Train and evaluate a slot-based temperature-state scorer."
    )
    parser.add_argument("inputs", nargs="+", help="Input .sr files")
    parser.add_argument(
        "--clock-bit",
        type=int,
        default=7,
        help="Clock bit index (default: 7 for D7).",
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
        help="Clock edge used for sampling symbols.",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=192,
        help="Assumed scan period in symbols.",
    )
    parser.add_argument(
        "--slots",
        default=",".join(str(slot) for slot in DEFAULT_SLOTS),
        help="Comma-separated slot indices used as features.",
    )
    parser.add_argument(
        "--window",
        action="append",
        default=[],
        help="State window as label:start-end in seconds.",
    )
    return parser.parse_args()


def parse_data_bits(spec: str) -> tuple[int, ...]:
    """Parse comma-separated bit indices."""
    values = tuple(int(item.strip()) for item in spec.split(",") if item.strip())
    if not values:
        raise ValueError("--data-bits must contain at least one index.")
    if any(item < 0 or item > 7 for item in values):
        raise ValueError("--data-bits supports only indices 0..7.")
    return values


def parse_slots(spec: str, period: int) -> tuple[int, ...]:
    """Parse and validate feature slot list."""
    values = tuple(int(item.strip()) for item in spec.split(",") if item.strip())
    if not values:
        raise ValueError("--slots must contain at least one slot index.")
    if any(item < 0 or item >= period for item in values):
        raise ValueError("--slots contains indices outside configured period.")
    return values


def parse_window(spec: str) -> TimeWindow:
    """Parse one window descriptor label:start-end."""
    if ":" not in spec:
        raise ValueError(f"Invalid --window format: {spec!r}")
    label, range_part = spec.split(":", maxsplit=1)
    if "-" not in range_part:
        raise ValueError(f"Invalid --window range: {spec!r}")
    start_text, end_text = range_part.split("-", maxsplit=1)
    start_s = float(start_text)
    end_s = float(end_text)
    if end_s <= start_s:
        raise ValueError(f"Window end must be larger than start: {spec!r}")
    return TimeWindow(label=label, start_s=start_s, end_s=end_s)


def parse_windows(specs: list[str]) -> tuple[TimeWindow, ...]:
    """Parse optional windows or use defaults."""
    if not specs:
        return DEFAULT_WINDOWS
    return tuple(parse_window(item) for item in specs)


def state_distributions(
    symbols: tuple[int, ...],
    symbol_rate: float,
    windows: tuple[TimeWindow, ...],
    period: int,
    alphabet_size: int,
) -> dict[str, list[list[float]]]:
    """Compute per-state per-slot distributions over symbol values."""
    result: dict[str, list[list[float]]] = {}
    for window in windows:
        start = int(round(window.start_s * symbol_rate))
        end = int(round(window.end_s * symbol_rate))
        counts = [[0 for _ in range(alphabet_size)] for _ in range(period)]
        totals = [0 for _ in range(period)]
        for index, value in enumerate(symbols[start:end]):
            slot = index % period
            counts[slot][value] += 1
            totals[slot] += 1

        distributions: list[list[float]] = []
        for slot in range(period):
            total = totals[slot]
            if total == 0:
                distributions.append([0.0 for _ in range(alphabet_size)])
            else:
                distributions.append(
                    [item / total for item in counts[slot]]
                )
        result[window.label] = distributions
    return result


def feature_vector(
    distributions: list[list[float]],
    slots: tuple[int, ...],
) -> tuple[float, ...]:
    """Flatten selected slot distributions to a feature vector."""
    values: list[float] = []
    for slot in slots:
        values.extend(distributions[slot])
    return tuple(values)


def l1_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    """Compute L1 distance between two vectors."""
    return sum(abs(a - b) for a, b in zip(left, right))


def predict(
    sample: tuple[float, ...],
    templates: tuple[StateTemplate, ...],
) -> tuple[str, float]:
    """Predict nearest state label and corresponding distance."""
    best_label = ""
    best_distance = float("inf")
    for template in templates:
        distance = l1_distance(sample, template.vector)
        if distance < best_distance:
            best_distance = distance
            best_label = template.label
    return best_label, best_distance


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    windows = parse_windows(args.window)
    slots = parse_slots(args.slots, args.period)
    data_bits = parse_data_bits(args.data_bits)
    alphabet_size = 1 << len(data_bits)

    paths = tuple(Path(item) for item in args.inputs)
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)

    per_capture_vectors: dict[str, dict[str, tuple[float, ...]]] = {}
    print("=== Feature Extraction ===")
    for path in paths:
        samples, samplerate_hz = load_logic_capture(path)
        symbols = extract_symbols(samples, args.clock_bit, data_bits, args.edge)
        effective_samplerate = samplerate_hz if samplerate_hz is not None else 2_000_000
        duration_s = len(samples) / float(effective_samplerate)
        symbol_rate = len(symbols) / duration_s if duration_s > 0.0 else 0.0
        distributions = state_distributions(
            symbols=symbols,
            symbol_rate=symbol_rate,
            windows=windows,
            period=args.period,
            alphabet_size=alphabet_size,
        )
        vectors = {
            label: feature_vector(distributions[label], slots)
            for label in distributions
        }
        per_capture_vectors[path.name] = vectors
        print(
            f"{path.name}: samples={len(samples)} symbols={len(symbols)} "
            f"samplerate={effective_samplerate}Hz symbol_rate={symbol_rate:.2f}/s"
        )

    labels = tuple(window.label for window in windows)
    reference_label_order = labels

    # Build templates by averaging vectors across captures.
    templates: list[StateTemplate] = []
    for label in reference_label_order:
        accum = [0.0 for _ in range(len(slots) * alphabet_size)]
        count = 0
        for capture_name in per_capture_vectors:
            vector = per_capture_vectors[capture_name][label]
            for index, value in enumerate(vector):
                accum[index] += value
            count += 1
        averaged = tuple(value / count for value in accum)
        templates.append(StateTemplate(label=label, vector=averaged))

    print()
    print("=== Template Classification ===")
    total = 0
    correct = 0
    confusion: dict[tuple[str, str], int] = {}

    for capture_name, vectors in per_capture_vectors.items():
        print(f"{capture_name}:")
        for label in reference_label_order:
            predicted, distance = predict(vectors[label], tuple(templates))
            ok = predicted == label
            total += 1
            if ok:
                correct += 1
            confusion[(label, predicted)] = confusion.get((label, predicted), 0) + 1
            status = "OK" if ok else "MISS"
            print(
                f"  {label:>6} -> {predicted:<6} distance={distance:.4f} {status}"
            )

    accuracy = correct / total if total else 0.0
    print()
    print(f"accuracy={accuracy:.4f} ({correct}/{total})")

    print("confusion:")
    for true_label in reference_label_order:
        for predicted_label in reference_label_order:
            key = (true_label, predicted_label)
            value = confusion.get(key, 0)
            if value > 0:
                print(f"  {true_label:>6} -> {predicted_label:<6}: {value}")

    print()
    print("=== Leave-One-Capture-Out ===")
    loco_total = 0
    loco_correct = 0
    for test_name in per_capture_vectors:
        train_names = [name for name in per_capture_vectors if name != test_name]
        loco_templates: list[StateTemplate] = []
        for label in reference_label_order:
            accum = [0.0 for _ in range(len(slots) * alphabet_size)]
            count = 0
            for train_name in train_names:
                vector = per_capture_vectors[train_name][label]
                for index, value in enumerate(vector):
                    accum[index] += value
                count += 1
            averaged = tuple(value / count for value in accum)
            loco_templates.append(StateTemplate(label=label, vector=averaged))

        test_correct = 0
        print(f"test_capture={test_name}")
        for label in reference_label_order:
            predicted, distance = predict(
                per_capture_vectors[test_name][label], tuple(loco_templates)
            )
            ok = predicted == label
            loco_total += 1
            if ok:
                loco_correct += 1
                test_correct += 1
            status = "OK" if ok else "MISS"
            print(
                f"  {label:>6} -> {predicted:<6} distance={distance:.4f} {status}"
            )
        print(f"  accuracy={test_correct}/4 = {test_correct / 4:.3f}")

    loco_accuracy = loco_correct / loco_total if loco_total else 0.0
    print(f"loco_accuracy={loco_accuracy:.4f} ({loco_correct}/{loco_total})")
    print()

    print("used_slots:", slots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())