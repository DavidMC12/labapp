"""Card validation and the fake payment gateway."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

from app.errors import ApiError

VALIDATION_MESSAGE = "Revisa los datos ingresados."
CARD_NUMBER_LENGTH = 16
CVC_LENGTH = 3

_EXPIRY_PATTERN = re.compile(r"^([0-9]{2})/([0-9]{2})$")
_CARD_MESSAGES: dict[str, str] = {
    "INVALID_FORMAT": "El formato no es válido.",
    "CARD_NUMBER_INVALID": "El número de tarjeta no es válido.",
    "CARD_EXPIRED": "La tarjeta está vencida.",
    "CARD_CVC_INVALID": "El código de seguridad no es válido.",
}


@dataclass(frozen=True)
class Card:
    """A validated card; only the last four digits are kept."""

    last4: str


@dataclass(frozen=True)
class GatewayDecision:
    """Outcome of the fake payment gateway."""

    outcome: str
    reason: str | None


def _normalize_number(number: str) -> str:
    return number.replace(" ", "").replace("-", "")


def _card_error(field: str, code: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": _CARD_MESSAGES[code]}


def luhn_valid(number: str) -> bool:
    """Return whether the number passes the Luhn checksum."""
    if not isinstance(number, str):
        return False

    digits = _normalize_number(number)
    if not digits.isascii() or not digits.isdigit():
        return False

    total = 0
    for position, character in enumerate(reversed(digits)):
        digit = int(character)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _expiry_problem(expiry: object, today: date) -> str | None:
    if not isinstance(expiry, str):
        return "INVALID_FORMAT"

    match = _EXPIRY_PATTERN.fullmatch(expiry)
    if match is None:
        return "INVALID_FORMAT"

    month = int(match.group(1))
    year = 2000 + int(match.group(2))
    if not 1 <= month <= 12:
        return "INVALID_FORMAT"

    last_day = date(year, month, calendar.monthrange(year, month)[1])
    if last_day < today:
        return "CARD_EXPIRED"
    return None


def parse_card(number: str, expiry: str, cvc: str, today: date) -> Card:
    """Validate card data and keep only the last four digits."""
    errors: list[dict[str, str]] = []

    normalized = _normalize_number(number) if isinstance(number, str) else ""
    if (
        not normalized.isascii()
        or not normalized.isdigit()
        or len(normalized) != CARD_NUMBER_LENGTH
        or not luhn_valid(normalized)
    ):
        errors.append(_card_error("card.number", "CARD_NUMBER_INVALID"))

    expiry_problem = _expiry_problem(expiry, today)
    if expiry_problem is not None:
        errors.append(_card_error("card.expiry", expiry_problem))

    if not isinstance(cvc, str) or not cvc.isascii() or not cvc.isdigit() or len(cvc) != CVC_LENGTH:
        errors.append(_card_error("card.cvc", "CARD_CVC_INVALID"))

    if errors:
        raise ApiError(422, "VALIDATION_ERROR", VALIDATION_MESSAGE, errors=errors)

    return Card(last4=normalized[-4:])


MIN_TRANSFER_REFERENCE_LENGTH = 4
MAX_TRANSFER_REFERENCE_LENGTH = 40


def _reference_error(code: str, message: str) -> ApiError:
    return ApiError(
        422,
        "VALIDATION_ERROR",
        VALIDATION_MESSAGE,
        errors=[{"field": "reference", "code": code, "message": message}],
    )


def validate_transfer_reference(reference: str) -> None:
    """Validate the length of a transfer reference."""
    length = len(reference)
    if length < MIN_TRANSFER_REFERENCE_LENGTH:
        raise _reference_error(
            "TOO_SHORT",
            f"Debe tener al menos {MIN_TRANSFER_REFERENCE_LENGTH} caracteres.",
        )
    if length > MAX_TRANSFER_REFERENCE_LENGTH:
        raise _reference_error(
            "TOO_LONG",
            f"Debe tener como máximo {MAX_TRANSFER_REFERENCE_LENGTH} caracteres.",
        )


def gateway_decision(method: str, card_last4: str | None = None) -> GatewayDecision:
    """Return the fake gateway outcome for a payment method."""
    if method == "card":
        if card_last4 == "0002":
            return GatewayDecision("declined", "CARD_DECLINED")
        if card_last4 == "0003":
            return GatewayDecision("unavailable", "GATEWAY_UNAVAILABLE")
        return GatewayDecision("approved", None)

    if method in ("transfer", "cash"):
        return GatewayDecision("approved", None)

    raise ValueError(f"unknown payment method: {method!r}")
