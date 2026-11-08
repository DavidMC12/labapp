"""Tests for registering payments."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.modules.customers.models import CustomerStatus
from tests.invoices.helpers import (
    assert_problem,
    card_body,
    cash_body,
    field_codes,
    pay,
    transfer_body,
)


def _issue_four(client: TestClient) -> None:
    assert client.post("/api/orders/2/invoice").status_code == 201


def test_an_approved_payment_pays_the_invoice_and_the_order(
    clients: dict[str, TestClient],
) -> None:
    client = clients["finance"]
    _issue_four(client)

    response = pay(client, 4, card_body(amount="121.00"))

    assert response.status_code == 201
    assert response.headers["etag"] == '"2"'
    body = response.json()
    assert body["payment"] == {
        "id": 5,
        "method": "card",
        "status": "approved",
        "amount": "121.00",
        "reference": None,
        "card_last4": "4242",
        "reason": None,
        "created_at": body["payment"]["created_at"],
    }
    assert body["invoice"]["status"] == "paid"
    assert body["invoice"]["version"] == 2
    assert [payment["id"] for payment in body["invoice"]["payments"]] == [5]
    order = client.get("/api/orders/2").json()
    assert order["status"] == "paid"
    assert order["version"] == 3


def test_a_repeat_answers_the_same_body_with_the_replayed_header(
    clients: dict[str, TestClient],
) -> None:
    client = clients["finance"]
    _issue_four(client)
    first = pay(client, 4, card_body(amount="121.00"))

    second = pay(client, 4, card_body(amount="121.00"))

    assert second.status_code == 201
    assert second.headers["idempotency-replayed"] == "true"
    assert second.json() == first.json()


def test_a_changed_cvc_is_the_same_redacted_body(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]
    _issue_four(client)
    first = pay(client, 4, card_body(amount="121.00"))

    second = pay(client, 4, card_body(amount="121.00", cvc="999"))

    assert second.status_code == 201
    assert second.headers["idempotency-replayed"] == "true"
    assert second.json() == first.json()


def test_the_same_key_with_another_body_is_reused(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]
    _issue_four(client)
    pay(client, 4, card_body(amount="121.00"))

    response = pay(client, 4, card_body(amount="121.00", number="4000 0000 0000 0002"))

    assert_problem(response, 422, "IDEMPOTENCY_KEY_REUSED")


def test_a_declined_payment_is_a_402_with_the_payment_and_reason(
    clients: dict[str, TestClient],
) -> None:
    response = pay(clients["finance"], 1, card_body(number="4000 0000 0000 0002"))

    body = assert_problem(response, 402, "PAYMENT_DECLINED")
    assert body == {
        "type": "about:blank",
        "title": "Payment Required",
        "status": 402,
        "code": "PAYMENT_DECLINED",
        "detail": "La pasarela rechazó el pago. Prueba con otra tarjeta.",
        "payment_id": 5,
        "reason": "CARD_DECLINED",
    }


def test_a_failed_payment_is_a_503_with_the_payment_and_reason(
    clients: dict[str, TestClient],
) -> None:
    response = pay(clients["finance"], 1, card_body(number="4000 0000 0009 0003"))

    body = assert_problem(response, 503, "PAYMENT_GATEWAY_UNAVAILABLE")
    assert body["payment_id"] == 5
    assert body["reason"] == "GATEWAY_UNAVAILABLE"


@pytest.mark.parametrize(
    "body",
    [
        transfer_body(),
        cash_body(),
    ],
)
def test_transfer_and_cash_are_approved(
    clients: dict[str, TestClient],
    body: dict[str, object],
) -> None:
    response = pay(clients["finance"], 1, body)

    assert response.status_code == 201
    assert response.json()["payment"]["status"] == "approved"


def test_an_amount_mismatch_is_a_top_level_422(clients: dict[str, TestClient]) -> None:
    response = pay(clients["finance"], 1, card_body(amount="327.81"))

    assert_problem(response, 422, "PAYMENT_AMOUNT_MISMATCH")


def test_a_paid_invoice_is_not_payable(clients: dict[str, TestClient]) -> None:
    response = pay(clients["finance"], 2, transfer_body(amount="197.97"))

    assert_problem(response, 409, "INVOICE_NOT_PAYABLE")


def test_a_stale_if_match_is_a_conflict(clients: dict[str, TestClient]) -> None:
    response = pay(clients["finance"], 1, card_body(), if_match='"9"')

    assert_problem(response, 409, "VERSION_CONFLICT")


def test_a_stale_version_on_a_paid_invoice_conflicts_first(
    clients: dict[str, TestClient],
) -> None:
    response = pay(
        clients["finance"],
        2,
        transfer_body(amount="197.97"),
        if_match='"9"',
    )

    assert_problem(response, 409, "VERSION_CONFLICT")


@pytest.mark.parametrize("value", ["abc", '"1', "1" * 11])
def test_a_malformed_if_match_is_a_field_error(
    clients: dict[str, TestClient],
    value: str,
) -> None:
    response = pay(clients["finance"], 1, card_body(), if_match=value)

    assert field_codes(response) == [("If-Match", "INVALID_FORMAT")]


def test_a_missing_key_is_required(clients: dict[str, TestClient]) -> None:
    response = pay(clients["finance"], 1, card_body(), key=None)

    assert_problem(response, 422, "IDEMPOTENCY_KEY_REQUIRED")


@pytest.mark.parametrize("key", ["A" * 65, "with space"])
def test_a_malformed_key_is_a_field_error(clients: dict[str, TestClient], key: str) -> None:
    response = pay(clients["finance"], 1, card_body(), key=key)

    assert field_codes(response) == [("Idempotency-Key", "INVALID_FORMAT")]


def test_an_unknown_invoice_is_not_found_before_the_body_error(
    clients: dict[str, TestClient],
) -> None:
    response = pay(clients["finance"], 99, [])

    assert_problem(response, 404, "NOT_FOUND")


def test_a_wrong_role_with_an_unknown_invoice_is_forbidden(
    clients: dict[str, TestClient],
) -> None:
    assert_problem(pay(clients["sales"], 99, card_body()), 403, "FORBIDDEN")


def test_a_replay_is_decided_before_body_validation(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]
    _issue_four(client)
    first = pay(client, 4, card_body(amount="121.00"))

    second = pay(client, 4, card_body(amount="121.00"))

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.headers["idempotency-replayed"] == "true"


def test_a_corrected_retry_after_a_validation_error_works(
    clients: dict[str, TestClient],
) -> None:
    client = clients["finance"]
    invalid = pay(client, 1, {"method": "card", "amount": "327.80"})
    assert invalid.status_code == 422

    assert pay(client, 1, card_body()).status_code == 201


def test_a_rejected_request_does_not_consume_the_key(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]
    mismatch = pay(client, 1, card_body(amount="327.81"))
    assert mismatch.status_code == 422

    assert pay(client, 1, card_body()).status_code == 201


def test_a_declined_attempt_consumes_the_key(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]
    body = card_body(number="4000 0000 0000 0002")
    first = pay(client, 1, body)
    second = pay(client, 1, body)

    assert first.status_code == 402
    assert second.status_code == 402
    assert second.headers["idempotency-replayed"] == "true"
    assert second.json() == first.json()


def test_a_failed_attempt_is_stored_and_can_be_replayed(
    clients: dict[str, TestClient],
) -> None:
    client = clients["finance"]
    body = card_body(number="4000 0000 0009 0003")
    first = pay(client, 1, body)
    second = pay(client, 1, body)

    assert first.status_code == 503
    assert second.status_code == 503
    assert second.headers["idempotency-replayed"] == "true"
    assert second.json() == first.json()


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (card_body(amount="327.801"), [("amount", "INVALID_FORMAT")]),
        (card_body(amount="-1"), [("amount", "INVALID_FORMAT")]),
        ({"method": "cash", "amount": 327.8}, [("amount", "INVALID_FORMAT")]),
        (card_body(number="4242 4242 4242 424"), [("card.number", "CARD_NUMBER_INVALID")]),
        (card_body(number="4242 4242 4242 4241"), [("card.number", "CARD_NUMBER_INVALID")]),
        (card_body(expiry="13/30"), [("card.expiry", "INVALID_FORMAT")]),
        (card_body(expiry="1/30"), [("card.expiry", "INVALID_FORMAT")]),
        (card_body(cvc="12"), [("card.cvc", "CARD_CVC_INVALID")]),
        (card_body(cvc="1234"), [("card.cvc", "CARD_CVC_INVALID")]),
        (transfer_body(reference="ABC"), [("reference", "TOO_SHORT")]),
        (transfer_body(reference="  ab  "), [("reference", "TOO_SHORT")]),
        (transfer_body(reference="A" * 41), [("reference", "TOO_LONG")]),
        ({"method": "cash", "amount": "327.80", "extra": 1}, [("extra", "INVALID_FORMAT")]),
        ({"method": "card", "amount": "327.80"}, [("card", "REQUIRED")]),
        ({"method": "card", "amount": "327.80", "card": None}, [("card", "REQUIRED")]),
    ],
)
def test_payment_validation_boundaries(
    clients: dict[str, TestClient],
    body: dict[str, object],
    expected: list[tuple[str, str]],
) -> None:
    response = pay(clients["finance"], 1, body)

    assert field_codes(response) == expected


def test_a_card_with_a_transfer_is_invalid(clients: dict[str, TestClient]) -> None:
    body = transfer_body()
    body["card"] = {"number": "4242 4242 4242 4242", "expiry": "12/30", "cvc": "123"}

    response = pay(clients["finance"], 1, body)

    assert ("card", "INVALID_FORMAT") in field_codes(response)


def test_a_body_that_is_not_an_object_is_invalid(clients: dict[str, TestClient]) -> None:
    response = pay(clients["finance"], 1, [])

    assert field_codes(response) == [("body", "INVALID_FORMAT")]


def test_a_non_finite_amount_in_raw_content_is_a_field_error(
    clients: dict[str, TestClient],
) -> None:
    response = clients["finance"].post(
        "/api/invoices/1/payments",
        content='{"method":"cash","amount":NaN}',
        headers={"Content-Type": "application/json", "Idempotency-Key": "key-1"},
    )

    assert field_codes(response) == [("amount", "INVALID_FORMAT")]


def test_a_text_plain_body_is_invalid(clients: dict[str, TestClient]) -> None:
    response = clients["finance"].post(
        "/api/invoices/1/payments",
        content='{"method":"cash","amount":"327.80"}',
        headers={"Content-Type": "text/plain", "Idempotency-Key": "key-1"},
    )

    assert field_codes(response) == [("body", "INVALID_FORMAT")]


def test_a_body_nested_nine_hundred_levels_is_invalid(
    clients: dict[str, TestClient],
) -> None:
    deep = '{"method":"cash","amount":"327.80","deep":' + '{"n":' * 900 + "1" + "}" * 900 + "}"
    response = clients["finance"].post(
        "/api/invoices/1/payments",
        content=deep,
        headers={"Content-Type": "application/json", "Idempotency-Key": "key-1"},
    )

    assert response.status_code == 422
    assert ("deep", "INVALID_FORMAT") in field_codes(response)


def test_valid_amount_and_reference_boundaries(clients: dict[str, TestClient]) -> None:
    client = clients["finance"]
    assert pay(client, 1, card_body(amount="327.8")).status_code == 201
    assert client.post("/api/orders/2/invoice").status_code == 201
    assert pay(client, 4, transfer_body(amount="121.00", reference="ABCD")).status_code == 201


def test_the_response_never_contains_the_card_number_or_the_cvc(
    clients: dict[str, TestClient],
) -> None:
    response = pay(clients["finance"], 1, card_body())

    assert response.status_code == 201
    text = response.text
    assert "4242 4242 4242 4242" not in text
    assert "4242424242424242" not in text
    assert "cvc" not in text
    assert response.json()["payment"]["card_last4"] == "4242"


def test_a_confirmed_order_of_an_inactive_customer_can_be_paid(
    app,
    clients: dict[str, TestClient],
) -> None:
    app.state.customer_repository.set_status(
        4,
        CustomerStatus.INACTIVE,
        None,
        datetime(2026, 11, 5, 15, 0, tzinfo=UTC),
    )

    response = pay(clients["finance"], 1, card_body())

    assert response.status_code == 201
