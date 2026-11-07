"""Seeded invoices and payments."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.modules.customers.seed import seed_customers
from app.modules.invoices.models import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentStatus,
)
from app.modules.invoices.rules import totals_for
from app.modules.orders.seed import seed_orders


def _issued_at(day: int) -> datetime:
    return datetime(2026, 1, day, 14, 0, tzinfo=UTC)


def _paid_at(day: int) -> datetime:
    return datetime(2026, 1, day, 15, 0, tzinfo=UTC)


def seed_invoices() -> list[Invoice]:
    """Return the three documented invoices with their line snapshots."""
    orders = {order.id: order for order in seed_orders()}
    customers = {customer.id: customer for customer in seed_customers()}
    day_by_order = {3: 3, 4: 4, 5: 5}
    status_by_invoice = {
        1: InvoiceStatus.ISSUED,
        2: InvoiceStatus.PAID,
        3: InvoiceStatus.PAID,
    }
    invoices: list[Invoice] = []
    next_line_id = 1
    for invoice_id, order_id in ((1, 3), (2, 4), (3, 5)):
        order = orders[order_id]
        customer = customers[order.customer_id]
        lines = tuple(
            InvoiceLine(
                id=next_line_id + position,
                product_id=line.product_id,
                sku=line.sku,
                name=line.name,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
            for position, line in enumerate(order.lines)
        )
        next_line_id += len(lines)
        rate = order.tax_rate if order.tax_rate is not None else Decimal("0.00")
        totals = totals_for(lines, rate)
        issued_at = _issued_at(day_by_order[order_id])
        invoices.append(
            Invoice(
                id=invoice_id,
                number=f"FAC-{invoice_id:04d}",
                status=status_by_invoice[invoice_id],
                order_id=order.id,
                order_number=order.number,
                customer_id=customer.id,
                customer_name=customer.name,
                customer_tax_id=customer.tax_id or "",
                customer_address=customer.address,
                lines=lines,
                subtotal=totals.subtotal,
                tax_rate=rate,
                tax=totals.tax,
                total=totals.total,
                version=1,
                created_at=issued_at,
                updated_at=issued_at,
            )
        )
    return invoices


def seed_payments() -> list[Payment]:
    """Return the four documented payment attempts."""
    return [
        Payment(
            id=1,
            invoice_id=1,
            method="card",
            status=PaymentStatus.DECLINED,
            amount=Decimal("327.80"),
            reference=None,
            card_last4="0002",
            reason="CARD_DECLINED",
            created_at=_paid_at(3),
        ),
        Payment(
            id=2,
            invoice_id=1,
            method="card",
            status=PaymentStatus.FAILED,
            amount=Decimal("327.80"),
            reference=None,
            card_last4="0003",
            reason="GATEWAY_UNAVAILABLE",
            created_at=_paid_at(3),
        ),
        Payment(
            id=3,
            invoice_id=2,
            method="transfer",
            status=PaymentStatus.APPROVED,
            amount=Decimal("197.97"),
            reference="TRF-2026-0001",
            card_last4=None,
            reason=None,
            created_at=_paid_at(4),
        ),
        Payment(
            id=4,
            invoice_id=3,
            method="cash",
            status=PaymentStatus.APPROVED,
            amount=Decimal("768.90"),
            reference=None,
            card_last4=None,
            reason=None,
            created_at=_paid_at(5),
        ),
    ]
