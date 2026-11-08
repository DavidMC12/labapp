"""Application clock with a controllable offset."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol

from app.modules.testcontrols.ports import ClockOffsetStore

clock_offset: ContextVar[float | None] = ContextVar("clock_offset_seconds", default=None)


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


class ControlledClock:
    """A clock whose offset lives in a store, used only when the controls are enabled.

    When disabled it never reads the store and ignores ``clock_offset``. When enabled
    it uses the request value set by the controls middleware, or the stored value for
    the CLI and the exempt paths.
    """

    def __init__(self, base: Clock, store: ClockOffsetStore, enabled: bool) -> None:
        self._base = base
        self._store = store
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """Return whether the store and the context value may be read."""
        return self._enabled

    def now(self) -> datetime:
        if not self._enabled:
            return self._base.now()

        offset = clock_offset.get()
        if offset is None:
            offset = self._store.get()
        return self._base.now() + timedelta(seconds=offset)
