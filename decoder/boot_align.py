"""Align and compare Sundance boot captures on a 2-bit symbol stream.

This tool extracts symbols from selected data lines on selected clock edges,
aligns captures by maximizing symbol agreement, and compares a configurable
number of boot phases using distribution distances.
"""

from __future__ import annotations

import argparse
import math
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CaptureSymbols:
    """Symbol stream extracted from one capture."""

    path: Path
    symbols: tuple[int, ...]


@dataclass(frozen=True)
class LagResult:
    """Best lag estimate between reference and candidate stream."""

    lag: int
    score: float
    compared: int


@dataclass(frozen=True)
class SegmentStats:
    """Per-segment symbol distribution summary."""

    start: int
    end: int
    distribution: tuple[float, ...]


SAMPLERATE_PATTERN = re.compile(
    r"^samplerate\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*([kMGT]?Hz)\s*$",
    re.MULTILINE,
)
SAMPLERATE_SCALE = {
    "Hz": 1,
    "kHz": 1_000,
    "MHz": 1_000_000,
    "GHz": 1_000_000_000,
    "THz": 1_000_000_000_000,
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Align boot captures on D7-clocked symbol stream and compare "
            "phase similarity."
        )
    )
    parser.add_argument("inputs", nargs="+", help="Input .sr files")
    parser.add_argument(
        "--clock-bit",
        type=int,
        default=7,
        help="Clock channel bit index (default: 7 for D7).",
    )
    parser.add_argument(
        "--data-bits",
        default="4,5",
        help="Comma-separated data channel bit indices (default: 4,5).",
    )
    parser.add_argument(
        "--edge",
        choices=("rising", "falling"),
        default="rising",
        help="Clock edge used for sampling symbols.",
    )
    parser.add_argument(
        "--max-lag",
        type=int,
        default=5000,
        help="Maximum lag (in symbols) to scan for alignment.",
    )
    parser.add_argument(
        "--align-window",
        type=int,
        default=40000,
        help="Maximum symbols used for lag estimation.",
    )
    parser.add_argument(
        "--phases",
        type=int,
        default=4,
        help="Number of boot phases to segment (default: 4).",
    )
    parser.add_argument(
        "--change-window",
        type=int,
        default=1000,
        help="Half-window in symbols for change-point scoring.",
    )
    parser.add_argument(
        "--min-gap",
        type=int,
        default=5000,
        help="Minimum gap between phase boundaries.",
    )
    return parser.parse_args()


def parse_data_bits(spec: str) -> tuple[int, ...]:
    """Convert a comma-separated bit string to a tuple of bit indices."""
    parsed = tuple(int(item.strip()) for item in spec.split(",") if item.strip())
    if not parsed:
        raise ValueError("--data-bits must contain at least one bit index.")
    if any(bit < 0 or bit > 7 for bit in parsed):
        raise ValueError("Bit indices must be in range 0..7.")
    return parsed


def parse_samplerate_hz(metadata_text: str) -> int | None:
    """Extract samplerate in Hz from Sigrok metadata text."""
    match = SAMPLERATE_PATTERN.search(metadata_text)
    if match is None:
        return None

    value_text = match.group(1)
    unit_text = match.group(2)
    multiplier = SAMPLERATE_SCALE.get(unit_text)
    if multiplier is None:
        return None
    return int(float(value_text) * multiplier)


def load_logic_capture(path: Path) -> tuple[bytes, int | None]:
    """Load logic samples and optional samplerate from a Sigrok .sr archive."""
    metadata_text: str | None = None
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if "metadata" in names:
            metadata_text = archive.read("metadata").decode("utf-8", errors="replace")

        chunk_names = [name for name in names if name.startswith("logic-1-")]
        if chunk_names:
            chunk_names.sort(key=lambda item: int(item.rsplit("-", maxsplit=1)[1]))
            samples = b"".join(archive.read(name) for name in chunk_names)
        elif "logic-1" in names:
            samples = archive.read("logic-1")
        elif "logic-1-1" in names:
            samples = archive.read("logic-1-1")
        else:
            raise ValueError(f"{path} does not contain a logic stream.")

    samplerate_hz = parse_samplerate_hz(metadata_text) if metadata_text is not None else None
    return samples, samplerate_hz


def load_logic_samples(path: Path) -> bytes:
    """Load logic samples from a Sigrok .sr archive."""
    samples, _ = load_logic_capture(path)
    return samples


