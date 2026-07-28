"""Read Sigrok .sr captures and derive low-level channel statistics."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path


TEMPERATURE_PATTERN = re.compile(r"(\d+)-(\d+)")


@dataclass(frozen=True)
class TemperatureStep:
    """Temperature transition encoded in the capture filename."""

    from_temp: int
    to_temp: int


@dataclass(frozen=True)
class Capture:
    """In-memory representation of one Sigrok capture."""

    path: Path
    name: str
    step: TemperatureStep
    samples: bytes


@dataclass(frozen=True)
class BitStats:
    """Per-channel activity summary."""

    ones_ratio: float
    transitions: int


def parse_temperature_step(name: str) -> TemperatureStep:
    """Extract the temperature transition from a filename.

    Some captures do not encode a temperature step in the file name, so we fall back to
    a neutral zero-step value for import workflows instead of failing hard.
    """
    match = TEMPERATURE_PATTERN.search(name)
    if match is None:
        return TemperatureStep(from_temp=0, to_temp=0)
    return TemperatureStep(from_temp=int(match.group(1)), to_temp=int(match.group(2)))


def load_capture(path: Path) -> Capture:
    """Load one .sr archive and return the logic samples."""
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()

        # Newer sigrok files store data as chunked logic-1-N entries.
        chunk_names = [name for name in names if name.startswith("logic-1-")]
        if chunk_names:
            chunk_names.sort(key=lambda item: int(item.rsplit("-", maxsplit=1)[1]))
            samples = b"".join(archive.read(name) for name in chunk_names)
        elif "logic-1" in names:
            samples = archive.read("logic-1")
        elif "logic-1-1" in names:
            samples = archive.read("logic-1-1")
        else:
            raise ValueError(f"{path} does not contain logic sample streams.")

    return Capture(
        path=path,
        name=path.name,
        step=parse_temperature_step(path.name),
        samples=samples,
    )


def bit_statistics(samples: bytes) -> tuple[BitStats, ...]:
    """Compute duty cycle and transitions for all eight logic channels."""
    if not samples:
        raise ValueError("Empty sample stream.")

    total = len(samples)
    ones = [0] * 8
    transitions = [0] * 8
    previous = samples[0]

    for value in samples:
        for bit in range(8):
            ones[bit] += (value >> bit) & 0x01
        diff = previous ^ value
        for bit in range(8):
            transitions[bit] += (diff >> bit) & 0x01
        previous = value

    return tuple(
        BitStats(ones_ratio=ones[bit] / total, transitions=transitions[bit])
        for bit in range(8)
    )


def active_bits(stats: tuple[BitStats, ...]) -> tuple[int, ...]:
    """Return channels with at least one transition."""
    return tuple(bit for bit, item in enumerate(stats) if item.transitions > 0)


def validate_inputs(paths: list[Path]) -> list[Path]:
    """Verify that all input files exist before reading them."""
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input file(s): {', '.join(missing)}")
    return paths