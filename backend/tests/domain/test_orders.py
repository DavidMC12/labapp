"""Tests for order transitions, line validation and stock checks."""

from __future__ import annotations

import pytest

from app.domain.orders import (
    DraftLineInput,
    OrderAction,
    OrderStatus,
    ProductStock,
    check_stock,
    ensure_confirmable,
    next_status,
    validate_draft_lines,
)
from app.errors import ApiError

SPANISH_STATE = {
    OrderStatus.DRAFT: "borrador",
    OrderStatus.CONFIRMED: "confirmado",
    OrderStatus.PAID: "pagado",
    OrderStatus.SHIPPED: "enviado",
    OrderStatus.CANCELLED: "cancelado",
}

SPANISH_TARGET = {
    OrderAction.CONFIRM: "confirmado",
    OrderAction.PAY: "pagado",
    OrderAction.SHIP: "enviado",
    OrderAction.CANCEL: "cancelado",
}

TRANSITION_MATRIX = [
    (OrderStatus.DRAFT, OrderAction.CONFIRM, OrderStatus.CONFIRMED),
    (OrderStatus.DRAFT, OrderAction.PAY, None),
    (OrderStatus.DRAFT, OrderAction.SHIP, None),
    (OrderStatus.DRAFT, OrderAction.CANCEL, OrderStatus.CANCELLED),
    (OrderStatus.CONFIRMED, OrderAction.CONFIRM, None),
    (OrderStatus.CONFIRMED, OrderAction.PAY, OrderStatus.PAID),
    (OrderStatus.CONFIRMED, OrderAction.SHIP, None),
    (OrderStatus.CONFIRMED, OrderAction.CANCEL, OrderStatus.CANCELLED),
    (OrderStatus.PAID, OrderAction.CONFIRM, None),
    (OrderStatus.PAID, OrderAction.PAY, None),
    (OrderStatus.PAID, OrderAction.SHIP, OrderStatus.SHIPPED),
    (OrderStatus.PAID, OrderAction.CANCEL, None),
    (OrderStatus.SHIPPED, OrderAction.CONFIRM, None),
    (OrderStatus.SHIPPED, OrderAction.PAY, None),
    (OrderStatus.SHIPPED, OrderAction.SHIP, None),
    (OrderStatus.SHIPPED, OrderAction.CANCEL, None),
    (OrderStatus.CANCELLED, OrderAction.CONFIRM, None),
    (OrderStatus.CANCELLED, OrderAction.PAY, None),
    (OrderStatus.CANCELLED, OrderAction.SHIP, None),
    (OrderStatus.CANCELLED, OrderAction.CANCEL, None),
]


@pytest.mark.parametrize(("current", "action", "expected"), TRANSITION_MATRIX)
def test_transition_matrix(
    current: OrderStatus, action: OrderAction, expected: OrderStatus | None
) -> None:
    if expected is not None:
        assert next_status(current, action) is expected
        return

    expected_detail = (
        f"No se puede pasar el pedido de {SPANISH_STATE[current]} a {SPANISH_TARGET[action]}."
    )
    with pytest.raises(ApiError) as error:
        next_status(current, action)

    assert error.value.status == 409
    assert error.value.code == "INVALID_TRANSITION"
    assert error.value.detail == expected_detail


def test_the_matrix_covers_every_status_and_action() -> None:
    assert len(TRANSITION_MATRIX) == len(OrderStatus) * len(OrderAction)


def test_invalid_transition_message_uses_spanish_state_labels() -> None:
    with pytest.raises(ApiError) as error:
        next_status(OrderStatus.SHIPPED, OrderAction.CANCEL)

    assert error.value.detail == "No se puede pasar el pedido de enviado a cancelado."


def _line(product_id: int = 1, quantity: object = 1) -> DraftLineInput:
    return DraftLineInput(product_id=product_id, quantity=quantity)


def _distinct_lines(count: int) -> list[DraftLineInput]:
    return [_line(product_id=product_id) for product_id in range(1, count + 1)]


def test_empty_draft_has_valid_lines() -> None:
    validate_draft_lines([])


@pytest.mark.parametrize("quantity", [1, 2, 999])
def test_accepts_integer_quantities_in_range(quantity: int) -> None:
    validate_draft_lines([_line(quantity=quantity)])


@pytest.mark.parametrize(
    ("quantity", "code", "message"),
    [
        (0, "OUT_OF_RANGE", "El valor debe estar entre 1 y 999."),
        (1000, "OUT_OF_RANGE", "El valor debe estar entre 1 y 999."),
        (-1, "OUT_OF_RANGE", "El valor debe estar entre 1 y 999."),
        (1.0, "INVALID_FORMAT", "El formato no es válido."),
        (1.5, "INVALID_FORMAT", "El formato no es válido."),
        ("2", "INVALID_FORMAT", "El formato no es válido."),
        (True, "INVALID_FORMAT", "El formato no es válido."),
        (False, "INVALID_FORMAT", "El formato no es válido."),
        (None, "INVALID_FORMAT", "El formato no es válido."),
    ],
)
def test_rejects_bad_quantities(quantity: object, code: str, message: str) -> None:
    with pytest.raises(ApiError) as error:
        validate_draft_lines([_line(quantity=quantity)])

    assert error.value.status == 422
    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.detail == "Revisa los datos ingresados."
    assert error.value.errors == [{"field": "lines[0].quantity", "code": code, "message": message}]


