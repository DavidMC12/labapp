"""The request guards around the contract paths and the test controls."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.modules.testcontrols.controls import RequestControls
from tests.guards.helpers import FakeMonotonic, make_app, make_settings

OPENAPI_PATH = "/api/openapi.json"
DOCS_PATH = "/api/docs"
DATABASE_URL = "postgresql+psycopg://user:password@host/db"


def test_the_rate_limit_counts_the_contract_paths() -> None:
    client = TestClient(make_app(make_settings(), FakeMonotonic()))

    assert [client.get(DOCS_PATH).status_code for _ in range(120)] == [200] * 120

    response = client.get(OPENAPI_PATH)

    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"


def test_the_contract_paths_open_no_connection_with_the_controls_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("the application opened a connection")

    monkeypatch.setattr(psycopg, "connect", unexpected_connect)
    app = create_app(Settings(session_secret="test-secret", database_url=DATABASE_URL))
    client = TestClient(app)

    assert client.get(OPENAPI_PATH).status_code == 200
    assert client.get(DOCS_PATH).status_code == 200


def test_the_contract_paths_load_the_controls_when_they_are_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    original = RequestControls.load_request_controls

    def spy(
        self: RequestControls,
        method: str,
        path: str,
    ) -> tuple[float, object]:
        calls.append((method, path))
        return original(self, method, path)

    monkeypatch.setattr(RequestControls, "load_request_controls", spy)
    client = TestClient(create_app(Settings(session_secret="test-secret", test_mode=True)))

    assert client.get(OPENAPI_PATH).status_code == 200
    assert client.get(DOCS_PATH).status_code == 200
    assert calls == [("GET", OPENAPI_PATH), ("GET", DOCS_PATH)]


def test_the_contract_paths_are_public_while_the_test_controls_stay_guarded() -> None:
    client = TestClient(
        create_app(
            Settings(
                session_secret="test-secret",
                test_mode=False,
                test_token="secret",
            )
        )
    )

    assert client.get(OPENAPI_PATH).status_code == 200
    assert client.get(DOCS_PATH).status_code == 200
    assert client.get("/__test__/clock").status_code == 404
    assert client.get("/__test__/clock", headers={"X-Test-Token": "secret"}).status_code == 200
