#!/usr/bin/env python3
"""Experimental Panel96 decoder CLI for Sigrok captures."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from capture_webui.importer import import_recording_bundle
from decoder.bus_decoder import BusLayout, decode_bursts, infer_layout
from decoder.compare import combine_window, rank_variants
from decoder.sr_reader import load_capture, validate_inputs


@dataclass(frozen=True)
class RampFieldCandidate:
    """One field candidate found in a ramp analysis window."""

    word_index: int
    field_width: int
    points: int
    slope: float
    intercept: float
    r2: float


@dataclass(frozen=True)
class RampWindowReport:
    """Best field fit and quality classification for one ramp window."""

    window_start: int
    window_end: int
    center: int
    approx_temp: float
    best: RampFieldCandidate
    quality: str


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Prototype CLI for Panel96-style Sigrok decoding."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Input .sr files, e.g. messungen/pool_26-27.sr",
    )
    parser.add_argument(
        "--max-reports",
        type=int,
        default=8,
        help="Maximum number of ranked decode variants to print.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=6,
        help="Maximum field candidates to print per variant.",
    )
    parser.add_argument(
        "--max-field-words",
        type=int,
        default=4,
        help="Maximum number of consecutive words to combine into one field.",
    )
    parser.add_argument(
        "--dump-bursts",
        nargs="*",
        type=int,
        default=None,
        help="Optional burst indices to dump for a specific decode variant.",
    )
    parser.add_argument(
        "--dump-edge",
        choices=("rising", "falling", "both"),
        default="falling",
        help="Clock edge used for burst dumps.",
    )
    parser.add_argument(
        "--dump-data-bits",
        default="4,5",
        help="Comma-separated data bit indices for burst dumps, e.g. 4,5.",
    )
    parser.add_argument(
        "--dump-word-bits",
        type=int,
        default=2,
        help="Word width used for burst dumps.",
    )
    parser.add_argument(
        "--dump-bit-order",
        choices=("msb", "lsb"),
        default="msb",
        help="Bit order used for burst dumps.",
    )
    parser.add_argument(
        "--dump-word-center",
        type=int,
        default=None,
        help="Optional word index around which the burst dump is cropped.",
    )
    parser.add_argument(
        "--dump-word-radius",
        type=int,
        default=8,
        help="Number of words printed before and after the dump center.",
    )
    parser.add_argument(
        "--ramp-start",
        type=float,
        default=None,
        help="Start temperature for single-file ramp analysis.",
    )
    parser.add_argument(
        "--ramp-end",
        type=float,
        default=None,
        help="End temperature for single-file ramp analysis.",
    )
    parser.add_argument(
        "--window-bursts",
        type=int,
        default=80,
        help="Burst count per analysis window in ramp mode.",
    )
    parser.add_argument(
        "--window-step",
        type=int,
        default=20,
        help="Burst step between consecutive windows in ramp mode.",
    )
    parser.add_argument(
        "--window-top-fields",
        type=int,
        default=5,
        help="Maximum field candidates printed per window in ramp mode.",
    )
    parser.add_argument(
        "--ramp-min-points",
        type=int,
        default=28,
        help="Minimum data points required for one ramp field fit.",
    )
    parser.add_argument(
        "--ramp-min-r2",
        type=float,
        default=0.60,
        help="Minimum R^2 required for one ramp field fit.",
    )
    parser.add_argument(
        "--ramp-edge",
        choices=("rising", "falling", "both"),
        default="falling",
        help="Clock edge used in ramp mode.",
    )
    parser.add_argument(
        "--ramp-data-bits",
        default="4,5",
        help="Comma-separated data bits for ramp mode, e.g. 4,5.",
    )
    parser.add_argument(
        "--ramp-word-bits",
        type=int,
        default=2,
        help="Word width used in ramp mode.",
    )
    parser.add_argument(
        "--ramp-bit-order",
        choices=("msb", "lsb"),
        default="msb",
        help="Bit order used in ramp mode.",
    )
    parser.add_argument(
        "--ramp-report-limit",
        type=int,
        default=40,
        help="Maximum number of ramp windows printed in the summary table.",
    )
    parser.add_argument(
        "--annotation-json",
        nargs="*",
        type=Path,
        default=None,
        help="Optional annotation JSON files for the input captures. If omitted, the decoder looks for sibling .json files.",
    )
    return parser.parse_args()


def parse_data_bits(text: str) -> tuple[int, ...]:
    """Parse a comma-separated list of bit indices."""
    parts = [item.strip() for item in text.split(",") if item.strip()]
    if not parts:
        raise ValueError("At least one dump data bit must be specified.")
    bits = tuple(int(item) for item in parts)
    if any(bit < 0 or bit > 7 for bit in bits):
        raise ValueError("Dump data bits must be in range 0..7.")
    return bits


def format_layout(layout: BusLayout) -> str:
    """Render one inferred bus layout as text."""
    active = ", ".join(
        f"D{bit}(edges={layout.bit_stats[bit].transitions},duty={layout.bit_stats[bit].ones_ratio:.4f})"
        for bit in layout.active_bits
    )
    return (
        f"{layout.capture.name}: step={layout.capture.step.from_temp}->{layout.capture.step.to_temp} "
        f"clock=D{layout.clock_bit} gate=D{layout.gate_bit} active={layout.gate_active_level} "
        f"bursts={len(layout.burst_ranges)}\n"
        f"  active bits: {active}"
    )


def linear_fit(x_values: list[float], y_values: list[float]) -> tuple[float, float, float] | None:
    """Return slope, intercept, and R^2 for a least-squares linear fit."""
    count = len(x_values)
    if count != len(y_values) or count < 2:
        return None

    mean_x = sum(x_values) / count
    mean_y = sum(y_values) / count
    ss_xx = sum((value - mean_x) ** 2 for value in x_values)
    if ss_xx == 0:
        return None

    ss_xy = sum((x_values[index] - mean_x) * (y_values[index] - mean_y) for index in range(count))
    slope = ss_xy / ss_xx
    intercept = mean_y - (slope * mean_x)

    ss_tot = sum((value - mean_y) ** 2 for value in y_values)
    if ss_tot == 0:
        return None

    ss_res = sum((y_values[index] - ((slope * x_values[index]) + intercept)) ** 2 for index in range(count))
    r2 = 1.0 - (ss_res / ss_tot)
    return slope, intercept, r2


def ramp_temperature_at(
    burst_index: int,
    burst_count: int,
    start_temp: float,
    end_temp: float,
) -> float:
    """Map a burst index to an approximate ramp temperature."""
    if burst_count <= 1:
        return start_temp
    progress = burst_index / (burst_count - 1)
    return start_temp + ((end_temp - start_temp) * progress)


def fit_ramp_fields_for_window(
    bursts: list[list[int]],
    window_start: int,
    window_end: int,
    start_temp: float,
    end_temp: float,
    word_bits: int,
    max_field_words: int,
    min_points: int,
    min_r2: float,
    top_fields: int,
) -> list[RampFieldCandidate]:
    """Fit candidate fields in one burst window against ramp temperature."""
    if window_end <= window_start:
        return []

    max_len = 0
    for burst_index in range(window_start, window_end):
        max_len = max(max_len, len(bursts[burst_index]))
    if max_len == 0:
        return []

    candidates: list[RampFieldCandidate] = []
    for field_width in range(1, max_field_words + 1):
        if field_width > max_len:
            break
        for word_index in range(0, max_len - field_width + 1):
            x_values: list[float] = []
            y_values: list[float] = []
            for burst_index in range(window_start, window_end):
                words = bursts[burst_index]
                if len(words) < word_index + field_width:
                    continue
                x_values.append(
                    ramp_temperature_at(
                        burst_index,
                        len(bursts),
                        start_temp,
                        end_temp,
                    )
                )
                y_values.append(float(combine_window(words, word_index, field_width, word_bits)))

            if len(x_values) < min_points:
                continue

            fitted = linear_fit(x_values, y_values)
            if fitted is None:
                continue
            slope, intercept, r2 = fitted
            if r2 < min_r2:
                continue

            candidates.append(
                RampFieldCandidate(
                    word_index=word_index,
                    field_width=field_width,
                    points=len(x_values),
                    slope=slope,
                    intercept=intercept,
                    r2=r2,
                )
            )

    candidates.sort(
        key=lambda item: (
            -item.r2,
            -item.points,
            item.field_width,
            abs(item.slope),
            item.word_index,
        )
    )
    return candidates[:top_fields]


def classify_ramp_quality(
    candidate: RampFieldCandidate,
    window_size: int,
) -> str:
    """Classify ramp fit quality into stable, uncertain, or disturbance."""
    coverage = candidate.points / max(1, window_size)
    slope_ok = abs(candidate.slope) >= 0.25

    if candidate.r2 >= 0.80 and coverage >= 0.80 and slope_ok:
        return "stable"
    if candidate.r2 >= 0.60 and coverage >= 0.60:
        return "uncertain"
    return "disturbance"


def print_ramp_table(reports: list[RampWindowReport], limit: int) -> None:
    """Print one-line table rows for ramp windows."""
    if not reports:
        print("No ramp window reports available.")
        return

    print(
        "window_start window_end center temp field_word width points r2 slope intercept quality"
    )
    for item in reports[:limit]:
        best = item.best
        print(
            f"{item.window_start:04d} {item.window_end:04d} {item.center:04d} "
            f"{item.approx_temp:6.2f} {best.word_index:03d} {best.field_width:02d} "
            f"{best.points:03d} {best.r2:0.4f} {best.slope:+0.4f} {best.intercept:+0.4f} "
            f"{item.quality}"
        )


def print_ramp_analysis(args: argparse.Namespace, layouts: list[BusLayout]) -> None:
    """Run and print a sliding-window ramp analysis for one capture."""
    if args.ramp_start is None and args.ramp_end is None:
        return
    if args.ramp_start is None or args.ramp_end is None:
        raise ValueError("Both --ramp-start and --ramp-end must be provided.")
    if len(layouts) != 1:
        raise ValueError("Ramp analysis expects exactly one input capture file.")
    if args.window_bursts < 2:
        raise ValueError("--window-bursts must be at least 2.")
    if args.window_step < 1:
        raise ValueError("--window-step must be at least 1.")

    layout = layouts[0]
    data_bits = parse_data_bits(args.ramp_data_bits)
    bursts = decode_bursts(
        layout,
        edge=args.ramp_edge,
        data_bits=data_bits,
        word_bits=args.ramp_word_bits,
        bit_order=args.ramp_bit_order,
    )
    burst_count = len(bursts)
    if burst_count == 0:
        print("\n=== Ramp analysis ===")
        print("No bursts available for ramp analysis.")
        return

    print("\n=== Ramp analysis ===")
    print(
        f"variant edge={args.ramp_edge} data={','.join(f'D{bit}' for bit in data_bits)} "
        f"word_bits={args.ramp_word_bits} bit_order={args.ramp_bit_order} "
        f"temp={args.ramp_start}->{args.ramp_end} bursts={burst_count}"
    )

    reports: list[RampWindowReport] = []
    for window_start in range(0, burst_count, args.window_step):
        window_end = min(burst_count, window_start + args.window_bursts)
        window_size = window_end - window_start
        if window_size < max(2, args.ramp_min_points // 2):
            continue

        top = fit_ramp_fields_for_window(
            bursts=bursts,
            window_start=window_start,
            window_end=window_end,
            start_temp=args.ramp_start,
            end_temp=args.ramp_end,
            word_bits=args.ramp_word_bits,
            max_field_words=args.max_field_words,
            min_points=args.ramp_min_points,
            min_r2=args.ramp_min_r2,
            top_fields=args.window_top_fields,
        )
        if not top:
            continue

        center = (window_start + window_end - 1) // 2
        approx_temp = ramp_temperature_at(center, burst_count, args.ramp_start, args.ramp_end)
        best = top[0]
        quality = classify_ramp_quality(best, window_size)
        reports.append(
            RampWindowReport(
                window_start=window_start,
                window_end=window_end - 1,
                center=center,
                approx_temp=approx_temp,
                best=best,
                quality=quality,
            )
        )

    if not reports:
        print("No ramp field candidates matched the current thresholds.")
        return

    reports.sort(
        key=lambda item: (
            item.quality != "stable",
            item.quality == "disturbance",
            -item.best.r2,
            -item.best.points,
            item.window_start,
        )
    )

    stable = sum(1 for item in reports if item.quality == "stable")
    uncertain = sum(1 for item in reports if item.quality == "uncertain")
    disturbance = len(reports) - stable - uncertain
    print(
        f"windows matched={len(reports)} stable={stable} "
        f"uncertain={uncertain} disturbance={disturbance}"
    )
    print_ramp_table(reports, args.ramp_report_limit)


def print_burst_dumps(args: argparse.Namespace, layouts: list[BusLayout]) -> None:
    """Print decoded words for selected bursts across all captures."""
    if not args.dump_bursts:
        return

    data_bits = parse_data_bits(args.dump_data_bits)
    per_capture = [
        decode_bursts(
            layout,
            edge=args.dump_edge,
            data_bits=data_bits,
            word_bits=args.dump_word_bits,
            bit_order=args.dump_bit_order,
        )
        for layout in layouts
    ]

    print("\n=== Burst dumps ===")
    print(
        f"variant edge={args.dump_edge} data={','.join(f'D{bit}' for bit in data_bits)} "
        f"word_bits={args.dump_word_bits} bit_order={args.dump_bit_order}"
    )

    for burst_index in args.dump_bursts:
        print(f"\nburst={burst_index:03d}")
        for layout, bursts in zip(layouts, per_capture):
            if burst_index >= len(bursts):
                print(
                    f"  {layout.capture.step.from_temp}->{layout.capture.step.to_temp}: missing"
                )
                continue

            words = bursts[burst_index]
            start = 0
            end = len(words)
            if args.dump_word_center is not None:
                start = max(0, args.dump_word_center - args.dump_word_radius)
                end = min(len(words), args.dump_word_center + args.dump_word_radius + 1)

            values = " ".join(str(word) for word in words[start:end])
            print(
                f"  {layout.capture.step.from_temp}->{layout.capture.step.to_temp} "
                f"len={len(words)} words[{start}:{max(start, end - 1)}]: {values}"
            )


def format_temperature_map(scale: float | None, offset: float | None) -> str:
    """Render an estimated linear mapping from field values to temperatures."""
    if scale is None or offset is None:
        return ""
    return f" temp≈({scale:.4f}*value)+{offset:.4f}"


def resolve_annotation_paths(inputs: list[Path], explicit: list[Path] | None) -> list[Path | None]:
    """Resolve annotation JSON files for each input capture."""
    if explicit is not None:
        if len(explicit) != len(inputs):
            raise ValueError("The number of --annotation-json files must match the number of input captures.")
        return list(explicit)

    resolved: list[Path | None] = []
    for path in inputs:
        candidate = path.with_suffix(".json")
        resolved.append(candidate if candidate.exists() else None)
    return resolved


def summarize_annotation_bundle(bundle: dict[str, object]) -> dict[str, object]:
    """Create a compact summary of imported annotation events for CLI output."""
    annotations = bundle.get("annotations", []) or []
    display_states: list[str] = []
    button_presses = 0
    sequence: list[str] = []

    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        kind = str(annotation.get("kind", ""))
        payload = annotation.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        if kind == "display_state":
            text = str(payload.get("text", ""))
            if text:
                display_states.append(text)
                sequence.append(f"display:{text}")
        elif kind == "button_press":
            button_presses += 1
            sequence.append("button")

    return {
        "annotation_count": len(annotations),
        "display_state_count": len(display_states),
        "button_press_count": button_presses,
        "display_states": display_states,
        "sequence": sequence,
    }


def print_annotation_comparison(captures: list[object], annotation_paths: list[Path | None]) -> None:
    """Print a human-readable comparison summary for imported annotation JSON files."""
    print("\n=== Annotation comparison ===")
    for capture, annotation_path in zip(captures, annotation_paths, strict=True):
        capture_name = getattr(capture, "name", str(capture))
        if annotation_path is None or not annotation_path.exists():
            print(f"{capture_name}: no annotation JSON found")
            continue

        bundle = import_recording_bundle(capture.path, annotation_path)
        summary = summarize_annotation_bundle(bundle)
        display_states = ", ".join(summary["display_states"]) if summary["display_states"] else "(none)"
        sequence = " -> ".join(summary["sequence"]) if summary["sequence"] else "(none)"
        print(
            f"{capture_name}: annotations={summary['annotation_count']} "
            f"display_states={summary['display_state_count']} button_presses={summary['button_press_count']}"
        )
        print(f"  display sequence: {display_states}")
        print(f"  event flow: {sequence}")


def main() -> int:
    """Program entry point."""
    args = parse_args()
    input_paths = validate_inputs(args.inputs)

    captures = [load_capture(path) for path in input_paths]
    captures.sort(key=lambda item: item.step.from_temp)
    layouts = [infer_layout(capture) for capture in captures]

    print("=== Inferred bus layout ===")
    for layout in layouts:
        print(format_layout(layout))

    annotation_paths = resolve_annotation_paths(input_paths, args.annotation_json)
    print_annotation_comparison(captures, annotation_paths)

    reports = rank_variants(
        layouts=layouts,
        max_reports=args.max_reports,
        max_candidates=args.max_candidates,
        max_field_words=args.max_field_words,
    )
    print("\n=== Ranked decode variants ===")
    if not reports:
        print("No monotonic field candidates found.")
    else:
        for index, report in enumerate(reports, start=1):
            data_bits = ",".join(f"D{bit}" for bit in report.variant.data_bits)
            print(
                f"#{index} edge={report.variant.edge} data={data_bits} "
                f"word_bits={report.variant.word_bits} bit_order={report.variant.bit_order} "
                f"bursts={report.burst_count} identical={report.identical_bursts} score={report.score}"
            )
            for candidate in report.field_candidates:
                values = ", ".join(str(value) for value in candidate.values)
                mapping = format_temperature_map(
                    candidate.temperature_scale,
                    candidate.temperature_offset,
                )
                print(
                    f"  burst={candidate.burst_index:03d} word={candidate.word_index:03d} "
                    f"width={candidate.field_width} values=[{values}] step={candidate.step:+d}"
                    f"{mapping}"
                )

    print_burst_dumps(args, layouts)
    print_ramp_analysis(args, layouts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())