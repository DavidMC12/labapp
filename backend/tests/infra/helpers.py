"""Helpers shared by the infrastructure tests."""

from __future__ import annotations

from datetime import UTC, datetime

NOW = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


class FixedClock:
    """A deterministic base clock for tests."""

    def __init__(self, now: datetime = NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now
