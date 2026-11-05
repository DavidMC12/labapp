"""Tests for the order service validation and view building."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import FastAPI

from app.errors import ApiError
from app.modules.orders.service import OrderService


def _service(app: FastAPI) -> OrderService:
    return app.state.orders


@pytest.mark.parametrize(
    ("value", "expected"),
    [("7", Decimal("7.00")), ("0", Decimal("0.00")), ("100", Decimal("100.00"))],
)
def test_set_tax_rate_stores_two_decimals(app: FastAPI, value: str, expected: Decimal) -> None:
    service = _service(app)

    assert service.set_tax_rate(value) == expected
    assert service.get_tax_rate() == expected


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (None, "REQUIRED"),
        ("1e1", "INVALID_FORMAT"),
        (" 7", "INVALID_FORMAT"),
        ("10.123", "INVALID_FORMAT"),
        ("100.01", "OUT_OF_RANGE"),
    ],
)
def test_set_tax_rate_validation(app: FastAPI, value: str | None, code: str) -> None:
    with pytest.raises(ApiError) as error:
        _service(app).set_tax_rate(value)

    assert error.value.status == 422
    assert error.value.errors == [
        {
            "field": "tax_rate",
            "code": code,
            "message": {
                "REQUIRED": "Este campo es obligatorio.",
                "INVALID_FORMAT": "El formato no es válido.",
                "OUT_OF_RANGE": "El valor debe estar entre 0 y 100.",
            }[code],
        }
    ]


def test_list_orders_trims_the_query(app: FastAPI) -> None:
    items, total = _service(app).list_orders(1, "  cafeteria  ", None, None)

    assert total == 1
    assert items[0].order.id == 7


@pytest.mark.parametrize("customer_id", [0, 2_147_483_648, 10**30])
def test_list_orders_customer_id_out_of_range(app: FastAPI, customer_id: int) -> None:
    with pytest.raises(ApiError) as error:
        _service(app).list_orders(1, None, None, customer_id)

    assert error.value.errors == [
        {
            "field": "customer_id",
            "code": "OUT_OF_RANGE",
            "message": "El valor debe estar entre 1 y 2147483647.",
        }
    ]


@pytest.mark.parametrize("customer_id", [None, "1", 1.0, True, 0, 2_147_483_648])
def test_create_rejects_bad_customer_ids(app: FastAPI, customer_id: object) -> None:
    with pytest.raises(ApiError) as error:
        _service(app).create(customer_id)  # type: ignore[arg-type]

    assert error.value.errors is not None
    assert error.value.errors[0]["field"] == "customer_id"
    assert error.value.errors[0]["code"] in {"REQUIRED", "INVALID_FORMAT", "REFERENCE_NOT_FOUND"}


@pytest.mark.parametrize(
    ("quantity", "code"),
    [
        (0, "OUT_OF_RANGE"),
        (1000, "OUT_OF_RANGE"),
        ("2", "INVALID_FORMAT"),
        (2.0, "INVALID_FORMAT"),
        (True, "INVALID_FORMAT"),
        (None, "REQUIRED"),
    ],
)
def test_add_line_uses_the_quantity_field(app: FastAPI, quantity: object, code: str) -> None:
    with pytest.raises(ApiError) as error:
        _service(app).add_line(1, 2, quantity, 1)  # type: ignore[arg-type]

    assert error.value.errors is not None
    assert error.value.errors[0]["field"] == "quantity"
    assert error.value.errors[0]["code"] == code


def test_get_unknown_order_is_not_found(app: FastAPI) -> None:
    with pytest.raises(ApiError) as error:
        _service(app).get(99)

    assert error.value.status == 404
    assert error.value.code == "NOT_FOUND"


def test_a_draft_view_uses_the_current_rate(app: FastAPI) -> None:
    view = _service(app).get(1)

    assert view.tax_rate == Decimal("10.00")
    assert view.subtotal == Decimal("39.80")
    assert view.total == Decimal("43.78")

    _service(app).set_tax_rate("7")
    view = _service(app).get(1)

    assert view.tax_rate == Decimal("7.00")
    assert view.tax == Decimal("2.79")
    assert view.total == Decimal("42.59")


def test_a_confirmed_view_keeps_the_frozen_rate(app: FastAPI) -> None:
    service = _service(app)
    service.set_tax_rate("7")

    view = service.get(2)

    assert view.tax_rate == Decimal("10.00")
    assert view.total == Decimal("121.00")
