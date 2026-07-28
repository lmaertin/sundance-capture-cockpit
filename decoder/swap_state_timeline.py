#!/usr/bin/env python3
"""Summarize stable swap states and transitions from a display-bus capture.

The tool clusters decoded bursts into a small set of state families, smooths the
labels, extracts stable runs, and can emit a Markdown report with Mermaid
diagrams aligned to an optional reference video.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import load_logic_capture, parse_data_bits


@dataclass(frozen=True)
class StableRun:
    """One stable clustered state span."""

    start_index: int
    end_index: int
    label: int
    width: int
    start_time_s: float
    end_time_s: float


@dataclass(frozen=True)
class StableTransition:
    """One transition between stable runs."""

    from_label: int
    to_label: int
    at_index: int
    at_time_s: float


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Report stable swap states and transitions from one .sr file."
    )
    parser.add_argument("input", type=Path, help="Input .sr file")
    parser.add_argument(
        "--video",
        type=Path,
        default=None,
        help="Optional reference video for duration alignment.",
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
        default="4,7",
        help="Comma-separated data bits used for state clustering.",
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
        default=6,
        help="Number of dominant signatures used as clustering prototypes.",
    )
    parser.add_argument(
        "--smooth-radius",
        type=int,
        default=5,
        help="Half-window for majority smoothing over cluster labels.",
    )
    parser.add_argument(
        "--min-stable-width",
        type=int,
        default=18,
        help="Minimum burst count for a run to count as stable.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Optional Markdown report path.",
    )
    return parser.parse_args()


def active_segments(
    samples: bytes,
    bit: int,
    active_level: int,
) -> list[tuple[int, int]]:
    """Return contiguous active ranges for one gate signal."""
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(samples):
        level = (value >> bit) & 0x01
        if level == active_level and start is None:
            start = index
        elif level != active_level and start is not None:
            segments.append((start, index))
            start = None
    if start is not None:
        segments.append((start, len(samples)))
    return segments


def edge_positions(samples: bytes, bit: int, start: int, end: int) -> list[int]:
    """Return all edge positions for the selected bit inside one segment."""
    if end - start < 2:
        return []

    positions: list[int] = []
    previous = (samples[start] >> bit) & 0x01
    for index in range(start + 1, end):
        current = (samples[index] >> bit) & 0x01
        if current != previous:
            positions.append(index)
        previous = current
    return positions


def decode_symbols(
    samples: bytes,
    positions: list[int],
    data_bits: tuple[int, ...],
) -> tuple[int, ...]:
    """Decode multi-bit symbol values at sampled edge positions."""
    values: list[int] = []
    for position in positions:
        raw = samples[position]
        symbol = 0
        for bit in data_bits:
            symbol = (symbol << 1) | ((raw >> bit) & 0x01)
        values.append(symbol)
    return tuple(values)


def hamming(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    """Return Hamming distance between equal-length symbol sequences."""
    return sum(1 for a, b in zip(left, right) if a != b)


def load_bursts(
    path: Path,
    clock_bit: int,
    gate_bit: int,
    gate_active: int,
    data_bits: tuple[int, ...],
    symbols_per_burst: int,
) -> tuple[list[tuple[int, ...]], list[float], int]:
    """Load one capture and decode valid bursts."""
    samples, samplerate_hz = load_logic_capture(path)
    if samplerate_hz is None:
        samplerate_hz = 24_000_000

    segments = active_segments(samples, gate_bit, gate_active)
    bursts: list[tuple[int, ...]] = []
    times: list[float] = []
    for start, end in segments:
        positions = edge_positions(samples, clock_bit, start, end)
        if len(positions) != symbols_per_burst:
            continue
        bursts.append(decode_symbols(samples, positions, data_bits))
        center_sample = (start + end) / 2.0
        times.append(center_sample / float(samplerate_hz))
    return bursts, times, samplerate_hz


def smooth_labels(labels: list[int], radius: int) -> list[int]:
    """Apply majority smoothing to a label sequence."""
    smoothed: list[int] = []
    for index in range(len(labels)):
        start = max(0, index - radius)
        end = min(len(labels), index + radius + 1)
        smoothed.append(Counter(labels[start:end]).most_common(1)[0][0])
    return smoothed


def build_stable_runs(
    labels: list[int],
    times: list[float],
    min_width: int,
) -> list[StableRun]:
    """Compress labels into stable runs and keep wide enough spans."""
    if not labels:
        return []

    runs: list[StableRun] = []
    start = 0
    current = labels[0]
    for index, value in enumerate(labels[1:], start=1):
        if value != current:
            width = index - start
            if width >= min_width:
                runs.append(
                    StableRun(
                        start_index=start,
                        end_index=index - 1,
                        label=current,
                        width=width,
                        start_time_s=times[start],
                        end_time_s=times[index - 1],
                    )
                )
            start = index
            current = value

    width = len(labels) - start
    if width >= min_width:
        runs.append(
            StableRun(
                start_index=start,
                end_index=len(labels) - 1,
                label=current,
                width=width,
                start_time_s=times[start],
                end_time_s=times[-1],
            )
        )
    return runs


def build_transitions(runs: list[StableRun]) -> list[StableTransition]:
    """Build transitions between neighboring stable runs."""
    transitions: list[StableTransition] = []
    for left, right in zip(runs, runs[1:]):
        if left.label == right.label:
            continue
        transitions.append(
            StableTransition(
                from_label=left.label,
                to_label=right.label,
                at_index=right.start_index,
                at_time_s=right.start_time_s,
            )
        )
    return transitions


def read_video_duration(video_path: Path | None) -> float | None:
    """Return video duration in seconds when ffprobe is available."""
    if video_path is None or not video_path.exists():
        return None

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nk=1:nw=1",
        str(video_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    return float(text) if text else None


def markdown_report(
    capture_name: str,
    samplerate_hz: int,
    data_bits: tuple[int, ...],
    burst_count: int,
    stable_runs: list[StableRun],
    transitions: list[StableTransition],
    video_duration_s: float | None,
) -> str:
    """Render a Markdown report with Mermaid diagrams."""
    lines: list[str] = []
    lines.append(f"# Swap Timeline: {capture_name}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- samplerate: {samplerate_hz} Hz")
    lines.append(f"- data bits: {','.join(f'D{bit}' for bit in data_bits)}")
    lines.append(f"- usable bursts: {burst_count}")
    lines.append(f"- stable runs: {len(stable_runs)}")
    lines.append(f"- stable transitions: {len(transitions)}")
    if video_duration_s is not None:
        lines.append(f"- video duration: {video_duration_s:.3f} s")
    lines.append("")
    lines.append("## Stable Runs")
    lines.append("")
    for index, run in enumerate(stable_runs, start=1):
        duration = max(0.0, run.end_time_s - run.start_time_s)
        lines.append(
            f"- run {index}: label {run.label}, {run.start_time_s:.3f}s -> "
            f"{run.end_time_s:.3f}s, duration ~{duration:.3f}s, width={run.width}"
        )
    lines.append("")
    lines.append("## State Timeline")
    lines.append("")
    lines.append("```mermaid")
    lines.append("timeline")
    lines.append(f"    title {capture_name} stable state timeline")
    lines.append("    section Stable runs")
    for index, run in enumerate(stable_runs, start=1):
        lines.append(
            f"      run {index} / state {run.label} : "
            f"{run.start_time_s:.3f}s to {run.end_time_s:.3f}s"
        )
    lines.append("```")
    lines.append("")
    lines.append("## Transition Graph")
    lines.append("")
    lines.append("```mermaid")
    lines.append("stateDiagram-v2")
    lines.append("    [*] --> state0")
    if stable_runs:
        lines.append(f"    state{stable_runs[0].label} --> [*]")
    for transition in transitions:
        lines.append(
            f"    state{transition.from_label} --> state{transition.to_label}: "
            f"{transition.at_time_s:.3f}s"
        )
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)

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
        return 0

    counts = Counter(bursts)
    prototypes = [signature for signature, _ in counts.most_common(args.top_prototypes)]
    labels = []
    for burst in bursts:
        distances = [hamming(burst, proto) for proto in prototypes]
        labels.append(min(range(len(distances)), key=lambda index: distances[index]))

    smoothed = smooth_labels(labels, args.smooth_radius)
    stable_runs = build_stable_runs(smoothed, times, args.min_stable_width)
    transitions = build_transitions(stable_runs)
    video_duration_s = read_video_duration(args.video)

    print("=== Swap State Timeline ===")
    print(
        f"file={args.input.name} samplerate={samplerate_hz}Hz "
        f"usable_bursts={len(bursts)} data={','.join(f'D{bit}' for bit in data_bits)}"
    )
    print(f"top_signature_counts={[count for _, count in counts.most_common(8)]}")
    if video_duration_s is not None:
        print(f"video_duration={video_duration_s:.3f}s")
    print(f"stable_runs={len(stable_runs)} transitions={len(transitions)}")

    for index, run in enumerate(stable_runs, start=1):
        duration = max(0.0, run.end_time_s - run.start_time_s)
        print(
            f"run{index}: label={run.label} t=[{run.start_time_s:.3f},{run.end_time_s:.3f}] "
            f"dur~{duration:.3f}s width={run.width}"
        )

    if transitions:
        print("transitions:")
        for transition in transitions:
            print(
                f"  {transition.from_label}->{transition.to_label} "
                f"at {transition.at_time_s:.3f}s"
            )

    if args.markdown_output is not None:
        report = markdown_report(
            capture_name=args.input.name,
            samplerate_hz=samplerate_hz,
            data_bits=data_bits,
            burst_count=len(bursts),
            stable_runs=stable_runs,
            transitions=transitions,
            video_duration_s=video_duration_s,
        )
        args.markdown_output.write_text(report, encoding="utf-8")
        print(f"markdown_report={args.markdown_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())