def test_reports_every_bad_line_together() -> None:
    lines = [_line(1, 0), _line(2, "two"), _line(3, True), _line(4, 1000)]

    with pytest.raises(ApiError) as error:
        validate_draft_lines(lines)

    assert error.value.errors == [
        {
            "field": "lines[0].quantity",
            "code": "OUT_OF_RANGE",
            "message": "El valor debe estar entre 1 y 999.",
        },
        {
            "field": "lines[1].quantity",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        },
        {
            "field": "lines[2].quantity",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        },
        {
            "field": "lines[3].quantity",
            "code": "OUT_OF_RANGE",
            "message": "El valor debe estar entre 1 y 999.",
        },
    ]


def test_duplicate_product_is_rejected() -> None:
    with pytest.raises(ApiError) as error:
        validate_draft_lines([_line(1, 1), _line(2, 1), _line(1, 2)])

    assert error.value.status == 422
    assert error.value.code == "ORDER_DUPLICATE_PRODUCT"
    assert error.value.detail == "Ese producto ya está en el pedido; edita su cantidad."


def test_ten_lines_are_allowed() -> None:
    validate_draft_lines(_distinct_lines(10))


def test_eleven_lines_are_rejected() -> None:
    with pytest.raises(ApiError) as error:
        validate_draft_lines(_distinct_lines(11))

    assert error.value.status == 422
    assert error.value.code == "ORDER_TOO_MANY_LINES"
    assert error.value.detail == "Un pedido admite como máximo 10 líneas."


def test_field_errors_win_over_the_duplicate_check() -> None:
    with pytest.raises(ApiError) as error:
        validate_draft_lines([_line(1, 1), _line(1, 0)])

    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.errors == [
        {
            "field": "lines[1].quantity",
            "code": "OUT_OF_RANGE",
            "message": "El valor debe estar entre 1 y 999.",
        }
    ]


def test_duplicate_products_win_over_the_line_cap() -> None:
    duplicate = [_line(1, 1), _line(1, 2)]
    other_lines = [_line(product_id, 1) for product_id in range(2, 11)]

    with pytest.raises(ApiError) as error:
        validate_draft_lines(duplicate + other_lines)

    assert len(duplicate + other_lines) == 11
    assert error.value.code == "ORDER_DUPLICATE_PRODUCT"


def test_ensure_confirmable_rejects_an_empty_order() -> None:
    with pytest.raises(ApiError) as error:
        ensure_confirmable([])

    assert error.value.status == 422
    assert error.value.code == "ORDER_EMPTY"
    assert error.value.detail == "El pedido debe tener al menos una línea."


def test_ensure_confirmable_accepts_at_least_one_line() -> None:
    assert ensure_confirmable([_line()]) is None


STOCK = {
    1: ProductStock(sku="KB-100", name="Teclado USB", available=5),
    2: ProductStock(sku="MS-200", name="Mouse óptico", available=0),
    3: ProductStock(sku="MN-240", name='Monitor 24"', available=10),
}


def test_stock_check_accepts_enough_stock_including_the_boundary() -> None:
    assert check_stock([_line(1, 5), _line(3, 10)], STOCK) is None


def test_stock_check_accepts_no_lines() -> None:
    assert check_stock([], STOCK) is None


def test_single_shortage_reports_the_line_details() -> None:
    with pytest.raises(ApiError) as error:
        check_stock([_line(2, 1)], STOCK)

    assert error.value.status == 409
    assert error.value.code == "INSUFFICIENT_STOCK"
    assert error.value.detail == (
        "No hay stock suficiente de Mouse óptico: disponible 0, solicitado 1."
    )
    assert error.value.extra["shortages"] == [
        {
            "product_id": 2,
            "sku": "MS-200",
            "name": "Mouse óptico",
            "available": 0,
            "requested": 1,
        }
    ]


def test_multiple_shortages_are_ordered_by_product_id() -> None:
    lines = [_line(3, 20), _line(1, 6), _line(2, 1)]

    with pytest.raises(ApiError) as error:
        check_stock(lines, STOCK)

    assert error.value.detail == (
        "No hay stock suficiente de Teclado USB: disponible 5, solicitado 6."
    )
    assert error.value.extra["shortages"] == [
        {
            "product_id": 1,
            "sku": "KB-100",
            "name": "Teclado USB",
            "available": 5,
            "requested": 6,
        },
        {
            "product_id": 2,
            "sku": "MS-200",
            "name": "Mouse óptico",
            "available": 0,
            "requested": 1,
        },
        {
            "product_id": 3,
            "sku": "MN-240",
            "name": 'Monitor 24"',
            "available": 10,
            "requested": 20,
        },
    ]


def test_lines_with_enough_stock_are_not_listed() -> None:
    with pytest.raises(ApiError) as error:
        check_stock([_line(1, 5), _line(2, 1)], STOCK)

    assert error.value.extra["shortages"] == [
        {
            "product_id": 2,
            "sku": "MS-200",
            "name": "Mouse óptico",
            "available": 0,
            "requested": 1,
        }
    ]
