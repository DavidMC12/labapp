"""Order states, transitions, line validation and stock checks."""

from __future__ import annotations

from enum import StrEnum

from app.domain.labels import ORDER_STATUS_LABELS
from app.errors import ApiError


class OrderStatus(StrEnum):
    """The five order states."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class OrderAction(StrEnum):
    """The four order transitions."""

    CONFIRM = "confirm"
    PAY = "pay"
    SHIP = "ship"
    CANCEL = "cancel"


_TRANSITIONS: dict[tuple[OrderStatus, OrderAction], OrderStatus] = {
    (OrderStatus.DRAFT, OrderAction.CONFIRM): OrderStatus.CONFIRMED,
    (OrderStatus.CONFIRMED, OrderAction.PAY): OrderStatus.PAID,
    (OrderStatus.PAID, OrderAction.SHIP): OrderStatus.SHIPPED,
    (OrderStatus.DRAFT, OrderAction.CANCEL): OrderStatus.CANCELLED,
    (OrderStatus.CONFIRMED, OrderAction.CANCEL): OrderStatus.CANCELLED,
}

_ACTION_TARGETS: dict[OrderAction, OrderStatus] = {
    OrderAction.CONFIRM: OrderStatus.CONFIRMED,
    OrderAction.PAY: OrderStatus.PAID,
    OrderAction.SHIP: OrderStatus.SHIPPED,
    OrderAction.CANCEL: OrderStatus.CANCELLED,
}


def next_status(current: OrderStatus, action: OrderAction) -> OrderStatus:
    """Return the status produced by the action or raise INVALID_TRANSITION."""
    new_status = _TRANSITIONS.get((current, action))
    if new_status is not None:
        return new_status

    target = _ACTION_TARGETS[action]
    from_label = ORDER_STATUS_LABELS[current.value]
    to_label = ORDER_STATUS_LABELS[target.value]
    raise ApiError(
        409,
        "INVALID_TRANSITION",
        f"No se puede pasar el pedido de {from_label} a {to_label}.",
    )
