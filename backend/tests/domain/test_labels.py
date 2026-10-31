"""Tests for the Spanish domain labels."""

from __future__ import annotations

from app.domain.labels import (
    INVOICE_STATUS_LABELS,
    ORDER_STATUS_LABELS,
    PAYMENT_METHOD_LABELS,
    PAYMENT_STATUS_LABELS,
    ROLE_LABELS,
)


def test_order_status_labels() -> None:
    assert ORDER_STATUS_LABELS == {
        "draft": "borrador",
        "confirmed": "confirmado",
        "paid": "pagado",
        "shipped": "enviado",
        "cancelled": "cancelado",
    }


def test_invoice_status_labels() -> None:
    assert INVOICE_STATUS_LABELS == {
        "issued": "emitida",
        "paid": "pagada",
        "void": "anulada",
    }


def test_payment_status_labels() -> None:
    assert PAYMENT_STATUS_LABELS == {
        "approved": "aprobado",
        "declined": "rechazado",
        "failed": "fallido",
    }


def test_payment_method_labels() -> None:
    assert PAYMENT_METHOD_LABELS == {
        "card": "tarjeta",
        "transfer": "transferencia",
        "cash": "efectivo",
    }


def test_role_labels() -> None:
    assert ROLE_LABELS == {
        "admin": "Admin",
        "sales": "Ventas",
        "finance": "Finanzas",
        "readonly": "Solo lectura",
    }
