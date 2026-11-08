"""The HTTP status and Spanish message of every SPEC error table row."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.labels import ORDER_STATUS_LABELS
from app.domain.orders import (
    DraftLineInput,
    OrderAction,
    OrderStatus,
    ProductStock,
    check_stock,
    ensure_confirmable,
    next_status,
    validate_draft_lines,
)
from app.domain.permissions import Action, Role, require
from app.errors import (
    _HTTP_ERRORS,
    ApiError,
    _handle_database_error,
    _handle_http_exception,
    _handle_validation_error,
)
from app.guards.request_controls import INJECTED_FAULT, INJECTED_FAULT_DETAIL
from app.infra.clock import SystemClock
from app.modules.auth.adapters.memory import InMemorySessionStore, InMemoryUserRepository
from app.modules.auth.models import Session
from app.modules.auth.seed import seed_users
from app.modules.auth.service import SESSION_IDLE_TIMEOUT, AuthService
from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.customers.service import CustomerService
from app.modules.invoices import rules as invoice_rules
from app.modules.orders.ports import CustomerInactive, OrderNotEditable, VersionConflict
from app.modules.orders.service import OrderService
from app.modules.testcontrols.routes import _run_reset
from app.modules.testcontrols.validation import MAX_STATUS, MIN_STATUS
from app.security.idempotency import validate_key
from app.security.origin import check_origin
from app.security.ratelimit import rate_limited_error

from . import support


@dataclass(frozen=True)
class _Problem:
    status: int
    code: str
    detail: str


Factory = Callable[[], ApiError | _Problem]


def _raises(action: Callable[[], object]) -> ApiError:
    with pytest.raises(ApiError) as info:
        action()
    return info.value


class _RaisingStore:
    """A store that raises the port error the service must translate."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def create_order(self, customer_id: int, now: object) -> None:
        raise self._error

    def set_customer(
        self,
        id: int,
        customer_id: int,
        expected_version: int | None,
        now: object,
    ) -> None:
        raise self._error


def _order_service(error: Exception) -> OrderService:
    return OrderService(
        _RaisingStore(error),
        SystemClock(),
        InMemoryCustomerRepository(),
    )


def _never(stored: str, presented: str) -> bool:
    return False


def _auth_parts() -> tuple[AuthService, InMemorySessionStore, SystemClock]:
    users = InMemoryUserRepository(seed_users("test-hash"))
    sessions = InMemorySessionStore()
    clock = SystemClock()
    service = AuthService(
        users,
        sessions,
        clock,
        dummy_hash="dummy-hash",
        verify=_never,
    )
    return service, sessions, clock


def _request() -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(request_id="docs-test"),
        method="GET",
        url=SimpleNamespace(path="/api/test"),
    )


def _from_response(response: object) -> _Problem:
    body = json.loads(response.body)  # type: ignore[attr-defined]
    return _Problem(body["status"], body["code"], body["detail"])


class _Validation(Exception):
    def __init__(self, errors: list[dict[str, object]]) -> None:
        self._errors = errors

    def errors(self) -> list[dict[str, object]]:
        return self._errors


def _validation_problem(errors: list[dict[str, object]]) -> _Problem:
    response = asyncio.run(_handle_validation_error(_request(), _Validation(errors)))
    return _from_response(response)


def _http_problem(code: str) -> _Problem:
    for status, (mapped, _) in _HTTP_ERRORS.items():
        if mapped == code:
            response = asyncio.run(
                _handle_http_exception(_request(), StarletteHTTPException(status_code=status))
            )
            return _from_response(response)
    raise AssertionError(f"{code} is not a common error of app.errors")


def _invalid_credentials() -> object:
    service, _, _ = _auth_parts()
    return _raises(lambda: service.login("nobody@example.test", "password"))


def _unauthenticated() -> object:
    service, _, _ = _auth_parts()
    return _raises(lambda: service.authenticate(None))


def _session_expired() -> object:
    service, sessions, clock = _auth_parts()
    old = clock.now() - SESSION_IDLE_TIMEOUT - timedelta(minutes=1)
    token = "token"
    sessions.create(
        Session(
            token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            user_id=1,
            created_at=old,
            last_seen_at=old,
        )
    )
    return _raises(lambda: service.authenticate(token))


def _service_busy() -> object:
    service, _, _ = _auth_parts()
    service._hash_load = service._max_hash_load
    return _raises(lambda: service.login("nobody@example.test", "password"))


def _customer_email_taken() -> object:
    service = CustomerService(InMemoryCustomerRepository(seed_customers()), SystemClock())
    return _raises(lambda: service.create({"name": "Acme Copia", "email": "acme@example.test"}))


def _customer_inactive() -> object:
    return _raises(lambda: _order_service(CustomerInactive()).create(1))


def _order_not_editable() -> object:
    return _raises(lambda: _order_service(OrderNotEditable()).set_customer(1, 2, 1))


def _version_conflict() -> object:
    return _raises(lambda: _order_service(VersionConflict()).set_customer(1, 2, 1))


def _order_duplicate_product() -> object:
    return _raises(lambda: validate_draft_lines([DraftLineInput(1, 1), DraftLineInput(1, 2)]))


def _order_too_many_lines() -> object:
    lines = [DraftLineInput(product_id, 1) for product_id in range(1, 12)]
    return _raises(lambda: validate_draft_lines(lines))


def _order_empty() -> object:
    return _raises(lambda: ensure_confirmable([]))


def _insufficient_stock() -> object:
    return _raises(
        lambda: check_stock(
            [DraftLineInput(1, 5)],
            {1: ProductStock(sku="KB-100", name="Teclado USB", available=2)},
        )
    )


