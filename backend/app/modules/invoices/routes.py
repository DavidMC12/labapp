"""Invoice and payment routes."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Header, Response
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from app.domain.csv_export import CSV_CONTENT_TYPE, csv_response
from app.domain.permissions import Action
from app.domain.sorting import SortDirection
from app.errors import PROBLEM_MEDIA_TYPE, ApiError
from app.modules.auth.dependencies import get_current_user, require_action
from app.modules.auth.models import User
from app.modules.invoices import schemas
from app.modules.invoices.dependencies import get_invoice, get_service
from app.modules.invoices.models import Invoice, InvoiceStatus
from app.modules.invoices.service import MAX_ID, PAGE_SIZE, InvoiceService
from app.modules.orders.dependencies import get_order
from app.modules.orders.service import OrderView
from app.openapi import component_ref, documented_responses

router = APIRouter(prefix="/api", tags=["invoices"])

SortField = Literal["created_at", "number", "customer", "total"]

_DIGITS = re.compile(r"[0-9]+")

_LIST_RESPONSES = documented_responses(
    method="GET",
    extra={422: "The query parameters are invalid. Code: `VALIDATION_ERROR` (with `errors[]`)."},
)
_EXPORT_RESPONSES = {
    200: csv_response("The invoices of the list filters as a CSV file."),
    **_LIST_RESPONSES,
}
_READ_RESPONSES = documented_responses(
    method="GET",
    extra={
        404: "The invoice does not exist. Code: `NOT_FOUND`.",
        422: "The id is not an integer. Code: `VALIDATION_ERROR` (with `errors[]`).",
    },
)
_ISSUE_RESPONSES = documented_responses(
    method="POST",
    permission=True,
    extra={
        404: "The order does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale, the order already has an invoice or it is not "
        "confirmed. Codes: `VERSION_CONFLICT`, `INVOICE_ALREADY_EXISTS`, "
        "`ORDER_NOT_INVOICEABLE`.",
        422: "The id or the If-Match header is invalid, or the customer has no tax "
        "id. Codes: `VALIDATION_ERROR` (with `errors[]`), "
        "`CUSTOMER_TAX_ID_REQUIRED`.",
    },
)
_PAYMENT_RESPONSES = documented_responses(
    method="POST",
    body=True,
    permission=True,
    unavailable=("LOCK_TIMEOUT", "PAYMENT_GATEWAY_UNAVAILABLE"),
    extra={
        402: "The gateway declined the payment. Code: `PAYMENT_DECLINED`; the body "
        "carries `payment_id` and `reason`.",
        404: "The invoice does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale or the invoice does not accept payments. Codes: "
        "`VERSION_CONFLICT`, `INVOICE_NOT_PAYABLE`.",
        422: "The body, the Idempotency-Key header or the If-Match header is "
        "invalid, the key was reused, the amount differs from the total, or a card "
        "or transfer field is invalid. Codes: `VALIDATION_ERROR` (with "
        "`errors[]`), `IDEMPOTENCY_KEY_REQUIRED`, `IDEMPOTENCY_KEY_REUSED`, "
        "`PAYMENT_AMOUNT_MISMATCH`.",
    },
)

_PAYMENT_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": component_ref("PaymentCreate")},
            }
        },
    }
}


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


def _summary_out(invoice: Invoice) -> schemas.InvoiceSummary:
    return schemas.InvoiceSummary(
        id=invoice.id,
        number=invoice.number,
        status=invoice.status,
        order_id=invoice.order_id,
        order_number=invoice.order_number,
        customer_name=invoice.customer_name,
        total=invoice.total,
        version=invoice.version,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


@router.get("/invoices", response_model=schemas.InvoiceListOut, responses=_LIST_RESPONSES)
def list_invoices(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_service)],
    page: int = 1,
    q: str | None = None,
    status: InvoiceStatus | None = None,
    order_id: int | None = None,
    sort: SortField | None = None,
    direction: SortDirection | None = None,
) -> schemas.InvoiceListOut:
    """List invoices with a literal, accent-insensitive search."""
    items, total = service.list_invoices(page, q, status, order_id, sort, direction)
    return schemas.InvoiceListOut(
        items=[_summary_out(invoice) for invoice in items],
        page=page,
        page_size=PAGE_SIZE,
        total=total,
    )


@router.get("/invoices/export", response_class=Response, responses=_EXPORT_RESPONSES)
def export_invoices(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_service)],
    q: str | None = None,
    status: InvoiceStatus | None = None,
    order_id: int | None = None,
    sort: SortField | None = None,
    direction: SortDirection | None = None,
) -> Response:
    """Export every invoice of the list filters as a CSV file."""
    document = service.export_invoices(q, status, order_id, sort, direction)
    return Response(
        content=document.text,
        media_type=CSV_CONTENT_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/invoices/{id}", response_model=schemas.Invoice, responses=_READ_RESPONSES)
def read_invoice(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    invoice: Annotated[Invoice, Depends(get_invoice)],
    service: Annotated[InvoiceService, Depends(get_service)],
) -> schemas.Invoice:
    """Return one invoice."""
    response.headers["ETag"] = f'"{invoice.version}"'
    return service.invoice_out(invoice)


@router.post(
    "/orders/{id}/invoice",
    status_code=http_status.HTTP_201_CREATED,
    response_model=schemas.Invoice,
    responses=_ISSUE_RESPONSES,
)
def issue_invoice(
    response: Response,
    user: Annotated[User, Depends(require_action(Action.CREATE_INVOICES))],
    order: Annotated[OrderView, Depends(get_order)],
    service: Annotated[InvoiceService, Depends(get_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> schemas.Invoice:
    """Issue the invoice of a confirmed order."""
    invoice = service.issue(order.order.id, _parse_if_match(if_match))
    response.headers["Location"] = f"/api/invoices/{invoice.id}"
    response.headers["ETag"] = f'"{invoice.version}"'
    return service.invoice_out(invoice)


@router.post(
    "/invoices/{id}/payments",
    status_code=http_status.HTTP_201_CREATED,
    response_model=schemas.PaymentResult,
    responses=_PAYMENT_RESPONSES,
    openapi_extra=_PAYMENT_BODY,
)
def register_payment(
    body: Annotated[Any, Body()],
    user: Annotated[User, Depends(require_action(Action.REGISTER_PAYMENTS))],
    invoice: Annotated[Invoice, Depends(get_invoice)],
    service: Annotated[InvoiceService, Depends(get_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> JSONResponse:
    """Register a payment, replaying a known idempotency key first."""
    outcome = service.pay(
        invoice.id,
        idempotency_key,
        body,
        _parse_if_match(if_match),
    )
    headers: dict[str, str] = {}
    if outcome.replayed:
        headers["Idempotency-Replayed"] = "true"
    if outcome.response.status_code == http_status.HTTP_201_CREATED:
        invoice_body = outcome.response.body.get("invoice")
        if isinstance(invoice_body, dict) and "version" in invoice_body:
            headers["ETag"] = f'"{invoice_body["version"]}"'
        media_type = "application/json"
    else:
        media_type = PROBLEM_MEDIA_TYPE
    return JSONResponse(
        content=outcome.response.body,
        status_code=outcome.response.status_code,
        headers=headers,
        media_type=media_type,
    )
