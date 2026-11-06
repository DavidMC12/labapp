"""Tests for the middleware order."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.middleware import MAX_BODY_BYTES
from tests.guards.helpers import FakeMonotonic, make_app, make_settings


class Body(BaseModel):
    value: int


def _with_test_routes(app: FastAPI) -> FastAPI:
    router = APIRouter(include_in_schema=False)

    @router.get("/__test__/x")
    def x() -> dict[str, bool]:
        return {"ok": True}

    @router.post("/__test__/body")
    def body(payload: Body) -> dict[str, int]:
        return {"value": payload.value}

    app.include_router(router)
    return app


def _exhaust_general(client: TestClient) -> None:
    for _ in range(120):
        assert client.get("/api/customers").status_code == 401


def test_a_rate_limited_request_wins_over_the_body_size() -> None:
    client = TestClient(make_app(make_settings(), FakeMonotonic()))
    _exhaust_general(client)

    response = client.post(
        "/api/auth/login",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 429


def test_a_rate_limited_request_wins_over_malformed_json() -> None:
    client = TestClient(make_app(make_settings(), FakeMonotonic()))
    _exhaust_general(client)

    response = client.post(
        "/api/auth/login",
        content=b"{bad",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 429


def test_a_declared_body_over_the_limit_is_413_when_not_rate_limited() -> None:
    client = TestClient(make_app(make_settings(), FakeMonotonic()))

    response = client.post(
        "/api/auth/login",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_the_body_size_wins_over_a_wrong_origin() -> None:
    client = TestClient(make_app(make_settings(), FakeMonotonic()))

    response = client.post(
        "/api/auth/login",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={
            "Content-Type": "application/json",
            "Origin": "http://evil.test",
        },
    )

    assert response.status_code == 413


def test_a_streamed_body_over_the_limit_is_413_when_not_rate_limited() -> None:
    client = TestClient(make_app(make_settings(), FakeMonotonic()))

    def chunks() -> Iterator[bytes]:
        yield b"x" * (MAX_BODY_BYTES + 1)

    response = client.post(
        "/api/auth/login",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_health_still_works_after_the_general_limit_is_exhausted() -> None:
    client = TestClient(make_app(make_settings(), FakeMonotonic()))
    _exhaust_general(client)

    assert client.get("/api/health").status_code == 200


def test_unauthorized_test_control_probes_are_404_before_any_other_guard() -> None:
    app = _with_test_routes(make_app(make_settings(test_token="secret"), FakeMonotonic()))
    client = TestClient(app)

    assert client.post("/__test__/x").status_code == 404
    assert client.get("/__test__/x/").status_code == 404
    assert (
        client.post(
            "/__test__/body",
            content=b"{bad",
            headers={"Content-Type": "application/json"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/__test__/body",
            content=b"x" * (MAX_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"},
        ).status_code
        == 404
    )
