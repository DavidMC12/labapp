"""SQLAlchemy Core tables for products, orders, lines and settings."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Sequence,
    Table,
    Text,
)

from app.infra.db import metadata

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("sku", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("price", Numeric(12, 2), nullable=False),
    Column("stock", Integer, nullable=False),
    CheckConstraint("price > 0", name="price"),
    CheckConstraint("stock >= 0", name="stock"),
)

Index("products_sku_key", products.c.sku, unique=True)

orders = Table(
    "orders",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column("number", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
    Column("tax_rate", Numeric(5, 2), nullable=True),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("invoice_id", Integer, nullable=True),
    CheckConstraint(
        "status IN ('draft', 'confirmed', 'paid', 'shipped', 'cancelled')",
        name="status",
    ),
    CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="tax_rate"),
)

Index("orders_number_key", orders.c.number, unique=True)
Index("orders_created_at_id_idx", orders.c.created_at.desc(), orders.c.id.desc())
Index("ix_orders_customer_id", orders.c.customer_id)

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column(
        "order_id",
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("sku", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Numeric(12, 2), nullable=False),
    CheckConstraint("quantity >= 1 AND quantity <= 999", name="quantity"),
)

Index(
    "order_lines_order_product_key",
    order_lines.c.order_id,
    order_lines.c.product_id,
    unique=True,
)
Index("ix_order_lines_order_id", order_lines.c.order_id)

settings = Table(
    "settings",
    metadata,
    Column("key", Text, primary_key=True),
    Column("value", Text, nullable=False),
)

order_number_seq = Sequence("order_number_seq", start=1, metadata=metadata)
