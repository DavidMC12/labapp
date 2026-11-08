"""The two guard layers of the test-only controls."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse
from starlette.types import Receive, Scope, Send

from app.config import Settings
from app.errors import register_error_handlers
from app.guards.controls import ControlsGuardMiddleware
from app.main import create_app
from app.modules.testcontrols.routes import router as controls_router

TOKEN = "secret"


async def _accepting_app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "websocket":
        await send({"type": "websocket.accept"})
        return
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


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


def test_the_controls_are_not_in_the_openapi_schema(
    controls_client: TestClient,
) -> None:
    schema = controls_client.get("/api/openapi.json").json()

    assert not any(path.startswith("/__test__") for path in schema["paths"])


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


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/__test__/reset"),
        ("POST", "/__test__/reset"),
        ("HEAD", "/__test__/reset"),
        ("OPTIONS", "/__test__/reset"),
        ("POST", "/__test__/reset/"),
        ("POST", "//__test__/reset"),
        ("POST", "/__TEST__/reset"),
        ("POST", "/%5F%5Ftest%5F%5F/reset"),
    ],
)
def test_the_guard_answers_not_found_for_every_variant(
    method: str,
    path: str,
) -> None:
    client = _client(test_mode=False, test_token=TOKEN)

    response = client.request(method, path)

    assert response.status_code == 404
    if method != "HEAD":
        assert response.json()["code"] == "NOT_FOUND"


def test_the_guard_uses_the_path_without_the_root_path() -> None:
    client = TestClient(
        create_app(
            Settings(
                session_secret="test-secret",
                test_mode=False,
                test_token=TOKEN,
            )
        ),
        root_path="/prefix",
    )

    denied = client.post("/prefix/__test__/reset")
    allowed = client.post(
        "/prefix/__test__/reset",
        headers={"X-Test-Token": TOKEN},
    )

    assert denied.status_code == 404
    assert allowed.status_code == 200


def test_the_guard_denies_a_websocket_under_the_controls() -> None:
    middleware = ControlsGuardMiddleware(
        _accepting_app,
        Settings(session_secret="test-secret", test_mode=False, test_token=TOKEN),
    )
    client = TestClient(middleware)

    with pytest.raises(WebSocketDenialResponse) as info:
        with client.websocket_connect("/__test__/reset"):
            pass

    assert info.value.status_code == 404
    assert json.loads(info.value.content)["code"] == "NOT_FOUND"

    with client.websocket_connect(
        "/__test__/reset",
        headers={"X-Test-Token": TOKEN},
    ):
        pass


def test_a_websocket_outside_the_controls_is_not_denied() -> None:
    middleware = ControlsGuardMiddleware(
        _accepting_app,
        Settings(session_secret="test-secret", test_mode=False, test_token=TOKEN),
    )
    client = TestClient(middleware)

    with client.websocket_connect("/api/stream"):
        pass
