"""The controllable application clock and its in-memory offset store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.engine import Connection

from app.infra.clock import ControlledClock, OffsetClock, clock_offset
from app.modules.testcontrols.memory import InMemoryClockOffsetStore

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


class FixedClock:
    """A clock that always returns the same instant."""

    def __init__(self, now: datetime) -> None:
        self.value = now

    def now(self) -> datetime:
        return self.value


class RecordingStore:
    """An offset store that counts its reads."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self.reads = 0

    def get(self, *, connection: Connection | None = None) -> float:
        self.reads += 1
        return self.seconds

    def set(self, seconds: float, *, connection: Connection | None = None) -> None:
        self.seconds = seconds

    def advance(self, seconds: float, *, connection: Connection | None = None) -> float:
        self.seconds += seconds
        return self.seconds


def test_the_in_memory_store_sets_and_advances_the_offset() -> None:
    clock = OffsetClock(FixedClock(NOW))
    store = InMemoryClockOffsetStore(clock)

    assert store.get() == 0.0
    store.set(60)
    assert store.get() == 60.0
    assert clock.now() == NOW + timedelta(seconds=60)

    assert store.advance(30.5) == 90.5
    assert clock.now() == NOW + timedelta(seconds=90.5)


def test_a_disabled_controlled_clock_never_reads_the_store_or_the_context() -> None:
    base = FixedClock(NOW)
    store = RecordingStore(3600)
    clock = ControlledClock(base, store, enabled=False)

    token = clock_offset.set(7200)
    try:
        assert clock.now() == NOW
    finally:
        clock_offset.reset(token)

    assert clock.enabled is False
    assert store.reads == 0


def test_an_enabled_controlled_clock_reads_the_store_for_exempt_paths() -> None:
    base = FixedClock(NOW)
    store = RecordingStore(3600)
    clock = ControlledClock(base, store, enabled=True)

    assert clock.now() == NOW + timedelta(seconds=3600)
    assert store.reads == 1


def test_an_enabled_controlled_clock_prefers_the_request_value() -> None:
    base = FixedClock(NOW)
    store = RecordingStore(3600)
    clock = ControlledClock(base, store, enabled=True)

    token = clock_offset.set(120)
    try:
        assert clock.now() == NOW + timedelta(seconds=120)
    finally:
        clock_offset.reset(token)

    assert store.reads == 0
    assert clock.now() == NOW + timedelta(seconds=3600)
    assert store.reads == 1
