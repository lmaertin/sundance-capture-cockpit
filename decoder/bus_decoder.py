"""Generic helpers for clocked bus discovery and burst decoding."""

from __future__ import annotations

from dataclasses import dataclass

from decoder.sr_reader import BitStats, Capture, active_bits, bit_statistics


SUPPORTED_WORD_BITS = (7, 8, 9, 10, 12, 16)


@dataclass(frozen=True)
class BusLayout:
    """Inferred bus structure for one capture."""

    capture: Capture
    bit_stats: tuple[BitStats, ...]
    active_bits: tuple[int, ...]
    clock_bit: int
    gate_bit: int
    gate_active_level: int
    burst_ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class DecodeVariant:
    """One decode configuration to test against the captures."""

    edge: str
    data_bits: tuple[int, ...]
    word_bits: int
    bit_order: str


def infer_clock_bit(stats: tuple[BitStats, ...]) -> int:
    """Choose the most active line as clock candidate."""
    return max(range(8), key=lambda bit: stats[bit].transitions)


def infer_gate_bit(stats: tuple[BitStats, ...], clock_bit: int) -> tuple[int, int]:
    """Choose a sparse control line as frame gate."""
    candidates: list[int] = []
    for bit in range(8):
        if bit == clock_bit:
            continue
        bit_stats = stats[bit]
        if bit_stats.transitions == 0:
            continue
        if bit_stats.ones_ratio < 0.15 or bit_stats.ones_ratio > 0.85:
            candidates.append(bit)

    if not candidates:
        fallback = min(
            (bit for bit in range(8) if bit != clock_bit),
            key=lambda bit: stats[bit].transitions,
        )
        active_level = 1 if stats[fallback].ones_ratio > 0.5 else 0
        return fallback, active_level

    gate_bit = min(candidates, key=lambda bit: stats[bit].transitions)
    active_level = 1 if stats[gate_bit].ones_ratio > 0.5 else 0
    return gate_bit, active_level


def active_segments(
    samples: bytes,
    bit: int,
    active_level: int,
) -> list[tuple[int, int]]:
    """Return contiguous ranges where the gate line is active."""
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


def edge_positions_in_range(
    samples: bytes,
    bit: int,
    edge: str,
    start: int,
    end: int,
) -> list[int]:
    """Return selected clock edges inside one range."""
    if end - start < 2:
        return []

    positions: list[int] = []
    previous = (samples[start] >> bit) & 0x01
    for index in range(start + 1, end):
        level = (samples[index] >> bit) & 0x01
        if level == previous:
            continue
        if edge == "both":
            positions.append(index)
        elif edge == "rising" and previous == 0 and level == 1:
            positions.append(index)
        elif edge == "falling" and previous == 1 and level == 0:
            positions.append(index)
        previous = level
    return positions


def infer_layout(capture: Capture) -> BusLayout:
    """Infer clock, gate, and burst ranges for one capture."""
    stats = bit_statistics(capture.samples)
    clock_bit = infer_clock_bit(stats)
    gate_bit, gate_active_level = infer_gate_bit(stats, clock_bit)
    burst_ranges = tuple(active_segments(capture.samples, gate_bit, gate_active_level))
    return BusLayout(
        capture=capture,
        bit_stats=stats,
        active_bits=active_bits(stats),
        clock_bit=clock_bit,
        gate_bit=gate_bit,
        gate_active_level=gate_active_level,
        burst_ranges=burst_ranges,
    )


def sample_data_bits(
    samples: bytes,
    positions: list[int],
    data_bits: tuple[int, ...],
) -> list[int]:
    """Extract the selected data bits at each clock position."""
    bits: list[int] = []
    for position in positions:
        value = samples[position]
        for bit in data_bits:
            bits.append((value >> bit) & 0x01)
    return bits


def pack_words(bitstream: list[int], word_bits: int, bit_order: str) -> list[int]:
    """Pack a serial bitstream into words of configurable width."""
    words: list[int] = []
    chunk_count = len(bitstream) // word_bits

    for index in range(chunk_count):
        chunk = bitstream[index * word_bits : (index + 1) * word_bits]
        value = 0
        if bit_order == "msb":
            for bit in chunk:
                value = (value << 1) | bit
        else:
            for offset, bit in enumerate(chunk):
                value |= bit << offset
        words.append(value)

    return words


def decode_bursts(
    layout: BusLayout,
    edge: str,
    data_bits: tuple[int, ...],
    word_bits: int,
    bit_order: str,
) -> list[list[int]]:
    """Decode all bursts for one capture into word lists."""
    bursts: list[list[int]] = []
    for start, end in layout.burst_ranges:
        positions = edge_positions_in_range(
            layout.capture.samples,
            layout.clock_bit,
            edge,
            start,
            end,
        )
        bitstream = sample_data_bits(layout.capture.samples, positions, data_bits)
        bursts.append(pack_words(bitstream, word_bits, bit_order))
    return bursts


def candidate_data_groups(layout: BusLayout) -> tuple[tuple[int, ...], ...]:
    """Return one- and two-line payload candidates excluding clock and gate."""
    candidates = [
        bit for bit in layout.active_bits if bit not in (layout.clock_bit, layout.gate_bit)
    ]
    groups: list[tuple[int, ...]] = []
    for bit in candidates:
        groups.append((bit,))
    for first_index, first_bit in enumerate(candidates):
        for second_bit in candidates[first_index + 1 :]:
            groups.append((first_bit, second_bit))
    return tuple(groups)


def generate_variants(layout: BusLayout) -> tuple[DecodeVariant, ...]:
    """Generate generic decode variants for an inferred layout."""
    variants: list[DecodeVariant] = []
    for edge in ("rising", "falling"):
        for data_bits in candidate_data_groups(layout):
            widths = sorted(set(SUPPORTED_WORD_BITS + (len(data_bits),)))
            for word_bits in widths:
                for bit_order in ("msb", "lsb"):
                    variants.append(
                        DecodeVariant(
                            edge=edge,
                            data_bits=data_bits,
                            word_bits=word_bits,
                            bit_order=bit_order,
                        )
                    )
    return tuple(variants)