"""Tests for the customer list route."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.customers.helpers import assert_field_error, assert_problem, create_payload


def test_default_page_lists_every_seed_customer_newest_first(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].get("/api/customers")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 10
    assert [item["id"] for item in body["items"]] == list(range(10, 0, -1))


def test_page_two_and_an_empty_page_beyond_the_end(clients: dict[str, TestClient]) -> None:
    for index in range(12):
        response = clients["sales"].post(
            "/api/customers",
            json=create_payload(
                name=f"List Customer {index}",
                email=f"list{index}@example.test",
            ),
        )
        assert response.status_code == 201

    first = clients["sales"].get("/api/customers", params={"page": 1})
    second = clients["sales"].get("/api/customers", params={"page": 2})
    third = clients["sales"].get("/api/customers", params={"page": 3})

    assert first.json()["total"] == 22
    assert len(first.json()["items"]) == 20
    assert len(second.json()["items"]) == 2
    assert second.json()["total"] == 22
    assert third.json()["items"] == []
    assert third.json()["total"] == 22


@pytest.mark.parametrize("query", ["cafeteria", "CAFETERÍA"])
def test_search_ignores_case_and_accents(
    clients: dict[str, TestClient],
    query: str,
) -> None:
    response = clients["sales"].get("/api/customers", params={"q": query})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["name"] for item in body["items"]] == ["Cafetería La Esquina"]


def test_search_is_literal_text(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/customers", params={"q": "%"})

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_search_query_too_long(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/customers", params={"q": "a" * 101})

    assert_field_error(
        response,
        field="q",
        code="TOO_LONG",
        message="Debe tener como máximo 100 caracteres.",
    )


@pytest.mark.parametrize(
    ("status_value", "expected_ids"),
    [
        ("active", [10, 9, 7, 6, 4, 3, 2, 1]),
        ("inactive", [8, 5]),
    ],
)
def test_status_filter(
    clients: dict[str, TestClient],
    status_value: str,
    expected_ids: list[int],
) -> None:
    response = clients["sales"].get("/api/customers", params={"status": status_value})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(expected_ids)
    assert [item["id"] for item in body["items"]] == expected_ids
    assert all(item["status"] == status_value for item in body["items"])


def test_invalid_page_is_a_validation_error(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/customers", params={"page": "abc"})

    assert_field_error(
        response,
        field="page",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


@pytest.mark.parametrize("page", [0, 1_000_001])
def test_page_out_of_range(clients: dict[str, TestClient], page: int) -> None:
    response = clients["sales"].get("/api/customers", params={"page": page})

    assert_field_error(
        response,
        field="page",
        code="OUT_OF_RANGE",
        message="El valor debe estar entre 1 y 1000000.",
    )


def test_invalid_status(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].get("/api/customers", params={"status": "deleted"})

    assert response.status_code == 422
    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"] == [
        {
            "field": "status",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]