def _invalid_transition() -> object:
    return _raises(lambda: next_status(OrderStatus.DRAFT, OrderAction.SHIP))


def _forbidden() -> object:
    return _raises(lambda: require(Role.SALES, Action.CHANGE_TAX_RATE))


def _csrf_origin_mismatch() -> object:
    return _raises(lambda: check_origin("POST", "http://evil.example", "http://localhost:3000"))


def _rate_limited() -> object:
    return rate_limited_error(1)


def _idempotency_key_required() -> object:
    return _raises(lambda: validate_key(None))


def _injected_fault() -> object:
    return _Problem(400, INJECTED_FAULT, INJECTED_FAULT_DETAIL)


def _reset_conflict() -> object:
    def conflict() -> None:
        raise IntegrityError("statement", {}, Exception("conflict"))

    return _raises(lambda: _run_reset(conflict))


def _lock_timeout() -> object:
    try:
        raise psycopg.errors.LockNotAvailable("lock timeout")
    except psycopg.errors.LockNotAvailable as error:
        response = asyncio.run(_handle_database_error(_request(), error))
    return _from_response(response)


FACTORIES: dict[str, tuple[Factory, dict[str, str]]] = {
    "INVALID_CREDENTIALS": (_invalid_credentials, {}),
    "UNAUTHENTICATED": (_unauthenticated, {}),
    "SESSION_EXPIRED": (_session_expired, {}),
    "CSRF_ORIGIN_MISMATCH": (_csrf_origin_mismatch, {}),
    "RATE_LIMITED": (_rate_limited, {}),
    "CUSTOMER_EMAIL_TAKEN": (_customer_email_taken, {}),
    "CUSTOMER_INACTIVE": (_customer_inactive, {}),
    "CUSTOMER_TAX_ID_REQUIRED": (invoice_rules.customer_tax_id_required, {}),
    "ORDER_DUPLICATE_PRODUCT": (_order_duplicate_product, {}),
    "ORDER_TOO_MANY_LINES": (_order_too_many_lines, {}),
    "ORDER_EMPTY": (_order_empty, {}),
    "ORDER_NOT_EDITABLE": (_order_not_editable, {}),
    "INSUFFICIENT_STOCK": (
        _insufficient_stock,
        {"product": "Teclado USB", "available": "2", "requested": "5"},
    ),
    "VERSION_CONFLICT": (_version_conflict, {}),
    "ORDER_NOT_INVOICEABLE": (invoice_rules.order_not_invoiceable, {}),
    "INVOICE_ALREADY_EXISTS": (invoice_rules.invoice_already_exists, {}),
    "INVOICE_NOT_PAYABLE": (invoice_rules.invoice_not_payable, {}),
    "PAYMENT_AMOUNT_MISMATCH": (invoice_rules.amount_mismatch, {}),
    "PAYMENT_DECLINED": (lambda: invoice_rules.payment_declined(5, "CARD_DECLINED"), {}),
    "PAYMENT_GATEWAY_UNAVAILABLE": (
        lambda: invoice_rules.gateway_unavailable(5, "GATEWAY_UNAVAILABLE"),
        {},
    ),
    "IDEMPOTENCY_KEY_REQUIRED": (_idempotency_key_required, {}),
    "IDEMPOTENCY_KEY_REUSED": (invoice_rules.key_reused, {}),
    "NOT_FOUND": (lambda: _http_problem("NOT_FOUND"), {}),
    "PAYLOAD_TOO_LARGE": (lambda: _http_problem("PAYLOAD_TOO_LARGE"), {}),
    "INTERNAL_ERROR": (lambda: _http_problem("INTERNAL_ERROR"), {}),
    "FORBIDDEN": (_forbidden, {}),
    "VALIDATION_ERROR": (
        lambda: _validation_problem([{"type": "missing", "loc": ("body", "name")}]),
        {},
    ),
    "INVALID_TRANSITION": (
        _invalid_transition,
        {
            "from": ORDER_STATUS_LABELS[OrderStatus.DRAFT.value],
            "to": ORDER_STATUS_LABELS[OrderStatus.SHIPPED.value],
        },
    ),
    "MALFORMED_JSON": (lambda: _validation_problem([{"type": "json_invalid"}]), {}),
    "LOCK_TIMEOUT": (_lock_timeout, {}),
    "SERVICE_BUSY": (_service_busy, {}),
    "METHOD_NOT_ALLOWED": (lambda: _http_problem("METHOD_NOT_ALLOWED"), {}),
    "INJECTED_FAULT": (_injected_fault, {}),
    "RESET_CONFLICT": (_reset_conflict, {}),
}

ROWS = support.spec_error_rows()


def test_the_document_does_not_contradict_itself() -> None:
    seen: dict[str, tuple[str, str]] = {}
    for row in ROWS:
        key = (row["HTTP"], row["Message (es)"])
        assert seen.setdefault(row["Code"], key) == key, row["Code"]


@pytest.mark.parametrize("row", ROWS, ids=[row["Code"] for row in ROWS])
def test_http_status_and_spanish_message_match_the_code(row: dict[str, str]) -> None:
    code = row["Code"]
    assert code in FACTORIES, f"no factory for the document code {code}"
    factory, substitutions = FACTORIES[code]

    problem = factory()

    assert problem.code == code  # type: ignore[attr-defined]
    if row["HTTP"] == "400 to 599 as configured":
        assert code == INJECTED_FAULT
        assert row["HTTP"] == f"{MIN_STATUS} to {MAX_STATUS} as configured"
    else:
        assert problem.status == int(row["HTTP"])  # type: ignore[attr-defined]

    expected = row["Message (es)"].format(**substitutions)
    assert problem.detail == expected  # type: ignore[attr-defined]
