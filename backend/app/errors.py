from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"
REQUEST_ID_HEADER = "X-Request-Id"

NOT_FOUND = "NOT_FOUND"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"
MALFORMED_JSON = "MALFORMED_JSON"

ERROR_MESSAGES: dict[str, str] = {
    NOT_FOUND: "No se encontró el recurso solicitado.",
    METHOD_NOT_ALLOWED: "Método no permitido para este recurso.",
    PAYLOAD_TOO_LARGE: "La solicitud es demasiado grande.",
    VALIDATION_ERROR: "Revisa los datos ingresados.",
    INTERNAL_ERROR: "Ocurrió un error inesperado. Inténtalo de nuevo.",
    MALFORMED_JSON: "El cuerpo de la solicitud no es un JSON válido.",
}

DEFAULT_ERROR_DETAIL = "No se pudo completar la solicitud."

FIELD_MESSAGES: dict[str, str] = {
    "REQUIRED": "Este campo es obligatorio.",
    "INVALID_FORMAT": "El formato no es válido.",
}

_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    404: (NOT_FOUND, ERROR_MESSAGES[NOT_FOUND]),
    405: (METHOD_NOT_ALLOWED, ERROR_MESSAGES[METHOD_NOT_ALLOWED]),
    413: (PAYLOAD_TOO_LARGE, ERROR_MESSAGES[PAYLOAD_TOO_LARGE]),
    500: (INTERNAL_ERROR, ERROR_MESSAGES[INTERNAL_ERROR]),
}


class ApiError(Exception):
    """Domain error rendered as an RFC 9457 problem document."""

    def __init__(
        self,
        status: int,
        code: str,
        detail: str,
        *,
        title: str | None = None,
        errors: list[dict[str, str]] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.title = title or _title_for_status(status)
        self.errors = errors
        self.extra = extra


def _title_for_status(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return str(uuid4())


def problem_response(
    request_id: str,
    *,
    status: int,
    code: str,
    detail: str,
    title: str | None = None,
    errors: list[dict[str, str]] | None = None,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build an RFC 9457 problem response."""
    document: dict[str, Any] = {
        "type": "about:blank",
        "title": title or _title_for_status(status),
        "status": status,
        "code": code,
        "detail": detail,
    }
    if errors is not None:
        document["errors"] = errors
    if extra:
        document.update(extra)

    response_headers = dict(headers or {})
    response_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status,
        content=document,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=response_headers,
    )


async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return problem_response(
        get_request_id(request),
        status=exc.status,
        code=exc.code,
        detail=exc.detail,
        title=exc.title,
        errors=exc.errors,
        extra=exc.extra,
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    status = exc.status_code
    common = _HTTP_ERRORS.get(status)
    if common is not None:
        code, detail = common
    else:
        try:
            code = HTTPStatus(status).name
        except ValueError:
            code = "HTTP_ERROR"
        detail = DEFAULT_ERROR_DETAIL
    return problem_response(
        get_request_id(request),
        status=status,
        code=code,
        detail=detail,
        headers=dict(exc.headers or {}),
    )


def _field_path(loc: tuple[Any, ...]) -> str:
    parts = list(loc)
    if parts and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    path = ""
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path = f"{path}.{part}" if path else str(part)
    return path or "body"


def _field_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        code = "REQUIRED" if error.get("type") == "missing" else "INVALID_FORMAT"
        details.append(
            {
                "field": _field_path(tuple(error.get("loc", ()))),
                "code": code,
                "message": FIELD_MESSAGES[code],
            }
        )
    return details


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    if any(error.get("type") == "json_invalid" for error in exc.errors()):
        return problem_response(
            get_request_id(request),
            status=400,
            code=MALFORMED_JSON,
            detail=ERROR_MESSAGES[MALFORMED_JSON],
        )
    return problem_response(
        get_request_id(request),
        status=422,
        code=VALIDATION_ERROR,
        detail=ERROR_MESSAGES[VALIDATION_ERROR],
        errors=_field_errors(exc),
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, (DBAPIError, psycopg.Error)):
        original = getattr(exc, "orig", None)
        sqlstate = getattr(original, "sqlstate", None) or getattr(exc, "sqlstate", None)
        logger.error(
            "Unhandled database exception %s (SQLSTATE %s) on request %s",
            type(exc).__name__,
            sqlstate or "unknown",
            get_request_id(request),
        )
    else:
        logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    return problem_response(
        get_request_id(request),
        status=500,
        code=INTERNAL_ERROR,
        detail=ERROR_MESSAGES[INTERNAL_ERROR],
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register the handlers that render every error as a problem document."""
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
