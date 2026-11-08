"""Tests for the invoice service."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.errors import ApiError
from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.models import CustomerStatus
from app.modules.customers.seed import seed_customers
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.models import InvoiceStatus, PaymentStatus
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.invoices.service import InvoiceService
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.seed import seed_orders, seed_products
from tests.infra.helpers import FixedClock
from tests.invoices.contract_store import CountingGateway

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
SECRET = b"test-secret"


class RecordingMailer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def invoice_issued(self, to_email: str, number: str) -> None:
        self.calls.append((to_email, number))


class FailingMailer:
    def invoice_issued(self, to_email: str, number: str) -> None:
        raise RuntimeError("email failed")


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)


@pytest.fixture
def customers() -> InMemoryCustomerRepository:
    return InMemoryCustomerRepository(seed_customers())


@pytest.fixture
def orders(customers: InMemoryCustomerRepository) -> InMemoryOrderStore:
    store = InMemoryOrderStore(customers)
    store.replace_all(seed_products(), seed_orders(), Decimal("10.00"))
    return store


@pytest.fixture
def gateway() -> CountingGateway:
    return CountingGateway()


@pytest.fixture
def store(
    orders: InMemoryOrderStore,
    customers: InMemoryCustomerRepository,
    gateway: CountingGateway,
) -> InMemoryInvoiceStore:
    store = InMemoryInvoiceStore(orders, customers, gateway)
    store.replace_all(seed_invoices(), seed_payments())
    orders.invoices = store
    return store


@pytest.fixture
def mailer() -> RecordingMailer:
    return RecordingMailer()


@pytest.fixture
def service(
    store: InMemoryInvoiceStore,
    orders: InMemoryOrderStore,
    customers: InMemoryCustomerRepository,
    clock: FixedClock,
    mailer: RecordingMailer,
) -> InvoiceService:
    return InvoiceService(store, orders, customers, clock, mailer, SECRET)


def card_body(
    *,
    amount: str = "327.80",
    number: str = "4242 4242 4242 4242",
    expiry: str = "12/30",
    cvc: str = "123",
) -> dict[str, object]:
    return {
        "method": "card",
        "amount": amount,
        "card": {"number": number, "expiry": expiry, "cvc": cvc},
    }


def transfer_body(
    *,
    amount: str = "327.80",
    reference: str = "TRF-2026-0001",
) -> dict[str, object]:
    return {"method": "transfer", "amount": amount, "reference": reference}


def cash_body(*, amount: str = "327.80") -> dict[str, object]:
    return {"method": "cash", "amount": amount}


def _error(service: InvoiceService, body: object, key: str | None = "key-1") -> ApiError:
    with pytest.raises(ApiError) as error:
        service.pay(1, key, body, None)
    return error.value


def _field_codes(error: ApiError) -> list[tuple[str, str]]:
    assert error.errors is not None
    return [(item["field"], item["code"]) for item in error.errors]


def test_issue_sends_one_notice_to_the_customer_email(service, mailer, store) -> None:
    invoice = service.issue(2, 1)

    assert invoice.number == "FAC-0004"
    assert mailer.calls == [("beta@example.test", "FAC-0004")]


def test_a_failing_mailer_does_not_change_the_answer(
    store,
    orders,
    customers,
    clock,
) -> None:
    service = InvoiceService(store, orders, customers, clock, FailingMailer(), SECRET)

    invoice = service.issue(2, 1)

    assert invoice.status == InvoiceStatus.ISSUED
    assert store.get_invoice(invoice.id).status == InvoiceStatus.ISSUED


def test_issue_allows_an_inactive_customer(service, customers) -> None:
    customers.set_status(2, CustomerStatus.INACTIVE, None, NOW)

    assert service.issue(2, None).id == 4


def test_issue_unknown_order_and_stale_version(service) -> None:
    with pytest.raises(ApiError) as missing:
        service.issue(99, None)
    assert missing.value.status == 404

    with pytest.raises(ApiError) as stale:
        service.issue(2, 9)
    assert stale.value.status == 409
    assert stale.value.code == "VERSION_CONFLICT"


def test_a_validation_error_on_the_version_is_reported(service) -> None:
    with pytest.raises(ApiError) as error:
        service.issue(2, "1")  # type: ignore[arg-type]

    assert _field_codes(error.value) == [("version", "INVALID_FORMAT")]


def test_an_approved_payment_returns_the_rendered_result(service, store) -> None:
    outcome = service.pay(1, "key-1", card_body(), None)

    assert outcome.replayed is False
    assert outcome.response.status_code == 201
    body = outcome.response.body
    assert body["payment"]["status"] == "approved"
    assert body["payment"]["amount"] == "327.80"
    assert body["payment"]["card_last4"] == "4242"
    assert body["payment"]["reference"] is None
    assert body["invoice"]["status"] == "paid"
    assert body["invoice"]["version"] == 2
    assert [payment["id"] for payment in body["invoice"]["payments"]] == [1, 2, 5]
    assert store.get_invoice(1).status == InvoiceStatus.PAID


def test_the_stored_response_never_holds_the_card_number_or_the_cvc(service) -> None:
    outcome = service.pay(1, "key-1", card_body(), None)

    serialized = json.dumps(outcome.response.body)
    assert "4242424242424242" not in serialized
    assert "4242 4242 4242 4242" not in serialized
    assert "123" not in json.dumps(outcome.response.body["payment"])


def test_a_declined_payment_answers_a_problem_with_payment_and_reason(service) -> None:
    outcome = service.pay(1, "key-1", card_body(number="4000 0000 0000 0002"), None)

    assert outcome.response.status_code == 402
    assert outcome.response.body == {
        "type": "about:blank",
        "title": "Payment Required",
        "status": 402,
        "code": "PAYMENT_DECLINED",
        "detail": "La pasarela rechazó el pago. Prueba con otra tarjeta.",
        "payment_id": 5,
        "reason": "CARD_DECLINED",
    }


def test_a_failed_payment_answers_a_problem_with_payment_and_reason(service) -> None:
    outcome = service.pay(1, "key-1", card_body(number="4000 0000 0009 0003"), None)

    assert outcome.response.status_code == 503
    assert outcome.response.body["code"] == "PAYMENT_GATEWAY_UNAVAILABLE"
    assert outcome.response.body["payment_id"] == 5
    assert outcome.response.body["reason"] == "GATEWAY_UNAVAILABLE"


def test_a_repeated_request_replays_before_business_rules(service, gateway) -> None:
    first = service.pay(1, "key-1", card_body(), None)
    second = service.pay(1, "key-1", card_body(), None)

    assert first.response == second.response
    assert first.replayed is False
    assert second.replayed is True
    assert gateway.calls == 1


def test_the_same_key_with_another_invalid_body_is_reused(service) -> None:
    service.pay(1, "key-1", card_body(), None)

    error = _error(service, {"method": "card", "amount": "327.80"})

    assert error.code == "IDEMPOTENCY_KEY_REUSED"


def test_a_corrected_retry_with_the_same_key_works(service) -> None:
    with pytest.raises(ApiError):
        service.pay(1, "key-1", {"method": "card", "amount": "327.80"}, None)

    outcome = service.pay(1, "key-1", card_body(), None)

    assert outcome.replayed is False
    assert outcome.response.status_code == 201


def test_a_rejected_request_does_not_consume_the_key(service) -> None:
    with pytest.raises(ApiError) as error:
        service.pay(1, "key-1", card_body(amount="327.81"), None)
    assert error.value.code == "PAYMENT_AMOUNT_MISMATCH"

    outcome = service.pay(1, "key-1", card_body(), None)

    assert outcome.response.status_code == 201


def test_a_declined_attempt_consumes_the_key(service) -> None:
    first = service.pay(1, "key-1", card_body(number="4000 0000 0000 0002"), None)
    second = service.pay(1, "key-1", card_body(number="4000 0000 0000 0002"), None)

    assert first.response.status_code == 402
    assert second.replayed is True
    assert second.response == first.response


def test_a_missing_key_is_reported_at_once(service) -> None:
    for key in (None, ""):
        error = _error(service, {}, key=key)

        assert error.code == "IDEMPOTENCY_KEY_REQUIRED"
        assert error.errors is None


def test_a_malformed_key_is_merged_with_the_body_errors(service) -> None:
    error = _error(service, {"unknown": 1}, key="bad key")

    assert error.code == "VALIDATION_ERROR"
    fields = {field for field, _ in _field_codes(error)}
    assert "Idempotency-Key" in fields
    assert "unknown" in fields


def test_a_malformed_key_cannot_replay_a_stored_response(service) -> None:
    service.pay(1, "key-1", card_body(), None)

    error = _error(service, card_body(), key="key-1 ")

    assert _field_codes(error) == [("Idempotency-Key", "INVALID_FORMAT")]


@pytest.mark.parametrize("amount", ["327.8", "327.80"])
def test_valid_amount_boundaries(service, amount: str) -> None:
    outcome = service.pay(1, "key-1", card_body(amount=amount), None)

    assert outcome.response.status_code == 201


@pytest.mark.parametrize(
    "amount",
    ["327.801", "-1", "", "327.80\n", "３２７.８０"],
)
def test_invalid_amount_formats(service, amount: str) -> None:
    error = _error(service, card_body(amount=amount))

    assert ("amount", "INVALID_FORMAT") in _field_codes(error)


def test_a_number_amount_is_invalid(service) -> None:
    error = _error(service, {"method": "cash", "amount": 327.8})

    assert ("amount", "INVALID_FORMAT") in _field_codes(error)


@pytest.mark.parametrize(
    "number",
    ["4242-4242-4242-4242", "4242424242424242"],
)
def test_card_numbers_with_spaces_and_hyphens_are_valid(service, number: str) -> None:
    outcome = service.pay(1, "key-1", card_body(number=number), None)

    assert outcome.response.status_code == 201


@pytest.mark.parametrize("number", ["424242424242424", "42424242424242424", "4242424242424241"])
def test_invalid_card_numbers(service, number: str) -> None:
    error = _error(service, card_body(number=number))

    assert ("card.number", "CARD_NUMBER_INVALID") in _field_codes(error)


@pytest.mark.parametrize("expiry", ["13/30", "1/30", "12-30", "", "12/30\n"])
def test_malformed_expiry(service, expiry: str) -> None:
    error = _error(service, card_body(expiry=expiry))

    assert ("card.expiry", "INVALID_FORMAT") in _field_codes(error)


def test_the_current_month_is_valid_and_the_last_one_is_expired(service) -> None:
    assert service.pay(1, "key-1", card_body(expiry="06/26"), None).response.status_code == 201

    error = _error(service, card_body(expiry="05/26"), key="key-2")
    assert ("card.expiry", "CARD_EXPIRED") in _field_codes(error)


@pytest.mark.parametrize("cvc", ["12", "1234", "12a"])
def test_invalid_cvc(service, cvc: str) -> None:
    error = _error(service, card_body(cvc=cvc))

    assert ("card.cvc", "CARD_CVC_INVALID") in _field_codes(error)


@pytest.mark.parametrize(
    ("reference", "code"),
    [
        ("ABC", "TOO_SHORT"),
        ("  ab  ", "TOO_SHORT"),
        ("A" * 41, "TOO_LONG"),
    ],
)
def test_invalid_transfer_references(service, reference: str, code: str) -> None:
    error = _error(service, transfer_body(reference=reference))

    assert ("reference", code) in _field_codes(error)


@pytest.mark.parametrize("reference", ["ab\u0000cd", "ab\tcd", "ab\ncd", "\u0000abcd"])
def test_transfer_references_with_control_characters_are_rejected(service, reference: str) -> None:
    error = _error(service, transfer_body(reference=reference))

    assert ("reference", "INVALID_FORMAT") in _field_codes(error)


@pytest.mark.parametrize("reference", ["ABCD", "A" * 40])
def test_valid_transfer_references(service, reference: str) -> None:
    outcome = service.pay(1, "key-1", transfer_body(reference=reference), None)

    assert outcome.response.status_code == 201


def test_unknown_fields_are_rejected(service) -> None:
    error = _error(service, {"method": "cash", "amount": "327.80", "extra": 1})

    assert ("extra", "INVALID_FORMAT") in _field_codes(error)


def test_a_card_with_a_transfer_is_rejected(service) -> None:
    body = transfer_body()
    body["card"] = {"number": "4242 4242 4242 4242", "expiry": "12/30", "cvc": "123"}

    error = _error(service, body)

    assert ("card", "INVALID_FORMAT") in _field_codes(error)


def test_a_missing_card_object_is_required(service) -> None:
    error = _error(service, {"method": "card", "amount": "327.80"})

    assert ("card", "REQUIRED") in _field_codes(error)


def test_a_null_card_object_is_required(service) -> None:
    error = _error(service, {"method": "card", "amount": "327.80", "card": None})

    assert ("card", "REQUIRED") in _field_codes(error)


def test_a_body_that_is_not_an_object_is_invalid(service) -> None:
    for body in ([], None, "text", b"bytes", 3):
        error = _error(service, body)
        assert _field_codes(error) == [("body", "INVALID_FORMAT")]


def test_a_non_finite_amount_never_returns_a_server_error(service) -> None:
    body = {"method": "cash", "amount": float("nan")}

    error = _error(service, body)

    assert ("amount", "INVALID_FORMAT") in _field_codes(error)


def test_a_non_finite_amount_is_rejected_even_with_a_stored_key(service) -> None:
    service.pay(1, "key-1", card_body(), None)

    error = _error(service, {"method": "cash", "amount": float("nan")})

    assert error.code == "VALIDATION_ERROR"
    assert ("amount", "INVALID_FORMAT") in _field_codes(error)


def test_a_deep_body_never_returns_a_server_error(service) -> None:
    body: dict[str, object] = {"method": "cash", "amount": "327.80"}
    nested: dict[str, object] = {}
    current = nested
    for _ in range(900):
        child: dict[str, object] = {}
        current["nested"] = child
        current = child
    body["deep"] = nested

    error = _error(service, body)

    assert error.code == "VALIDATION_ERROR"


def test_a_stale_version_on_a_paid_invoice_conflicts_first(service) -> None:
    with pytest.raises(ApiError) as error:
        service.pay(2, "key-1", card_body(amount="197.97", number="4242 4242 4242 4242"), 9)

    assert error.value.status == 409
    assert error.value.code == "VERSION_CONFLICT"


def test_pay_unknown_invoice_is_not_found(service) -> None:
    with pytest.raises(ApiError) as error:
        service.pay(99, "key-1", card_body(), None)

    assert error.value.status == 404


def test_a_cash_payment_is_rendered_without_card_data(service) -> None:
    outcome = service.pay(1, "key-1", cash_body(), None)

    assert outcome.response.body["payment"]["method"] == "cash"
    assert outcome.response.body["payment"]["card_last4"] is None
    assert outcome.response.body["payment"]["reference"] is None
    assert outcome.response.body["payment"]["status"] == PaymentStatus.APPROVED.value


def test_no_log_record_contains_the_card_number_or_the_cvc(
    service,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        service.pay(1, "key-1", card_body(), None)

    assert "4242 4242 4242 4242" not in caplog.text
    assert "4242424242424242" not in caplog.text
    assert "cvc" not in caplog.text


def test_list_rejects_an_invalid_order_id_type(service) -> None:
    with pytest.raises(ApiError) as error:
        service.list_invoices(1, None, None, "1")  # type: ignore[arg-type]

    assert _field_codes(error.value) == [("order_id", "INVALID_FORMAT")]


def test_list_rejects_a_control_character_and_ignores_blank_queries(service) -> None:
    with pytest.raises(ApiError) as error:
        service.list_invoices(1, "acme\u0000", None, None)
    assert _field_codes(error.value) == [("q", "INVALID_FORMAT")]

    items, total = service.list_invoices(1, "   ", None, None)
    assert total == 3
    assert len(items) == 3


def test_get_and_issue_reject_an_out_of_range_id(service) -> None:
    with pytest.raises(ApiError) as missing:
        service.get(0)
    assert missing.value.status == 404

    with pytest.raises(ApiError) as order:
        service.issue(2_147_483_648, None)
    assert order.value.status == 404


def test_issue_rejects_an_out_of_range_version(service) -> None:
    with pytest.raises(ApiError) as error:
        service.issue(2, 2_147_483_648)

    assert _field_codes(error.value) == [("version", "OUT_OF_RANGE")]


@pytest.mark.parametrize("method", ["bitcoin", 3, ["card"]])
def test_an_unsupported_method_is_invalid(service, method: object) -> None:
    error = _error(service, {"method": method, "amount": "1.00"})

    assert ("method", "INVALID_FORMAT") in _field_codes(error)


def test_a_card_that_is_not_an_object_is_invalid(service) -> None:
    error = _error(service, {"method": "card", "amount": "1.00", "card": "4242"})

    assert _field_codes(error) == [("card", "INVALID_FORMAT")]


def test_each_card_field_is_validated(service) -> None:
    error = _error(
        service,
        {"method": "card", "amount": "1.00", "card": {"number": "4242 4242 4242 4242"}},
    )

    assert _field_codes(error) == [
        ("card.expiry", "REQUIRED"),
        ("card.cvc", "REQUIRED"),
    ]

    error = _error(
        service,
        {
            "method": "card",
            "amount": "1.00",
            "card": {"number": 4242, "expiry": 1230, "cvc": 123, "holder": "Ana"},
        },
    )

    assert _field_codes(error) == [
        ("card.number", "INVALID_FORMAT"),
        ("card.expiry", "INVALID_FORMAT"),
        ("card.cvc", "INVALID_FORMAT"),
        ("card.holder", "INVALID_FORMAT"),
    ]


def test_a_reference_is_rejected_outside_a_transfer(service) -> None:
    error = _error(service, {"method": "cash", "amount": "1.00", "reference": "TRF-1"})

    assert _field_codes(error) == [("reference", "INVALID_FORMAT")]


def test_a_transfer_needs_a_string_reference(service) -> None:
    error = _error(service, {"method": "transfer", "amount": "1.00"})
    assert _field_codes(error) == [("reference", "REQUIRED")]

    error = _error(service, {"method": "transfer", "amount": "1.00", "reference": 42})
    assert _field_codes(error) == [("reference", "INVALID_FORMAT")]


class MissingCustomerRepository:
    def get(self, id: int) -> None:
        return None


def test_an_invoice_for_a_deleted_customer_skips_the_notice(
    store,
    orders,
    clock,
    mailer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = InvoiceService(store, orders, MissingCustomerRepository(), clock, mailer, SECRET)  # type: ignore[arg-type]

    with caplog.at_level(logging.WARNING):
        invoice = service.issue(2, 1)

    assert invoice.number == "FAC-0004"
    assert mailer.calls == []
    assert "customer 2 not found" in caplog.text


def test_list_rejects_an_out_of_range_page_and_order_id_and_a_long_query(service) -> None:
    with pytest.raises(ApiError) as page:
        service.list_invoices(0, None, None, None)
    assert _field_codes(page.value) == [("page", "OUT_OF_RANGE")]

    with pytest.raises(ApiError) as order:
        service.list_invoices(1, None, None, 0)
    assert _field_codes(order.value) == [("order_id", "OUT_OF_RANGE")]

    with pytest.raises(ApiError) as query:
        service.list_invoices(1, "a" * 101, None, None)
    assert _field_codes(query.value) == [("q", "TOO_LONG")]

    items, total = service.list_invoices(1, "FAC-0001", None, 3)
    assert total == 1
    assert items[0].number == "FAC-0001"


class VanishingStore:
    """An invoice store whose invoice disappears between the read and the payment."""

    def __init__(self, inner: InMemoryInvoiceStore) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    def register_payment(self, *args: object, **kwargs: object) -> object:
        from app.modules.invoices.ports import InvoiceNotFound

        raise InvoiceNotFound()


def test_a_payment_on_an_invoice_that_vanished_is_not_found(
    service, store, orders, customers, clock, mailer
) -> None:
    vanishing = InvoiceService(VanishingStore(store), orders, customers, clock, mailer, SECRET)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        vanishing.pay(1, "key-1", card_body(), None)

    assert error.value.status == 404
    assert error.value.code == "NOT_FOUND"
