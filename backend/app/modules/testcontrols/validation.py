"""Validation shared by the fault endpoints of task 024."""

from __future__ import annotations

from app.errors import ERROR_MESSAGES, ApiError
from app.modules.testcontrols.models import NewRule

ALLOWED_TARGETS = frozenset({"route", "gateway"})
ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
MAX_LATENCY_MS = 10_000
MIN_STATUS = 400
MAX_STATUS = 599
VALIDATION_DETAIL = ERROR_MESSAGES["VALIDATION_ERROR"]


def _error(field: str, code: str, message: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": message}


def _invalid(field: str) -> dict[str, str]:
    return _error(field, "INVALID_FORMAT", "El formato no es válido.")


def _required(field: str) -> dict[str, str]:
    return _error(field, "REQUIRED", "Este campo es obligatorio.")


def _out_of_range(field: str, minimum: object, maximum: object) -> dict[str, str]:
    return _error(
        field,
        "OUT_OF_RANGE",
        f"El valor debe estar entre {minimum} y {maximum}.",
    )


def validate_rule(rule: NewRule) -> None:
    """Raise a 422 ``VALIDATION_ERROR`` when a fault rule is not valid."""
    errors: list[dict[str, str]] = []

    if rule.target not in ALLOWED_TARGETS:
        errors.append(_invalid("target"))
    if rule.method is not None and rule.method not in ALLOWED_METHODS:
        errors.append(_invalid("method"))
    if not 0 <= rule.latency_ms <= MAX_LATENCY_MS:
        errors.append(_out_of_range("latency_ms", 0, MAX_LATENCY_MS))
    if rule.status is not None and not MIN_STATUS <= rule.status <= MAX_STATUS:
        errors.append(_out_of_range("status", MIN_STATUS, MAX_STATUS))
    if rule.remaining is not None and rule.remaining < 0:
        errors.append(_out_of_range("remaining", 0, "sin límite"))

    if rule.target == "route":
        if not rule.path:
            errors.append(_required("path"))
        elif not rule.path.startswith("/"):
            errors.append(_invalid("path"))
        if rule.latency_ms <= 0 and rule.status is None:
            errors.append(
                _error(
                    "latency_ms",
                    "INVALID_FORMAT",
                    "La regla necesita latencia o un estado.",
                )
            )
    elif rule.target == "gateway":
        if rule.method is not None:
            errors.append(_invalid("method"))
        if rule.path is not None:
            errors.append(_invalid("path"))
        if rule.status is not None:
            errors.append(_invalid("status"))

    if errors:
        raise ApiError(422, "VALIDATION_ERROR", VALIDATION_DETAIL, errors=errors)
