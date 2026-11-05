"""FastAPI dependencies for the orders module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.errors import ERROR_MESSAGES, NOT_FOUND, ApiError
from app.modules.orders.ports import OrderStore
from app.modules.orders.service import OrderLineView, OrderService, OrderView


def get_service(request: Request) -> OrderService:
    """Return the order service built by create_app."""
    return request.app.state.orders


def get_store(request: Request) -> OrderStore:
    """Return the order store built by create_app."""
    return request.app.state.order_store


def get_order(
    id: int,
    service: Annotated[OrderService, Depends(get_service)],
) -> OrderView:
    """Load the order or raise the 404 problem before body validation."""
    return service.get(id)


def get_line(
    order: Annotated[OrderView, Depends(get_order)],
    line_id: int,
) -> OrderLineView:
    """Load the line from the order or raise the 404 problem."""
    for line in order.lines:
        if line.line.id == line_id:
            return line
    raise ApiError(404, NOT_FOUND, ERROR_MESSAGES[NOT_FOUND])
