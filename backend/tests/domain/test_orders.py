"""Tests for order transitions, line validation and stock checks."""

from __future__ import annotations

import pytest

from app.domain.orders import OrderAction, OrderStatus, next_status
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
