"""Request and response schemas for products, settings and orders."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StrictInt,
    WithJsonSchema,
    field_serializer,
)

from app.domain.money import quantize_money
from app.domain.orders import OrderStatus
from app.modules.customers.models import CustomerStatus
from app.openapi import ID_MAXIMUM, ID_MINIMUM, MONEY_JSON_SCHEMA, TaxRate


def _money(value: Decimal) -> str:
    return format(quantize_money(value), "f")


Money = Annotated[
    Decimal,
    PlainSerializer(_money, return_type=str),
    WithJsonSchema(MONEY_JSON_SCHEMA),
]


class Product(BaseModel):
    """A product of the read-only catalog."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    sku: str
    name: str
    price: Money
    stock: int


class ProductListOut(BaseModel):
    """The whole catalog."""

    items: list[Product]


class TaxRateOut(BaseModel):
    """The current settings."""

    tax_rate: Money


class SettingsPatch(BaseModel):
    """The settings update payload."""

    model_config = ConfigDict(extra="forbid")

    tax_rate: TaxRate | None = None


class OrderLine(BaseModel):
    """One line of an order."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    product_id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    sku: str
    name: str
    quantity: int
    unit_price: Money
    line_total: Money


class OrderCustomer(BaseModel):
    """The current customer of an order."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    name: str
    status: CustomerStatus


class Order(BaseModel):
    """The full order representation."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    number: str
    status: OrderStatus
    customer: OrderCustomer
    lines: list[OrderLine]
    subtotal: Money
    tax_rate: Money
    tax: Money
    total: Money
    invoice_id: int | None = Field(default=None, ge=ID_MINIMUM, le=ID_MAXIMUM)
    version: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class OrderSummary(BaseModel):
    """One row of the order list."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    number: str
    status: OrderStatus
    customer_id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    customer_name: str
    line_count: int
    total: Money
    version: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class OrderListOut(BaseModel):
    """One page of orders."""

    items: list[OrderSummary]
    page: int
    page_size: int
    total: int


class OrderCreate(BaseModel):
    """The order creation payload."""

    model_config = ConfigDict(extra="forbid")

    customer_id: StrictInt | None = None


class OrderCustomerPatch(BaseModel):
    """The payload that changes the customer of a draft."""

    model_config = ConfigDict(extra="forbid")

    customer_id: StrictInt | None = None
    version: StrictInt


class OrderLineCreate(BaseModel):
    """The payload that adds a line."""

    model_config = ConfigDict(extra="forbid")

    product_id: StrictInt | None = None
    quantity: StrictInt | None = None
    version: StrictInt


class OrderLinePatch(BaseModel):
    """The payload that changes a line quantity."""

    model_config = ConfigDict(extra="forbid")

    quantity: StrictInt | None = None
    version: StrictInt
