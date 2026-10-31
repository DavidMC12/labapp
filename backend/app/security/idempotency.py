"""Idempotency key and request fingerprint helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
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


def canonical_json(body: object) -> bytes:
    """Serialize a body as compact UTF-8 JSON with sorted keys."""
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def fingerprint(secret: bytes, body: object) -> str:
    """Return the hex HMAC-SHA-256 of the canonical JSON body."""
    return hmac.new(secret, canonical_json(body), hashlib.sha256).hexdigest()


def same_request(secret: bytes, stored_fingerprint: str, body: object) -> bool:
    """Compare a stored fingerprint with the body in constant time."""
    return hmac.compare_digest(fingerprint(secret, body), stored_fingerprint)
