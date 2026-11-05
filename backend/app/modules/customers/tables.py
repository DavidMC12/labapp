"""SQLAlchemy Core tables for the customers module."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Identity,
    Index,
    Integer,
    Table,
    Text,
    func,
)

from app.infra.db import metadata

customers = Table(
    "customers",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column("name", Text, nullable=False),
    Column("email", Text, nullable=False),
    Column("phone", Text, nullable=True),
    Column("tax_id", Text, nullable=True),
    Column("address", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("name_search", Text, nullable=False),
    Column("email_search", Text, nullable=False),
    CheckConstraint("status IN ('active', 'inactive')", name="status"),
)

Index("customers_email_lower_key", func.lower(customers.c.email), unique=True)
Index(
    "customers_created_at_id_idx",
    customers.c.created_at.desc(),
    customers.c.id.desc(),
)