def extract_symbols(
    samples: bytes,
    clock_bit: int,
    data_bits: tuple[int, ...],
    edge: str,
) -> tuple[int, ...]:
    """Extract symbol values from data bits on selected clock edges."""
    if not samples:
        return tuple()

    symbols: list[int] = []
    previous = (samples[0] >> clock_bit) & 0x01
    for value in samples[1:]:
        current = (value >> clock_bit) & 0x01
        transition = previous != current
        rising = previous == 0 and current == 1
        falling = previous == 1 and current == 0
        use_edge = transition and ((edge == "rising" and rising) or (edge == "falling" and falling))
        if use_edge:
            symbol = 0
            for bit in data_bits:
                symbol = (symbol << 1) | ((value >> bit) & 0x01)
            symbols.append(symbol)
        previous = current
    return tuple(symbols)


def best_lag(
    reference: tuple[int, ...],
    candidate: tuple[int, ...],
    max_lag: int,
    align_window: int,
) -> LagResult:
    """Find lag that maximizes equality ratio between two symbol streams."""
    best = LagResult(lag=0, score=-1.0, compared=0)
    ref_len = len(reference)
    cand_len = len(candidate)

    for lag in range(-max_lag, max_lag + 1):
        start_ref = max(0, -lag)
        start_cand = start_ref + lag
        if start_cand < 0:
            continue

        available = min(ref_len - start_ref, cand_len - start_cand, align_window)
        if available <= 0:
            continue

        matches = 0
        for index in range(available):
            if reference[start_ref + index] == candidate[start_cand + index]:
                matches += 1
        score = matches / available

        if score > best.score:
            best = LagResult(lag=lag, score=score, compared=available)

    return best


def common_reference_range(
    captures: tuple[CaptureSymbols, ...],
    lag_map: dict[Path, LagResult],
) -> tuple[int, int]:
    """Return reference index range valid for all aligned streams."""
    reference_len = len(captures[0].symbols)
    start = 0
    end = reference_len

    for capture in captures:
        lag = lag_map[capture.path].lag
        cand_len = len(capture.symbols)
        start = max(start, -lag)
        end = min(end, cand_len - lag)

    if end <= start:
        raise ValueError("No common aligned range across captures.")
    return start, end


def distribution_prefix(symbols: tuple[int, ...], alphabet_size: int) -> list[list[int]]:
    """Build prefix counters for fast symbol distribution queries."""
    prefix = [[0] * alphabet_size]
    running = [0] * alphabet_size
    for symbol in symbols:
        running = running.copy()
        running[symbol] += 1
        prefix.append(running)
    return prefix


def range_distribution(
    prefix: list[list[int]],
    start: int,
    end: int,
    alphabet_size: int,
) -> tuple[float, ...]:
    """Compute normalized symbol distribution for [start, end)."""
    total = end - start
    if total <= 0:
        return tuple(0.0 for _ in range(alphabet_size))
    values = []
    for symbol in range(alphabet_size):
        count = prefix[end][symbol] - prefix[start][symbol]
        values.append(count / total)
    return tuple(values)


