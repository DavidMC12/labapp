"""SQLAlchemy Core table for the test-only fault rules."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Identity,
    Integer,
    Table,
    Text,
    func,
    text,
)

from app.infra.db import metadata

fault_rules = Table(
    "fault_rules",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column("target", Text, nullable=False),
    Column("method", Text, nullable=True),
    Column("path", Text, nullable=True),
    Column("latency_ms", Integer, nullable=False, server_default=text("0")),
    Column("status", Integer, nullable=True),
    Column("remaining", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("target IN ('route', 'gateway')", name="target"),
    CheckConstraint("method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')", name="method"),
    CheckConstraint("latency_ms >= 0 AND latency_ms <= 10000", name="latency_ms"),
    CheckConstraint("status >= 400 AND status <= 599", name="status"),
    CheckConstraint("remaining >= 0", name="remaining"),
)
