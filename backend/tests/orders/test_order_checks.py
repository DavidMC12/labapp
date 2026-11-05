"""Tests for the order of the checks on order writes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.orders.helpers import (
    add_line_payload,
    assert_field_error,
    assert_problem,
    change_customer_payload,
    create_order_payload,
    quantity_payload,
)


def test_permission_is_checked_before_unknown_id_and_body(
    clients: dict[str, TestClient],
) -> None:
    assert_problem(
        clients["finance"].patch("/api/orders/999", json=change_customer_payload(0, 0)),
        403,
        "FORBIDDEN",
    )
    assert_problem(
        clients["readonly"].post("/api/orders/999/lines", json=add_line_payload(0, 0, 0)),
        403,
        "FORBIDDEN",
    )
    assert_problem(
        clients["readonly"].post("/api/orders", json=create_order_payload(0)),
        403,
        "FORBIDDEN",
    )


def test_unknown_id_is_checked_before_an_invalid_body(
    clients: dict[str, TestClient],
) -> None:
    assert_problem(
        clients["sales"].patch("/api/orders/999", json=change_customer_payload(0, 0)),
        404,
        "NOT_FOUND",
    )
    assert_problem(
        clients["sales"].post("/api/orders/999/lines", json=add_line_payload(0, 0, 0)),
        404,
        "NOT_FOUND",
    )
    assert_problem(
        clients["sales"].patch("/api/orders/999/lines/1", json=quantity_payload(0, 0)),
        404,
        "NOT_FOUND",
    )


def test_existing_id_with_an_invalid_body_is_a_validation_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].patch("/api/orders/1", json=change_customer_payload(0, 1))

    assert_field_error(
        response,
        field="customer_id",
        code="REFERENCE_NOT_FOUND",
        message="El registro indicado no existe.",
    )


def test_stale_version_wins_over_order_not_editable(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].patch("/api/orders/2", json=change_customer_payload(1, 99))

    assert_problem(response, 409, "VERSION_CONFLICT")


def test_unknown_id_is_checked_before_a_malformed_if_match(
    clients: dict[str, TestClient],
) -> None:
    assert_problem(
        clients["sales"].post("/api/orders/999/confirm", headers={"If-Match": "not-a-version"}),
        404,
        "NOT_FOUND",
    )
    assert_problem(
        clients["sales"].delete("/api/orders/999/lines/1", headers={"If-Match": "not-a-version"}),
        404,
        "NOT_FOUND",
    )


def test_ids_at_zero_and_above_the_limit_are_not_found(
    clients: dict[str, TestClient],
) -> None:
    for order_id in (0, 2_147_483_648):
        assert_problem(clients["sales"].get(f"/api/orders/{order_id}"), 404, "NOT_FOUND")
        assert_problem(
            clients["sales"].patch(f"/api/orders/{order_id}", json=change_customer_payload(1, 1)),
            404,
            "NOT_FOUND",
        )

    assert_problem(
        clients["sales"].patch("/api/orders/1/lines/0", json=quantity_payload(2, 1)),
        404,
        "NOT_FOUND",
    )


def test_a_non_integer_line_id_is_a_validation_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].patch("/api/orders/1/lines/abc", json=quantity_payload(2, 1))

    assert_field_error(
        response,
        field="line_id",
        code="INVALID_FORMAT",
        message="El formato no es válido.",
    )


def test_a_line_from_another_order_is_not_found_before_body_validation(
    clients: dict[str, TestClient],
) -> None:
    created = clients["sales"].post("/api/orders", json=create_order_payload(1))
    order_id = created.json()["id"]
    added = clients["sales"].post(f"/api/orders/{order_id}/lines", json=add_line_payload(1, 2, 1))
    line_id = added.json()["lines"][0]["id"]

    response = clients["sales"].patch(f"/api/orders/1/lines/{line_id}", json=quantity_payload(0, 0))

    assert_problem(response, 404, "NOT_FOUND")


def test_permission_precedes_the_body_in_settings(
    clients: dict[str, TestClient],
) -> None:
    assert_problem(
        clients["sales"].patch("/api/settings", json={"tax_rate": "not-a-rate"}),
        403,
        "FORBIDDEN",
    )
