"""The three seeded invoices and four payments of docs/SEED.md."""

from __future__ import annotations

import re

from app.modules.invoices.seed import seed_invoices, seed_payments

from . import support

_INVOICE = re.compile(r"(?P<number>FAC-[0-9]{4}) (?P<status>issued|paid|void)")
_PAYMENT = re.compile(r"#(?P<id>[0-9]+) (?P<method>card|transfer|cash)")
_PAYMENT_STATUS = re.compile(r"\b(approved|declined|failed)\b")
_TRANSFER_REFERENCE = re.compile(r"reference (TRF-[0-9-]+)")


def test_the_seeded_invoices_and_payments_match_the_document() -> None:
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
    invoices = {invoice.order_id: invoice for invoice in seed_invoices()}
    payments = {payment.id: payment for payment in seed_payments()}
    payment_ids: list[int] = []

    assert len(rows) == 7
    for row in rows:
        order_id = int(row["Order"].split("-")[1])

        invoice_cell = row["Invoice"]
        if invoice_cell == "none":
            assert order_id not in invoices
        else:
            match = _INVOICE.fullmatch(invoice_cell)
            assert match is not None, f"unexpected invoice cell: {invoice_cell!r}"
            invoice = invoices[order_id]
            assert invoice.number == match.group("number")
            assert invoice.status.value == match.group("status")

        payments_cell = row["Payments"]
        if payments_cell == "none":
            continue
        for part in payments_cell.split(";"):
            match = _PAYMENT.match(part.strip())
            assert match is not None, f"unexpected payment cell: {part!r}"
            payment_id = int(match.group("id"))
            payment_ids.append(payment_id)
            payment = payments[payment_id]
            assert payment.method == match.group("method")
            status = _PAYMENT_STATUS.search(part)
            assert status is not None, f"payment without a status: {part!r}"
            assert payment.status.value == status.group(1)
            reference = _TRANSFER_REFERENCE.search(part)
            assert payment.reference == (reference.group(1) if reference is not None else None)

    assert sorted(payment_ids) == sorted(payments)
