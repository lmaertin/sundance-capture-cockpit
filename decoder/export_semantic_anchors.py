#!/usr/bin/env python3
"""Export compact semantic_anchors candidates from panel96 frame streams.

This tool can aggregate multiple recordings, detect dominant alternating
phase-pairs, and merge near-identical pairs into compact clusters.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder.boot_align import load_logic_capture
from decoder.frame96_mapper import extract_frames


@dataclass(frozen=True)
class PairStat:
    """Observed transition pair between two signatures."""

    left: str
    right: str
    count: int


def normalize_bits_to_hex(bits: tuple[int, ...]) -> str:
    """Convert bit tuple to 24-hex form and keep the lower 80 bits."""
    bit_string = "".join("1" if value else "0" for value in bits)
    raw_hex = f"{int(bit_string, 2):024X}"
    return raw_hex[-20:]


def pair_key(sig_a: str, sig_b: str) -> tuple[str, str]:
    """Return deterministic ordered key for two signatures."""
    return (sig_a, sig_b) if sig_a <= sig_b else (sig_b, sig_a)


def hamming_hex(left: str, right: str) -> int:
    """Return bit Hamming distance for equal-length hex strings."""
    left_bits = bin(int(left, 16))[2:].zfill(len(left) * 4)
    right_bits = bin(int(right, 16))[2:].zfill(len(right) * 4)
    return sum(a != b for a, b in zip(left_bits, right_bits))


def pair_distance(a: tuple[str, str], b: tuple[str, str]) -> int:
    """Distance between two ordered pairs, allowing phase swap alignment."""
    direct = hamming_hex(a[0], b[0]) + hamming_hex(a[1], b[1])
    swapped = hamming_hex(a[0], b[1]) + hamming_hex(a[1], b[0])
    return min(direct, swapped)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export semantic_anchors from panel96 recordings."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input .sr recordings")
    parser.add_argument("--clock-bit", type=int, default=7)
    parser.add_argument("--latch-bit", type=int, default=6)
    parser.add_argument("--data-bit", type=int, default=4)
    parser.add_argument("--clock-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--latch-edge", choices=("rising", "falling"), default="rising")
    parser.add_argument("--expected-bits", type=int, default=96)
    parser.add_argument(
        "--min-pair-count",
        type=int,
        default=20,
        help="Minimum alternating count before a pair is considered.",
    )
    parser.add_argument(
        "--max-states",
        type=int,
        default=8,
        help="Maximum number of state pairs to export.",
    )
    parser.add_argument(
        "--cluster-distance",
        type=int,
        default=0,
        help="Merge pairs with distance <= N (0 disables merging).",
    )
    parser.add_argument(
        "--label-prefix",
        default="S",
        help="Prefix for generated labels (S1, S2, ...).",
    )
    parser.add_argument(
        "--time-safe-labels",
        action="store_true",
        help="Generate labels suitable for sigrok-cli option parsing (no colon).",
    )
    return parser.parse_args()


def expand_inputs(paths: list[Path]) -> list[Path]:
    """Expand directories into recursive .sr lists and deduplicate by path."""
    files: list[Path] = []
    for item in paths:
        if item.is_dir():
            files.extend(sorted(item.rglob("*.sr")))
        else:
            files.append(item)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def collect_counts(
    files: list[Path],
    clock_bit: int,
    latch_bit: int,
    data_bit: int,
    clock_edge: str,
    latch_edge: str,
    expected_bits: int,
) -> tuple[Counter[str], Counter[tuple[str, str]], int]:
    """Collect global signature and pair counts across files."""
    signature_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    total_frames = 0

    for path in files:
        if not path.exists():
            continue
        try:
            samples, samplerate_hz = load_logic_capture(path)
        except Exception:
            continue
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
            expected_bits=expected_bits,
        )
        if not frames:
            continue

        signatures = [normalize_bits_to_hex(frame.bits) for frame in frames]
        signature_counts.update(signatures)
        total_frames += len(signatures)

        previous: str | None = None
        for signature in signatures:
            if previous is not None and previous != signature:
                pair_counts[pair_key(previous, signature)] += 1
            previous = signature

    return signature_counts, pair_counts, total_frames


def cluster_pairs(
    pair_counts: Counter[tuple[str, str]],
    min_count: int,
    max_states: int,
    cluster_distance: int,
) -> list[PairStat]:
    """Select dominant pairs and optionally merge near-identical variants."""
    candidates = [item for item in pair_counts.items() if item[1] >= min_count]
    candidates.sort(key=lambda item: item[1], reverse=True)

    if not candidates:
        return []

    if cluster_distance <= 0:
        out: list[PairStat] = []
        for (left, right), count in candidates[:max_states]:
            out.append(PairStat(left=left, right=right, count=count))
        return out

    clusters: list[dict[str, object]] = []
    for pair, count in candidates:
        assigned = False
        for cluster in clusters:
            center = cluster["center"]
            assert isinstance(center, tuple)
            if pair_distance(pair, center) <= cluster_distance:
                cluster["count"] = int(cluster["count"]) + count
                assigned = True
                break
        if not assigned:
            clusters.append({"center": pair, "count": count})

    clusters.sort(key=lambda item: int(item["count"]), reverse=True)

    out: list[PairStat] = []
    for cluster in clusters[:max_states]:
        center = cluster["center"]
        assert isinstance(center, tuple)
        out.append(
            PairStat(
                left=center[0],
                right=center[1],
                count=int(cluster["count"]),
            )
        )
    return out


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    files = expand_inputs(args.inputs)
    if not files:
        print("No input files found.")
        return 0

    signature_counts, pair_counts, total_frames = collect_counts(
        files=files,
        clock_bit=args.clock_bit,
        latch_bit=args.latch_bit,
        data_bit=args.data_bit,
        clock_edge=args.clock_edge,
        latch_edge=args.latch_edge,
        expected_bits=args.expected_bits,
    )

    selected = cluster_pairs(
        pair_counts=pair_counts,
        min_count=args.min_pair_count,
        max_states=args.max_states,
        cluster_distance=args.cluster_distance,
    )

    print("=== semantic_anchors export ===")
    print(f"inputs={len(files)} total_frames={total_frames}")
    print(f"unique_signatures={len(signature_counts)} unique_pairs={len(pair_counts)}")
    print("top_signatures:")
    for signature, count in signature_counts.most_common(10):
        print(f"  {count:5d} 0x{signature}")

    if not selected:
        print("\nNo stable phase-pairs above threshold.")
        print("Tip: reduce --min-pair-count or --cluster-distance.")
        return 0

    print("\nselected_pairs:")
    for index, item in enumerate(selected, start=1):
        print(f"  state{index} count={item.count} 0x{item.left}|0x{item.right}")

    anchors: list[str] = []
    for index, item in enumerate(selected, start=1):
        label = f"{args.label_prefix}{index}"
        if args.time_safe_labels:
            label = label.replace(":", "_")
        anchors.append(f"{label}=0x{item.left}|0x{item.right}")

    print("\nsemantic_anchors:")
    print(";".join(anchors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
