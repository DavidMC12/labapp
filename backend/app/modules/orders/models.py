"""Order, product and line models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.orders import OrderStatus


@dataclass(frozen=True)
class Product:
    """A read-only product from the catalog."""

    id: int
    sku: str
    name: str
    price: Decimal
    stock: int


@dataclass(frozen=True)
class OrderLine:
    """A line of an order, with the product data copied when it was added."""

    id: int
    product_id: int
    sku: str
    name: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class Order:
    """A stored order."""

    id: int
    number: str
    status: OrderStatus
    customer_id: int
    lines: tuple[OrderLine, ...]
    tax_rate: Decimal | None
    version: int
    created_at: datetime
    updated_at: datetime
    invoice_id: int | None


@dataclass(frozen=True)
class Shortage:
    """A line that does not have enough stock when confirming."""

    product_id: int
    sku: str
    name: str
    available: int
    requested: int
