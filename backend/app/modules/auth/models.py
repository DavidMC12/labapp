"""Authentication models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.permissions import Role


@dataclass(frozen=True)
class User:
    """A seeded user account."""

    id: int
    name: str
    email: str
    role: Role
    password_hash: str = field(repr=False)
    created_at: datetime
    version: int = 1


@dataclass(frozen=True)
class Session:
    """A server-side session keyed by the token digest."""

    token_hash: str = field(repr=False)
    user_id: int
    created_at: datetime
    last_seen_at: datetime
