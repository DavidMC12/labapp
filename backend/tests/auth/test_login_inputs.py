"""Tests for unusual login payloads."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.modules.auth.seed import DEMO_PASSWORD

LOGIN = "/api/auth/login"


def _assert_invalid_credentials(response: Any) -> None:
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["detail"] == "Email o contraseña incorrectos."
    assert "errors" not in body


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "admin\u0000@labapp.test", "password": DEMO_PASSWORD},
        {"email": "admin@labapp.test", "password": "Demo\u0000-LabApp-2026!"},
        {"email": "admin@labapp.test", "password": "x" * 90_000},
        {"email": "x" * 90_000 + "@labapp.test", "password": DEMO_PASSWORD},
    ],
    ids=["nul-email", "nul-password", "large-password", "large-email"],
)
def test_odd_string_inputs_are_invalid_credentials(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    assert len(json.dumps(payload)) < 100 * 1024

    response = client.post(LOGIN, json=payload)

    _assert_invalid_credentials(response)


@pytest.mark.parametrize("field", ["email", "password"])
def test_a_lone_surrogate_is_invalid_credentials(
    client: TestClient,
    field: str,
) -> None:
    payload = {"email": "admin@labapp.test", "password": DEMO_PASSWORD}
    payload[field] = "\ud800"

    response = client.post(
        LOGIN,
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    _assert_invalid_credentials(response)


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"email": 123, "password": DEMO_PASSWORD}, "email"),
        ({"email": ["admin@labapp.test"], "password": DEMO_PASSWORD}, "email"),
        ({"email": "admin@labapp.test", "password": None}, "password"),
        ({"email": "admin@labapp.test", "password": {"value": "secret"}}, "password"),
    ],
    ids=["int-email", "list-email", "null-password", "object-password"],
)
def test_wrong_json_types_are_validation_errors(
    client: TestClient,
    payload: dict[str, object],
    field: str,
) -> None:
    response = client.post(LOGIN, json=payload)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"] == "Revisa los datos ingresados."
    assert body["errors"] == [
        {
            "field": field,
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]
