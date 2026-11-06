"""Sliding-window rate limiting."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from app.errors import ApiError

GENERAL_LIMIT = (120, 60)
LOGIN_LIMIT = (10, 60)
RATE_LIMITED_MESSAGE = "Demasiadas solicitudes. Espera un momento e inténtalo de nuevo."


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
        max_keys: int = 10_000,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0")
        if max_keys < 1:
            raise ValueError("max_keys must be at least 1")

        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._last_sweep: float | None = None
        self._lock = Lock()

    def hit(self, key: str) -> RateDecision:
        """Record a hit for the key and decide whether it is allowed."""
        with self._lock:
            now = self._clock()
            self._sweep_expired(now)
            hits = self._hits.get(key)

            if hits is not None:
                self._drop_expired(hits, now)
                if not hits:
                    del self._hits[key]
                    hits = None

            if hits is not None and len(hits) >= self._limit:
                return RateDecision(
                    allowed=False,
                    retry_after=self._retry_after(hits[0], now),
                )

            if hits is None:
                if len(self._hits) >= self._max_keys:
                    oldest = min(self._hits, key=lambda key: self._hits[key][-1])
                    del self._hits[oldest]
                hits = deque()
                self._hits[key] = hits
            hits.append(now)
            return RateDecision(allowed=True, retry_after=0)

    def clear(self) -> None:
        """Forget every tracked key and its hits."""
        with self._lock:
            self._hits.clear()
            self._last_sweep = None

    def _sweep_expired(self, now: float) -> None:
        if self._last_sweep is not None and now - self._last_sweep < self._window_seconds:
            return

        self._last_sweep = now
        expired = [
            key for key, hits in self._hits.items() if now - hits[-1] >= self._window_seconds
        ]
        for key in expired:
            del self._hits[key]

    def _drop_expired(self, hits: deque[float], now: float) -> None:
        while hits and now - hits[0] >= self._window_seconds:
            hits.popleft()

    def _retry_after(self, oldest: float, now: float) -> int:
        remaining = oldest + self._window_seconds - now
        return max(1, math.ceil(remaining))


def rate_limited_error(retry_after: int) -> ApiError:
    """Build the 429 error and expose the Retry-After value as an extra member."""
    return ApiError(429, "RATE_LIMITED", RATE_LIMITED_MESSAGE, retry_after=retry_after)
