"""Tests for the security headers of every API response (SPEC section 8)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from app.middleware import MAX_BODY_BYTES, ApiResponseHeadersMiddleware
from tests.guards.helpers import FakeMonotonic, make_app, make_settings
from tests.testcontrols.helpers import login

TEST_TOKEN = {"X-Test-Token": "secret"}


def _client(**overrides: Any) -> TestClient:
    return TestClient(make_app(make_settings(**overrides), FakeMonotonic()))


def _session_client() -> TestClient:
    client = _client(test_token="secret")
    login(client)
    return client


def _values(response: Any, name: str) -> list[str]:
    return response.headers.get_list(name)


def _assert_api_headers(response: Any, cache_control: str | None = "no-store") -> None:
    assert _values(response, "x-content-type-options") == ["nosniff"]
    expected = [] if cache_control is None else [cache_control]
    assert _values(response, "cache-control") == expected


def test_a_successful_read_carries_both_headers() -> None:
    response = _session_client().get("/api/customers")

    assert response.status_code == 200
    _assert_api_headers(response)


def test_health_carries_both_headers() -> None:
    response = _client().get("/api/health")

    assert response.status_code == 200
    _assert_api_headers(response)


def test_an_unauthenticated_read_carries_both_headers() -> None:
    response = _client().get("/api/customers")

    assert response.status_code == 401
    _assert_api_headers(response)


def test_an_unknown_api_path_carries_both_headers() -> None:
    response = _client().get("/api/nope")

    assert response.status_code == 404
    _assert_api_headers(response)


def test_a_validation_error_carries_both_headers() -> None:
    response = _session_client().get("/api/customers", params={"status": "nope"})

    assert response.status_code == 422
    _assert_api_headers(response)


def test_a_body_over_the_limit_carries_both_headers() -> None:
    response = _client(test_token="secret").post(
        "/api/auth/login",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={"Content-Type": "application/json", **TEST_TOKEN},
    )

    assert response.status_code == 413
    _assert_api_headers(response)


def test_a_rate_limited_login_carries_both_headers() -> None:
    client = _client()
    for _ in range(10):
        assert client.post("/api/auth/login", json={}).status_code == 422

    response = client.post("/api/auth/login", json={})

    assert response.status_code == 429
    _assert_api_headers(response)


def test_an_unauthorized_reset_carries_both_headers() -> None:
    response = _client(test_token="secret").post("/__test__/reset")

    assert response.status_code == 404
    _assert_api_headers(response)


def test_an_authorized_reset_carries_both_headers() -> None:
    response = _client(test_token="secret").post("/__test__/reset", headers=TEST_TOKEN)

    assert response.status_code == 200
    _assert_api_headers(response)


def test_the_csv_export_keeps_its_own_cache_control() -> None:
    response = _session_client().get("/api/customers/export")

    assert response.status_code == 200
    _assert_api_headers(response)
    assert _values(response, "cache-control") == ["no-store"]


def test_a_route_that_sets_its_own_cache_control_keeps_it() -> None:
    app = make_app(make_settings(test_token="secret"), FakeMonotonic())

    @app.get("/api/private")
    def private(response: Response) -> dict[str, bool]:
        response.headers["Cache-Control"] = "private"
        return {"ok": True}

    response = TestClient(app).get("/api/private")

    assert response.status_code == 200
    assert _values(response, "x-content-type-options") == ["nosniff"]
    assert _values(response, "cache-control") == ["private"]


def test_an_unhandled_error_carries_both_headers() -> None:
    app = make_app(make_settings(test_token="secret"), FakeMonotonic())

    @app.get("/api/explode")
    def explode() -> None:
        raise RuntimeError("boom")

    response = TestClient(app, raise_server_exceptions=False).get("/api/explode")

    assert response.status_code == 500
    _assert_api_headers(response)


@pytest.mark.parametrize("path", ["/api/openapi.json", "/api/docs"])
def test_the_public_documents_only_carry_nosniff(path: str) -> None:
    response = _client().get(path)

    assert response.status_code == 200
    _assert_api_headers(response, cache_control=None)


def test_a_path_outside_the_api_prefix_gets_no_headers() -> None:
    response = _client().get("/robots.txt")

    assert response.status_code == 404
    assert _values(response, "x-content-type-options") == []
    assert _values(response, "cache-control") == []


def test_the_middleware_passes_a_lifespan_scope_through() -> None:
    scopes: list[dict[str, Any]] = []

    async def inner(scope: dict[str, Any], receive: Any, send: Any) -> None:
        scopes.append(scope)

    async def receive() -> dict[str, Any]:
        return {"type": "lifespan.startup"}

    async def send(message: dict[str, Any]) -> None:
        return None

    scope: dict[str, Any] = {"type": "lifespan"}

    asyncio.run(ApiResponseHeadersMiddleware(inner)(scope, receive, send))

    assert scopes == [scope]
