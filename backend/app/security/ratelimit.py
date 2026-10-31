"""Sliding-window rate limiting."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

GENERAL_LIMIT = (120, 60)
LOGIN_LIMIT = (10, 60)


@dataclass(frozen=True)
class RateDecision:
    """The result of one rate limiter hit."""

    allowed: bool
    retry_after: int


class SlidingWindowLimiter:
    """A per-key sliding-window limiter with an injected clock."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float],
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> RateDecision:
        """Record a hit for the key and decide whether it is allowed."""
        now = self._clock()
        hits = self._hits.get(key)

        if hits is not None:
            self._drop_expired(hits, now)
            if not hits:
                del self._hits[key]
                hits = None

        if hits is not None and len(hits) >= self._limit:
            return RateDecision(allowed=False, retry_after=self._retry_after(hits[0], now))

        if hits is None:
            hits = deque()
            self._hits[key] = hits
        hits.append(now)
        return RateDecision(allowed=True, retry_after=0)

    def _drop_expired(self, hits: deque[float], now: float) -> None:
        while hits and now - hits[0] >= self._window_seconds:
            hits.popleft()

    def _retry_after(self, oldest: float, now: float) -> int:
        remaining = oldest + self._window_seconds - now
        return max(1, math.ceil(remaining))
