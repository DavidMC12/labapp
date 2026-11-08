"""Customer routes."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Header, Response, UploadFile, status

from app.domain.csv_export import CSV_CONTENT_TYPE, csv_response
from app.domain.permissions import Action
from app.domain.sorting import SortDirection
from app.errors import ApiError
from app.modules.auth.dependencies import get_current_user, require_action
from app.modules.auth.models import User
from app.modules.customers.dependencies import get_customer, get_service
from app.modules.customers.models import Customer, CustomerStatus
from app.modules.customers.schemas import (
    CustomerCreate,
    CustomerImportOut,
    CustomerListOut,
    CustomerOut,
    CustomerPatch,
)
from app.modules.customers.service import MAX_ID, PAGE_SIZE, CustomerService
from app.openapi import body_examples, documented_responses, response_examples
from app.openapi_examples import (
    CUSTOMER_CREATE_EXAMPLES,
    CUSTOMER_CREATED_EXAMPLES,
    CUSTOMER_EMAIL_TAKEN_EXAMPLES,
    CUSTOMER_IMPORT_CREATED_EXAMPLES,
    CUSTOMER_IMPORT_VALIDATION_EXAMPLES,
    CUSTOMER_PATCH_EXAMPLES,
)

router = APIRouter(prefix="/api/customers", tags=["customers"])

SortField = Literal["created_at", "name", "email"]

_LIST_RESPONSES = documented_responses(
    method="GET",
    extra={422: "The query parameters are invalid. Code: `VALIDATION_ERROR` (with `errors[]`)."},
)
_EXPORT_RESPONSES = {
    200: csv_response("The customers of the list filters as a CSV file."),
    **_LIST_RESPONSES,
}
_CREATE_RESPONSES = {
    **documented_responses(
        method="POST",
        body=True,
        permission=True,
        extra={
            409: "The email already belongs to another customer. Code: `CUSTOMER_EMAIL_TAKEN`.",
            422: "The body is invalid. Code: `VALIDATION_ERROR` (with `errors[]`).",
        },
        problem_examples={409: CUSTOMER_EMAIL_TAKEN_EXAMPLES},
    ),
    201: response_examples(CUSTOMER_CREATED_EXAMPLES),
}
_IMPORT_RESPONSES = {
    **documented_responses(
        method="POST",
        body=True,
        permission=True,
        extra={
            409: "The email is already used by another customer. Code: `CUSTOMER_EMAIL_TAKEN`.",
            422: "The file is missing or invalid. Codes: `VALIDATION_ERROR` (with "
            "`errors[]`) and `CUSTOMER_EMAIL_TAKEN` for a row whose email is already used.",
        },
        problem_examples={
            409: CUSTOMER_EMAIL_TAKEN_EXAMPLES,
            422: CUSTOMER_IMPORT_VALIDATION_EXAMPLES,
        },
    ),
    201: response_examples(CUSTOMER_IMPORT_CREATED_EXAMPLES),
}
_READ_RESPONSES = documented_responses(
    method="GET",
    extra={
        404: "The customer does not exist. Code: `NOT_FOUND`.",
        422: "The id is not an integer. Code: `VALIDATION_ERROR` (with `errors[]`).",
    },
)
_PATCH_RESPONSES = documented_responses(
    method="PATCH",
    body=True,
    permission=True,
    extra={
        404: "The customer does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale or the email is taken. Codes: `VERSION_CONFLICT`, "
        "`CUSTOMER_EMAIL_TAKEN`.",
        422: "The id or the body is invalid. Code: `VALIDATION_ERROR` (with `errors[]`).",
    },
)
_STATUS_RESPONSES = documented_responses(
    method="POST",
    permission=True,
    extra={
        404: "The customer does not exist. Code: `NOT_FOUND`.",
        409: "The version is stale. Code: `VERSION_CONFLICT`.",
        422: "The id or the If-Match header is invalid. Code: `VALIDATION_ERROR` "
        "(with `errors[]`).",
    },
)

_DIGITS = re.compile(r"[0-9]+")


def _customer_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        tax_id=customer.tax_id,
        address=customer.address,
        status=customer.status,
        version=customer.version,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


def _set_etag(response: Response, customer: Customer) -> None:
    response.headers["ETag"] = f'"{customer.version}"'


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


@router.get("", response_model=CustomerListOut, responses=_LIST_RESPONSES)
def list_customers(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CustomerService, Depends(get_service)],
    page: int = 1,
    q: str | None = None,
    status: CustomerStatus | None = None,
    sort: SortField | None = None,
    direction: SortDirection | None = None,
) -> CustomerListOut:
    """List customers with literal, accent-insensitive search."""
    items, total = service.list_customers(page, q, status, sort, direction)
    return CustomerListOut(
        items=[_customer_out(customer) for customer in items],
        page=page,
        page_size=PAGE_SIZE,
        total=total,
    )


@router.get("/export", response_class=Response, responses=_EXPORT_RESPONSES)
def export_customers(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CustomerService, Depends(get_service)],
    q: str | None = None,
    status: CustomerStatus | None = None,
    sort: SortField | None = None,
    direction: SortDirection | None = None,
) -> Response:
    """Export every customer of the list filters as a CSV file."""
    document = service.export_customers(q, status, sort, direction)
    return Response(
        content=document.text,
        media_type=CSV_CONTENT_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    response_model=CustomerImportOut,
    responses=_IMPORT_RESPONSES,
)
async def import_customers(
    user: Annotated[User, Depends(require_action(Action.MANAGE_CUSTOMERS))],
    service: Annotated[CustomerService, Depends(get_service)],
    file: Annotated[UploadFile, File(description="A UTF-8 CSV file named *.csv.")],
) -> CustomerImportOut:
    """Import the customers of a CSV file, all or nothing.

    The body is `multipart/form-data` with one file part named `file`. The file
    must be UTF-8 (an optional byte order mark is ignored), its name must end in
    `.csv` in any case, and it must use a comma separator with RFC 4180 quoting
    and CRLF or LF line ends. The first non-blank line is the header: its trimmed
    cells are column names among `name`, `email`, `phone`, `tax_id` and `address`,
    each at most once, and `name` and `email` are required. The following
    non-blank lines are 1 to 200 data rows. A row with fewer or more cells than
    the header is reported as `rows[N]`, where `N` is its physical line in the
    file (the header is line 1). Each row follows the creation rules: `name` 2 to
    120 characters, a valid `email` (stored trimmed and lowercased), an optional
    `phone` of 7 to 20 digits, spaces, `+`, `-`, `(`, `)`; an optional `tax_id`
    of 3 to 30 letters, digits or hyphens; and an optional `address` of up to 200
    characters. An empty optional value is stored as `null`, and the leading
    single quote of a neutralized formula is kept. Errors are listed in file
    order, at most 100; when any row fails nothing is created.
    """
    customers = service.import_customers(await file.read(), file.filename)
    return CustomerImportOut(
        created=len(customers),
        items=[_customer_out(customer) for customer in customers],
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CustomerOut,
    responses=_CREATE_RESPONSES,
    openapi_extra=body_examples(CUSTOMER_CREATE_EXAMPLES),
)
def create_customer(
    payload: CustomerCreate,
    response: Response,
    user: Annotated[User, Depends(require_action(Action.MANAGE_CUSTOMERS))],
    service: Annotated[CustomerService, Depends(get_service)],
) -> CustomerOut:
    """Create a customer."""
    customer = service.create(payload.model_dump())
    response.headers["Location"] = f"/api/customers/{customer.id}"
    _set_etag(response, customer)
    return _customer_out(customer)


@router.get("/{id}", response_model=CustomerOut, responses=_READ_RESPONSES)
def read_customer(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    customer: Annotated[Customer, Depends(get_customer)],
) -> CustomerOut:
    """Return one customer."""
    _set_etag(response, customer)
    return _customer_out(customer)


@router.patch(
    "/{id}",
    response_model=CustomerOut,
    responses=_PATCH_RESPONSES,
    openapi_extra=body_examples(CUSTOMER_PATCH_EXAMPLES),
)
def update_customer(
    payload: CustomerPatch,
    response: Response,
    user: Annotated[User, Depends(require_action(Action.MANAGE_CUSTOMERS))],
    customer: Annotated[Customer, Depends(get_customer)],
    service: Annotated[CustomerService, Depends(get_service)],
) -> CustomerOut:
    """Update the fields present in the body."""
    data = {
        field: getattr(payload, field) for field in payload.model_fields_set if field != "version"
    }
    updated = service.update(customer.id, data, payload.version)
    _set_etag(response, updated)
    return _customer_out(updated)


@router.post("/{id}/deactivate", response_model=CustomerOut, responses=_STATUS_RESPONSES)
def deactivate_customer(
    response: Response,
    user: Annotated[User, Depends(require_action(Action.MANAGE_CUSTOMERS))],
    customer: Annotated[Customer, Depends(get_customer)],
    service: Annotated[CustomerService, Depends(get_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> CustomerOut:
    """Set a customer to inactive."""
    updated = service.deactivate(customer.id, _parse_if_match(if_match))
    _set_etag(response, updated)
    return _customer_out(updated)


@router.post("/{id}/reactivate", response_model=CustomerOut, responses=_STATUS_RESPONSES)
def reactivate_customer(
    response: Response,
    user: Annotated[User, Depends(require_action(Action.MANAGE_CUSTOMERS))],
    customer: Annotated[Customer, Depends(get_customer)],
    service: Annotated[CustomerService, Depends(get_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> CustomerOut:
    """Set a customer to active."""
    updated = service.reactivate(customer.id, _parse_if_match(if_match))
    _set_etag(response, updated)
    return _customer_out(updated)
