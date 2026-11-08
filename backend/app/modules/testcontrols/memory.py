"""In-memory implementations of the test-only control stores."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.engine import Connection

from app.infra.clock import OffsetClock


class InMemoryClockOffsetStore:
    """Persist the offset in the application's existing ``OffsetClock``."""

    def __init__(self, clock: OffsetClock) -> None:
        self._clock = clock

    def get(self, *, connection: Connection | None = None) -> float:
        return self._clock.offset.total_seconds()

    def set(self, seconds: float, *, connection: Connection | None = None) -> None:
        self._clock.set_offset(timedelta(seconds=seconds))

    def advance(self, seconds: float, *, connection: Connection | None = None) -> float:
        self._clock.advance(timedelta(seconds=seconds))
        return self.get()
