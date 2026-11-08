"""The two guard layers of the test-only controls."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import register_error_handlers
from app.main import create_app
from app.modules.testcontrols.routes import router as controls_router

TOKEN = "secret"


def _client(*, test_mode: bool, test_token: str) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                session_secret="test-secret",
                test_mode=test_mode,
                test_token=test_token,
            )
        )
    )


def test_a_token_opens_the_controls_without_test_mode() -> None:
    client = _client(test_mode=False, test_token=TOKEN)

    assert client.post("/__test__/reset").status_code == 404
    assert client.post("/__test__/reset", headers={"X-Test-Token": "wrong"}).status_code == 404

    response = client.post("/__test__/reset", headers={"X-Test-Token": TOKEN})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_without_a_configured_token_every_probe_is_not_found() -> None:
    client = _client(test_mode=False, test_token="")

    response = client.post("/__test__/reset", headers={"X-Test-Token": "anything"})

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_test_mode_opens_the_controls_without_a_token() -> None:
    client = _client(test_mode=True, test_token="")

    assert client.post("/__test__/reset").status_code == 200
    assert client.get("/__test__/clock").status_code == 200


def test_the_router_repeats_the_guard_without_the_middleware() -> None:
    source = create_app(
        Settings(
            session_secret="test-secret",
            test_mode=False,
            test_token=TOKEN,
        )
    )
    app = FastAPI()
    app.state.settings = source.state.settings
    app.state.clock_store = source.state.clock_store
    app.state.container = source.state.container
    register_error_handlers(app)
    app.include_router(controls_router)
    client = TestClient(app)

    denied = client.get("/__test__/clock")
    allowed = client.get("/__test__/clock", headers={"X-Test-Token": TOKEN})

    assert denied.status_code == 404
    assert denied.json()["code"] == "NOT_FOUND"
    assert allowed.status_code == 200
