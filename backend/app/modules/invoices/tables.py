"""SQLAlchemy Core tables for invoices, payments and idempotency keys."""

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
from sqlalchemy.dialects.postgresql import JSONB

from app.infra.db import metadata

invoices = Table(
    "invoices",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column("number", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("order_id", Integer, ForeignKey("orders.id"), nullable=False),
    Column("order_number", Text, nullable=False),
    Column("customer_id", Integer, nullable=False),
    Column("customer_name", Text, nullable=False),
    Column("customer_name_search", Text, nullable=False),
    Column("customer_tax_id", Text, nullable=False),
    Column("customer_address", Text, nullable=True),
    Column("subtotal", Numeric(12, 2), nullable=False),
    Column("tax", Numeric(12, 2), nullable=False),
    Column("total", Numeric(12, 2), nullable=False),
    Column("tax_rate", Numeric(5, 2), nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("status IN ('issued', 'paid', 'void')", name="status"),
)

Index("invoices_number_key", invoices.c.number, unique=True)
Index("invoices_order_key", invoices.c.order_id, unique=True)
Index("invoices_created_at_id_idx", invoices.c.created_at.desc(), invoices.c.id.desc())

invoice_lines = Table(
    "invoice_lines",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column(
        "invoice_id",
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("product_id", Integer, nullable=False),
    Column("sku", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Numeric(12, 2), nullable=False),
)

Index("ix_invoice_lines_invoice_id", invoice_lines.c.invoice_id)

payments = Table(
    "payments",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column("invoice_id", Integer, ForeignKey("invoices.id"), nullable=False),
    Column("method", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("reference", Text, nullable=True),
    Column("card_last4", Text, nullable=True),
    Column("reason", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("method IN ('card', 'transfer', 'cash')", name="method"),
    CheckConstraint("status IN ('approved', 'declined', 'failed')", name="status"),
    CheckConstraint("card_last4 IS NULL OR card_last4 ~ '^[0-9]{4}$'", name="card_last4"),
)

Index("ix_payments_invoice_id", payments.c.invoice_id)

idempotency_keys = Table(
    "idempotency_keys",
    metadata,
    Column("invoice_id", Integer, ForeignKey("invoices.id"), primary_key=True),
    Column("key", Text, primary_key=True),
    Column("fingerprint", Text, nullable=False),
    Column("status_code", Integer, nullable=False),
    Column("response", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

invoice_number_seq = Sequence("invoice_number_seq", start=1, metadata=metadata)
