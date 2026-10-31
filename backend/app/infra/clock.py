"""Application clock with a controllable offset."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol


class Clock(Protocol):
    """A source of timezone-aware UTC timestamps."""

    def now(self) -> datetime: ...


class SystemClock:
    """The real system clock, in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class OffsetClock:
    """A clock that adds a mutable offset to a base clock, safely across threads."""

    def __init__(self, base: Clock) -> None:
        self._base = base
        self._offset = timedelta(0)
        self._lock = Lock()

    @property
    def offset(self) -> timedelta:
        with self._lock:
            return self._offset

    def set_offset(self, delta: timedelta) -> None:
        with self._lock:
            self._offset = delta

    def advance(self, delta: timedelta) -> None:
        with self._lock:
            self._offset += delta

    def now(self) -> datetime:
        with self._lock:
            offset = self._offset
        return self._base.now() + offset
