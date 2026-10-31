"""Tests for card validation and the fake payment gateway."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from app.domain.payments import Card, luhn_valid, parse_card, validate_transfer_reference
from app.errors import ApiError

TODAY = date(2026, 10, 31)
VALID_NUMBER = "4242 4242 4242 4242"
VALID_EXPIRY = "12/30"
VALID_CVC = "123"


def _card_errors(
    number: str = VALID_NUMBER,
    expiry: str = VALID_EXPIRY,
    cvc: str = VALID_CVC,
    today: date = TODAY,
) -> list[dict[str, str]]:
    with pytest.raises(ApiError) as error:
        parse_card(number, expiry, cvc, today)

    assert error.value.status == 422
    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.detail == "Revisa los datos ingresados."
    assert error.value.errors is not None
    return error.value.errors


@pytest.mark.parametrize(
    "number",
    [
        "4242424242424242",
        "4242 4242 4242 4242",
        "4242-4242-4242-4242",
        "4000000000000002",
        "4000 0000 0000 0002",
        "4000000000090003",
        "4000 0000 0009 0003",
    ],
)
def test_luhn_accepts_valid_numbers(number: str) -> None:
    assert luhn_valid(number) is True


@pytest.mark.parametrize(
    "number",
    [
        "4242424242424241",
        "1234567890123456",
        "",
        "4242abcd42424242",
        "4242 4242 4242 4243",
    ],
)
def test_luhn_rejects_invalid_numbers(number: str) -> None:
    assert luhn_valid(number) is False


def test_parse_card_returns_only_the_last_four_digits() -> None:
    card = parse_card(VALID_NUMBER, VALID_EXPIRY, VALID_CVC, TODAY)

    assert card == Card(last4="4242")
    assert [field.name for field in fields(Card)] == ["last4"]


@pytest.mark.parametrize("number", ["4000-0000-0000-0002", "4000 0000 0000 0002"])
def test_parse_card_ignores_spaces_and_hyphens(number: str) -> None:
    card = parse_card(number, VALID_EXPIRY, VALID_CVC, TODAY)

    assert card.last4 == "0002"


@pytest.mark.parametrize(
    "number",
    [
        "424242424242424",
        "42424242424242424",
        "4242424242424241",
        "4242 4242 4242 424a",
        "",
    ],
)
def test_invalid_card_number_is_reported(number: str) -> None:
    errors = _card_errors(number=number)

    assert errors == [
        {
            "field": "card.number",
            "code": "CARD_NUMBER_INVALID",
            "message": "El número de tarjeta no es válido.",
        }
    ]


@pytest.mark.parametrize("today", [date(2026, 10, 1), date(2026, 10, 31)])
def test_expiry_in_the_current_month_is_valid(today: date) -> None:
    card = parse_card(VALID_NUMBER, "10/26", VALID_CVC, today)

    assert card.last4 == "4242"


def test_expiry_in_the_previous_month_is_expired() -> None:
    errors = _card_errors(expiry="09/26")

    assert errors == [
        {
            "field": "card.expiry",
            "code": "CARD_EXPIRED",
            "message": "La tarjeta está vencida.",
        }
    ]


@pytest.mark.parametrize(
    "expiry", ["13/26", "1/26", "12-30", "12/2030", "", "aa/bb", "00/26", "12/2"]
)
def test_malformed_expiry_is_invalid_format(expiry: str) -> None:
    errors = _card_errors(expiry=expiry)

    assert errors == [
        {
            "field": "card.expiry",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


def test_expiry_is_valid_through_the_last_day_of_february() -> None:
    card = parse_card(VALID_NUMBER, "02/28", VALID_CVC, date(2028, 2, 29))

    assert card.last4 == "4242"

    errors = _card_errors(expiry="02/28", today=date(2028, 3, 1))
    assert errors[0]["code"] == "CARD_EXPIRED"


@pytest.mark.parametrize("cvc", ["12", "1234", "12a", "", " 12"])
def test_invalid_cvc_is_reported(cvc: str) -> None:
    errors = _card_errors(cvc=cvc)

    assert errors == [
        {
            "field": "card.cvc",
            "code": "CARD_CVC_INVALID",
            "message": "El código de seguridad no es válido.",
        }
    ]


def test_all_card_problems_are_reported_together() -> None:
    errors = _card_errors(number="1234", expiry="13/26", cvc="12")

    assert errors == [
        {
            "field": "card.number",
            "code": "CARD_NUMBER_INVALID",
            "message": "El número de tarjeta no es válido.",
        },
        {
            "field": "card.expiry",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        },
        {
            "field": "card.cvc",
            "code": "CARD_CVC_INVALID",
            "message": "El código de seguridad no es válido.",
        },
    ]


@pytest.mark.parametrize("reference", ["ABCD", "A" * 40])
def test_transfer_reference_length_is_valid(reference: str) -> None:
    assert validate_transfer_reference(reference) is None


def test_transfer_reference_of_three_characters_is_too_short() -> None:
    with pytest.raises(ApiError) as error:
        validate_transfer_reference("ABC")

    assert error.value.status == 422
    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.detail == "Revisa los datos ingresados."
    assert error.value.errors == [
        {
            "field": "reference",
            "code": "TOO_SHORT",
            "message": "Debe tener al menos 4 caracteres.",
        }
    ]


def test_transfer_reference_of_forty_one_characters_is_too_long() -> None:
    with pytest.raises(ApiError) as error:
        validate_transfer_reference("A" * 41)

    assert error.value.status == 422
    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.detail == "Revisa los datos ingresados."
    assert error.value.errors == [
        {
            "field": "reference",
            "code": "TOO_LONG",
            "message": "Debe tener como máximo 40 caracteres.",
        }
    ]
