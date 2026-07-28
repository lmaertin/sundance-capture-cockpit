"""Compare decoded burst streams across captures."""

from __future__ import annotations

from dataclasses import dataclass

from decoder.bus_decoder import BusLayout, DecodeVariant, decode_bursts


@dataclass(frozen=True)
class FieldCandidate:
    """One field position that changes monotonically across captures."""

    burst_index: int
    word_index: int
    field_width: int
    values: tuple[int, ...]
    step: int
    temperature_scale: float | None
    temperature_offset: float | None


@dataclass(frozen=True)
class VariantReport:
    """Comparison result for one decode variant."""

    variant: DecodeVariant
    burst_count: int
    identical_bursts: int
    field_candidates: tuple[FieldCandidate, ...]
    score: int


def combine_window(words: list[int], start: int, width: int, word_bits: int) -> int:
    """Combine consecutive words into one integer field value."""
    value = 0
    mask = (1 << word_bits) - 1
    for offset in range(width):
        value = (value << word_bits) | (words[start + offset] & mask)
    return value


def monotonic_step(values: tuple[int, ...]) -> int | None:
    """Return the constant consecutive delta of a value sequence."""
    if len(values) < 2:
        return None
    deltas = [values[index + 1] - values[index] for index in range(len(values) - 1)]
    first = deltas[0]
    if all(delta == first for delta in deltas) and first != 0:
        return first
    return None


def linear_temperature_map(
    values: tuple[int, ...],
    temperatures: tuple[int, ...],
) -> tuple[float, float] | tuple[None, None]:
    """Return a linear mapping from field values to temperatures when defined."""
    if len(values) != len(temperatures) or len(values) < 2:
        return None, None

    value_step = values[1] - values[0]
    temp_step = temperatures[1] - temperatures[0]
    if value_step == 0 or temp_step == 0:
        return None, None

    for index in range(len(values) - 1):
        if values[index + 1] - values[index] != value_step:
            return None, None
        if temperatures[index + 1] - temperatures[index] != temp_step:
            return None, None

    scale = temp_step / value_step
    offset = temperatures[0] - (values[0] * scale)
    return scale, offset


def compare_variant(
    layouts: list[BusLayout],
    variant: DecodeVariant,
    max_candidates: int,
    max_field_words: int,
) -> VariantReport:
    """Compare one decode variant across captures."""
    per_capture = [decode_bursts(layout, **variant.__dict__) for layout in layouts]
    burst_count = min(len(item) for item in per_capture)
    identical_bursts = 0
    candidates: list[FieldCandidate] = []
    temperatures = tuple(layout.capture.step.from_temp for layout in layouts)

    for burst_index in range(burst_count):
        streams = [item[burst_index] for item in per_capture]
        if all(stream == streams[0] for stream in streams[1:]):
            identical_bursts += 1

        min_words = min(len(stream) for stream in streams)
        for field_width in range(1, max_field_words + 1):
            if min_words < field_width:
                break
            last_start = min_words - field_width + 1
            for word_index in range(last_start):
                values = tuple(
                    combine_window(stream, word_index, field_width, variant.word_bits)
                    for stream in streams
                )
                step = monotonic_step(values)
                if step is None:
                    continue
                scale, offset = linear_temperature_map(values, temperatures)
                candidates.append(
                    FieldCandidate(
                        burst_index=burst_index,
                        word_index=word_index,
                        field_width=field_width,
                        values=values,
                        step=step,
                        temperature_scale=scale,
                        temperature_offset=offset,
                    )
                )

    ranked = sorted(
        candidates,
        key=lambda item: (
            item.temperature_scale is None,
            abs(item.step) != 1,
            abs(item.step),
            item.field_width != 1,
            item.burst_index,
            item.word_index,
        ),
    )
    score = (len(ranked) * 10) + identical_bursts
    if ranked and ranked[0].temperature_scale is not None:
        score += 50
    return VariantReport(
        variant=variant,
        burst_count=burst_count,
        identical_bursts=identical_bursts,
        field_candidates=tuple(ranked[:max_candidates]),
        score=score,
    )


def rank_variants(
    layouts: list[BusLayout],
    max_reports: int,
    max_candidates: int,
    max_field_words: int,
) -> list[VariantReport]:
    """Run and rank generic decode variants."""
    if not layouts:
        return []

    reports: list[VariantReport] = []
    reference = layouts[0]
    from decoder.bus_decoder import generate_variants

    for variant in generate_variants(reference):
        report = compare_variant(layouts, variant, max_candidates, max_field_words)
        if report.field_candidates:
            reports.append(report)

    reports.sort(
        key=lambda item: (
            -item.score,
            -item.identical_bursts,
            len(item.variant.data_bits),
            item.variant.word_bits,
        )
    )
    return reports[:max_reports]