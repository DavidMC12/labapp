"""The OpenAPI document and the Swagger UI are served under `/api`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.testcontrols.helpers import login

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
OPENAPI_PATH = "/api/openapi.json"
DOCS_PATH = "/api/docs"
OLD_PATHS = ("/openapi.json", "/docs", "/redoc")


def _committed_contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_the_contract_path_serves_the_committed_document(client: TestClient) -> None:
    response = client.get(OPENAPI_PATH)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == _committed_contract()


def test_the_swagger_page_points_at_the_contract_on_the_same_origin(
    client: TestClient,
) -> None:
    response = client.get(DOCS_PATH)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert OPENAPI_PATH in response.text
    assert "redoc" not in response.text.lower()


def test_a_logged_in_user_reads_both_paths(client: TestClient) -> None:
    login(client)

    assert client.get(OPENAPI_PATH).json() == _committed_contract()
    assert client.get(DOCS_PATH).status_code == 200


def test_a_get_from_another_origin_is_allowed(client: TestClient) -> None:
    headers = {"Origin": "https://evil.test"}

    assert client.get(OPENAPI_PATH, headers=headers).status_code == 200
    assert client.get(DOCS_PATH, headers=headers).status_code == 200


@pytest.mark.parametrize("path", OLD_PATHS)
def test_the_old_paths_answer_the_standard_404_problem(
    client: TestClient,
    path: str,
) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 404
    assert body["code"] == "NOT_FOUND"
