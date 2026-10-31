"""Order and invoice number formatting."""

from __future__ import annotations

VALID_PREFIXES = frozenset({"PED", "FAC"})
MIN_NUMBER = 1
MIN_DIGITS = 4


def format_number(prefix: str, value: int) -> str:
    """Format a sequence number as PREFIX-0000, growing beyond four digits."""
    if prefix not in VALID_PREFIXES:
        raise ValueError(f"unsupported prefix: {prefix!r}")
    if value < MIN_NUMBER:
        raise ValueError("value must be at least 1")
    return f"{prefix}-{value:0{MIN_DIGITS}d}"
