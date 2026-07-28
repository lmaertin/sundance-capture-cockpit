#!/usr/bin/env python3
"""Decode numeric labels over time from proprietary Sundance panel96 recordings.

The decoder learns frame signatures from labeled reference captures and predicts
numeric states (temperature/time-like) for an arbitrary target recording.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import load_logic_capture
from decoder.frame96_mapper import extract_frames, filename_labels


DIGIT_LABEL = re.compile(r".*\d.*")
TEMP_LABEL = re.compile(r"^\d{1,2}\.\dC$")
TIME_LABEL = re.compile(r"^\d{1,2}:\d{2}$")


@dataclass(frozen=True)
class Template:
    """One learned signature template for a label."""

    label: str
    bits: tuple[int, ...]
    source: str


@dataclass(frozen=True)
class PredictedFrame:
    """Prediction for one frame."""

    label: str
    confidence: float
    time_s: float


@dataclass(frozen=True)
class TimeRun:
    """One compressed timeline run."""

    label: str
    start_s: float
    end_s: float
    frames: int
    mean_confidence: float


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Predict numeric display values over time for panel96 recordings."
    )
    parser.add_argument("input", type=Path, help="Target recording (.sr)")
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path("messungen"),
        help="Directory with reference .sr files used for learning.",
    )
    parser.add_argument("--clock-bit", type=int, default=7)
    parser.add_argument("--latch-bit", type=int, default=6)
    parser.add_argument("--data-bit", type=int, default=4)
    parser.add_argument("--clock-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--latch-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--frame-bits", type=int, default=96)
    parser.add_argument("--smooth-radius", type=int, default=8)
    parser.add_argument("--min-run-frames", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=0.70)
    parser.add_argument(
        "--include-non-numeric",
        action="store_true",
        help="Also print runs without numeric-looking labels.",
    )
    parser.add_argument(
        "--mode",
        choices=("all", "temp", "time"),
        default="all",
        help="Filter output runs: all labels, only temperature-like, or only time-like.",
    )
    return parser.parse_args()


def hamming(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    """Return Hamming distance for equal-length bit tuples."""
    return sum(1 for a, b in zip(left, right) if a != b)


def majority_smooth(labels: list[str], radius: int) -> list[str]:
    """Apply majority smoothing to a label sequence."""
    if not labels or radius <= 0:
        return labels
    output: list[str] = []
    for index in range(len(labels)):
        start = max(0, index - radius)
        end = min(len(labels), index + radius + 1)
        output.append(Counter(labels[start:end]).most_common(1)[0][0])
    return output


def build_templates_for_file(
    path: Path,
    clock_bit: int,
    latch_bit: int,
    data_bit: int,
    clock_edge: str,
    latch_edge: str,
    frame_bits: int,
) -> list[Template]:
    """Learn templates for one reference file from filename-derived labels."""
    labels = filename_labels(path)
    if len(labels) < 1:
        return []

    samples, samplerate_hz = load_logic_capture(path)
    if samplerate_hz is None:
        samplerate_hz = 2_000_000

    frames = extract_frames(
        samples=samples,
        samplerate_hz=samplerate_hz,
        clock_bit=clock_bit,
        latch_bit=latch_bit,
        data_bits=(data_bit,),
        clock_edge=clock_edge,
        latch_edge=latch_edge,
        expected_bits=frame_bits,
    )
    if not frames:
        return []

    pattern_counts = Counter(frame.bits for frame in frames)
    top_patterns = [item[0] for item in pattern_counts.most_common(max(2, len(labels) + 1))]
    if not top_patterns:
        return []

    # Map each frame to nearest top pattern index for coarse state sequence.
    idx_series: list[int] = []
    for frame in frames:
        idx = min(
            range(len(top_patterns)),
            key=lambda value: hamming(frame.bits, top_patterns[value]),
        )
        idx_series.append(idx)

    # Order states by first appearance and map against filename labels in order.
    ordered: list[int] = []
    seen: set[int] = set()
    for idx in idx_series:
        if idx in seen:
            continue
        seen.add(idx)
        ordered.append(idx)

    templates: list[Template] = []
    for label, idx in zip(labels, ordered):
        templates.append(
            Template(
                label=label,
                bits=top_patterns[idx],
                source=path.name,
            )
        )
    return templates


def collect_templates(
    target: Path,
    reference_dir: Path,
    clock_bit: int,
    latch_bit: int,
    data_bit: int,
    clock_edge: str,
    latch_edge: str,
    frame_bits: int,
) -> list[Template]:
    """Collect templates from all reference files except target."""
    templates: list[Template] = []
    for path in sorted(reference_dir.rglob("*.sr")):
        if path.resolve() == target.resolve():
            continue
        templates.extend(
            build_templates_for_file(
                path=path,
                clock_bit=clock_bit,
                latch_bit=latch_bit,
                data_bit=data_bit,
                clock_edge=clock_edge,
                latch_edge=latch_edge,
                frame_bits=frame_bits,
            )
        )

    # Deduplicate exact label+bits pairs.
    dedup: dict[tuple[str, tuple[int, ...]], Template] = {}
    for item in templates:
        dedup[(item.label, item.bits)] = item
    return list(dedup.values())


def predict_frames(
    frames: list[tuple[float, tuple[int, ...]]],
    templates: list[Template],
    min_confidence: float,
) -> list[PredictedFrame]:
    """Predict labels for all frames using nearest template distance."""
    results: list[PredictedFrame] = []
    if not templates:
        return results

    bit_count = len(templates[0].bits)
    for time_s, bits in frames:
        best_label = "UNKNOWN"
        best_confidence = 0.0
        best_distance = bit_count + 1

        for template in templates:
            distance = hamming(bits, template.bits)
            confidence = 1.0 - (distance / bit_count)
            if distance < best_distance:
                best_distance = distance
                best_confidence = confidence
                best_label = template.label

        if best_confidence < min_confidence:
            best_label = "UNKNOWN"

        results.append(
            PredictedFrame(
                label=best_label,
                confidence=best_confidence,
                time_s=time_s,
            )
        )
    return results


def compress_runs(
    predictions: list[PredictedFrame],
    min_run_frames: int,
) -> list[TimeRun]:
    """Compress frame-level predictions into time runs."""
    if not predictions:
        return []

    runs: list[TimeRun] = []
    start = 0
    current = predictions[0].label
    for index, item in enumerate(predictions[1:], start=1):
        if item.label == current:
            continue

        width = index - start
        if width >= min_run_frames:
            confidences = [p.confidence for p in predictions[start:index]]
            runs.append(
                TimeRun(
                    label=current,
                    start_s=predictions[start].time_s,
                    end_s=predictions[index - 1].time_s,
                    frames=width,
                    mean_confidence=sum(confidences) / len(confidences),
                )
            )

        start = index
        current = item.label

    width = len(predictions) - start
    if width >= min_run_frames:
        confidences = [p.confidence for p in predictions[start:]]
        runs.append(
            TimeRun(
                label=current,
                start_s=predictions[start].time_s,
                end_s=predictions[-1].time_s,
                frames=width,
                mean_confidence=sum(confidences) / len(confidences),
            )
        )

    return runs


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)
    if not args.reference_dir.exists():
        raise FileNotFoundError(args.reference_dir)

    templates = collect_templates(
        target=args.input,
        reference_dir=args.reference_dir,
        clock_bit=args.clock_bit,
        latch_bit=args.latch_bit,
        data_bit=args.data_bit,
        clock_edge=args.clock_edge,
        latch_edge=args.latch_edge,
        frame_bits=args.frame_bits,
    )

    samples, samplerate_hz = load_logic_capture(args.input)
    if samplerate_hz is None:
        samplerate_hz = 2_000_000

    frames_raw = extract_frames(
        samples=samples,
        samplerate_hz=samplerate_hz,
        clock_bit=args.clock_bit,
        latch_bit=args.latch_bit,
        data_bits=(args.data_bit,),
        clock_edge=args.clock_edge,
        latch_edge=args.latch_edge,
        expected_bits=args.frame_bits,
    )
    frames = [(item.time_s, item.bits) for item in frames_raw]

    print("=== Panel96 Number Timeline ===")
    print(f"input={args.input.name} samplerate={samplerate_hz}Hz frames={len(frames)}")
    print(f"templates={len(templates)} from={args.reference_dir}")

    if not frames:
        print("No valid frames extracted.")
        return 1
    if not templates:
        print("No templates learned from reference recordings.")
        return 2

    by_label: dict[str, int] = defaultdict(int)
    for item in templates:
        by_label[item.label] += 1
    print("template_labels:")
    for label, count in sorted(by_label.items(), key=lambda x: x[0]):
        print(f"  {label}: {count}")

    raw_predictions = predict_frames(frames, templates, args.min_confidence)
    raw_labels = [item.label for item in raw_predictions]
    smoothed_labels = majority_smooth(raw_labels, args.smooth_radius)

    smoothed_predictions: list[PredictedFrame] = []
    for base, label in zip(raw_predictions, smoothed_labels):
        smoothed_predictions.append(
            PredictedFrame(label=label, confidence=base.confidence, time_s=base.time_s)
        )

    runs = compress_runs(smoothed_predictions, args.min_run_frames)

    print("runs:")
    for run in runs:
        if not args.include_non_numeric and not DIGIT_LABEL.match(run.label):
            continue
        if args.mode == "temp" and not TEMP_LABEL.match(run.label):
            continue
        if args.mode == "time" and not TIME_LABEL.match(run.label):
            continue
        duration = max(0.0, run.end_s - run.start_s)
        print(
            f"  {run.label} t=[{run.start_s:.3f},{run.end_s:.3f}] "
            f"dur~{duration:.3f}s frames={run.frames} conf={run.mean_confidence:.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
