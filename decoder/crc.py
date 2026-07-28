"""Small checksum helpers for reverse-engineering experiments."""

from __future__ import annotations


def xor_checksum(words: list[int], width_bits: int) -> int:
    """Return a width-limited XOR checksum."""
    mask = (1 << width_bits) - 1
    checksum = 0
    for value in words:
        checksum ^= value & mask
    return checksum & mask


def sum_checksum(words: list[int], width_bits: int) -> int:
    """Return a width-limited additive checksum."""
    mask = (1 << width_bits) - 1
    checksum = 0
    for value in words:
        checksum = (checksum + value) & mask
    return checksum