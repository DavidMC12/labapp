"""Tests for the malformed JSON mapping."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.guards.helpers import FakeMonotonic, make_app, make_settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(make_app(make_settings(test_mode=True), FakeMonotonic()))


def _assert_malformed(response: object) -> None:
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Bad Request",
        "status": 400,
        "code": "MALFORMED_JSON",
        "detail": "El cuerpo de la solicitud no es un JSON válido.",
    }


def test_broken_json_on_login_is_400(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        content=b"{bad",
        headers={"Content-Type": "application/json"},
    )

    _assert_malformed(response)


def test_broken_json_on_customers_is_400_without_a_session(client: TestClient) -> None:
    response = client.post(
        "/api/customers",
        content=b"{bad",
        headers={"Content-Type": "application/json"},
    )

    _assert_malformed(response)


def test_broken_json_wins_over_a_wrong_origin(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        content=b"{bad",
        headers={
            "Content-Type": "application/json",
            "Origin": "http://evil.test",
        },
    )

    _assert_malformed(response)


def test_valid_json_with_a_missing_field_is_still_422(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"]
