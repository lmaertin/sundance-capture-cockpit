#!/usr/bin/env python3
"""Pattern-based display text recognition across Sundance .sr captures.

The script builds a weakly supervised template model from all captures under a
folder. Labels are inferred only from filename tokens that look like display
texts (time/temperature). For a target capture, it predicts state texts from
burst patterns with optional leave-one-file-out training.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable

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


TIME_TOKEN = re.compile(r"(?<!\d)(\d{1,2})-(\d{2})(?!\d)")
TEMP_TOKEN = re.compile(r"(?<!\d)(\d{1,2}\.\d)(?!\d)")
POOL_TOKEN = re.compile(r"pool_(\d{1,2})-(\d{1,2})", re.IGNORECASE)


@dataclass(frozen=True)
class RunPattern:
    """One stable run represented by its dominant burst pattern."""

    pattern: tuple[int, ...]
    start_time_s: float
    end_time_s: float
    width: int


@dataclass(frozen=True)
class LabeledPattern:
    """One training sample mapping a pattern to text."""

    label: str
    pattern: tuple[int, ...]
    source: str


@dataclass(frozen=True)
class Prediction:
    """Predicted label for one stable run."""

    label: str
    score: float
    shift: int
    start_time_s: float
    end_time_s: float
    width: int


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train a weakly supervised display-pattern model and predict texts."
    )
    parser.add_argument(
        "--captures-dir",
        type=Path,
        default=Path("messungen"),
        help="Root folder containing .sr captures (default: messungen).",
    )
    parser.add_argument(
        "--predict",
        type=Path,
        required=True,
        help="Target capture for display text prediction.",
    )
    parser.add_argument(
        "--exclude-predict-from-train",
        action="store_true",
        help="Do not use the target file during model training.",
    )
    parser.add_argument(
        "--data-bits",
        default="5,7",
        help="Comma-separated data bits used for pattern decoding (default: 5,7).",
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
        "--symbols-per-burst",
        type=int,
        default=192,
        help="Expected symbol count per burst (default: 192).",
    )
    parser.add_argument(
        "--top-prototypes",
        type=int,
        default=8,
        help="Prototype count for in-file run extraction.",
    )
    parser.add_argument(
        "--smooth-radius",
        type=int,
        default=5,
        help="Smoothing radius for stable-run extraction.",
    )
    parser.add_argument(
        "--min-stable-width",
        type=int,
        default=18,
        help="Minimum run width in bursts.",
    )
    parser.add_argument(
        "--max-circular-shift",
        type=int,
        default=24,
        help="Maximum circular shift tested for pattern matching.",
    )
    return parser.parse_args()


def filename_labels(path: Path) -> list[str]:
    """Extract display-like labels from filename tokens.

    Priority:
    1) Temperatures with decimal, e.g. 29.9 -> 29.9C
    2) Times, e.g. 12-45 -> 12:45
    3) pool_26-27 style as temperatures 26.0C,27.0C
    """
    stem = path.stem
    labels: list[str] = []

    pool = POOL_TOKEN.search(stem)
    if pool is not None:
        labels.append(f"{int(pool.group(1))}.0C")
        labels.append(f"{int(pool.group(2))}.0C")
        return labels

    ordered: list[tuple[int, str]] = []

    for match in TIME_TOKEN.finditer(stem):
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour > 23 or minute > 59:
            continue
        ordered.append((match.start(), f"{hour}:{minute:02d}"))

    for match in TEMP_TOKEN.finditer(stem):
        ordered.append((match.start(), f"{match.group(1)}C"))

    ordered.sort(key=lambda item: item[0])
    labels = [item[1] for item in ordered]

    seen: set[str] = set()
    unique: list[str] = []
    for label in labels:
        if label in seen:
            continue
        seen.add(label)
        unique.append(label)
    return unique


def extract_run_patterns(
    path: Path,
    clock_bit: int,
    gate_bit: int,
    gate_active: int,
    data_bits: tuple[int, ...],
    symbols_per_burst: int,
    top_prototypes: int,
    smooth_radius: int,
    min_stable_width: int,
) -> list[RunPattern]:
    """Extract stable runs and represent each by a dominant burst pattern."""
    bursts, times, _ = load_bursts(
        path=path,
        clock_bit=clock_bit,
        gate_bit=gate_bit,
        gate_active=gate_active,
        data_bits=data_bits,
        symbols_per_burst=symbols_per_burst,
    )
    if not bursts:
        return []

    counts = Counter(bursts)
    prototypes = [signature for signature, _ in counts.most_common(top_prototypes)]
    if not prototypes:
        return []

    labels: list[int] = []
    for burst in bursts:
        distances = [hamming(burst, proto) for proto in prototypes]
        best = min(range(len(distances)), key=lambda index: distances[index])
        labels.append(best)

    smoothed = smooth_labels(labels, smooth_radius)
    runs = build_stable_runs(smoothed, times, min_stable_width)
    if not runs:
        return []

    patterns: list[RunPattern] = []
    for run in runs:
        run_bursts = bursts[run.start_index : run.end_index + 1]
        dominant = Counter(run_bursts).most_common(1)[0][0]
        patterns.append(
            RunPattern(
                pattern=dominant,
                start_time_s=run.start_time_s,
                end_time_s=run.end_time_s,
                width=run.width,
            )
        )
    return patterns


def circular_hamming(
    left: tuple[int, ...],
    right: tuple[int, ...],
    max_shift: int,
) -> tuple[int, int]:
    """Return minimum Hamming distance with bounded circular shifts."""
    if len(left) != len(right):
        raise ValueError("Pattern lengths must match")

    best_distance = len(left) + 1
    best_shift = 0
    length = len(left)

    for shift in range(-max_shift, max_shift + 1):
        if shift == 0:
            shifted = right
        elif shift > 0:
            shifted = right[shift:] + right[:shift]
        else:
            value = -shift
            shifted = right[length - value :] + right[: length - value]

        distance = hamming(left, shifted)
        if distance < best_distance:
            best_distance = distance
            best_shift = shift
    return best_distance, best_shift


def build_training_samples(
    captures: Iterable[Path],
    predict_path: Path,
    exclude_predict: bool,
    clock_bit: int,
    gate_bit: int,
    gate_active: int,
    data_bits: tuple[int, ...],
    symbols_per_burst: int,
    top_prototypes: int,
    smooth_radius: int,
    min_stable_width: int,
) -> list[LabeledPattern]:
    """Build weakly supervised samples from all labeled capture filenames."""
    samples: list[LabeledPattern] = []

    for path in sorted(captures):
        if exclude_predict and path.resolve() == predict_path.resolve():
            continue

        labels = filename_labels(path)
        if not labels:
            continue

        patterns = extract_run_patterns(
            path=path,
            clock_bit=clock_bit,
            gate_bit=gate_bit,
            gate_active=gate_active,
            data_bits=data_bits,
            symbols_per_burst=symbols_per_burst,
            top_prototypes=top_prototypes,
            smooth_radius=smooth_radius,
            min_stable_width=min_stable_width,
        )
        if not patterns:
            continue

        # If one label is known, map dominant run to that label.
        if len(labels) == 1:
            dominant = max(patterns, key=lambda item: item.width)
            samples.append(
                LabeledPattern(
                    label=labels[0],
                    pattern=dominant.pattern,
                    source=path.name,
                )
            )
            continue

        # For two+ labels, map by order of first appearance among wide runs.
        ranked_runs = sorted(patterns, key=lambda item: item.start_time_s)
        for label, run in zip(labels, ranked_runs):
            samples.append(
                LabeledPattern(
                    label=label,
                    pattern=run.pattern,
                    source=path.name,
                )
            )

    return samples


def predict_runs(
    runs: list[RunPattern],
    templates: list[LabeledPattern],
    max_shift: int,
) -> list[Prediction]:
    """Predict one display label per run from nearest template."""
    predictions: list[Prediction] = []
    if not runs or not templates:
        return predictions

    for run in runs:
        best_label = "UNKNOWN"
        best_score = -1.0
        best_shift = 0

        for template in templates:
            distance, shift = circular_hamming(
                run.pattern,
                template.pattern,
                max_shift=max_shift,
            )
            score = 1.0 - (distance / len(run.pattern))
            if score > best_score:
                best_score = score
                best_label = template.label
                best_shift = shift

        predictions.append(
            Prediction(
                label=best_label,
                score=best_score,
                shift=best_shift,
                start_time_s=run.start_time_s,
                end_time_s=run.end_time_s,
                width=run.width,
            )
        )
    return predictions


def summarize_templates(samples: list[LabeledPattern]) -> dict[str, int]:
    """Count templates per label for quick reporting."""
    counts: dict[str, int] = defaultdict(int)
    for item in samples:
        counts[item.label] += 1
    return dict(sorted(counts.items(), key=lambda pair: pair[0]))


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    if not args.captures_dir.exists():
        raise FileNotFoundError(args.captures_dir)
    if not args.predict.exists():
        raise FileNotFoundError(args.predict)

    captures = tuple(sorted(args.captures_dir.rglob("*.sr")))
    if not captures:
        raise FileNotFoundError("No .sr files found under captures dir")

    data_bits = parse_data_bits(args.data_bits)

    templates = build_training_samples(
        captures=captures,
        predict_path=args.predict,
        exclude_predict=args.exclude_predict_from_train,
        clock_bit=args.clock_bit,
        gate_bit=args.gate_bit,
        gate_active=args.gate_active,
        data_bits=data_bits,
        symbols_per_burst=args.symbols_per_burst,
        top_prototypes=args.top_prototypes,
        smooth_radius=args.smooth_radius,
        min_stable_width=args.min_stable_width,
    )

    runs = extract_run_patterns(
        path=args.predict,
        clock_bit=args.clock_bit,
        gate_bit=args.gate_bit,
        gate_active=args.gate_active,
        data_bits=data_bits,
        symbols_per_burst=args.symbols_per_burst,
        top_prototypes=args.top_prototypes,
        smooth_radius=args.smooth_radius,
        min_stable_width=args.min_stable_width,
    )

    print("=== Display Pattern AI ===")
    print(f"captures_total={len(captures)} predict={args.predict.name}")
    print(
        f"training_templates={len(templates)} "
        f"exclude_predict={args.exclude_predict_from_train}"
    )
    print(f"data_bits={','.join(f'D{bit}' for bit in data_bits)}")

    if not templates:
        print("No labeled templates could be built from filenames.")
        return 2

    label_counts = summarize_templates(templates)
    print("template_labels:")
    for label, count in label_counts.items():
        print(f"  {label}: {count}")

    if not runs:
        print("No stable runs detected in predict capture.")
        return 3

    predictions = predict_runs(
        runs=runs,
        templates=templates,
        max_shift=args.max_circular_shift,
    )
    if not predictions:
        print("No predictions generated.")
        return 4

    print("predicted_runs:")
    for index, prediction in enumerate(predictions, start=1):
        duration = max(0.0, prediction.end_time_s - prediction.start_time_s)
        print(
            f"  run{index}: {prediction.label} "
            f"score={prediction.score:.4f} shift={prediction.shift:+d} "
            f"t=[{prediction.start_time_s:.3f},{prediction.end_time_s:.3f}] "
            f"dur~{duration:.3f}s width={prediction.width}"
        )

    print("transitions:")
    previous = predictions[0].label
    for prediction in predictions[1:]:
        if prediction.label != previous:
            print(
                f"  {previous} -> {prediction.label} "
                f"at {prediction.start_time_s:.3f}s"
            )
        previous = prediction.label

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
