"""Invoice and payment models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class InvoiceStatus(StrEnum):
    """The three invoice states."""

    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


class PaymentStatus(StrEnum):
    """The three payment states."""

    APPROVED = "approved"
    DECLINED = "declined"
    FAILED = "failed"


@dataclass(frozen=True)
class InvoiceLine:
    """A line of an invoice, with the order line data copied at issue time."""

    id: int
    product_id: int
    sku: str
    name: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class Payment:
    """A stored payment attempt.

    Only the last four digits of a card are kept; the number and the CVC never
    reach this layer.
    """

    id: int
    invoice_id: int
    method: str
    status: PaymentStatus
    amount: Decimal
    reference: str | None
    card_last4: str | None
    reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class Invoice:
    """A stored invoice with its frozen snapshot.

    ``lines`` and ``payments`` may be empty in list results; ``get_invoice``,
    ``issue_invoice`` and ``register_payment`` fill them.
    """

    id: int
    number: str
    status: InvoiceStatus
    order_id: int
    order_number: str
    customer_id: int
    customer_name: str
    customer_tax_id: str
    customer_address: str | None
    lines: tuple[InvoiceLine, ...]
    subtotal: Decimal
    tax_rate: Decimal
    tax: Decimal
    total: Decimal
    version: int
    created_at: datetime
    updated_at: datetime
    payments: tuple[Payment, ...] = ()


@dataclass(frozen=True)
class StoredResponse:
    """A rendered response kept with an idempotency key.

    ``body`` holds JSON values only, ready to be serialized as an answer.
    """

    status_code: int
    body: dict[str, object]


@dataclass(frozen=True)
class StoredKey:
    """A committed, not expired idempotency key of one invoice."""

    fingerprint: str
    response: StoredResponse


@dataclass(frozen=True)
class PaymentAttempt:
    """The validated request to register a payment.

    It holds the last four digits of a card, never the number or the CVC.
    """

    method: str
    amount: Decimal
    card_last4: str | None
    reference: str | None


@dataclass(frozen=True)
class PaymentOutcome:
    """The result of registering a payment: the stored answer and the origin."""

    response: StoredResponse
    replayed: bool