def total_variation(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    """Return total variation distance between two distributions."""
    return 0.5 * sum(abs(a - b) for a, b in zip(left, right))


def select_change_points(
    symbols: tuple[int, ...],
    phases: int,
    window: int,
    min_gap: int,
    alphabet_size: int,
) -> tuple[int, ...]:
    """Select phase boundaries from strongest distribution changes."""
    if phases <= 1:
        return tuple()
    if len(symbols) < (2 * window + 1):
        return tuple()

    prefix = distribution_prefix(symbols, alphabet_size)
    scored: list[tuple[float, int]] = []
    for center in range(window, len(symbols) - window):
        left = range_distribution(prefix, center - window, center, alphabet_size)
        right = range_distribution(prefix, center, center + window, alphabet_size)
        score = total_variation(left, right)
        scored.append((score, center))

    scored.sort(reverse=True)
    chosen: list[int] = []
    for score, center in scored:
        if score <= 0.0:
            continue
        if any(abs(center - existing) < min_gap for existing in chosen):
            continue
        chosen.append(center)
        if len(chosen) >= phases - 1:
            break

    chosen.sort()
    return tuple(chosen)


def segment_statistics(
    symbols: tuple[int, ...],
    boundaries: tuple[int, ...],
    alphabet_size: int,
) -> tuple[SegmentStats, ...]:
    """Compute per-segment distributions from boundaries."""
    points = (0, *boundaries, len(symbols))
    prefix = distribution_prefix(symbols, alphabet_size)
    stats: list[SegmentStats] = []
    for start, end in zip(points, points[1:]):
        dist = range_distribution(prefix, start, end, alphabet_size)
        stats.append(SegmentStats(start=start, end=end, distribution=dist))
    return tuple(stats)


def js_divergence(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    """Compute Jensen-Shannon divergence (base 2)."""
    mixed = tuple((a + b) / 2.0 for a, b in zip(left, right))

    def kl_divergence(first: tuple[float, ...], second: tuple[float, ...]) -> float:
        value = 0.0
        for first_item, second_item in zip(first, second):
            if first_item > 0.0 and second_item > 0.0:
                value += first_item * math.log2(first_item / second_item)
        return value

    return 0.5 * kl_divergence(left, mixed) + 0.5 * kl_divergence(right, mixed)


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    input_paths = tuple(Path(item) for item in args.inputs)
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(path)

    data_bits = parse_data_bits(args.data_bits)
    alphabet_size = 1 << len(data_bits)

    captures: list[CaptureSymbols] = []
    for path in input_paths:
        samples = load_logic_samples(path)
        symbols = extract_symbols(samples, args.clock_bit, data_bits, args.edge)
        captures.append(CaptureSymbols(path=path, symbols=symbols))

    captures_tuple = tuple(captures)
    reference = captures_tuple[0]

    lag_map: dict[Path, LagResult] = {}
    lag_map[reference.path] = LagResult(lag=0, score=1.0, compared=min(len(reference.symbols), args.align_window))
    for capture in captures_tuple[1:]:
        lag_map[capture.path] = best_lag(
            reference.symbols,
            capture.symbols,
            max_lag=args.max_lag,
            align_window=args.align_window,
        )

    common_start, common_end = common_reference_range(captures_tuple, lag_map)
    ref_common = reference.symbols[common_start:common_end]

    print("=== Boot Alignment Summary ===")
    print(
        f"reference={reference.path.name} "
        f"clock=D{args.clock_bit} data_bits={data_bits} edge={args.edge}"
    )
    print(f"common_range=[{common_start}, {common_end}) len={len(ref_common)} symbols")
    print()

    for capture in captures_tuple:
        lag = lag_map[capture.path]
        start = common_start + lag.lag
        end = common_end + lag.lag
        aligned = capture.symbols[start:end]
        compared = min(len(ref_common), len(aligned))
        matches = sum(
            1 for index in range(compared) if ref_common[index] == aligned[index]
        )
        ratio = (matches / compared) if compared else 0.0
        print(
            f"{capture.path.name}: symbols={len(capture.symbols)} "
            f"lag={lag.lag:+d} lag_score={lag.score:.4f} "
            f"aligned_match={ratio:.4f} ({matches}/{compared})"
        )

    boundaries = select_change_points(
        ref_common,
        phases=args.phases,
        window=args.change_window,
        min_gap=args.min_gap,
        alphabet_size=alphabet_size,
    )
    ref_segments = segment_statistics(ref_common, boundaries, alphabet_size)

    print()
    print("=== Phase Boundaries (reference timeline) ===")
    if not boundaries:
        print("No robust boundaries found; capture may be too short or too stationary.")
    else:
        print(f"boundaries={list(boundaries)}")

    print()
    print("=== Phase Similarity (JSD, lower is better) ===")
    for segment_index, ref_segment in enumerate(ref_segments, start=1):
        print(
            f"phase={segment_index} ref_range=[{ref_segment.start}, {ref_segment.end}) "
            f"len={ref_segment.end - ref_segment.start}"
        )
        for capture in captures_tuple[1:]:
            lag = lag_map[capture.path].lag
            seg_start = common_start + ref_segment.start + lag
            seg_end = common_start + ref_segment.end + lag
            segment = capture.symbols[seg_start:seg_end]
            if not segment:
                print(f"  {capture.path.name}: empty segment after alignment")
                continue
            prefix = distribution_prefix(segment, alphabet_size)
            dist = range_distribution(prefix, 0, len(segment), alphabet_size)
            distance = js_divergence(ref_segment.distribution, dist)
            print(f"  {capture.path.name}: jsd={distance:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())