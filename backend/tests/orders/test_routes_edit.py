"""Tests for editing drafts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.customers.models import CustomerStatus
from tests.orders.helpers import (
    add_line_payload,
    assert_field_error,
    assert_problem,
    change_customer_payload,
    create_order_payload,
    quantity_payload,
)


def _deactivate(app: FastAPI, customer_id: int = 1) -> None:
    app.state.customer_repository.set_status(
        customer_id, CustomerStatus.INACTIVE, None, datetime.now(UTC)
    )


def _draft_with_line(client: TestClient) -> dict[str, object]:
    created = client.post("/api/orders", json=create_order_payload(1))
    assert created.status_code == 201
    order_id = created.json()["id"]
    added = client.post(
        f"/api/orders/{order_id}/lines",
        json=add_line_payload(1, 2, 1),
    )
    assert added.status_code == 201
    return added.json()


def test_changing_the_customer_to_the_same_one_is_a_noop(
    clients: dict[str, TestClient],
) -> None:
    original = clients["sales"].get("/api/orders/1").json()

    response = clients["sales"].patch("/api/orders/1", json=change_customer_payload(1, 1))

    assert response.status_code == 200
    assert response.headers["etag"] == '"1"'
    assert response.json() == original


def test_changing_the_customer_bumps_the_version(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch("/api/orders/1", json=change_customer_payload(2, 1))

    assert response.status_code == 200
    assert response.headers["etag"] == '"2"'
    body = response.json()
    assert body["customer"] == {
        "id": 2,
        "name": "Beta Comercial Ltda.",
        "status": "active",
    }
    assert body["version"] == 2


def test_changing_the_customer_checks_in_order(
    clients: dict[str, TestClient], app: FastAPI
) -> None:
    assert_problem(
        clients["sales"].patch("/api/orders/999", json=change_customer_payload(1, 1)),
        404,
        "NOT_FOUND",
    )
    assert_field_error(
        clients["sales"].patch("/api/orders/1", json=change_customer_payload(99, 1)),
        field="customer_id",
        code="REFERENCE_NOT_FOUND",
        message="El registro indicado no existe.",
    )
    assert_problem(
        clients["sales"].patch("/api/orders/1", json=change_customer_payload(5, 1)),
        422,
        "CUSTOMER_INACTIVE",
    )
    assert_problem(
        clients["sales"].patch("/api/orders/2", json=change_customer_payload(1, 1)),
        409,
        "ORDER_NOT_EDITABLE",
    )
    assert_problem(
        clients["sales"].patch("/api/orders/1", json=change_customer_payload(2, 99)),
        409,
        "VERSION_CONFLICT",
    )

    _deactivate(app, 1)
    assert_problem(
        clients["sales"].patch("/api/orders/1", json=change_customer_payload(1, 1)),
        422,
        "CUSTOMER_INACTIVE",
    )
    assert (
        clients["sales"].patch("/api/orders/1", json=change_customer_payload(2, 1)).status_code
        == 200
    )


@pytest.mark.parametrize("version", [0, 2_147_483_648])
def test_change_customer_version_out_of_range(clients: dict[str, TestClient], version: int) -> None:
    response = clients["sales"].patch("/api/orders/1", json=change_customer_payload(1, version))

    assert_field_error(
        response,
        field="version",
        code="OUT_OF_RANGE",
        message="El valor debe estar entre 1 y 2147483647.",
    )


def test_change_customer_body_validation(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].patch("/api/orders/1", json={"customer_id": 1})
    assert_field_error(
        response,
        field="version",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )

    response = clients["sales"].patch("/api/orders/1", json={"version": 1})
    assert_field_error(
        response,
        field="customer_id",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )

    response = clients["sales"].patch("/api/orders/1", json={"customer_id": "1", "version": 1})
    assert_field_error(
        response,
        field="customer_id",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )

    response = clients["sales"].patch("/api/orders/1", json={"customer_id": 1, "version": "1"})
    assert_field_error(
        response,
        field="version",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )

    response = clients["sales"].patch(
        "/api/orders/1", json={"customer_id": 1, "version": 1, "unknown": 1}
    )
    assert_field_error(
        response,
        field="unknown",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_adding_a_line_copies_the_product(clients: dict[str, TestClient]) -> None:
    created = clients["sales"].post("/api/orders", json=create_order_payload(1))
    order_id = created.json()["id"]

    response = clients["sales"].post(
        f"/api/orders/{order_id}/lines",
        json=add_line_payload(1, 2, 1),
    )

    assert response.status_code == 201
    assert response.headers["etag"] == '"2"'
    assert "location" not in response.headers
    body = response.json()
    assert body["lines"] == [
        {
            "id": 10,
            "product_id": 1,
            "sku": "KB-100",
            "name": "Teclado USB",
            "quantity": 2,
            "unit_price": "19.90",
            "line_total": "39.80",
        }
    ]
    assert body["subtotal"] == "39.80"
    assert body["tax"] == "3.98"
    assert body["total"] == "43.78"
    assert body["version"] == 2


def test_adding_a_duplicate_or_the_eleventh_line(
    clients: dict[str, TestClient],
) -> None:
    assert_problem(
        clients["sales"].post("/api/orders/1/lines", json=add_line_payload(1, 1, 1)),
        422,
        "ORDER_DUPLICATE_PRODUCT",
    )

    created = clients["sales"].post("/api/orders", json=create_order_payload(1))
    order_id = created.json()["id"]
    version = 1
    for product_id in range(1, 11):
        response = clients["sales"].post(
            f"/api/orders/{order_id}/lines",
            json=add_line_payload(product_id, 1, version),
        )
        assert response.status_code == 201
        version = response.json()["version"]

    assert_problem(
        clients["sales"].post(
            f"/api/orders/{order_id}/lines",
            json=add_line_payload(11, 1, version),
        ),
        422,
        "ORDER_TOO_MANY_LINES",
    )


@pytest.mark.parametrize(
    ("payload", "field", "code", "message"),
    [
        (
            add_line_payload(1, 0, 1),
            "quantity",
            "OUT_OF_RANGE",
            "El valor debe estar entre 1 y 999.",
        ),
        (
            add_line_payload(1, 1000, 1),
            "quantity",
            "OUT_OF_RANGE",
            "El valor debe estar entre 1 y 999.",
        ),
        (
            add_line_payload(1, "2", 1),
            "quantity",
            "INVALID_FORMAT",
            "El formato no es válido.",
        ),
        (
            add_line_payload(1, 2.0, 1),
            "quantity",
            "INVALID_FORMAT",
            "El formato no es válido.",
        ),
    ],
)
def test_add_line_quantity_validation(
    clients: dict[str, TestClient],
    draft_id: int,
    payload: dict[str, object],
    field: str,
    code: str,
    message: str,
) -> None:
    response = clients["sales"].post(f"/api/orders/{draft_id}/lines", json=payload)

    assert_field_error(response, field=field, code=code, message=message)


def test_add_line_missing_quantity(clients: dict[str, TestClient], draft_id: int) -> None:
    response = clients["sales"].post(
        f"/api/orders/{draft_id}/lines", json={"product_id": 1, "version": 1}
    )

    assert_field_error(
        response,
        field="quantity",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )


@pytest.mark.parametrize("quantity", [1, 999])
def test_add_line_accepts_the_quantity_boundaries(
    clients: dict[str, TestClient], draft_id: int, quantity: int
) -> None:
    response = clients["sales"].post(
        f"/api/orders/{draft_id}/lines",
        json=add_line_payload(1, quantity, 1),
    )

    assert response.status_code == 201
    assert response.json()["lines"][0]["quantity"] == quantity


@pytest.mark.parametrize("product_id", [99, 0, 2_147_483_648])
def test_add_line_unknown_product(
    clients: dict[str, TestClient], draft_id: int, product_id: int
) -> None:
    response = clients["sales"].post(
        f"/api/orders/{draft_id}/lines", json=add_line_payload(product_id, 1, 1)
    )

    assert_field_error(
        response,
        field="product_id",
        code="REFERENCE_NOT_FOUND",
        message="El registro indicado no existe.",
    )


def test_add_line_product_and_version_validation(
    clients: dict[str, TestClient], draft_id: int
) -> None:
    response = clients["sales"].post(
        f"/api/orders/{draft_id}/lines", json={"quantity": 1, "version": 1}
    )
    assert_field_error(
        response,
        field="product_id",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )

    response = clients["sales"].post(
        f"/api/orders/{draft_id}/lines", json=add_line_payload("1", 1, 1)
    )
    assert_field_error(
        response,
        field="product_id",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )

    response = clients["sales"].post(
        f"/api/orders/{draft_id}/lines", json={"product_id": 1, "quantity": 1}
    )
    assert_field_error(
        response,
        field="version",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )

    for version in (0, 2_147_483_648):
        response = clients["sales"].post(
            f"/api/orders/{draft_id}/lines", json=add_line_payload(1, 1, version)
        )
        assert_field_error(
            response,
            field="version",
            code="OUT_OF_RANGE",
            message="El valor debe estar entre 1 y 2147483647.",
        )


def test_add_line_checks_the_order_state_and_customer(
    clients: dict[str, TestClient], app: FastAPI
) -> None:
    assert_problem(
        clients["sales"].post("/api/orders/999/lines", json=add_line_payload(1, 1, 1)),
        404,
        "NOT_FOUND",
    )
    assert_problem(
        clients["sales"].post("/api/orders/2/lines", json=add_line_payload(1, 1, 1)),
        409,
        "ORDER_NOT_EDITABLE",
    )

    _deactivate(app, 1)
    assert_problem(
        clients["sales"].post("/api/orders/1/lines", json=add_line_payload(2, 1, 1)),
        422,
        "CUSTOMER_INACTIVE",
    )


def test_setting_the_same_quantity_is_a_noop(clients: dict[str, TestClient]) -> None:
    order = _draft_with_line(clients["sales"])

    response = clients["sales"].patch(
        f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}",
        json=quantity_payload(2, order["version"]),
    )

    assert response.status_code == 200
    assert response.headers["etag"] == '"2"'
    assert response.json() == order


def test_setting_a_new_quantity_keeps_the_unit_price(
    clients: dict[str, TestClient],
) -> None:
    order = _draft_with_line(clients["sales"])
    line = order["lines"][0]

    response = clients["sales"].patch(
        f"/api/orders/{order['id']}/lines/{line['id']}",
        json=quantity_payload(3, order["version"]),
    )

    assert response.status_code == 200
    assert response.headers["etag"] == '"3"'
    body = response.json()
    assert body["lines"][0]["quantity"] == 3
    assert body["lines"][0]["unit_price"] == "19.90"
    assert body["lines"][0]["line_total"] == "59.70"
    assert body["version"] == 3


def test_set_quantity_checks_in_order(clients: dict[str, TestClient], app: FastAPI) -> None:
    order = _draft_with_line(clients["sales"])
    line_id = order["lines"][0]["id"]

    assert_problem(
        clients["sales"].patch("/api/orders/999/lines/1", json=quantity_payload(2, 1)),
        404,
        "NOT_FOUND",
    )
    assert_problem(
        clients["sales"].patch(f"/api/orders/{order['id']}/lines/99", json=quantity_payload(2, 2)),
        404,
        "NOT_FOUND",
    )
    assert_problem(
        clients["sales"].patch(
            f"/api/orders/{order['id']}/lines/{line_id}",
            json=quantity_payload(2, 99),
        ),
        409,
        "VERSION_CONFLICT",
    )
    assert_problem(
        clients["sales"].patch("/api/orders/2/lines/2", json=quantity_payload(2, 1)),
        409,
        "ORDER_NOT_EDITABLE",
    )

    _deactivate(app, 1)
    assert_problem(
        clients["sales"].patch(
            f"/api/orders/{order['id']}/lines/{line_id}",
            json=quantity_payload(2, order["version"]),
        ),
        422,
        "CUSTOMER_INACTIVE",
    )


@pytest.mark.parametrize(
    ("payload", "field", "code", "message"),
    [
        (
            quantity_payload(0, 2),
            "quantity",
            "OUT_OF_RANGE",
            "El valor debe estar entre 1 y 999.",
        ),
        (
            quantity_payload(1000, 2),
            "quantity",
            "OUT_OF_RANGE",
            "El valor debe estar entre 1 y 999.",
        ),
        (
            quantity_payload("2", 2),
            "quantity",
            "INVALID_FORMAT",
            "El formato no es válido.",
        ),
        (
            quantity_payload(2.0, 2),
            "quantity",
            "INVALID_FORMAT",
            "El formato no es válido.",
        ),
    ],
)
def test_set_quantity_validation(
    clients: dict[str, TestClient],
    payload: dict[str, object],
    field: str,
    code: str,
    message: str,
) -> None:
    order = _draft_with_line(clients["sales"])

    response = clients["sales"].patch(
        f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}",
        json=payload,
    )

    assert_field_error(response, field=field, code=code, message=message)


def test_set_quantity_version_and_unknown_fields(
    clients: dict[str, TestClient],
) -> None:
    order = _draft_with_line(clients["sales"])
    url = f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}"

    response = clients["sales"].patch(url, json={"quantity": 2})
    assert_field_error(
        response,
        field="version",
        code="REQUIRED",
        message="Este campo es obligatorio.",
    )

    response = clients["sales"].patch(url, json={"quantity": 2, "version": "2"})
    assert_field_error(
        response,
        field="version",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )

    response = clients["sales"].patch(url, json={"quantity": 2, "version": 2, "unknown": 1})
    assert_field_error(
        response,
        field="unknown",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_removing_a_line_bumps_the_version(clients: dict[str, TestClient]) -> None:
    order = _draft_with_line(clients["sales"])

    response = clients["sales"].delete(f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}")

    assert response.status_code == 200
    assert response.headers["etag"] == '"3"'
    body = response.json()
    assert body["lines"] == []
    assert body["version"] == 3


def test_removing_a_line_checks_in_order(clients: dict[str, TestClient], app: FastAPI) -> None:
    order = _draft_with_line(clients["sales"])
    line_id = order["lines"][0]["id"]

    assert_problem(clients["sales"].delete("/api/orders/999/lines/1"), 404, "NOT_FOUND")
    assert_problem(
        clients["sales"].delete(f"/api/orders/{order['id']}/lines/99"),
        404,
        "NOT_FOUND",
    )
    assert_problem(
        clients["sales"].delete(
            f"/api/orders/{order['id']}/lines/{line_id}",
            headers={"If-Match": '"1"'},
        ),
        409,
        "VERSION_CONFLICT",
    )
    assert_problem(clients["sales"].delete("/api/orders/2/lines/2"), 409, "ORDER_NOT_EDITABLE")

    _deactivate(app, 1)
    assert_problem(
        clients["sales"].delete(f"/api/orders/{order['id']}/lines/{line_id}"),
        422,
        "CUSTOMER_INACTIVE",
    )


def test_removing_a_line_parses_if_match(clients: dict[str, TestClient]) -> None:
    order = _draft_with_line(clients["sales"])
    url = f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}"

    response = clients["sales"].delete(url, headers={"If-Match": "not-a-version"})

    assert_field_error(
        response,
        field="If-Match",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


@pytest.mark.parametrize("value", ['1"2', "2147483648"])
def test_if_match_rejects_a_quote_in_the_middle_and_a_version_above_the_limit(
    clients: dict[str, TestClient],
    value: str,
) -> None:
    order = _draft_with_line(clients["sales"])
    url = f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}"

    response = clients["sales"].delete(url, headers={"If-Match": value})

    assert_field_error(
        response,
        field="If-Match",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_admin_and_sales_can_edit(clients: dict[str, TestClient], role: str) -> None:
    assert (
        clients[role].patch("/api/orders/1", json=change_customer_payload(1, 1)).status_code == 200
    )


@pytest.mark.parametrize("role", ["finance", "readonly"])
def test_other_roles_cannot_edit(clients: dict[str, TestClient], role: str) -> None:
    order = clients["sales"].get("/api/orders/1").json()

    assert_problem(
        clients[role].patch("/api/orders/1", json=change_customer_payload(1, 1)),
        403,
        "FORBIDDEN",
    )
    assert_problem(
        clients[role].post("/api/orders", json=create_order_payload(1)),
        403,
        "FORBIDDEN",
    )
    assert_problem(
        clients[role].post(f"/api/orders/{order['id']}/lines", json=add_line_payload(2, 1, 1)),
        403,
        "FORBIDDEN",
    )
    assert_problem(
        clients[role].patch(
            f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}",
            json=quantity_payload(2, 1),
        ),
        403,
        "FORBIDDEN",
    )
    assert_problem(
        clients[role].delete(f"/api/orders/{order['id']}/lines/{order['lines'][0]['id']}"),
        403,
        "FORBIDDEN",
    )
