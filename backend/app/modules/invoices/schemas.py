"""Request and response schemas for invoices and payments."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
    field_serializer,
)

from app.domain.money import quantize_money
from app.modules.invoices.models import InvoiceStatus, PaymentStatus
from app.openapi import ID_MAXIMUM, ID_MINIMUM, MONEY_JSON_SCHEMA, PAYMENT_AMOUNT_PATTERN


def _money(value: Decimal) -> str:
    return format(quantize_money(value), "f")


Money = Annotated[
    Decimal,
    PlainSerializer(_money, return_type=str),
    WithJsonSchema(MONEY_JSON_SCHEMA),
]


class _Timestamped(BaseModel):
    """A model that renders its timestamps as UTC with a trailing Z."""

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class InvoiceCustomer(BaseModel):
    """The customer snapshot taken at issue time."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    name: str
    tax_id: str
    address: str | None


class InvoiceLine(BaseModel):
    """One line of the invoice snapshot."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    product_id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    sku: str
    name: str
    quantity: int
    unit_price: Money
    line_total: Money


class Payment(BaseModel):
    """One stored payment attempt."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
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

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    number: str
    status: InvoiceStatus
    order_id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    order_number: str
    customer: InvoiceCustomer
    lines: list[InvoiceLine]
    subtotal: Money
    tax_rate: Money
    tax: Money
    total: Money
    payments: list[Payment]
    version: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    created_at: datetime
    updated_at: datetime


class InvoiceSummary(BaseModel):
    """One row of the invoice list."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    number: str
    status: InvoiceStatus
    order_id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    order_number: str
    customer_name: str
    total: Money
    version: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
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


class PaymentCard(BaseModel):
    """The card object of a card payment."""

    number: str = Field(description="The card number. Spaces are allowed and ignored.")
    expiry: str = Field(description="The expiry date as `MM/YY`.")
    cvc: str = Field(description="The three-digit security code.")


class PaymentCreate(BaseModel):
    """The documented shape of the payment body.

    `method` and `amount` are always required. With `method: card`, `card` is required
    and `reference` is not used. With `method: transfer`, `reference` is required and
    `card` is not used. With `method: cash`, neither `card` nor `reference` is used.

    The route receives the raw JSON body so that the idempotency replay can be decided
    before validation; this model only documents the contract in OpenAPI.
    """

    model_config = ConfigDict(extra="forbid")

    method: Literal["card", "transfer", "cash"] = Field(description="`card`, `transfer` or `cash`.")
    amount: str = Field(
        pattern=PAYMENT_AMOUNT_PATTERN,
        json_schema_extra={"example": "121.00"},
        description="The amount, as a string with at most two decimals.",
    )
    card: PaymentCard | None = Field(
        default=None,
        description="Required with `method: card`; not used with another method.",
    )
    reference: str | None = Field(
        default=None,
        description="Required with `method: transfer`; not used with another method.",
    )
