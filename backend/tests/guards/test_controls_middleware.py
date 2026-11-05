"""Tests for the test-controls guard middleware."""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import Settings
from app.middleware import MAX_BODY_BYTES
from tests.guards.helpers import FakeMonotonic, make_app, make_settings


class Body(BaseModel):
    value: int


def _app(settings: Settings) -> FastAPI:
    app = make_app(settings, FakeMonotonic())
    router = APIRouter(include_in_schema=False)

    @router.get("/__test__")
    def root() -> dict[str, bool]:
        return {"ok": True}

    @router.get("/__test__/x")
    def x() -> dict[str, bool]:
        return {"ok": True}

    @router.post("/__test__/body")
    def body(payload: Body) -> dict[str, int]:
        return {"value": payload.value}

    app.include_router(router)
    return app


def _headers(token: str | None) -> dict[str, str]:
    return {} if token is None else {"X-Test-Token": token}


@pytest.mark.parametrize(
    ("test_mode", "test_token", "header", "expected"),
    [
        (True, "", None, 200),
        (True, "", "", 200),
        (True, "", "anything", 200),
        (True, "secret", "wrong", 200),
        (False, "", None, 404),
        (False, "", "", 404),
        (False, "", "anything", 404),
        (False, "secret", None, 404),
        (False, "secret", "", 404),
        (False, "secret", "wrong", 404),
        (False, "secret", "Secret", 404),
        (False, "secret", "secret", 200),
    ],
)
def test_guard_table(
    test_mode: bool,
    test_token: str,
    header: str | None,
    expected: int,
) -> None:
    client = TestClient(_app(make_settings(test_mode=test_mode, test_token=test_token)))

    assert client.get("/__test__/x", headers=_headers(header)).status_code == expected


def test_the_root_test_path_is_guarded_too() -> None:
    client = TestClient(_app(make_settings(test_token="secret")))

    assert client.get("/__test__").status_code == 404
    assert client.get("/__test__", headers={"X-Test-Token": "secret"}).status_code == 200


def test_a_guarded_request_gets_the_not_found_problem() -> None:
    response = TestClient(_app(make_settings(test_token="secret"))).get("/__test__/x")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"]
    body = response.json()
    assert body["status"] == 404
    assert body["code"] == "NOT_FOUND"
    assert body["detail"] == "No se encontró el recurso solicitado."


def test_an_unauthorized_probe_is_404_for_everything() -> None:
    client = TestClient(_app(make_settings(test_token="secret")))

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


def test_with_the_token_the_route_behaves_normally() -> None:
    client = TestClient(_app(make_settings(test_token="secret")))
    headers = {"X-Test-Token": "secret"}

    assert client.post("/__test__/x", headers=headers).status_code == 405
    assert client.get("/__test__/x/", headers=headers, follow_redirects=False).status_code in {
        307,
        308,
    }
    assert (
        client.post(
            "/__test__/body",
            content=b"{bad",
            headers={**headers, "Content-Type": "application/json"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/__test__/body",
            content=b"x" * (MAX_BODY_BYTES + 1),
            headers={**headers, "Content-Type": "application/json"},
        ).status_code
        == 413
    )


def test_paths_outside_the_test_prefix_are_not_guarded() -> None:
    client = TestClient(_app(make_settings(test_token="secret")))

    assert client.get("/api/health").status_code == 200
