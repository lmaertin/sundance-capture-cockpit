#!/usr/bin/env python3
"""Analyze recording bundles and export collaboration-friendly summaries.

The script scans a directory for pairs of:
- <basename>.sr
- <basename>.json

It computes per-recording metrics and aggregate statistics to support
community reverse engineering work.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from capture_webui.importer import parse_capture_summary


@dataclass(frozen=True)
class SignalMetrics:
    """Signal metrics extracted from one .sr file."""

    sample_count: int
    bit_transitions: list[int]
    bit_ones_ratio: list[float]

    @property
    def max_bit_transitions(self) -> int:
        """Maximum transition count among all bits."""
        if not self.bit_transitions:
            return 0
        return max(self.bit_transitions)

    @property
    def active_bits(self) -> int:
        """Number of bits with at least one transition."""
        return sum(1 for count in self.bit_transitions if count > 0)


@dataclass(frozen=True)
class RecordingAnalysis:
    """Computed metrics and classifications for one recording bundle."""

    basename: str
    json_path: Path
    sr_path: Path
    has_sr_pair: bool
    recording_id: str
    status: str
    samplerate: str
    channels: str
    start_time: str
    end_time: str
    annotation_count: int
    button_press_count: int
    display_state_count: int
    other_event_count: int
    unique_buttons: list[str]
    unique_symbols: list[str]
    display_values: list[str]
    symbol_transition_count: int
    display_value_changes: int
    signal_metrics: SignalMetrics | None
    decoder_usable: bool
    quality: str
    quality_reasons: list[str]


@dataclass(frozen=True)
class AnalysisConfig:
    """Tunable analysis thresholds."""

    min_max_transitions: int
    min_active_bits: int


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze .sr/.json recording bundles and generate markdown/csv "
            "summaries for collaborative protocol reverse engineering."
        )
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing recording bundles",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Path for markdown report (default: <input_dir>/recordings_analysis.md)",
    )
    parser.add_argument(
        "--csv-out",
        type=Path,
        default=None,
        help="Path for csv report (default: <input_dir>/recordings_analysis.csv)",
    )
    parser.add_argument(
        "--min-max-transitions",
        type=int,
        default=100,
        help="Minimum max bit transitions for decoder-usable classification",
    )
    parser.add_argument(
        "--min-active-bits",
        type=int,
        default=2,
        help="Minimum active bits for decoder-usable classification",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, object]:
    """Load one JSON file as dictionary."""
    payload_obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError(f"Expected object in {path}")
    return payload_obj


def as_dict(value: object) -> dict[str, object]:
    """Return dictionary value or an empty dictionary."""
    if isinstance(value, dict):
        return value
    return {}


def as_list(value: object) -> list[object]:
    """Return list value or an empty list."""
    if isinstance(value, list):
        return value
    return []


def as_str(value: object, default: str = "") -> str:
    """Return string value or default."""
    if isinstance(value, str):
        return value
    return default


def as_int(value: object, default: int = 0) -> int:
    """Return integer value or default."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return default


def as_str_list(value: object) -> list[str]:
    """Normalize list values to a list of strings."""
    normalized: list[str] = []
    for item in as_list(value):
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append(text)
    return normalized


def safe_join(items: list[str], separator: str = "|") -> str:
    """Join list values for csv/markdown cells."""
    if not items:
        return ""
    return separator.join(items)


def signal_metrics_for(sr_path: Path) -> SignalMetrics | None:
    """Extract signal metrics from one .sr file."""
    if not sr_path.exists() or not sr_path.is_file():
        return None

    summary = parse_capture_summary(sr_path)
    stats_obj = summary.get("stats")
    sample_count_obj = summary.get("sample_count")

    transitions: list[int] = []
    ones_ratios: list[float] = []
    for item_obj in as_list(stats_obj):
        item = as_dict(item_obj)
        transitions.append(as_int(item.get("transitions")))
        ones_ratio_obj = item.get("ones_ratio")
        if isinstance(ones_ratio_obj, float):
            ones_ratios.append(ones_ratio_obj)
        elif isinstance(ones_ratio_obj, int):
            ones_ratios.append(float(ones_ratio_obj))
        else:
            ones_ratios.append(0.0)

    sample_count = as_int(sample_count_obj)
    return SignalMetrics(
        sample_count=sample_count,
        bit_transitions=transitions,
        bit_ones_ratio=ones_ratios,
    )


