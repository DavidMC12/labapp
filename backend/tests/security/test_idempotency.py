"""Tests for the idempotency helpers."""

from __future__ import annotations

import copy
import json
import re

import pytest

from app.errors import ApiError
from app.security.idempotency import (
    canonical_json,
    fingerprint,
    redact_card,
    same_request,
    validate_key,
)

SECRET = b"test-secret"


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


def test_canonical_json_sorts_keys_and_removes_spaces() -> None:
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_canonical_json_ignores_key_order_and_whitespace() -> None:
    first = json.loads('{"b": 2, "a": {"d": 4, "c": 3}}')
    second = json.loads('{ "a": { "c": 3, "d": 4 }, "b": 2 }')

    assert canonical_json(first) == canonical_json(second)
    assert canonical_json(first) == b'{"a":{"c":3,"d":4},"b":2}'


def test_canonical_json_keeps_unicode_readable() -> None:
    assert canonical_json({"name": "Café"}) == '{"name":"Café"}'.encode()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_canonical_json_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValueError):
        canonical_json({"value": value})


def test_fingerprint_is_stable_across_key_order() -> None:
    assert fingerprint(SECRET, {"a": 1, "b": 2}) == fingerprint(SECRET, {"b": 2, "a": 1})


def test_fingerprint_changes_with_the_body() -> None:
    assert fingerprint(SECRET, {"a": 1}) != fingerprint(SECRET, {"a": 2})


def test_fingerprint_changes_with_the_secret() -> None:
    assert fingerprint(b"one", {"a": 1}) != fingerprint(b"two", {"a": 1})


def test_fingerprint_is_a_lowercase_sha256_hex_digest() -> None:
    assert re.fullmatch(r"[0-9a-f]{64}", fingerprint(SECRET, {"a": 1}))


def test_same_request_accepts_an_equivalent_body() -> None:
    stored = fingerprint(SECRET, {"a": 1, "b": 2})

    assert same_request(SECRET, stored, {"b": 2, "a": 1}) is True


def test_same_request_rejects_another_body_or_secret() -> None:
    stored = fingerprint(SECRET, {"a": 1})

    assert same_request(SECRET, stored, {"a": 2}) is False
    assert same_request(b"other-secret", stored, {"a": 1}) is False
    assert same_request(SECRET, "0" * 64, {"a": 1}) is False


def test_redact_card_keeps_only_the_last_four_digits_and_removes_cvc() -> None:
    body = {
        "invoice_id": 7,
        "amount": "327.80",
        "method": "card",
        "card": {
            "number": "4000 0000 0000 0002",
            "expiry": "12/30",
            "cvc": "123",
        },
    }

    redacted = redact_card(body)
    serialized = json.dumps(redacted)

    assert redacted["card"] == {"number": "0002", "expiry": "12/30"}
    assert "cvc" not in redacted["card"]
    assert "4000 0000 0000 0002" not in serialized
    assert "4000000000000002" not in serialized


def test_redact_card_handles_hyphenated_numbers() -> None:
    redacted = redact_card({"card": {"number": "4242-4242-4242-4242", "cvc": "999"}})

    assert redacted["card"] == {"number": "4242"}


def test_redact_card_does_not_mutate_the_original() -> None:
    body = {
        "card": {
            "number": "4242 4242 4242 4242",
            "expiry": "12/30",
            "cvc": "123",
        }
    }
    original = copy.deepcopy(body)

    redacted = redact_card(body)

    assert body == original
    assert redacted is not body
    assert redacted["card"] is not body["card"]


def test_redact_card_leaves_bodies_without_a_card_unchanged() -> None:
    body = {"method": "transfer", "reference": "TRF-2026-0001"}

    redacted = redact_card(body)

    assert redacted == body
    assert redacted is not body


def test_redact_card_removes_cvc_even_without_a_number() -> None:
    redacted = redact_card({"card": {"expiry": "12/30", "cvc": "123"}})

    assert redacted["card"] == {"expiry": "12/30"}


def test_redact_card_ignores_a_non_dict_card() -> None:
    body = {"card": "not-a-dict"}

    assert redact_card(body) == body
