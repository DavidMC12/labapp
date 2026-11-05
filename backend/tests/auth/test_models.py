"""Tests for the authentication models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.domain.permissions import Role
from app.modules.auth.models import Session, User

NOW = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


def _user() -> User:
    return User(
        id=1,
        name="Admin Demo",
        email="admin@labapp.test",
        role=Role.ADMIN,
        password_hash="super-secret-password-hash",
        created_at=NOW,
    )


def test_user_repr_hides_the_password_hash() -> None:
    rendered = repr(_user())

    assert "super-secret-password-hash" not in rendered
    assert "Admin Demo" in rendered


def test_session_repr_hides_the_token_hash() -> None:
    session = Session(
        token_hash="super-secret-token-hash",
        user_id=1,
        created_at=NOW,
        last_seen_at=NOW,
    )

    rendered = repr(session)

    assert "super-secret-token-hash" not in rendered
    assert "user_id=1" in rendered


def test_user_has_version_one_by_default() -> None:
    assert _user().version == 1


def test_models_are_frozen() -> None:
    user = _user()
    session = Session("hash", 1, NOW, NOW)

    with pytest.raises(FrozenInstanceError):
        user.name = "Other"
    with pytest.raises(FrozenInstanceError):
        session.last_seen_at = NOW
