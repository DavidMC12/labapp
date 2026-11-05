"""Seeded users and process-wide password hashes."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from functools import cache

from app.domain.permissions import Role
from app.modules.auth.models import User
from app.security.passwords import hash_password

DEMO_PASSWORD = "Demo-LabApp-2026!"
SEED_CREATED_AT = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


@cache
def demo_password_hash() -> str:
    """Return the Argon2id hash of the demo password, computed once per process."""
    return hash_password(DEMO_PASSWORD)


@cache
def dummy_hash() -> str:
    """Return the Argon2id hash of an unguessable value, computed once per process."""
    return hash_password(secrets.token_urlsafe(32))


def seed_users(password_hash: str) -> list[User]:
    """Return the four documented users with the given password hash."""
    return [
        User(
            id=1,
            name="Admin Demo",
            email="admin@labapp.test",
            role=Role.ADMIN,
            password_hash=password_hash,
            created_at=SEED_CREATED_AT,
        ),
        User(
            id=2,
            name="Ventas Demo",
            email="sales@labapp.test",
            role=Role.SALES,
            password_hash=password_hash,
            created_at=SEED_CREATED_AT,
        ),
        User(
            id=3,
            name="Finanzas Demo",
            email="finance@labapp.test",
            role=Role.FINANCE,
            password_hash=password_hash,
            created_at=SEED_CREATED_AT,
        ),
        User(
            id=4,
            name="Solo Lectura Demo",
            email="readonly@labapp.test",
            role=Role.READONLY,
            password_hash=password_hash,
            created_at=SEED_CREATED_AT,
        ),
    ]
