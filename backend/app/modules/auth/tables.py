"""SQLAlchemy Core tables for the authentication module."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Table,
    Text,
    func,
    text,
)

from app.domain.permissions import Role
from app.infra.db import metadata

_ROLE_VALUES = ", ".join(f"'{role.value}'" for role in Role)

users = Table(
    "users",
    metadata,
    Column("id", Integer, Identity(always=False), primary_key=True),
    Column("name", Text, nullable=False),
    Column("email", Text, nullable=False),
    Column("role", Text, nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("version", Integer, nullable=False, server_default=text("1")),
    CheckConstraint(f"role IN ({_ROLE_VALUES})", name="role"),
)

Index("users_email_lower_key", func.lower(users.c.email), unique=True)

sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", Text, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
)

Index("sessions_last_seen_at_idx", sessions.c.last_seen_at)
