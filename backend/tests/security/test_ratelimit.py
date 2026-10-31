"""Tests for the sliding-window rate limiter."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from app.errors import ApiError
from app.security.ratelimit import (
    GENERAL_LIMIT,
    LOGIN_LIMIT,
    RateDecision,
    SlidingWindowLimiter,
    rate_limited_error,
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


@pytest.mark.parametrize("retry_after", [1, 17, 60])
def test_rate_limited_error_carries_retry_after(retry_after: int) -> None:
    error = rate_limited_error(retry_after)

    assert isinstance(error, ApiError)
    assert error.status == 429
    assert error.code == "RATE_LIMITED"
    assert error.detail == ("Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.")
    assert error.extra["retry_after"] == retry_after


def test_sweep_removes_expired_keys_that_are_never_hit_again() -> None:
    limiter, clock = _limiter(limit=5, window_seconds=60)
    for index in range(1000):
        assert limiter.hit(f"key-{index}").allowed is True

    assert len(limiter._hits) == 1000
    clock.advance(61)

    assert limiter.hit("new-key").allowed is True
    assert len(limiter._hits) <= 2


def test_sweep_keeps_a_key_that_still_has_a_live_hit() -> None:
    limiter, clock = _limiter(limit=5, window_seconds=60)
    limiter.hit("old")
    clock.advance(50)
    limiter.hit("live")

    clock.advance(11)
    assert limiter.hit("new").allowed is True

    assert "old" not in limiter._hits
    assert "live" in limiter._hits
    assert "new" in limiter._hits


def test_sweep_runs_at_most_once_per_window() -> None:
    limiter, clock = _limiter(limit=5, window_seconds=60)
    limiter.hit("a")
    assert limiter._last_sweep == 0

    clock.advance(30)
    limiter.hit("b")
    assert limiter._last_sweep == 0

    clock.advance(30)
    limiter.hit("c")
    assert limiter._last_sweep == 60
    assert "a" not in limiter._hits
    assert "b" in limiter._hits


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_must_be_at_least_one(limit: int) -> None:
    with pytest.raises(ValueError):
        SlidingWindowLimiter(limit, 60, lambda: 0.0)


@pytest.mark.parametrize("window_seconds", [0, -0.1, -60])
def test_window_must_be_positive(window_seconds: float) -> None:
    with pytest.raises(ValueError):
        SlidingWindowLimiter(1, window_seconds, lambda: 0.0)


def test_valid_constructor_arguments_are_accepted() -> None:
    limiter = SlidingWindowLimiter(1, 0.001, lambda: 0.0)

    assert limiter.hit("k").allowed is True


def test_concurrent_hits_allow_exactly_the_limit() -> None:
    limiter = SlidingWindowLimiter(limit=10, window_seconds=60, clock=lambda: 0.0)

    with ThreadPoolExecutor(max_workers=20) as executor:
        decisions = list(executor.map(limiter.hit, ["same-key"] * 100))

    assert sum(decision.allowed for decision in decisions) == 10
    assert all(decision.retry_after == 60 for decision in decisions if not decision.allowed)
