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


def test_sort_by_name_orders_the_returned_items(clients: dict[str, TestClient]) -> None:
    created = clients["sales"].post(
        "/api/customers",
        json=create_payload(name="Zzz Último", email="zzz@example.test"),
    )
    assert created.status_code == 201
    new_id = created.json()["id"]

    ascending = clients["sales"].get(
        "/api/customers",
        params={"sort": "name", "direction": "asc"},
    )
    descending = clients["sales"].get(
        "/api/customers",
        params={"sort": "name", "direction": "desc"},
    )

    assert ascending.status_code == 200
    assert [item["id"] for item in ascending.json()["items"]] == list(range(1, 11)) + [new_id]
    assert [item["id"] for item in descending.json()["items"]] == [new_id] + list(range(10, 0, -1))


def test_direction_defaults_and_a_lone_direction(clients: dict[str, TestClient]) -> None:
    default = clients["sales"].get("/api/customers")
    by_created_at = clients["sales"].get("/api/customers", params={"sort": "created_at"})
    by_email = clients["sales"].get("/api/customers", params={"sort": "email"})
    ascending = clients["sales"].get("/api/customers", params={"direction": "asc"})
    descending = clients["sales"].get("/api/customers", params={"direction": "desc"})

    assert [item["id"] for item in default.json()["items"]] == list(range(10, 0, -1))
    assert [item["id"] for item in by_created_at.json()["items"]] == list(range(10, 0, -1))
    assert [item["id"] for item in by_email.json()["items"]] == list(range(1, 11))
    assert [item["id"] for item in ascending.json()["items"]] == list(range(1, 11))
    assert [item["id"] for item in descending.json()["items"]] == list(range(10, 0, -1))


@pytest.mark.parametrize("sort", ["", "unknown", "Name", "createdAt"])
def test_invalid_sort_is_a_validation_error(
    clients: dict[str, TestClient],
    sort: str,
) -> None:
    response = clients["sales"].get("/api/customers", params={"sort": sort})

    assert_field_error(
        response,
        field="sort",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


@pytest.mark.parametrize("direction", ["", "ASC", "Desc", "ascending"])
def test_invalid_direction_is_a_validation_error(
    clients: dict[str, TestClient],
    direction: str,
) -> None:
    response = clients["sales"].get("/api/customers", params={"direction": direction})

    assert_field_error(
        response,
        field="direction",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_an_empty_sort_is_invalid_like_an_empty_status(
    clients: dict[str, TestClient],
) -> None:
    sort = clients["sales"].get("/api/customers", params={"sort": ""})
    status = clients["sales"].get("/api/customers", params={"status": ""})

    assert_field_error(
        sort,
        field="sort",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )
    assert_field_error(
        status,
        field="status",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )
