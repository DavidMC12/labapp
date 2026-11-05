"""Tests for the declared and streamed body size limit."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi.testclient import TestClient

from app.middleware import MAX_BODY_BYTES
from tests.guards.helpers import FakeMonotonic, make_app, make_settings


def _client() -> TestClient:
    return TestClient(make_app(make_settings(test_mode=True), FakeMonotonic()))


def _chunks(size: int) -> Iterator[bytes]:
    yield b"x" * size


def _assert_too_large(response: Any) -> None:
    assert response.status_code == 413
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"]
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["status"] == 413
    assert body["code"] == "PAYLOAD_TOO_LARGE"
    assert body["detail"] == "La solicitud es demasiado grande."


def test_a_declared_body_at_the_limit_is_allowed() -> None:
    response = _client().post(
        "/api/auth/login",
        content=b"x" * MAX_BODY_BYTES,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code != 413


def test_a_declared_body_one_byte_over_the_limit_is_413() -> None:
    response = _client().post(
        "/api/auth/login",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )

    _assert_too_large(response)


def test_a_streamed_body_at_the_limit_is_allowed() -> None:
    response = _client().post(
        "/api/auth/login",
        content=_chunks(MAX_BODY_BYTES),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code != 413


def test_a_streamed_body_one_byte_over_the_limit_is_413() -> None:
    response = _client().post(
        "/api/auth/login",
        content=_chunks(MAX_BODY_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )

    _assert_too_large(response)