def classify_quality(
    has_sr_pair: bool,
    button_press_count: int,
    display_state_count: int,
    symbol_transition_count: int,
    display_value_changes: int,
    signal_metrics: SignalMetrics | None,
    config: AnalysisConfig,
) -> tuple[bool, str, list[str]]:
    """Classify decoder usability and quality level."""
    reasons: list[str] = []

    if not has_sr_pair:
        reasons.append("missing_sr_pair")
    if button_press_count <= 0:
        reasons.append("no_button_press")
    if display_state_count <= 0:
        reasons.append("no_display_state")

    if signal_metrics is None:
        reasons.append("no_signal_metrics")
    else:
        if signal_metrics.max_bit_transitions < config.min_max_transitions:
            reasons.append("low_signal_activity")
        if signal_metrics.active_bits < config.min_active_bits:
            reasons.append("too_few_active_bits")

    decoder_usable = len(reasons) == 0
    dynamics = symbol_transition_count + display_value_changes

    if decoder_usable and dynamics >= 1:
        return True, "A", ["clean_action_and_state_trace"]
    if decoder_usable:
        return True, "B", ["usable_but_low_state_dynamics"]
    return False, "C", reasons


def analyze_bundle(json_path: Path, config: AnalysisConfig) -> RecordingAnalysis:
    """Analyze one recording bundle from JSON plus optional SR pair."""
    payload = load_json(json_path)
    recording = as_dict(payload.get("recording"))
    annotations = as_list(payload.get("annotations"))

    basename = json_path.stem
    sr_path = json_path.with_suffix(".sr")
    has_sr_pair = sr_path.exists()

    button_counter: Counter[str] = Counter()
    symbol_counter: Counter[str] = Counter()
    value_counter: Counter[str] = Counter()

    button_press_count = 0
    display_state_count = 0
    other_event_count = 0
    symbol_transition_count = 0
    display_value_changes = 0

    prev_symbol_set: set[str] | None = None
    prev_display_value: str | None = None

    for annotation_obj in annotations:
        annotation = as_dict(annotation_obj)
        kind = as_str(annotation.get("kind"), default="unknown")
        payload_obj = as_dict(annotation.get("payload"))

        if kind == "button_press":
            button_press_count += 1
            button_code = as_str(payload_obj.get("button"), default="?")
            button_name = as_str(payload_obj.get("name"), default="?")
            button_counter[f"{button_code}:{button_name}"] += 1
            continue

        if kind == "display_state":
            display_state_count += 1

            display_value = as_str(payload_obj.get("value")).strip()
            symbols = as_str_list(payload_obj.get("symbols"))
            current_symbol_set = set(symbols)

            if display_value:
                value_counter[display_value] += 1

            for symbol in symbols:
                symbol_counter[symbol] += 1

            if prev_symbol_set is not None and current_symbol_set != prev_symbol_set:
                symbol_transition_count += 1
            if prev_display_value is not None and display_value and display_value != prev_display_value:
                display_value_changes += 1

            prev_symbol_set = current_symbol_set
            prev_display_value = display_value or prev_display_value
            continue

        other_event_count += 1

    signal_metrics = signal_metrics_for(sr_path)
    decoder_usable, quality, quality_reasons = classify_quality(
        has_sr_pair=has_sr_pair,
        button_press_count=button_press_count,
        display_state_count=display_state_count,
        symbol_transition_count=symbol_transition_count,
        display_value_changes=display_value_changes,
        signal_metrics=signal_metrics,
        config=config,
    )

    return RecordingAnalysis(
        basename=basename,
        json_path=json_path,
        sr_path=sr_path,
        has_sr_pair=has_sr_pair,
        recording_id=as_str(recording.get("id")),
        status=as_str(recording.get("status")),
        samplerate=as_str(recording.get("samplerate")),
        channels=as_str(recording.get("channels")),
        start_time=as_str(recording.get("start_time")),
        end_time=as_str(recording.get("end_time")),
        annotation_count=len(annotations),
        button_press_count=button_press_count,
        display_state_count=display_state_count,
        other_event_count=other_event_count,
        unique_buttons=sorted(button_counter.keys()),
        unique_symbols=sorted(symbol_counter.keys()),
        display_values=sorted(value_counter.keys()),
        symbol_transition_count=symbol_transition_count,
        display_value_changes=display_value_changes,
        signal_metrics=signal_metrics,
        decoder_usable=decoder_usable,
        quality=quality,
        quality_reasons=quality_reasons,
    )


