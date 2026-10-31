"""Tests for the application clock."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from app.infra.clock import OffsetClock, SystemClock

BASE = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


class FixedClock:
    """A deterministic base clock."""

    def __init__(self, now: datetime = BASE) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def test_system_clock_returns_utc() -> None:
    before = datetime.now(UTC)
    result = SystemClock().now()
    after = datetime.now(UTC)

    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)
    assert before <= result <= after


def test_offset_clock_starts_at_the_base_time() -> None:
    clock = OffsetClock(FixedClock())

    assert clock.offset == timedelta(0)
    assert clock.now() == BASE


def test_offset_can_be_set_and_advanced() -> None:
    clock = OffsetClock(FixedClock())

    clock.set_offset(timedelta(hours=1))
    assert clock.offset == timedelta(hours=1)
    assert clock.now() == BASE + timedelta(hours=1)

    clock.advance(timedelta(minutes=30))
    assert clock.offset == timedelta(hours=1, minutes=30)
    assert clock.now() == BASE + timedelta(hours=1, minutes=30)

    clock.set_offset(timedelta(0))
    assert clock.offset == timedelta(0)
    assert clock.now() == BASE


def test_advancing_from_several_threads_is_safe() -> None:
    clock = OffsetClock(FixedClock())
    increments = 800

    with ThreadPoolExecutor(max_workers=16) as executor:
        list(executor.map(clock.advance, [timedelta(seconds=1)] * increments))

    assert clock.offset == timedelta(seconds=increments)
    assert clock.now() == BASE + timedelta(seconds=increments)
