"""Tests for the seeded users and cached hashes."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.permissions import Role
from app.modules.auth.seed import (
    DEMO_PASSWORD,
    SEED_CREATED_AT,
    demo_password_hash,
    dummy_hash,
    seed_users,
)
from app.security.passwords import verify_password


def test_demo_password_constant() -> None:
    assert DEMO_PASSWORD == "Demo-LabApp-2026!"


def test_seed_users_match_the_documentation() -> None:
    users = seed_users("some-hash")

    assert [user.id for user in users] == [1, 2, 3, 4]
    assert [user.name for user in users] == [
        "Admin Demo",
        "Ventas Demo",
        "Finanzas Demo",
        "Solo Lectura Demo",
    ]
    assert [user.email for user in users] == [
        "admin@labapp.test",
        "sales@labapp.test",
        "finance@labapp.test",
        "readonly@labapp.test",
    ]
    assert [user.role for user in users] == [
        Role.ADMIN,
        Role.SALES,
        Role.FINANCE,
        Role.READONLY,
    ]
    assert all(user.password_hash == "some-hash" for user in users)
    assert all(user.created_at == SEED_CREATED_AT for user in users)
    assert SEED_CREATED_AT == datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
    assert all(user.version == 1 for user in users)


def test_demo_password_hash_is_argon2id_and_verifies() -> None:
    hashed = demo_password_hash()

    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, DEMO_PASSWORD) is True
    assert verify_password(hashed, "wrong-password") is False


def test_demo_password_hash_is_cached() -> None:
    assert demo_password_hash() is demo_password_hash()


def test_dummy_hash_is_cached_and_is_not_the_demo_hash() -> None:
    assert dummy_hash() is dummy_hash()
    assert dummy_hash() != demo_password_hash()
    assert verify_password(dummy_hash(), DEMO_PASSWORD) is False
