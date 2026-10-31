"""Tests for money rounding and order totals."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.money import LineInput, Totals, compute_totals, quantize_money


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("5.025"), Decimal("5.03")),
        (Decimal("5.024"), Decimal("5.02")),
        (Decimal("1.005"), Decimal("1.01")),
        (Decimal("2.675"), Decimal("2.68")),
        (Decimal("-1.005"), Decimal("-1.01")),
        (Decimal("43.78"), Decimal("43.78")),
        (Decimal("0"), Decimal("0.00")),
    ],
)
def test_quantize_money_rounds_half_up(value: Decimal, expected: Decimal) -> None:
    result = quantize_money(value)

    assert result == expected
    assert result.as_tuple().exponent == -2


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (
            [LineInput(Decimal("19.90"), 2)],
            Totals(Decimal("39.80"), Decimal("3.98"), Decimal("43.78")),
        ),
        (
            [LineInput(Decimal("9.50"), 5), LineInput(Decimal("6.25"), 10)],
            Totals(Decimal("110.00"), Decimal("11.00"), Decimal("121.00")),
        ),
        (
            [LineInput(Decimal("149.00"), 2)],
            Totals(Decimal("298.00"), Decimal("29.80"), Decimal("327.80")),
        ),
        (
            [LineInput(Decimal("59.99"), 3)],
            Totals(Decimal("179.97"), Decimal("18.00"), Decimal("197.97")),
        ),
        (
            [LineInput(Decimal("699.00"), 1)],
            Totals(Decimal("699.00"), Decimal("69.90"), Decimal("768.90")),
        ),
        (
            [LineInput(Decimal("27.40"), 4)],
            Totals(Decimal("109.60"), Decimal("10.96"), Decimal("120.56")),
        ),
        (
            [LineInput(Decimal("22.00"), 2), LineInput(Decimal("6.25"), 1)],
            Totals(Decimal("50.25"), Decimal("5.03"), Decimal("55.28")),
        ),
    ],
    ids=[
        "PED-0001",
        "PED-0002",
        "PED-0003",
        "PED-0004",
        "PED-0005",
        "PED-0006",
        "PED-0007",
    ],
)
def test_seed_order_totals(lines: list[LineInput], expected: Totals) -> None:
    assert compute_totals(lines, Decimal("10.00")) == expected


def test_tax_tie_rounds_half_up() -> None:
    totals = compute_totals([LineInput(Decimal("50.25"), 1)], Decimal("10.00"))

    assert totals.tax == Decimal("5.03")


def test_empty_lines_produce_zero_totals() -> None:
    totals = compute_totals([], Decimal("10.00"))

    assert totals == Totals(Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))


def test_zero_rate_has_no_tax() -> None:
    totals = compute_totals([LineInput(Decimal("10.00"), 3)], Decimal("0.00"))

    assert totals.subtotal == Decimal("30.00")
    assert totals.tax == Decimal("0.00")
    assert totals.total == Decimal("30.00")


def test_hundred_percent_rate_doubles_the_subtotal() -> None:
    totals = compute_totals([LineInput(Decimal("10.00"), 3)], Decimal("100.00"))

    assert totals.subtotal == Decimal("30.00")
    assert totals.tax == Decimal("30.00")
    assert totals.total == Decimal("60.00")


@pytest.mark.parametrize(
    "tax_rate",
    [
        Decimal("-0.01"),
        Decimal("100.01"),
        Decimal("0.001"),
        Decimal("10.001"),
        Decimal("10.000"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_invalid_tax_rate_raises(tax_rate: Decimal) -> None:
    with pytest.raises(ValueError):
        compute_totals([], tax_rate)


def test_line_input_is_frozen() -> None:
    line = LineInput(Decimal("1.00"), 1)

    with pytest.raises(FrozenInstanceError):
        line.quantity = 2
