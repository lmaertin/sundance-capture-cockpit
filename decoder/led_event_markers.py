#!/usr/bin/env python3
"""Detect macro button events in Sundance display-bus captures.

This tool suppresses fast scan oscillations by aggregating bursts into
cycle-sized blocks, then searches for stronger block-to-block state jumps.
It is designed for test captures where one button is pressed repeatedly
with pauses (for example, every 3 seconds).
"""

from __future__ import annotations

import argparse
from itertools import combinations
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import load_logic_capture, parse_data_bits


@dataclass(frozen=True)
class EventCluster:
    """One clustered macro event candidate."""

    start_block: int
    end_block: int
    center_block: int
    center_time_s: float
    width_blocks: int
    peak_distance: int
    score: float


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Detect repeated macro events (button presses) in one Sundance "
            "capture by filtering out the fast display scan cycle."
        )
    )
    parser.add_argument("input", type=Path, help="Input .sr file")
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
        help="Gate/enable bit index (default: 6).",
    )
    parser.add_argument(
        "--gate-active",
        type=int,
        choices=(0, 1),
        default=0,
        help="Active gate level (default: 0).",
    )
    parser.add_argument(
        "--data-bits",
        default="4,5",
        help="Comma-separated data bits (default: 4,5).",
    )
    parser.add_argument(
        "--edge",
        choices=("rising", "falling", "both"),
        default="both",
        help="Clock edge mode used for symbol extraction.",
    )
    parser.add_argument(
        "--symbols-per-burst",
        type=int,
        default=192,
        help="Expected symbol count per burst (default: 192).",
    )
    parser.add_argument(
        "--lag-min",
        type=int,
        default=2,
        help="Minimum lag scanned for cycle estimation.",
    )
    parser.add_argument(
        "--lag-max",
        type=int,
        default=20,
        help="Maximum lag scanned for cycle estimation.",
    )
    parser.add_argument(
        "--top-signatures",
        type=int,
        default=8,
        help="Number of most frequent signatures used in block histograms.",
    )
    parser.add_argument(
        "--threshold-offset",
        type=float,
        default=2.0,
        help="Distance threshold offset above median block jump.",
    )
    parser.add_argument(
        "--cluster-gap-blocks",
        type=int,
        default=2,
        help="Maximum block gap to merge neighboring jump indices.",
    )
    parser.add_argument(
        "--min-width-blocks",
        type=int,
        default=1,
        help="Minimum width in blocks for a kept cluster.",
    )
    parser.add_argument(
        "--select-top",
        type=int,
        default=3,
        help="Number of strongest macro events to keep.",
    )
    parser.add_argument(
        "--min-separation-s",
        type=float,
        default=1.8,
        help="Minimum time separation between selected events.",
    )
    parser.add_argument(
        "--expected-gap-s",
        type=float,
        default=3.0,
        help="Expected pause between clicks for plausibility scoring.",
    )
    parser.add_argument(
        "--gap-tolerance-s",
        type=float,
        default=0.8,
        help="Absolute tolerance for expected gap checks.",
    )
    parser.add_argument(
        "--fit-count",
        type=int,
        default=0,
        help=(
            "If > 1, select a best-fit event sequence with this number of events "
            "using expected-gap plausibility."
        ),
    )
    parser.add_argument(
        "--fit-gap-weight",
        type=float,
        default=4.0,
        help="Penalty weight for gap error during best-fit sequence search.",
    )
    return parser.parse_args()


def active_segments(
    samples: bytes,
    bit: int,
    active_level: int,
) -> list[tuple[int, int]]:
    """Return contiguous sample ranges where the selected bit is active."""
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


def edge_positions(
    samples: bytes,
    bit: int,
    start: int,
    end: int,
    edge: str,
) -> list[int]:
    """Return edge positions for one burst range."""
    if end - start < 2:
        return []

    positions: list[int] = []
    prev = (samples[start] >> bit) & 0x01
    for index in range(start + 1, end):
        cur = (samples[index] >> bit) & 0x01
        if cur == prev:
            continue

        if edge == "both":
            positions.append(index)
        elif edge == "rising" and prev == 0 and cur == 1:
            positions.append(index)
        elif edge == "falling" and prev == 1 and cur == 0:
            positions.append(index)

        prev = cur

    return positions


