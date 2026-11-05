"""Validation for customer creation and updates."""

from __future__ import annotations

import string
import unicodedata
from collections.abc import Mapping

from app.errors import ApiError
from app.modules.customers.models import Changes, NewCustomer

VALIDATION_DETAIL = "Revisa los datos ingresados."

NAME_MIN = 2
NAME_MAX = 120
PHONE_MIN = 7
PHONE_MAX = 20
TAX_ID_MIN = 3
TAX_ID_MAX = 30
ADDRESS_MAX = 200
EMAIL_MAX = 254

PHONE_CHARACTERS = frozenset(string.digits + " +()-")
TAX_ID_CHARACTERS = frozenset(string.ascii_letters + string.digits + "-")

_FIELDS = ("name", "email", "phone", "tax_id", "address")


def has_control_character(text: str) -> bool:
    """Return whether the text contains a Unicode control character."""
    return any(unicodedata.category(character) == "Cc" for character in text)


def _error(field: str, code: str, message: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": message}


def _required(field: str) -> dict[str, str]:
    return _error(field, "REQUIRED", "Este campo es obligatorio.")


def _invalid_format(field: str) -> dict[str, str]:
    return _error(field, "INVALID_FORMAT", "El formato no es válido.")


def _too_short(field: str, minimum: int) -> dict[str, str]:
    return _error(field, "TOO_SHORT", f"Debe tener al menos {minimum} caracteres.")


def _too_long(field: str, maximum: int) -> dict[str, str]:
    return _error(field, "TOO_LONG", f"Debe tener como máximo {maximum} caracteres.")


def _valid_email(text: str) -> bool:
    if any(character.isspace() for character in text):
        return False
    if text.count("@") != 1:
        return False
    local, domain = text.split("@")
    labels = domain.split(".")
    return bool(local) and len(labels) >= 2 and all(labels)


def _clean_text(
    field: str,
    value: object | None,
    *,
    required: bool,
    minimum: int | None = None,
    maximum: int | None = None,
    characters: frozenset[str] | None = None,
    email: bool = False,
) -> tuple[str | None, dict[str, str] | None]:
    if value is None:
        return None, _required(field) if required else None
    if not isinstance(value, str):
        return None, _invalid_format(field)
    if has_control_character(value):
        return None, _invalid_format(field)

    text = value.strip()
    if not text:
        return None, _required(field) if required else None

    if email:
        if not _valid_email(text):
            return None, _invalid_format(field)
        text = text.lower()
    elif characters is not None and any(character not in characters for character in text):
        return None, _invalid_format(field)

    if minimum is not None and len(text) < minimum:
        return None, _too_short(field, minimum)
    if maximum is not None and len(text) > maximum:
        return None, _too_long(field, maximum)
    return text, None


def _raise_validation_errors(errors: list[dict[str, str]]) -> None:
    if errors:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            VALIDATION_DETAIL,
            errors=errors,
        )


def _validate_field(field: str, value: object | None) -> tuple[str | None, dict[str, str] | None]:
    if field == "name":
        return _clean_text(field, value, required=True, minimum=NAME_MIN, maximum=NAME_MAX)
    if field == "email":
        return _clean_text(field, value, required=True, maximum=EMAIL_MAX, email=True)
    if field == "phone":
        return _clean_text(
            field,
            value,
            required=False,
            minimum=PHONE_MIN,
            maximum=PHONE_MAX,
            characters=PHONE_CHARACTERS,
        )
    if field == "tax_id":
        return _clean_text(
            field,
            value,
            required=False,
            minimum=TAX_ID_MIN,
            maximum=TAX_ID_MAX,
            characters=TAX_ID_CHARACTERS,
        )
    return _clean_text(field, value, required=False, maximum=ADDRESS_MAX)


def validate_new(data: Mapping[str, object | None]) -> NewCustomer:
    """Validate a creation payload and return its normalized values."""
    errors: list[dict[str, str]] = []
    values: dict[str, str | None] = {}
    for field in _FIELDS:
        value, error = _validate_field(field, data.get(field))
        if error is not None:
            errors.append(error)
        else:
            values[field] = value
    _raise_validation_errors(errors)
    return NewCustomer(
        name=values["name"] or "",
        email=values["email"] or "",
        phone=values["phone"],
        tax_id=values["tax_id"],
        address=values["address"],
    )


def validate_changes(data: Mapping[str, object | None]) -> Changes:
    """Validate only the fields present in an update payload."""
    errors: list[dict[str, str]] = []
    changes: dict[str, str | None] = {}
    for field in _FIELDS:
        if field not in data:
            continue
        value, error = _validate_field(field, data[field])
        if error is not None:
            errors.append(error)
        else:
            changes[field] = value
    _raise_validation_errors(errors)
    return changes
