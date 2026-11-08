"""Helpers shared by the test-only controls endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.auth.seed import DEMO_PASSWORD


def login(client: TestClient, email: str = "admin@labapp.test") -> None:
    """Start a session with the demo password."""
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
