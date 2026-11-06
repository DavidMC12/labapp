"""Helpers shared by the request guard tests."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.config import Settings
from app.main import create_app


class FakeMonotonic:
    """A deterministic monotonic clock for the rate limiter tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "session_secret": "test-secret",
        "test_mode": False,
        "app_origin": "http://localhost:3000",
    }
    values.update(overrides)
    return Settings(**values)


def make_app(
    settings: Settings,
    monotonic: FakeMonotonic,
) -> FastAPI:
    return create_app(settings, monotonic=monotonic)
