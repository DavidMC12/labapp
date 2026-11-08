"""Validation shared by the fault endpoints of task 024."""

from __future__ import annotations

import unicodedata

from app.errors import ERROR_MESSAGES, ApiError
from app.modules.testcontrols.models import NewRule

ALLOWED_TARGETS = frozenset({"route", "gateway"})
ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
MAX_LATENCY_MS = 10_000
MIN_STATUS = 400
MAX_STATUS = 599
MAX_PATH_LENGTH = 2_048
HEALTH_PATH = "/api/health"
TEST_PREFIX = "/__test__"
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


def _has_control_or_surrogate(value: str) -> bool:
    return any(unicodedata.category(character) in ("Cc", "Cs") for character in value)


def _path_error(message: str) -> dict[str, str]:
    return _error("path", "INVALID_FORMAT", message)


def _path_errors(path: str) -> list[dict[str, str]]:
    """Reject a path that the request controls can never match."""
    if not path.startswith("/"):
        return [_invalid("path")]
    if _has_control_or_surrogate(path):
        return [_path_error("La ruta no puede contener caracteres de control.")]
    if len(path) > MAX_PATH_LENGTH:
        return [_path_error(f"La ruta no puede tener más de {MAX_PATH_LENGTH} caracteres.")]
    if path.startswith(TEST_PREFIX):
        return [_path_error(f"La ruta no puede empezar por {TEST_PREFIX}.")]
    if path == HEALTH_PATH:
        return [_path_error(f"La ruta {HEALTH_PATH} no puede tener una falla inyectada.")]
    return []


def rule_errors(rule: NewRule) -> list[dict[str, str]]:
    """Return every problem of a fault rule, so a caller can report them together."""
    errors: list[dict[str, str]] = []

    if rule.target not in ALLOWED_TARGETS:
        errors.append(_invalid("target"))
    if not 0 <= rule.latency_ms <= MAX_LATENCY_MS:
        errors.append(_out_of_range("latency_ms", 0, MAX_LATENCY_MS))

    if rule.target == "route":
        if rule.method is not None and rule.method not in ALLOWED_METHODS:
            errors.append(_invalid("method"))
        if not rule.path:
            errors.append(_required("path"))
        else:
            errors.extend(_path_errors(rule.path))
        if rule.status is not None and not MIN_STATUS <= rule.status <= MAX_STATUS:
            errors.append(_out_of_range("status", MIN_STATUS, MAX_STATUS))
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

    if rule.remaining is not None and rule.remaining < 0:
        errors.append(_out_of_range("remaining", 0, "sin límite"))

    return errors


def validate_rule(rule: NewRule) -> None:
    """Raise a 422 ``VALIDATION_ERROR`` when a fault rule is not valid."""
    errors = rule_errors(rule)
    if errors:
        raise ApiError(422, "VALIDATION_ERROR", VALIDATION_DETAIL, errors=errors)
