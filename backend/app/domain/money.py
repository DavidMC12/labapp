"""Money rounding and order totals."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")
MIN_TAX_RATE = Decimal("0.00")
MAX_TAX_RATE = Decimal("100.00")


def quantize_money(value: Decimal) -> Decimal:
    """Round a money value to two decimals, half-up."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineInput:
    """A priced quantity used to compute totals."""

    unit_price: Decimal
    quantity: int


@dataclass(frozen=True)
class Totals:
    """The subtotal, tax and total of an order."""

    subtotal: Decimal
    tax: Decimal
    total: Decimal


def compute_totals(lines: Iterable[LineInput], tax_rate: Decimal) -> Totals:
    """Compute order totals for a percentage tax rate."""
    if not tax_rate.is_finite() or tax_rate < MIN_TAX_RATE or tax_rate > MAX_TAX_RATE:
        raise ValueError("tax_rate must be between 0.00 and 100.00")
    if tax_rate.as_tuple().exponent < -2:
        raise ValueError("tax_rate must have at most 2 decimals")

    subtotal = sum((line.unit_price * line.quantity for line in lines), Decimal("0.00"))
    tax = quantize_money(subtotal * tax_rate / Decimal("100"))
    return Totals(subtotal=subtotal, tax=tax, total=subtotal + tax)
