"""The seven seeded orders of docs/SEED.md."""

from __future__ import annotations

import re
from decimal import Decimal

from app.domain.money import LineInput, compute_totals
from app.domain.orders import OrderStatus
from app.modules.orders.seed import SEED_TAX_RATE, seed_orders

from . import support

_LINE = re.compile(r"(?P<sku>\S+) x (?P<quantity>[0-9]+)")


def _document_lines(cell: str) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = []
    for part in cell.split(","):
        match = _LINE.fullmatch(part.strip())
        assert match is not None, f"unexpected line in the document: {part!r}"
        lines.append((match.group("sku"), int(match.group("quantity"))))
    return lines


def test_the_seven_orders_match_the_document_and_recompute_their_totals() -> None:
    rows = support.seed_table(
        "Orders, invoices and payments",
        "Order",
        "Customer",
        "Status",
        "Lines",
        "Subtotal",
        "Tax",
        "Total",
        "Invoice",
        "Payments",
    )
    orders = seed_orders()

    assert len(rows) == len(orders) == 7
    for row, order in zip(rows, orders, strict=True):
        assert row["Order"] == order.number
        assert int(row["Customer"]) == order.customer_id
        assert row["Status"] == order.status.value
        assert _document_lines(row["Lines"]) == [(line.sku, line.quantity) for line in order.lines]

        totals = compute_totals(
            [LineInput(line.unit_price, line.quantity) for line in order.lines],
            SEED_TAX_RATE,
        )
        assert row["Subtotal"] == f"{totals.subtotal:.2f}"
        assert row["Tax"] == f"{totals.tax:.2f}"
        assert row["Total"] == f"{totals.total:.2f}"

        if order.status == OrderStatus.DRAFT:
            assert order.tax_rate is None
        else:
            assert order.tax_rate == Decimal("10.00")