def decode_symbols(
    samples: bytes,
    edge_idx: list[int],
    data_bits: tuple[int, ...],
) -> tuple[int, ...]:
    """Decode one symbol stream from sampled edge positions."""
    symbols: list[int] = []
    for position in edge_idx:
        value = samples[position]
        symbol = 0
        for bit in data_bits:
            symbol = (symbol << 1) | ((value >> bit) & 0x01)
        symbols.append(symbol)
    return tuple(symbols)


def l1_distance(left: list[int], right: list[int]) -> int:
    """Compute L1 distance between same-length vectors."""
    return sum(abs(a - b) for a, b in zip(left, right))


def estimate_cycle_lag(ids: list[int], lag_min: int, lag_max: int) -> tuple[int, int]:
    """Find lag with minimal mismatch count in an ID stream."""
    if lag_max < lag_min:
        raise ValueError("--lag-max must be >= --lag-min.")

    best_lag = lag_min
    best_mismatch = math.inf

    for lag in range(lag_min, lag_max + 1):
        if lag >= len(ids):
            break
        mismatch = sum(1 for i in range(len(ids) - lag) if ids[i] != ids[i + lag])
        if mismatch < best_mismatch:
            best_mismatch = mismatch
            best_lag = lag

    return best_lag, int(best_mismatch if best_mismatch is not math.inf else 0)


def cluster_indices(indices: list[int], max_gap: int) -> list[tuple[int, int]]:
    """Merge sorted indices into contiguous clusters with allowed gaps."""
    if not indices:
        return []

    clusters: list[tuple[int, int]] = []
    start = indices[0]
    end = indices[0]

    for index in indices[1:]:
        if index <= end + max_gap:
            end = index
            continue
        clusters.append((start, end))
        start = index
        end = index

    clusters.append((start, end))
    return clusters


def select_events(
    events: list[EventCluster],
    keep: int,
    min_separation_s: float,
) -> list[EventCluster]:
    """Pick strongest non-overlapping events in time."""
    ranked = sorted(events, key=lambda item: item.score, reverse=True)
    selected: list[EventCluster] = []

    for candidate in ranked:
        if any(
            abs(candidate.center_time_s - existing.center_time_s) < min_separation_s
            for existing in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) >= keep:
            break

    return sorted(selected, key=lambda item: item.center_time_s)


