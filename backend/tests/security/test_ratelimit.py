"""Tests for the sliding-window rate limiter."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.security.ratelimit import (
    GENERAL_LIMIT,
    LOGIN_LIMIT,
    RateDecision,
    SlidingWindowLimiter,
)


class FakeClock:
    """A deterministic clock for limiter tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _limiter(limit: int = 3, window_seconds: float = 60) -> tuple[SlidingWindowLimiter, FakeClock]:
    clock = FakeClock()
    return SlidingWindowLimiter(limit, window_seconds, clock), clock


def test_window_constants() -> None:
    assert GENERAL_LIMIT == (120, 60)
    assert LOGIN_LIMIT == (10, 60)


def test_hits_up_to_the_limit_are_allowed() -> None:
    limiter, _ = _limiter(limit=3)

    assert [limiter.hit("k") for _ in range(3)] == [RateDecision(True, 0)] * 3


def test_one_hit_over_the_limit_is_rejected() -> None:
    limiter, _ = _limiter(limit=3)

    for _ in range(3):
        limiter.hit("k")

    assert limiter.hit("k") == RateDecision(False, 60)


def test_request_is_allowed_after_the_window_moves() -> None:
    limiter, clock = _limiter(limit=1, window_seconds=10)

    assert limiter.hit("k") == RateDecision(True, 0)
    clock.advance(5)
    assert limiter.hit("k") == RateDecision(False, 5)

    clock.advance(5)
    assert limiter.hit("k") == RateDecision(True, 0)


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        (0.1, 10),
        (1.1, 9),
        (9.5, 1),
        (9.999, 1),
    ],
)
def test_retry_after_is_rounded_up_and_at_least_one(elapsed: float, expected: int) -> None:
    limiter, clock = _limiter(limit=1, window_seconds=10)
    limiter.hit("k")
    clock.advance(elapsed)

    assert limiter.hit("k") == RateDecision(False, expected)


def test_retry_after_uses_the_oldest_hit() -> None:
    limiter, clock = _limiter(limit=2, window_seconds=10)
    limiter.hit("k")
    clock.advance(4)
    limiter.hit("k")
    clock.advance(1)

    assert limiter.hit("k") == RateDecision(False, 5)


def test_keys_are_independent() -> None:
    limiter, _ = _limiter(limit=1)

    assert limiter.hit("a") == RateDecision(True, 0)
    assert limiter.hit("b") == RateDecision(True, 0)
    assert limiter.hit("a") == RateDecision(False, 60)
    assert limiter.hit("b") == RateDecision(False, 60)


def test_rejected_hits_do_not_grow_memory() -> None:
    limiter, _ = _limiter(limit=2, window_seconds=10)
    limiter.hit("k")
    limiter.hit("k")

    for _ in range(100):
        assert limiter.hit("k").allowed is False

    assert len(limiter._hits["k"]) == 2


def test_expired_hits_are_dropped() -> None:
    limiter, clock = _limiter(limit=2, window_seconds=10)
    limiter.hit("k")
    limiter.hit("k")
    clock.advance(10)

    assert limiter.hit("k") == RateDecision(True, 0)
    assert len(limiter._hits["k"]) == 1


def test_hit_at_the_window_boundary_is_no_longer_counted() -> None:
    limiter, clock = _limiter(limit=1, window_seconds=10)
    limiter.hit("k")
    clock.advance(10)

    assert limiter.hit("k") == RateDecision(True, 0)


def test_decision_is_frozen() -> None:
    decision = RateDecision(True, 0)

    with pytest.raises(FrozenInstanceError):
        decision.allowed = False
