"""Idempotency key and request fingerprint helpers."""

from __future__ import annotations

import re

from app.errors import ApiError

VALIDATION_MESSAGE = "Revisa los datos ingresados."
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def validate_key(key: str | None) -> str:
    """Validate and return an Idempotency-Key."""
    if not key:
        raise ApiError(
            422,
            "IDEMPOTENCY_KEY_REQUIRED",
            "Falta la cabecera Idempotency-Key.",
        )

    if _KEY_PATTERN.fullmatch(key) is None:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            VALIDATION_MESSAGE,
            errors=[
                {
                    "field": "Idempotency-Key",
                    "code": "INVALID_FORMAT",
                    "message": "El formato no es válido.",
                }
            ],
        )

    return key