def write_csv(path: Path, analyses: list[RecordingAnalysis]) -> None:
    """Write per-recording metrics as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "basename",
                "recording_id",
                "status",
                "samplerate",
                "channels",
                "annotation_count",
                "button_press_count",
                "display_state_count",
                "other_event_count",
                "unique_buttons",
                "unique_symbols",
                "display_values",
                "symbol_transition_count",
                "display_value_changes",
                "sample_count",
                "max_bit_transitions",
                "active_bits",
                "decoder_usable",
                "quality",
                "quality_reasons",
            ]
        )

        for row in analyses:
            sample_count = row.signal_metrics.sample_count if row.signal_metrics else 0
            max_bit_transitions = row.signal_metrics.max_bit_transitions if row.signal_metrics else 0
            active_bits = row.signal_metrics.active_bits if row.signal_metrics else 0
            writer.writerow(
                [
                    row.basename,
                    row.recording_id,
                    row.status,
                    row.samplerate,
                    row.channels,
                    row.annotation_count,
                    row.button_press_count,
                    row.display_state_count,
                    row.other_event_count,
                    safe_join(row.unique_buttons),
                    safe_join(row.unique_symbols),
                    safe_join(row.display_values),
                    row.symbol_transition_count,
                    row.display_value_changes,
                    sample_count,
                    max_bit_transitions,
                    active_bits,
                    "yes" if row.decoder_usable else "no",
                    row.quality,
                    safe_join(row.quality_reasons),
                ]
            )


def aggregate_counter(values: list[list[str]]) -> Counter[str]:
    """Aggregate lists of strings into one counter."""
    counter: Counter[str] = Counter()
    for row in values:
        for item in row:
            counter[item] += 1
    return counter


def render_top(counter: Counter[str], limit: int = 10) -> str:
    """Render top frequency list for markdown."""
    if not counter:
        return "- none"

    lines: list[str] = []
    for key, count in counter.most_common(limit):
        lines.append(f"- {key}: {count}")
    return "\n".join(lines)


def write_markdown(path: Path, analyses: list[RecordingAnalysis], config: AnalysisConfig) -> None:
    """Write human-readable markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    total_annotations = sum(item.annotation_count for item in analyses)
    total_buttons = sum(item.button_press_count for item in analyses)
    total_display_states = sum(item.display_state_count for item in analyses)
    usable_count = sum(1 for item in analyses if item.decoder_usable)

    quality_counter: Counter[str] = Counter(item.quality for item in analyses)
    buttons_counter = aggregate_counter([item.unique_buttons for item in analyses])
    symbols_counter = aggregate_counter([item.unique_symbols for item in analyses])
    values_counter = aggregate_counter([item.display_values for item in analyses])

    lines: list[str] = []
    lines.append("# Recording Bundle Analysis")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Bundles analyzed: {len(analyses)}")
    lines.append(f"- Total annotations: {total_annotations}")
    lines.append(f"- Button events: {total_buttons}")
    lines.append(f"- Display state events: {total_display_states}")
    lines.append(f"- Decoder-usable bundles: {usable_count}/{len(analyses)}")
    lines.append(
        f"- Quality counts: A={quality_counter.get('A', 0)}, "
        f"B={quality_counter.get('B', 0)}, C={quality_counter.get('C', 0)}"
    )
    lines.append("")
    lines.append("## Classification Rules")
    lines.append("")
    lines.append(
        f"- Decoder-usable requires: sr pair, >=1 button_press, >=1 display_state, "
        f"max bit transitions >= {config.min_max_transitions}, active bits >= {config.min_active_bits}."
    )
    lines.append("- Quality A: decoder-usable and at least one state dynamics change.")
    lines.append("- Quality B: decoder-usable but low observed state dynamics.")
    lines.append("- Quality C: fails decoder-usable criteria.")
    lines.append("")
    lines.append("## Top Frequencies")
    lines.append("")
    lines.append("### Buttons (presence by bundle)")
    lines.append(render_top(buttons_counter))
    lines.append("")
    lines.append("### Symbols (presence by bundle)")
    lines.append(render_top(symbols_counter))
    lines.append("")
    lines.append("### Display values (presence by bundle)")
    lines.append(render_top(values_counter))
    lines.append("")
    lines.append("## Per-Bundle Table")
    lines.append("")
    lines.append(
        "| Basename | Ann | Btn | Disp | SymTrans | ValChg | MaxTrans | ActBits | Usable | Quality |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")

    for row in analyses:
        max_trans = row.signal_metrics.max_bit_transitions if row.signal_metrics else 0
        active_bits = row.signal_metrics.active_bits if row.signal_metrics else 0
        lines.append(
            "| "
            f"{row.basename} | {row.annotation_count} | {row.button_press_count} | "
            f"{row.display_state_count} | {row.symbol_transition_count} | "
            f"{row.display_value_changes} | {max_trans} | {active_bits} | "
            f"{'yes' if row.decoder_usable else 'no'} | {row.quality} |"
        )

    lines.append("")
    lines.append("## Per-Bundle Notes")
    lines.append("")
    for row in analyses:
        lines.append(f"### {row.basename}")
        lines.append("")
        lines.append(f"- Quality: {row.quality}")
        lines.append(f"- Decoder-usable: {'yes' if row.decoder_usable else 'no'}")
        lines.append(f"- Reasons: {safe_join(row.quality_reasons, ', ') or 'none'}")
        lines.append(f"- Buttons: {safe_join(row.unique_buttons, ', ') or 'none'}")
        lines.append(f"- Symbols: {safe_join(row.unique_symbols, ', ') or 'none'}")
        lines.append(f"- Display values: {safe_join(row.display_values, ', ') or 'none'}")
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_analyses(input_dir: Path, config: AnalysisConfig) -> list[RecordingAnalysis]:
    """Collect analyses for all JSON bundles in an input directory."""
    json_files = sorted(input_dir.glob("*.json"))
    analyses = [analyze_bundle(path, config=config) for path in json_files]
    analyses.sort(key=lambda item: item.basename)
    return analyses


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    input_dir = args.input_dir.resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")

    config = AnalysisConfig(
        min_max_transitions=max(0, int(args.min_max_transitions)),
        min_active_bits=max(0, int(args.min_active_bits)),
    )

    analyses = collect_analyses(input_dir, config=config)
    if not analyses:
        raise SystemExit(f"No JSON recording bundles found in: {input_dir}")

    markdown_out = args.markdown_out or (input_dir / "recordings_analysis.md")
    csv_out = args.csv_out or (input_dir / "recordings_analysis.csv")

    write_markdown(markdown_out.resolve(), analyses, config=config)
    write_csv(csv_out.resolve(), analyses)

    usable_count = sum(1 for item in analyses if item.decoder_usable)
    print(f"Analyzed bundles: {len(analyses)}")
    print(f"Decoder-usable bundles: {usable_count}/{len(analyses)}")
    print(f"Markdown report: {markdown_out}")
    print(f"CSV report: {csv_out}")


if __name__ == "__main__":
    main()