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
from app.openapi_examples import OPERATION_EXAMPLES, PROBLEM_EXAMPLES

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


def problem(description: str, *, status: int) -> dict[str, Any]:
    """Document one error answer that carries a `Problem` body."""
    content: dict[str, Any] = {"schema": {"$ref": PROBLEM_REF}}
    examples = PROBLEM_EXAMPLES.get(status)
    if examples is not None:
        content["examples"] = dict(examples)
    return {
        "description": description,
        "content": {PROBLEM_MEDIA_TYPE: content},
    }


def body_examples(examples: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Document named examples for a JSON request body."""
    return {
        "requestBody": {
            "content": {"application/json": {"examples": dict(examples)}},
        }
    }


def response_examples(
    examples: Mapping[str, Mapping[str, Any]],
    *,
    media_type: str = "application/json",
) -> dict[str, Any]:
    """Add named examples to an answer documented by its response model."""
    return {"content": {media_type: {"examples": dict(examples)}}}


def documented_responses(
    *,
    method: str,
    protected: bool = True,
    body: bool = False,
    permission: bool = False,
    rate_limited: bool = True,
    unavailable: Sequence[str] | None = ("LOCK_TIMEOUT",),
    extra: Mapping[int, str] | None = None,
    problem_examples: Mapping[int, Mapping[str, Mapping[str, Any]]] | None = None,
) -> dict[int, dict[str, Any]]:
    """Describe the answers that apply to an operation.

    `extra` documents the answers specific to the operation; `unavailable` names the
    stable codes of its 503 answer, or is `None` for a route that never reaches the
    database or a password check. `problem_examples` replaces the shared example of one
    status, for the operation whose answer is the exception (the login 401).
    """
    responses: dict[int, dict[str, Any]] = {}
    if body:
        responses[400] = problem(
            "The request body is not valid JSON. Code: `MALFORMED_JSON`.",
            status=400,
        )
        responses[413] = problem(
            "The request body exceeds 100 KB. Code: `PAYLOAD_TOO_LARGE`.",
            status=413,
        )
    if protected:
        responses[401] = problem(
            "There is no session or it expired. Codes: `UNAUTHENTICATED`, `SESSION_EXPIRED`.",
            status=401,
        )
    if method.upper() in STATE_CHANGING_METHODS:
        if permission:
            responses[403] = problem(
                "The Origin is not allowed or the role lacks the permission. Codes: "
                "`CSRF_ORIGIN_MISMATCH`, `FORBIDDEN`.",
                status=403,
            )
        else:
            responses[403] = problem(
                "The request Origin is not allowed. Code: `CSRF_ORIGIN_MISMATCH`.",
                status=403,
            )
    if rate_limited:
        responses[429] = problem(
            "Too many requests. Code: `RATE_LIMITED`; the answer carries `Retry-After`.",
            status=429,
        )
    responses[500] = problem(
        "Unexpected server error. Code: `INTERNAL_ERROR`.",
        status=500,
    )
    if unavailable:
        noun = "Code" if len(unavailable) == 1 else "Codes"
        codes = ", ".join(f"`{code}`" for code in unavailable)
        responses[503] = problem(
            f"The service or a database lock is busy. {noun}: {codes}.",
            status=503,
        )
    for status, description in (extra or {}).items():
        responses[status] = problem(description, status=status)
    for status, examples in (problem_examples or {}).items():
        responses[status]["content"][PROBLEM_MEDIA_TYPE]["examples"] = dict(examples)
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
        _use_binary_file_parts(document)
        _apply_examples(document)
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


def _use_binary_file_parts(document: dict[str, Any]) -> None:
    """Describe an uploaded file part as ``format: binary``.

    FastAPI (through Pydantic) writes ``contentMediaType: application/octet-stream``
    for an ``UploadFile``. The contract of this API describes the part as binary so
    that a client knows it must send a file, not a string field.
    """
    schemas = document.get("components", {}).get("schemas", {})
    for operations in document.get("paths", {}).values():
        for operation in operations.values():
            body = operation.get("requestBody") or {}
            media = body.get("content", {}).get("multipart/form-data")
            if media is None:
                continue
            schema = media.get("schema")
            if isinstance(schema, dict) and "$ref" in schema:
                schema = schemas.get(schema["$ref"].rsplit("/", 1)[-1])
            if not isinstance(schema, dict):
                continue
            for field in schema.get("properties", {}).values():
                if field.get("contentMediaType") == "application/octet-stream":
                    field.pop("contentMediaType")
                    field["format"] = "binary"


def _apply_examples(document: dict[str, Any]) -> None:
    """Replay the named examples so that the nulls FastAPI drops stay in the contract."""
    for (method, path), examples in OPERATION_EXAMPLES.items():
        operation = document.get("paths", {}).get(path, {}).get(method.lower())
        if operation is None:
            continue
        request = examples.get("request")
        if request is not None:
            media = operation["requestBody"]["content"]["application/json"]
            media["examples"] = dict(request)
        for status, named_examples in examples.get("responses", {}).items():
            response = operation["responses"][status]
            media_type = PROBLEM_MEDIA_TYPE if int(status) >= 400 else "application/json"
            response["content"][media_type]["examples"] = dict(named_examples)
