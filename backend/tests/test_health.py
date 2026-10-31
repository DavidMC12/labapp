from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_needs_no_authentication(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert "set-cookie" not in response.headers


def test_request_id_is_generated(client: TestClient) -> None:
    response = client.get("/api/health")
    request_id = response.headers.get("x-request-id")

    assert request_id is not None
    assert UUID(request_id).version == 4
    assert str(UUID(request_id)) == request_id


@pytest.mark.parametrize("value", ["abc-123", "A" * 64, "trace.abc_123-XYZ"])
def test_request_id_is_echoed_when_valid(client: TestClient, value: str) -> None:
    response = client.get("/api/health", headers={"X-Request-Id": value})

    assert response.headers["x-request-id"] == value


@pytest.mark.parametrize(
    "value",
    ["a" * 65, "abc 123", "abc/123", "abc+123", "abc:123"],
)
def test_invalid_request_id_is_replaced(client: TestClient, value: str) -> None:
    response = client.get("/api/health", headers={"X-Request-Id": value})
    request_id = response.headers["x-request-id"]

    assert request_id != value
    assert UUID(request_id).version == 4
    assert str(UUID(request_id)) == request_id


def test_every_response_has_a_different_request_id(client: TestClient) -> None:
    first = client.get("/api/health").headers["x-request-id"]
    second = client.get("/api/health").headers["x-request-id"]

    assert first != second
