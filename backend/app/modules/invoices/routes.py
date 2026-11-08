"""Invoice and payment routes."""

from __future__ import annotations

import re
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, Response
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from app.domain.permissions import Action
from app.errors import PROBLEM_MEDIA_TYPE, ApiError
from app.modules.auth.dependencies import get_current_user, require_action
from app.modules.auth.models import User
from app.modules.invoices import schemas
from app.modules.invoices.dependencies import get_invoice, get_service
from app.modules.invoices.models import Invoice, InvoiceStatus
from app.modules.invoices.service import MAX_ID, PAGE_SIZE, InvoiceService
from app.modules.orders.dependencies import get_order
from app.modules.orders.service import OrderView

router = APIRouter(prefix="/api", tags=["invoices"])

_DIGITS = re.compile(r"[0-9]+")

_PROBLEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["type", "title", "status", "code", "detail"],
    "properties": {
        "type": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "code": {"type": "string"},
        "detail": {"type": "string"},
    },
}

_PAYMENT_PROBLEM_SCHEMA: dict[str, Any] = {
    "allOf": [_PROBLEM_SCHEMA],
    "properties": {
        "type": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "code": {"type": "string"},
        "detail": {"type": "string"},
        "payment_id": {"type": "integer"},
        "reason": {"type": "string"},
    },
}

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "Authentication failed.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    },
    403: {
        "description": "Permission denied.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    },
    404: {
        "description": "Invoice or order not found.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    },
    409: {
        "description": "Version or state conflict.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    },
    422: {
        "description": "Validation error.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    },
}

_PAYMENT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **_ERROR_RESPONSES,
    402: {
        "description": "The gateway declined the payment.",
        "content": {"application/problem+json": {"schema": _PAYMENT_PROBLEM_SCHEMA}},
    },
    503: {
        "description": "The gateway is unavailable.",
        "content": {"application/problem+json": {"schema": _PAYMENT_PROBLEM_SCHEMA}},
    },
}

_PAYMENT_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": schemas.PaymentCreate.model_json_schema(),
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


@router.get("/invoices", response_model=schemas.InvoiceListOut, responses=_ERROR_RESPONSES)
def list_invoices(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_service)],
    page: int = 1,
    q: str | None = None,
    status: InvoiceStatus | None = None,
    order_id: int | None = None,
) -> schemas.InvoiceListOut:
    """List invoices with a literal, accent-insensitive search."""
    items, total = service.list_invoices(page, q, status, order_id)
    return schemas.InvoiceListOut(
        items=[_summary_out(invoice) for invoice in items],
        page=page,
        page_size=PAGE_SIZE,
        total=total,
    )


@router.get("/invoices/{id}", response_model=schemas.Invoice, responses=_ERROR_RESPONSES)
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
    responses=_ERROR_RESPONSES,
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
