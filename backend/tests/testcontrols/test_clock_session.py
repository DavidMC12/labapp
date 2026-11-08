"""The stored clock offset drives session expiry through the real routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.modules.auth.seed import DEMO_PASSWORD

SESSION_TIMEOUT_SECONDS = 8 * 60 * 60


def _app() -> FastAPI:
    return create_app(Settings(session_secret="test-secret", test_mode=True))


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "finance@labapp.test", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200


def test_the_stored_offset_expires_a_session_through_the_real_routes() -> None:
    app = _app()
    client = TestClient(app)
    app.state.clock_store.set(3600)
    _login(client)
    assert client.get("/api/auth/me").status_code == 200

    app.state.clock_store.advance(SESSION_TIMEOUT_SECONDS + 1)

    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


def test_a_small_advance_keeps_the_session_alive() -> None:
    app = _app()
    client = TestClient(app)
    _login(client)

    app.state.clock_store.advance(SESSION_TIMEOUT_SECONDS - 1)

    assert client.get("/api/auth/me").status_code == 200
