"""Product, settings and order routes."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Response
from fastapi import status as http_status

from app.domain.csv_export import CSV_CONTENT_TYPE, csv_response
from app.domain.orders import OrderAction, OrderStatus
from app.domain.permissions import Action
from app.domain.sorting import SortDirection
from app.errors import ApiError
from app.modules.auth.dependencies import get_current_user, require_action
from app.modules.auth.models import User
from app.modules.orders import schemas
from app.modules.orders.dependencies import get_line, get_order, get_service
from app.modules.orders.models import Product
from app.modules.orders.service import (
    MAX_ID,
    PAGE_SIZE,
    OrderLineView,
    OrderService,
    OrderSummaryView,
    OrderView,
)
from app.openapi import documented_responses

router = APIRouter(prefix="/api", tags=["orders"])

ProductSortField = Literal["id", "sku", "name", "price", "stock"]
OrderSortField = Literal["created_at", "number", "customer"]

_READ_RESPONSES = documented_responses(method="GET")
_LIST_RESPONSES = documented_responses(
    method="GET",
    extra={422: "The query parameters are invalid. Code: `VALIDATION_ERROR` (with `errors[]`)."},
)
_EXPORT_RESPONSES = {
    200: csv_response("The orders of the list filters as a CSV file."),
    **_LIST_RESPONSES,
}
_SETTINGS_PATCH_RESPONSES = documented_responses(
    method="PATCH",
    body=True,
    permission=True,
    extra={422: "The body is invalid. Code: `VALIDATION_ERROR` (with `errors[]`)."},
)
_CREATE_RESPONSES = documented_responses(
    method="POST",
    body=True,
    permission=True,
    extra={
        422: "The body is invalid or the customer is inactive. Codes: "
        "`VALIDATION_ERROR` (with `errors[]`), `CUSTOMER_INACTIVE`."
    },
)
_ORDER_READ_RESPONSES = documented_responses(
    method="GET",
    extra={
        404: "The order does not exist. Code: `NOT_FOUND`.",
        422: "The id is not an integer. Code: `VALIDATION_ERROR` (with `errors[]`).",
    },
)
_EDIT_RESPONSES = documented_responses(
    method="PATCH",
    body=True,
    permission=True,
    extra={
        404: "The order does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale or the order is not a draft. Codes: "
        "`VERSION_CONFLICT`, `ORDER_NOT_EDITABLE`.",
        422: "The id or the body is invalid, or the customer is inactive. Codes: "
        "`VALIDATION_ERROR` (with `errors[]`), `CUSTOMER_INACTIVE`.",
    },
)
_ADD_LINE_RESPONSES = documented_responses(
    method="POST",
    body=True,
    permission=True,
    extra={
        404: "The order does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale or the order is not a draft. Codes: "
        "`VERSION_CONFLICT`, `ORDER_NOT_EDITABLE`.",
        422: "The id or the body is invalid, the customer is inactive, the product "
        "is repeated or the order is full. Codes: `VALIDATION_ERROR` "
        "(with `errors[]`), `CUSTOMER_INACTIVE`, `ORDER_DUPLICATE_PRODUCT`, "
        "`ORDER_TOO_MANY_LINES`.",
    },
)
_UPDATE_LINE_RESPONSES = documented_responses(
    method="PATCH",
    body=True,
    permission=True,
    extra={
        404: "The order or the line does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale or the order is not a draft. Codes: "
        "`VERSION_CONFLICT`, `ORDER_NOT_EDITABLE`.",
        422: "The id, the line id or the body is invalid, or the customer is "
        "inactive. Codes: `VALIDATION_ERROR` (with `errors[]`), "
        "`CUSTOMER_INACTIVE`.",
    },
)
_DELETE_LINE_RESPONSES = documented_responses(
    method="DELETE",
    permission=True,
    extra={
        404: "The order or the line does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale or the order is not a draft. Codes: "
        "`VERSION_CONFLICT`, `ORDER_NOT_EDITABLE`.",
        422: "The id, the line id or the If-Match header is invalid, or the "
        "customer is inactive. Codes: `VALIDATION_ERROR` (with `errors[]`), "
        "`CUSTOMER_INACTIVE`.",
    },
)
_CONFIRM_RESPONSES = documented_responses(
    method="POST",
    permission=True,
    extra={
        404: "The order does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale, the transition is not allowed or the stock is "
        "short. Codes: `VERSION_CONFLICT`, `INVALID_TRANSITION`, "
        "`INSUFFICIENT_STOCK` (with `shortages[]`).",
        422: "The id or the If-Match header is invalid, the customer is inactive or "
        "the order is empty. Codes: `VALIDATION_ERROR` (with `errors[]`), "
        "`CUSTOMER_INACTIVE`, `ORDER_EMPTY`.",
    },
)
_TRANSITION_RESPONSES = documented_responses(
    method="POST",
    permission=True,
    extra={
        404: "The order does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale or the transition is not allowed. Codes: "
        "`VERSION_CONFLICT`, `INVALID_TRANSITION`.",
        422: "The id or the If-Match header is invalid. Code: `VALIDATION_ERROR` "
        "(with `errors[]`).",
    },
)

_DIGITS = re.compile(r"[0-9]+")


def _invalid_if_match() -> ApiError:
    return ApiError(
        422,
        "VALIDATION_ERROR",
        "Revisa los datos ingresados.",
        errors=[
            {
                "field": "If-Match",
                "code": "INVALID_FORMAT",
                "message": "El formato no es válido.",
            }
        ],
    )


def _parse_if_match(value: str | None) -> int | None:
    if value is None:
        return None

    text = value.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    elif '"' in text:
        raise _invalid_if_match()

    if _DIGITS.fullmatch(text) is None or len(text) > 10:
        raise _invalid_if_match()
    version = int(text)
    if not 1 <= version <= MAX_ID:
        raise _invalid_if_match()
    return version


def _set_etag(response: Response, view: OrderView) -> None:
    response.headers["ETag"] = f'"{view.order.version}"'


def _product_out(product: Product) -> schemas.Product:
    return schemas.Product(
        id=product.id,
        sku=product.sku,
        name=product.name,
        price=product.price,
        stock=product.stock,
    )


def _order_out(view: OrderView) -> schemas.Order:
    return schemas.Order(
        id=view.order.id,
        number=view.order.number,
        status=view.order.status,
        customer=schemas.OrderCustomer(
            id=view.customer.id,
            name=view.customer.name,
            status=view.customer.status,
        ),
        lines=[
            schemas.OrderLine(
                id=line.line.id,
                product_id=line.line.product_id,
                sku=line.line.sku,
                name=line.line.name,
                quantity=line.line.quantity,
                unit_price=line.line.unit_price,
                line_total=line.line_total,
            )
            for line in view.lines
        ],
        subtotal=view.subtotal,
        tax_rate=view.tax_rate,
        tax=view.tax,
        total=view.total,
        invoice_id=view.order.invoice_id,
        version=view.order.version,
        created_at=view.order.created_at,
        updated_at=view.order.updated_at,
    )


def _summary_out(view: OrderSummaryView) -> schemas.OrderSummary:
    return schemas.OrderSummary(
        id=view.order.id,
        number=view.order.number,
        status=view.order.status,
        customer_id=view.order.customer_id,
        customer_name=view.customer_name,
        line_count=len(view.order.lines),
        total=view.total,
        version=view.order.version,
        created_at=view.order.created_at,
        updated_at=view.order.updated_at,
    )


@router.get("/products", response_model=schemas.ProductListOut, responses=_LIST_RESPONSES)
def list_products(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_service)],
    sort: ProductSortField | None = None,
    direction: SortDirection | None = None,
) -> schemas.ProductListOut:
    """Return the whole catalog following the requested sort."""
    return schemas.ProductListOut(
        items=[_product_out(product) for product in service.list_products(sort, direction)]
    )


@router.get("/settings", response_model=schemas.TaxRateOut, responses=_READ_RESPONSES)
def read_settings(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_service)],
) -> schemas.TaxRateOut:
    """Return the current tax rate."""
    return schemas.TaxRateOut(tax_rate=service.get_tax_rate())


@router.patch(
    "/settings",
    response_model=schemas.TaxRateOut,
    responses=_SETTINGS_PATCH_RESPONSES,
)
def update_settings(
    payload: schemas.SettingsPatch,
    user: Annotated[User, Depends(require_action(Action.CHANGE_TAX_RATE))],
    service: Annotated[OrderService, Depends(get_service)],
) -> schemas.TaxRateOut:
    """Change the tax rate (Admin only)."""
    return schemas.TaxRateOut(tax_rate=service.set_tax_rate(payload.tax_rate))


@router.get("/orders", response_model=schemas.OrderListOut, responses=_LIST_RESPONSES)
def list_orders(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_service)],
    page: int = 1,
    q: str | None = None,
    status: OrderStatus | None = None,
    customer_id: int | None = None,
    sort: OrderSortField | None = None,
    direction: SortDirection | None = None,
) -> schemas.OrderListOut:
    """List orders with literal, accent-insensitive search."""
    items, total = service.list_orders(page, q, status, customer_id, sort, direction)
    return schemas.OrderListOut(
        items=[_summary_out(item) for item in items],
        page=page,
        page_size=PAGE_SIZE,
        total=total,
    )


@router.get("/orders/export", response_class=Response, responses=_EXPORT_RESPONSES)
def export_orders(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_service)],
    q: str | None = None,
    status: OrderStatus | None = None,
    customer_id: int | None = None,
    sort: OrderSortField | None = None,
    direction: SortDirection | None = None,
) -> Response:
    """Export every order of the list filters as a CSV file."""
    document = service.export_orders(q, status, customer_id, sort, direction)
    return Response(
        content=document.text,
        media_type=CSV_CONTENT_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/orders",
    status_code=http_status.HTTP_201_CREATED,
    response_model=schemas.Order,
    responses=_CREATE_RESPONSES,
)
def create_order(
    payload: schemas.OrderCreate,
    response: Response,
    user: Annotated[User, Depends(require_action(Action.EDIT_DRAFT_ORDERS))],
    service: Annotated[OrderService, Depends(get_service)],
) -> schemas.Order:
    """Create a draft."""
    view = service.create(payload.customer_id)
    response.headers["Location"] = f"/api/orders/{view.order.id}"
    _set_etag(response, view)
    return _order_out(view)


@router.get("/orders/{id}", response_model=schemas.Order, responses=_ORDER_READ_RESPONSES)
def read_order(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    order: Annotated[OrderView, Depends(get_order)],
) -> schemas.Order:
    """Return one order."""
    _set_etag(response, order)
    return _order_out(order)


@router.patch("/orders/{id}", response_model=schemas.Order, responses=_EDIT_RESPONSES)
def update_order_customer(
    payload: schemas.OrderCustomerPatch,
    response: Response,
    user: Annotated[User, Depends(require_action(Action.EDIT_DRAFT_ORDERS))],
    order: Annotated[OrderView, Depends(get_order)],
    service: Annotated[OrderService, Depends(get_service)],
) -> schemas.Order:
    """Change the customer of a draft."""
    view = service.set_customer(order.order.id, payload.customer_id, payload.version)
    _set_etag(response, view)
    return _order_out(view)


@router.post(
    "/orders/{id}/lines",
    status_code=http_status.HTTP_201_CREATED,
    response_model=schemas.Order,
    responses=_ADD_LINE_RESPONSES,
)
def add_order_line(
    payload: schemas.OrderLineCreate,
    response: Response,
    user: Annotated[User, Depends(require_action(Action.EDIT_DRAFT_ORDERS))],
    order: Annotated[OrderView, Depends(get_order)],
    service: Annotated[OrderService, Depends(get_service)],
) -> schemas.Order:
    """Add a line to a draft."""
    view = service.add_line(
        order.order.id,
        payload.product_id,
        payload.quantity,
        payload.version,
    )
    _set_etag(response, view)
    return _order_out(view)


@router.patch(
    "/orders/{id}/lines/{line_id}",
    response_model=schemas.Order,
    responses=_UPDATE_LINE_RESPONSES,
)
def update_order_line(
    payload: schemas.OrderLinePatch,
    response: Response,
    user: Annotated[User, Depends(require_action(Action.EDIT_DRAFT_ORDERS))],
    order: Annotated[OrderView, Depends(get_order)],
    line: Annotated[OrderLineView, Depends(get_line)],
    service: Annotated[OrderService, Depends(get_service)],
) -> schemas.Order:
    """Change a line quantity of a draft."""
    view = service.set_quantity(
        order.order.id,
        line.line.id,
        payload.quantity,
        payload.version,
    )
    _set_etag(response, view)
    return _order_out(view)


@router.delete(
    "/orders/{id}/lines/{line_id}",
    response_model=schemas.Order,
    responses=_DELETE_LINE_RESPONSES,
)
def delete_order_line(
    response: Response,
    user: Annotated[User, Depends(require_action(Action.EDIT_DRAFT_ORDERS))],
    order: Annotated[OrderView, Depends(get_order)],
    line: Annotated[OrderLineView, Depends(get_line)],
    service: Annotated[OrderService, Depends(get_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> schemas.Order:
    """Remove a line from a draft."""
    view = service.remove_line(
        order.order.id,
        line.line.id,
        _parse_if_match(if_match),
    )
    _set_etag(response, view)
    return _order_out(view)


def _transition(
    action: OrderAction,
    order: OrderView,
    service: OrderService,
    if_match: str | None,
) -> OrderView:
    expected_version = _parse_if_match(if_match)
    if action == OrderAction.CONFIRM:
        return service.confirm(order.order.id, expected_version)
    if action == OrderAction.CANCEL:
        return service.cancel(order.order.id, expected_version)
    return service.ship(order.order.id, expected_version)


@router.post(
    "/orders/{id}/confirm",
    response_model=schemas.Order,
    responses=_CONFIRM_RESPONSES,
)
def confirm_order(
    response: Response,
    user: Annotated[User, Depends(require_action(Action.TRANSITION_ORDERS))],
    order: Annotated[OrderView, Depends(get_order)],
    service: Annotated[OrderService, Depends(get_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> schemas.Order:
    """Confirm a draft."""
    view = _transition(OrderAction.CONFIRM, order, service, if_match)
    _set_etag(response, view)
    return _order_out(view)


@router.post(
    "/orders/{id}/cancel",
    response_model=schemas.Order,
    responses=_TRANSITION_RESPONSES,
)
def cancel_order(
    response: Response,
    user: Annotated[User, Depends(require_action(Action.TRANSITION_ORDERS))],
    order: Annotated[OrderView, Depends(get_order)],
    service: Annotated[OrderService, Depends(get_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> schemas.Order:
    """Cancel a draft or a confirmed order."""
    view = _transition(OrderAction.CANCEL, order, service, if_match)
    _set_etag(response, view)
    return _order_out(view)


@router.post(
    "/orders/{id}/ship",
    response_model=schemas.Order,
    responses=_TRANSITION_RESPONSES,
)
def ship_order(
    response: Response,
    user: Annotated[User, Depends(require_action(Action.TRANSITION_ORDERS))],
    order: Annotated[OrderView, Depends(get_order)],
    service: Annotated[OrderService, Depends(get_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> schemas.Order:
    """Ship a paid order."""
    view = _transition(OrderAction.SHIP, order, service, if_match)
    _set_etag(response, view)
    return _order_out(view)
