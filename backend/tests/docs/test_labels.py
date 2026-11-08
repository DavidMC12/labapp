"""The Spanish labels of SPEC section 7 and app/domain/labels.py."""

from __future__ import annotations

from app.domain.labels import (
    INVOICE_STATUS_LABELS,
    ORDER_STATUS_LABELS,
    PAYMENT_METHOD_LABELS,
    PAYMENT_STATUS_LABELS,
    ROLE_LABELS,
)
from app.domain.orders import OrderStatus
from app.domain.permissions import Role
from app.modules.invoices.models import InvoiceStatus, PaymentStatus

from . import support

LABEL_TABLES = {
    "Order states": ORDER_STATUS_LABELS,
    "Invoice states": INVOICE_STATUS_LABELS,
    "Payment states": PAYMENT_STATUS_LABELS,
    "Payment methods": PAYMENT_METHOD_LABELS,
    "Roles": ROLE_LABELS,
}

EXPECTED_KEYS = {
    "Order states": {status.value for status in OrderStatus},
    "Invoice states": {status.value for status in InvoiceStatus},
    "Payment states": {status.value for status in PaymentStatus},
    "Payment methods": {"card", "transfer", "cash"},
    "Roles": {role.value for role in Role},
}


def test_every_label_table_matches_the_document() -> None:
    rows = support.spec_label_rows()

    assert {row["Concept"] for row in rows} == set(LABEL_TABLES)
    for row in rows:
        mapping = LABEL_TABLES[row["Concept"]]
        labels = [label.strip() for label in row["Spanish labels"].split(",")]
        assert labels == list(mapping.values())
        assert set(mapping) == EXPECTED_KEYS[row["Concept"]]
