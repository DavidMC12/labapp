"""Shared documentation for the OpenAPI contract.

The helpers here only describe the API: they never validate a request or change an
answer. `docs/SPEC.md` is the source of truth for the behaviour and the error codes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated, Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field, WithJsonSchema

from app.errors import PROBLEM_MEDIA_TYPE
from app.modules.auth.constants import SESSION_COOKIE_NAME

COMPONENT_REF_TEMPLATE = "#/components/schemas/{model}"
PROBLEM_REF = COMPONENT_REF_TEMPLATE.format(model="Problem")
SECURITY_SCHEME_NAME = "cookieAuth"
STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
PUBLIC_OPERATIONS = frozenset(
    {
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/health"),
    }
)

ID_MINIMUM = 1
ID_MAXIMUM = 2147483647
MONEY_PATTERN = r"^[0-9]+\.[0-9]{2}$"
TAX_RATE_PATTERN = r"^[0-9]{1,3}(\.[0-9]{1,2})?$"
PAYMENT_AMOUNT_PATTERN = r"^[0-9]{1,10}(\.[0-9]{1,2})?$"

MONEY_JSON_SCHEMA = {
    "type": "string",
    "pattern": MONEY_PATTERN,
    "example": "19.90",
}

TaxRate = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "pattern": TAX_RATE_PATTERN,
            "example": "10.00",
        }
    ),
]

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Log in, log out and read the current user (SPEC section 3).",
    },
    {
        "name": "customers",
        "description": "Customers: list, search, create and edit (SPEC section 4).",
    },
    {
        "name": "orders",
        "description": "Products, the tax rate and the order flows (SPEC section 5).",
    },
    {
        "name": "invoices",
        "description": "Invoices and payments (SPEC section 6).",
    },
    {
        "name": "health",
        "description": "Liveness check.",
    },
]

OPENAPI_DESCRIPTION = (
    "The HTTP contract of LabApp. `docs/SPEC.md` is the source of truth for the "
    "behaviour, the error codes and the field rules; this document describes every "
    "request and every answer."
)


class FieldError(BaseModel):
    """One field-level validation error."""

    field: str = Field(description="The path of the invalid field, such as `lines[0].quantity`.")
    code: str = Field(description="A stable code from the SPEC field-error table.")
    message: str = Field(description="A Spanish message for the user.")


class Shortage(BaseModel):
    """One line whose requested quantity exceeds the available stock."""

    product_id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    sku: str
    name: str
    available: int = Field(ge=0)
    requested: int = Field(ge=1)


class Problem(BaseModel):
    """An RFC 9457 problem document, served as `application/problem+json`."""

    type: str = Field(description="Always `about:blank`.")
    title: str
    status: int
    code: str = Field(description="A stable code from the SPEC error tables.")
    detail: str = Field(description="A Spanish message for the user.")
    errors: list[FieldError] | None = Field(
        default=None,
        description="One entry per invalid field, on a 422 `VALIDATION_ERROR`.",
    )
    shortages: list[Shortage] | None = Field(
        default=None,
        description="The short lines, on a 409 `INSUFFICIENT_STOCK`.",
    )
    payment_id: int | None = Field(
        default=None,
        ge=ID_MINIMUM,
        le=ID_MAXIMUM,
        description="The stored payment, on a 402 `PAYMENT_DECLINED` or a 503 "
        "`PAYMENT_GATEWAY_UNAVAILABLE`.",
    )
    reason: str | None = Field(
        default=None,
        description="`CARD_DECLINED` or `GATEWAY_UNAVAILABLE` on the same answers.",
    )
    retry_after: int | None = Field(
        default=None,
        description="The seconds to wait, on a 429 `RATE_LIMITED`; the same value "
        "is sent in the `Retry-After` header.",
    )


class HealthOut(BaseModel):
    """The answer of the health check."""

    status: Literal["ok"]


def application_version() -> str:
    """Return the package version, or a placeholder when it is not installed."""
    try:
        return version("labapp-backend")
    except PackageNotFoundError:
        return "0.0.0"


def component_ref(name: str) -> str:
    """Return the reference to a named schema of the document."""
    return COMPONENT_REF_TEMPLATE.format(model=name)


def problem(description: str) -> dict[str, Any]:
    """Document one error answer that carries a `Problem` body."""
    return {
        "description": description,
        "content": {PROBLEM_MEDIA_TYPE: {"schema": {"$ref": PROBLEM_REF}}},
    }


def documented_responses(
    *,
    method: str,
    protected: bool = True,
    body: bool = False,
    permission: bool = False,
    rate_limited: bool = True,
    unavailable: Sequence[str] | None = ("LOCK_TIMEOUT",),
    extra: Mapping[int, str] | None = None,
) -> dict[int, dict[str, Any]]:
    """Describe the answers that apply to an operation.

    `extra` documents the answers specific to the operation; `unavailable` names the
    stable codes of its 503 answer, or is `None` for a route that never reaches the
    database or a password check.
    """
    responses: dict[int, dict[str, Any]] = {}
    if body:
        responses[400] = problem("The request body is not valid JSON. Code: `MALFORMED_JSON`.")
        responses[413] = problem("The request body exceeds 100 KB. Code: `PAYLOAD_TOO_LARGE`.")
    if protected:
        responses[401] = problem(
            "There is no session or it expired. Codes: `UNAUTHENTICATED`, `SESSION_EXPIRED`."
        )
    if method.upper() in STATE_CHANGING_METHODS:
        if permission:
            responses[403] = problem(
                "The Origin is not allowed or the role lacks the permission. Codes: "
                "`CSRF_ORIGIN_MISMATCH`, `FORBIDDEN`."
            )
        else:
            responses[403] = problem(
                "The request Origin is not allowed. Code: `CSRF_ORIGIN_MISMATCH`."
            )
    if rate_limited:
        responses[429] = problem(
            "Too many requests. Code: `RATE_LIMITED`; the answer carries `Retry-After`."
        )
    responses[500] = problem("Unexpected server error. Code: `INTERNAL_ERROR`.")
    if unavailable:
        noun = "Code" if len(unavailable) == 1 else "Codes"
        codes = ", ".join(f"`{code}`" for code in unavailable)
        responses[503] = problem(f"The service or a database lock is busy. {noun}: {codes}.")
    for status, description in (extra or {}).items():
        responses[status] = problem(description)
    return responses


def install_openapi(app: FastAPI) -> None:
    """Add the named components and the cookie scheme to the generated document."""
    original = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        document = original()
        _add_components(document)
        _apply_security(document)
        _use_component_request_bodies(document)
        app.openapi_schema = document
        return document

    app.openapi = openapi  # type: ignore[method-assign]


def _add_components(document: dict[str, Any]) -> None:
    # Imported here so that the invoice schemas can import this module without a cycle.
    from app.modules.invoices.schemas import PaymentCard, PaymentCreate

    components = document.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    for model in (FieldError, Shortage, Problem, HealthOut, PaymentCard, PaymentCreate):
        _add_model_schema(schemas, model)
    components.setdefault("securitySchemes", {})[SECURITY_SCHEME_NAME] = {
        "type": "apiKey",
        "in": "cookie",
        "name": SESSION_COOKIE_NAME,
        "description": "The session cookie set by `POST /api/auth/login`.",
    }


def _add_model_schema(schemas: dict[str, Any], model: type[BaseModel]) -> None:
    definition = model.model_json_schema(ref_template=COMPONENT_REF_TEMPLATE)
    for name, nested in definition.pop("$defs", {}).items():
        schemas.setdefault(name, nested)
    schemas.setdefault(model.__name__, definition)


def _apply_security(document: dict[str, Any]) -> None:
    for path, operations in document.get("paths", {}).items():
        for method, operation in operations.items():
            if (method.upper(), path) in PUBLIC_OPERATIONS:
                continue
            operation["security"] = [{SECURITY_SCHEME_NAME: []}]


def _use_component_request_bodies(document: dict[str, Any]) -> None:
    """Keep only the reference when a body is documented with a named schema."""
    for operations in document.get("paths", {}).values():
        for operation in operations.values():
            request_body = operation.get("requestBody")
            if not request_body:
                continue
            for media in request_body.get("content", {}).values():
                schema = media.get("schema")
                if isinstance(schema, dict) and "$ref" in schema:
                    media["schema"] = {"$ref": schema["$ref"]}
