"""Tests for the idempotency helpers."""

from __future__ import annotations

import pytest

from app.errors import ApiError
from app.security.idempotency import validate_key


@pytest.mark.parametrize("key", [None, ""])
def test_missing_or_empty_key_is_required(key: str | None) -> None:
    with pytest.raises(ApiError) as error:
        validate_key(key)

    assert error.value.status == 422
    assert error.value.code == "IDEMPOTENCY_KEY_REQUIRED"
    assert error.value.detail == "Falta la cabecera Idempotency-Key."
    assert error.value.errors is None


@pytest.mark.parametrize("key", ["a", "A" * 64, "AZaz09._-"])
def test_valid_keys_are_returned(key: str) -> None:
    assert validate_key(key) == key


@pytest.mark.parametrize(
    "key",
    [
        "A" * 65,
        "with space",
        "with/slash",
        "with+plus",
        "with:colon",
        "withñ",
    ],
)
def test_invalid_format_is_rejected(key: str) -> None:
    with pytest.raises(ApiError) as error:
        validate_key(key)

    assert error.value.status == 422
    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.detail == "Revisa los datos ingresados."
    assert error.value.errors == [
        {
            "field": "Idempotency-Key",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]