def select_best_fit_sequence(
    events: list[EventCluster],
    count: int,
    expected_gap_s: float,
    gap_weight: float,
) -> list[EventCluster]:
    """Select event subsequence that best matches expected inter-event gaps."""
    if count <= 1:
        return []
    if len(events) < count:
        return []

    best_combo: tuple[EventCluster, ...] | None = None
    best_objective = -math.inf

    for combo in combinations(sorted(events, key=lambda item: item.center_time_s), count):
        score_sum = sum(item.score for item in combo)
        gaps = [
            combo[index + 1].center_time_s - combo[index].center_time_s
            for index in range(len(combo) - 1)
        ]
        gap_error = sum(abs(gap - expected_gap_s) for gap in gaps)
        objective = score_sum - (gap_weight * gap_error)
        if objective > best_objective:
            best_objective = objective
            best_combo = combo

    return list(best_combo) if best_combo is not None else []


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)

    data_bits = parse_data_bits(args.data_bits)
    samples, samplerate_hz = load_logic_capture(args.input)
    if samplerate_hz is None:
        samplerate_hz = 2_000_000

    segments = active_segments(samples, args.gate_bit, args.gate_active)
    symbol_streams: list[tuple[int, ...]] = []
    burst_times_s: list[float] = []
    edge_lengths: list[int] = []

    for start, end in segments:
        edges = edge_positions(samples, args.clock_bit, start, end, args.edge)
        edge_lengths.append(len(edges))
        if len(edges) != args.symbols_per_burst:
            continue

        symbol_streams.append(decode_symbols(samples, edges, data_bits))
        center_sample = (start + end) / 2.0
        burst_times_s.append(center_sample / float(samplerate_hz))

    if not symbol_streams:
        print("No usable bursts after symbol-length filtering.")
        return 0

    counts = Counter(symbol_streams)
    signature_to_id = {
        signature: index for index, (signature, _) in enumerate(counts.most_common())
    }
    ids = [signature_to_id[signature] for signature in symbol_streams]

    lag, mismatch = estimate_cycle_lag(ids, args.lag_min, args.lag_max)
    block_size = lag
    block_count = len(ids) // block_size
    if block_count < 3:
        print("Not enough blocks for macro-event analysis.")
        return 0

    top_k = min(args.top_signatures, len(signature_to_id))
    block_vectors: list[list[int]] = []
    block_times: list[float] = []

    for block_index in range(block_count):
        start = block_index * block_size
        end = start + block_size
        block_ids = ids[start:end]
        hist = Counter(block_ids)
        block_vectors.append([hist.get(index, 0) for index in range(top_k)])

        center = (start + end - 1) // 2
        block_times.append(burst_times_s[center])

    distances = [
        l1_distance(block_vectors[i], block_vectors[i + 1])
        for i in range(len(block_vectors) - 1)
    ]
    median_distance = sorted(distances)[len(distances) // 2]
    threshold = int(max(1.0, median_distance + args.threshold_offset))
    jump_indices = [i for i, value in enumerate(distances) if value >= threshold]

    clusters = cluster_indices(jump_indices, args.cluster_gap_blocks)

    events: list[EventCluster] = []
    for start, end in clusters:
        width = end - start + 1
        if width < args.min_width_blocks:
            continue

        center = (start + end) // 2
        peak = max(distances[start : end + 1])
        score = peak * math.sqrt(width)
        events.append(
            EventCluster(
                start_block=start,
                end_block=end,
                center_block=center,
                center_time_s=block_times[min(center, len(block_times) - 1)],
                width_blocks=width,
                peak_distance=peak,
                score=score,
            )
        )

    selected = select_events(events, args.select_top, args.min_separation_s)
    fit_sequence: list[EventCluster] = []
    if args.fit_count > 1:
        fit_sequence = select_best_fit_sequence(
            events=events,
            count=args.fit_count,
            expected_gap_s=args.expected_gap_s,
            gap_weight=args.fit_gap_weight,
        )

    print("=== LED Macro Event Markers ===")
    print(
        f"file={args.input.name} samplerate={samplerate_hz}Hz samples={len(samples)}"
    )
    print(
        f"decode clock=D{args.clock_bit} gate=D{args.gate_bit}:{args.gate_active} "
        f"edge={args.edge} data={','.join(f'D{bit}' for bit in data_bits)}"
    )
    print(
        f"segments={len(segments)} usable_bursts={len(symbol_streams)} "
        f"symbols_per_burst={args.symbols_per_burst}"
    )
    print(f"edge_length_common={Counter(edge_lengths).most_common(5)}")
    print(
        f"unique_signatures={len(signature_to_id)} "
        f"top_signature_counts={[count for _, count in counts.most_common(6)]}"
    )
    print(f"cycle_lag={lag} lag_mismatch={mismatch} blocks={block_count}")
    print(
        f"block_jump_median={median_distance} threshold={threshold} "
        f"jump_count={len(jump_indices)} cluster_count={len(clusters)}"
    )

    if not selected:
        print("No macro events selected. Try lowering threshold or min separation.")
        return 0

    print("\nSelected macro events:")
    for index, event in enumerate(selected, start=1):
        print(
            f"  event{index}: time={event.center_time_s:.3f}s "
            f"block={event.center_block} width={event.width_blocks} "
            f"peak={event.peak_distance} score={event.score:.2f}"
        )

    if len(selected) >= 2:
        gaps = [
            selected[index + 1].center_time_s - selected[index].center_time_s
            for index in range(len(selected) - 1)
        ]
        print("\nInter-event gaps:")
        for index, gap in enumerate(gaps, start=1):
            delta = gap - args.expected_gap_s
            ok = abs(delta) <= args.gap_tolerance_s
            status = "OK" if ok else "off"
            print(
                f"  gap{index}: {gap:.3f}s (expected {args.expected_gap_s:.3f}s, "
                f"delta {delta:+.3f}s) -> {status}"
            )

    if fit_sequence:
        print("\nBest-fit sequence:")
        for index, event in enumerate(fit_sequence, start=1):
            print(
                f"  fit{index}: time={event.center_time_s:.3f}s "
                f"block={event.center_block} width={event.width_blocks} "
                f"peak={event.peak_distance} score={event.score:.2f}"
            )

        if len(fit_sequence) >= 2:
            fit_gaps = [
                fit_sequence[index + 1].center_time_s - fit_sequence[index].center_time_s
                for index in range(len(fit_sequence) - 1)
            ]
            print("  fit gaps:")
            for index, gap in enumerate(fit_gaps, start=1):
                delta = gap - args.expected_gap_s
                ok = abs(delta) <= args.gap_tolerance_s
                status = "OK" if ok else "off"
                print(
                    f"    gap{index}: {gap:.3f}s (expected {args.expected_gap_s:.3f}s, "
                    f"delta {delta:+.3f}s) -> {status}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
