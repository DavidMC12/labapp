"""Request and response schemas for invoices and payments."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    PlainSerializer,
    WithJsonSchema,
    field_serializer,
)

from app.domain.money import quantize_money
from app.modules.invoices.models import InvoiceStatus, PaymentStatus


def _money(value: Decimal) -> str:
    return format(quantize_money(value), "f")


Money = Annotated[
    Decimal,
    PlainSerializer(_money, return_type=str),
    WithJsonSchema({"type": "string"}),
]


class _Timestamped(BaseModel):
    """A model that renders its timestamps as UTC with a trailing Z."""

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class InvoiceCustomer(BaseModel):
    """The customer snapshot taken at issue time."""

    id: int
    name: str
    tax_id: str
    address: str | None


class InvoiceLine(BaseModel):
    """One line of the invoice snapshot."""

    id: int
    product_id: int
    sku: str
    name: str
    quantity: int
    unit_price: Money
    line_total: Money


class Payment(BaseModel):
    """One stored payment attempt."""

    id: int
    method: str
    status: PaymentStatus
    amount: Money
    reference: str | None
    card_last4: str | None
    reason: str | None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class Invoice(_Timestamped):
    """The full invoice representation."""

    id: int
    number: str
    status: InvoiceStatus
    order_id: int
    order_number: str
    customer: InvoiceCustomer
    lines: list[InvoiceLine]
    subtotal: Money
    tax_rate: Money
    tax: Money
    total: Money
    payments: list[Payment]
    version: int
    created_at: datetime
    updated_at: datetime


class InvoiceSummary(BaseModel):
    """One row of the invoice list."""

    id: int
    number: str
    status: InvoiceStatus
    order_id: int
    order_number: str
    customer_name: str
    total: Money
    version: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class InvoiceListOut(BaseModel):
    """One page of invoices."""

    items: list[InvoiceSummary]
    page: int
    page_size: int
    total: int


class PaymentResult(BaseModel):
    """A payment and the invoice after it."""

    payment: Payment
    invoice: Invoice


class PaymentCreate(BaseModel):
    """The documented shape of the payment body.

    The route takes the raw JSON body so the idempotency replay can be decided
    before validation; this model only documents the contract in OpenAPI.
    """

    model_config = ConfigDict(extra="forbid")

    method: str | None = None
    amount: str | None = None
    card: dict[str, str] | None = None
    reference: str | None = None
