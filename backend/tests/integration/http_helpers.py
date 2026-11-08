"""Helpers to build the application over the test database."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD


def settings_for(database_settings: Settings, *, lock_timeout_ms: int | None = None) -> Settings:
    update: dict[str, object] = {
        "session_secret": "test-secret",
        "test_mode": True,
        "app_origin": "http://localhost:3000",
    }
    if lock_timeout_ms is not None:
        update["lock_timeout_ms"] = lock_timeout_ms
    return database_settings.model_copy(update=update)


@contextmanager
def app_for(settings: Settings) -> Iterator[FastAPI]:
    app = create_app(settings)
    try:
        yield app
    finally:
        app.state.engine.dispose()


def login_as_finance(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "finance@labapp.test", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
