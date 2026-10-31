"""Tests for order and invoice number formatting."""

from __future__ import annotations

import pytest

from app.domain.numbering import format_number


@pytest.mark.parametrize(
    ("prefix", "value", "expected"),
    [
        ("PED", 1, "PED-0001"),
        ("FAC", 42, "FAC-0042"),
        ("PED", 9999, "PED-9999"),
        ("PED", 10000, "PED-10000"),
        ("FAC", 123456, "FAC-123456"),
    ],
)
def test_format_number(prefix: str, value: int, expected: str) -> None:
    assert format_number(prefix, value) == expected


@pytest.mark.parametrize("prefix", ["INV", "ped", "", "PED-", " FAC"])
def test_unsupported_prefix_raises(prefix: str) -> None:
    with pytest.raises(ValueError):
        format_number(prefix, 1)


@pytest.mark.parametrize("value", [0, -1, -100])
def test_value_below_one_raises(value: int) -> None:
    with pytest.raises(ValueError):
        format_number("PED", value)
