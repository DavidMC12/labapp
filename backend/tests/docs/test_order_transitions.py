"""The order transition table of SPEC section 5 and app/domain/orders.py."""

from __future__ import annotations

import pytest

from app.domain.labels import ORDER_STATUS_LABELS
from app.domain.orders import OrderAction, OrderStatus, next_status
from app.errors import ApiError

from . import support

ACTION_BY_DOCUMENT_NAME = {
    "Confirm": OrderAction.CONFIRM,
    "Pay": OrderAction.PAY,
    "Ship": OrderAction.SHIP,
    "Cancel": OrderAction.CANCEL,
}

TARGET_BY_ACTION = {
    OrderAction.CONFIRM: OrderStatus.CONFIRMED,
    OrderAction.PAY: OrderStatus.PAID,
    OrderAction.SHIP: OrderStatus.SHIPPED,
    OrderAction.CANCEL: OrderStatus.CANCELLED,
}

DOCUMENT_ONLY_TRANSITIONS = {"Create"}


def _allowed_transitions() -> dict[tuple[OrderStatus, OrderAction], OrderStatus]:
    allowed: dict[tuple[OrderStatus, OrderAction], OrderStatus] = {}
    for row in support.spec_transition_rows():
        name = row["Transition"]
        if name in DOCUMENT_ONLY_TRANSITIONS:
            assert row["Allowed from"] == "none"
            continue
        action = ACTION_BY_DOCUMENT_NAME[name]
        target = TARGET_BY_ACTION[action]
        cell = row["Allowed from"]
        states = [] if cell == "none" else [OrderStatus(value.strip()) for value in cell.split(",")]
        for state in states:
            allowed[(state, action)] = target
    return allowed


def test_every_state_and_action_matches_the_transition_table() -> None:
    rows = support.spec_transition_rows()
    names = {row["Transition"] for row in rows}
    assert names == set(ACTION_BY_DOCUMENT_NAME) | DOCUMENT_ONLY_TRANSITIONS
    allowed = _allowed_transitions()

    for state in OrderStatus:
        for action in OrderAction:
            target = allowed.get((state, action))
            if target is not None:
                assert next_status(state, action) == target
                continue

            with pytest.raises(ApiError) as info:
                next_status(state, action)
            error = info.value
            assert error.status == 409
            assert error.code == "INVALID_TRANSITION"
            assert error.detail == (
                f"No se puede pasar el pedido de {ORDER_STATUS_LABELS[state.value]} "
                f"a {ORDER_STATUS_LABELS[TARGET_BY_ACTION[action].value]}."
            )
