"""Helpers shared by the authentication tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.auth.seed import DEMO_PASSWORD
from tests.infra.helpers import FixedClock

NOW = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
DUMMY_HASH = "dummy-hash"

__all__ = ["DUMMY_HASH", "FixedClock", "NOW", "RecordingVerifier"]


class RecordingVerifier:
    """A fast verifier that records every hash and password it receives."""

    def __init__(self, password: str = DEMO_PASSWORD) -> None:
        self._password = password
        self.calls: list[tuple[str, str]] = []

    def __call__(self, password_hash: str, password: str) -> bool:
        self.calls.append((password_hash, password))
        return password == self._password
