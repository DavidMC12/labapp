"""Origin guard tests."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import register_error_handlers
from app.guards.origin import origin_guard
from tests.guards.helpers import FakeMonotonic, make_app, make_settings

APP_ORIGIN = "http://localhost:3000"
STATE_CHANGING_METHODS = ["POST", "PUT", "PATCH", "DELETE"]


def _guard_app(settings: Settings) -> FastAPI:
    app = FastAPI(dependencies=[Depends(origin_guard)])
    app.state.settings = settings
    register_error_handlers(app)

    @app.api_route("/api/echo", methods=["GET", *STATE_CHANGING_METHODS])
    def echo() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/__test__/x")
    def test_route() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/outside/x")
    def outside() -> dict[str, bool]:
        return {"ok": True}

    return app


@pytest.mark.parametrize("method", STATE_CHANGING_METHODS)
def test_a_different_origin_is_rejected(method: str) -> None:
    client = TestClient(_guard_app(make_settings()))

    response = client.request(method, "/api/echo", headers={"Origin": "http://evil.test"})

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "CSRF_ORIGIN_MISMATCH"
    assert body["detail"] == "La solicitud no proviene de la aplicación."


@pytest.mark.parametrize("method", STATE_CHANGING_METHODS)
def test_a_matching_or_missing_origin_is_allowed(method: str) -> None:
    client = TestClient(_guard_app(make_settings()))

    assert client.request(method, "/api/echo", headers={"Origin": APP_ORIGIN}).status_code == 200
    assert client.request(method, "/api/echo").status_code == 200


def test_get_is_never_checked() -> None:
    client = TestClient(_guard_app(make_settings()))

    assert client.get("/api/echo", headers={"Origin": "http://evil.test"}).status_code == 200


def test_paths_outside_api_are_not_checked() -> None:
    client = TestClient(_guard_app(make_settings()))

    assert client.post("/__test__/x", headers={"Origin": "http://evil.test"}).status_code == 200
    assert client.post("/outside/x", headers={"Origin": "http://evil.test"}).status_code == 200


def test_any_allowed_origin_passes() -> None:
    settings = make_settings(vercel_url="preview.vercel.app")
    client = TestClient(_guard_app(settings))

    for origin in (APP_ORIGIN, "https://preview.vercel.app"):
        assert client.post("/api/echo", headers={"Origin": origin}).status_code == 200


def test_an_empty_allowed_list_rejects_an_origin_but_not_a_missing_one() -> None:
    settings = make_settings(app_origin="not-an-origin")
    assert settings.allowed_origins == ()
    client = TestClient(_guard_app(settings))

    assert client.post("/api/echo", headers={"Origin": APP_ORIGIN}).status_code == 403
    assert client.post("/api/echo").status_code == 200


def test_the_real_app_checks_the_origin_on_login() -> None:
    client = TestClient(make_app(make_settings(test_mode=True), FakeMonotonic()))

    assert (
        client.post(
            "/api/auth/login",
            json={},
            headers={"Origin": "http://evil.test"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/login",
            json={},
            headers={"Origin": APP_ORIGIN},
        ).status_code
        == 422
    )
    assert client.post("/api/auth/login", json={}).status_code == 422


def test_the_real_app_checks_origin_before_the_session() -> None:
    client = TestClient(make_app(make_settings(test_mode=True), FakeMonotonic()))

    assert (
        client.post(
            "/api/customers",
            json={},
            headers={"Origin": "http://evil.test"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/customers",
            json={},
            headers={"Origin": APP_ORIGIN},
        ).status_code
        == 401
    )


def test_real_get_requests_ignore_the_origin() -> None:
    client = TestClient(make_app(make_settings(test_mode=True), FakeMonotonic()))

    assert client.get("/api/health", headers={"Origin": "http://evil.test"}).status_code == 200
    assert client.get("/api/customers", headers={"Origin": "http://evil.test"}).status_code == 401
