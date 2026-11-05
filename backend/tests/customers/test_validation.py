"""Tests for customer validation."""

from __future__ import annotations

import pytest

from app.errors import ApiError
from app.modules.customers.models import NewCustomer
from app.modules.customers.validation import validate_changes, validate_new

BASE = {
    "name": "Acme Industrial",
    "email": "acme@example.test",
    "phone": None,
    "tax_id": None,
    "address": None,
}


def _new(**overrides: object) -> NewCustomer:
    return validate_new({**BASE, **overrides})


def _errors(data: dict[str, object]) -> list[dict[str, str]]:
    with pytest.raises(ApiError) as error:
        if "name" in data or "email" in data:
            validate_new({**BASE, **data})
        else:
            validate_changes(data)
    assert error.value.status == 422
    assert error.value.code == "VALIDATION_ERROR"
    assert error.value.detail == "Revisa los datos ingresados."
    assert error.value.errors is not None
    return error.value.errors


@pytest.mark.parametrize(
    ("length", "code"),
    [(1, "TOO_SHORT"), (2, None), (120, None), (121, "TOO_LONG")],
)
def test_name_length_boundaries(length: int, code: str | None) -> None:
    if code is None:
        assert _new(name="x" * length).name == "x" * length
    else:
        errors = _errors({"name": "x" * length})
        assert errors == [
            {
                "field": "name",
                "code": code,
                "message": (
                    "Debe tener al menos 2 caracteres."
                    if code == "TOO_SHORT"
                    else "Debe tener como máximo 120 caracteres."
                ),
            }
        ]


@pytest.mark.parametrize("field", ["name", "email"])
@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_required_fields_reject_empty_values(field: str, value: str) -> None:
    assert _errors({field: value}) == [
        {
            "field": field,
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        }
    ]


def test_valid_email_of_254_characters() -> None:
    email = "a" * (254 - len("@example.com")) + "@example.com"
    assert len(email) == 254

    assert _new(email=email).email == email


def test_email_of_255_characters_is_too_long() -> None:
    email = "a" * (255 - len("@example.com")) + "@example.com"
    assert len(email) == 255

    assert _errors({"email": email}) == [
        {
            "field": "email",
            "code": "TOO_LONG",
            "message": "Debe tener como máximo 254 caracteres.",
        }
    ]


@pytest.mark.parametrize(
    "email",
    [
        "no-at.example.test",
        "two@@example.test",
        "a@example",
        "a@.b",
        "a@example..test",
        "a@example.",
        "a b@example.test",
    ],
)
def test_invalid_email_formats(email: str) -> None:
    assert _errors({"email": email}) == [
        {
            "field": "email",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


@pytest.mark.parametrize(
    ("phone", "code"),
    [
        ("abc", "INVALID_FORMAT"),
        ("123", "TOO_SHORT"),
        ("1" * 20, None),
        ("1" * 21, "TOO_LONG"),
        ("é1234567", "INVALID_FORMAT"),
    ],
)
def test_phone_rules(phone: str, code: str | None) -> None:
    if code is None:
        assert _new(phone=phone).phone == phone
    else:
        assert _errors({"phone": phone})[0]["field"] == "phone"
        assert _errors({"phone": phone})[0]["code"] == code


@pytest.mark.parametrize(
    ("tax_id", "code"),
    [
        ("ab", "TOO_SHORT"),
        ("abc", None),
        ("a" * 30, None),
        ("a" * 31, "TOO_LONG"),
        ("ééé", "INVALID_FORMAT"),
    ],
)
def test_tax_id_rules(tax_id: str, code: str | None) -> None:
    if code is None:
        assert _new(tax_id=tax_id).tax_id == tax_id
    else:
        assert _errors({"tax_id": tax_id})[0]["field"] == "tax_id"
        assert _errors({"tax_id": tax_id})[0]["code"] == code


def test_address_length_boundaries() -> None:
    assert _new(address="a" * 200).address == "a" * 200
    assert _errors({"address": "a" * 201}) == [
        {
            "field": "address",
            "code": "TOO_LONG",
            "message": "Debe tener como máximo 200 caracteres.",
        }
    ]


@pytest.mark.parametrize("field", ["name", "email", "phone", "tax_id", "address"])
def test_control_characters_are_invalid(field: str) -> None:
    value = "abc\u0000def"
    assert _errors({field: value}) == [
        {
            "field": field,
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


def test_format_is_reported_before_minimum_length() -> None:
    assert _errors({"phone": "abc"}) == [
        {
            "field": "phone",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


def test_several_fields_are_reported_together() -> None:
    errors = _errors(
        {
            "name": " ",
            "email": "bad",
            "phone": "abc",
            "tax_id": "a",
            "address": "a" * 201,
        }
    )

    assert [(error["field"], error["code"]) for error in errors] == [
        ("name", "REQUIRED"),
        ("email", "INVALID_FORMAT"),
        ("phone", "INVALID_FORMAT"),
        ("tax_id", "TOO_SHORT"),
        ("address", "TOO_LONG"),
    ]


def test_missing_name_is_reported_with_a_bad_phone() -> None:
    data = dict(BASE)
    del data["name"]
    data["phone"] = "abc"

    with pytest.raises(ApiError) as error:
        validate_new(data)

    assert error.value.errors == [
        {
            "field": "name",
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        },
        {
            "field": "phone",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        },
    ]


def test_text_is_trimmed_optional_fields_become_none_and_email_is_lowercased() -> None:
    customer = _new(
        name="  Acme Industrial  ",
        email="  ACME@EXAMPLE.TEST  ",
        phone="   ",
        tax_id="",
        address="   ",
    )

    assert customer == NewCustomer(
        name="Acme Industrial",
        email="acme@example.test",
        phone=None,
        tax_id=None,
        address=None,
    )


def test_optional_fields_with_only_control_whitespace_become_none() -> None:
    customer = _new(phone="\t\n", tax_id=" \t ", address="\n")

    assert customer.phone is None
    assert customer.tax_id is None
    assert customer.address is None


def test_update_validates_only_the_fields_that_were_sent() -> None:
    changes = validate_changes(
        {
            "name": "  New Name  ",
            "email": "  NEW@EXAMPLE.TEST  ",
            "phone": "   ",
        }
    )

    assert changes == {
        "name": "New Name",
        "email": "new@example.test",
        "phone": None,
    }


@pytest.mark.parametrize("field", ["name", "email"])
def test_update_none_for_required_fields(field: str) -> None:
    with pytest.raises(ApiError) as error:
        validate_changes({field: None})

    assert error.value.errors == [
        {
            "field": field,
            "code": "REQUIRED",
            "message": "Este campo es obligatorio.",
        }
    ]


def test_update_none_clears_optional_fields() -> None:
    assert validate_changes({"address": None, "tax_id": None}) == {
        "tax_id": None,
        "address": None,
    }


def test_update_with_no_changes_returns_an_empty_mapping() -> None:
    assert validate_changes({}) == {}
