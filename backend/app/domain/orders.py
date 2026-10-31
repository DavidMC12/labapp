"""Order states, transitions, line validation and stock checks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from app.domain.labels import ORDER_STATUS_LABELS
from app.errors import ApiError

VALIDATION_MESSAGE = "Revisa los datos ingresados."
MIN_LINE_QUANTITY = 1
MAX_LINE_QUANTITY = 999
MAX_ORDER_LINES = 10

_INVALID_FORMAT_MESSAGE = "El formato no es válido."
_OUT_OF_RANGE_MESSAGE = "El valor debe estar entre 1 y 999."


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


@dataclass(frozen=True)
class DraftLineInput:
    """A raw order line before quantity validation."""

    product_id: int
    quantity: object


@dataclass(frozen=True)
class ProductStock:
    """Stock data needed to detect shortages."""

    sku: str
    name: str
    available: int


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


def _quantity_error(index: int, code: str, message: str) -> dict[str, str]:
    return {"field": f"lines[{index}].quantity", "code": code, "message": message}


def validate_draft_lines(lines: Sequence[DraftLineInput]) -> None:
    """Validate raw draft lines: quantities, duplicates and the line cap."""
    errors: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        quantity = line.quantity
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            errors.append(_quantity_error(index, "INVALID_FORMAT", _INVALID_FORMAT_MESSAGE))
        elif quantity < MIN_LINE_QUANTITY or quantity > MAX_LINE_QUANTITY:
            errors.append(_quantity_error(index, "OUT_OF_RANGE", _OUT_OF_RANGE_MESSAGE))

    if errors:
        raise ApiError(422, "VALIDATION_ERROR", VALIDATION_MESSAGE, errors=errors)

    product_ids = [line.product_id for line in lines]
    if len(set(product_ids)) != len(product_ids):
        raise ApiError(
            422,
            "ORDER_DUPLICATE_PRODUCT",
            "Ese producto ya está en el pedido; edita su cantidad.",
        )

    if len(lines) > MAX_ORDER_LINES:
        raise ApiError(
            422,
            "ORDER_TOO_MANY_LINES",
            f"Un pedido admite como máximo {MAX_ORDER_LINES} líneas.",
        )


def ensure_confirmable(lines: Sequence[object]) -> None:
    """Raise ORDER_EMPTY when a draft has no lines."""
    if not lines:
        raise ApiError(422, "ORDER_EMPTY", "El pedido debe tener al menos una línea.")


def check_stock(
    lines: Iterable[DraftLineInput],
    stock_by_product: Mapping[int, ProductStock],
) -> None:
    """Raise INSUFFICIENT_STOCK listing every short line, ordered by product id."""
    shortages: list[dict[str, object]] = []
    for line in lines:
        stock = stock_by_product[line.product_id]
        requested = cast(int, line.quantity)
        if requested > stock.available:
            shortages.append(
                {
                    "product_id": line.product_id,
                    "sku": stock.sku,
                    "name": stock.name,
                    "available": stock.available,
                    "requested": requested,
                }
            )

    if not shortages:
        return

    shortages.sort(key=lambda shortage: cast(int, shortage["product_id"]))
    first = shortages[0]
    detail = (
        f"No hay stock suficiente de {first['name']}: "
        f"disponible {first['available']}, solicitado {first['requested']}."
    )
    raise ApiError(409, "INSUFFICIENT_STOCK", detail, shortages=shortages)
