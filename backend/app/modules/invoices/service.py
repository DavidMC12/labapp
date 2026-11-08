"""Invoice service: validation, money views and port error translation."""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain.money import quantize_money
from app.domain.payments import Card, parse_card, validate_transfer_reference
from app.errors import ERROR_MESSAGES, NOT_FOUND, ApiError, problem_response
from app.infra.clock import Clock
from app.modules.customers.ports import CustomerRepository
from app.modules.customers.validation import has_control_character
from app.modules.invoices import rules, schemas
from app.modules.invoices.mail import Mailer
from app.modules.invoices.models import (
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentAttempt,
    PaymentOutcome,
    PaymentStatus,
    StoredResponse,
)
from app.modules.invoices.ports import InvoiceNotFound, InvoiceStore
from app.modules.orders.ports import OrderNotFound, VersionConflict
from app.security.idempotency import fingerprint, redact_card, validate_key

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
MAX_PAGE = 1_000_000
MAX_ID = 2_147_483_647
MAX_QUERY_LENGTH = 100

VALIDATION_DETAIL = "Revisa los datos ingresados."
VERSION_CONFLICT_MESSAGE = "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."

_ALLOWED_METHODS = frozenset({"card", "transfer", "cash"})
_CARD_FIELDS = ("number", "expiry", "cvc")
_AMOUNT_PATTERN = re.compile(r"[0-9]{1,10}(\.[0-9]{1,2})?")


def _error(field: str, code: str, message: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": message}


def _required(field: str) -> dict[str, str]:
    return _error(field, "REQUIRED", "Este campo es obligatorio.")


def _invalid_format(field: str) -> dict[str, str]:
    return _error(field, "INVALID_FORMAT", "El formato no es válido.")


def _out_of_range(field: str, minimum: object, maximum: object) -> dict[str, str]:
    return _error(field, "OUT_OF_RANGE", f"El valor debe estar entre {minimum} y {maximum}.")


def _too_long(field: str, maximum: int) -> dict[str, str]:
    return _error(field, "TOO_LONG", f"Debe tener como máximo {maximum} caracteres.")


def _raise_validation(errors: list[dict[str, str]]) -> None:
    raise ApiError(422, "VALIDATION_ERROR", VALIDATION_DETAIL, errors=errors)


def _not_found() -> ApiError:
    return ApiError(404, NOT_FOUND, ERROR_MESSAGES[NOT_FOUND])


def _version_errors(value: object) -> list[dict[str, str]]:
    if value is None:
        return [_required("version")]
    if not isinstance(value, int) or isinstance(value, bool):
        return [_invalid_format("version")]
    if not 1 <= value <= MAX_ID:
        return [_out_of_range("version", 1, MAX_ID)]
    return []


def _query_order_id_errors(value: object | None) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, int) or isinstance(value, bool):
        return [_invalid_format("order_id")]
    if not 1 <= value <= MAX_ID:
        return [_out_of_range("order_id", 1, MAX_ID)]
    return []


def _normalize_query(query: str | None) -> tuple[str | None, dict[str, str] | None]:
    if query is None:
        return None, None
    if has_control_character(query):
        return None, _invalid_format("q")
    trimmed = query.strip()
    if not trimmed:
        return None, None
    if len(trimmed) > MAX_QUERY_LENGTH:
        return None, _too_long("q", MAX_QUERY_LENGTH)
    return trimmed, None


class InvoiceService:
    """Invoice and payment operations over the invoice store port."""

    def __init__(
        self,
        store: InvoiceStore,
        orders: object,
        customers: CustomerRepository,
        clock: Clock,
        mailer: Mailer,
        secret: bytes,
    ) -> None:
        self._store = store
        self._orders = orders
        self._customers = customers
        self._clock = clock
        self._mailer = mailer
        self._secret = secret

    def list_invoices(
        self,
        page: int,
        query: str | None,
        status: InvoiceStatus | None,
        order_id: int | None,
    ) -> tuple[list[Invoice], int]:
        """Validate the list parameters and return one page plus the total."""
        errors: list[dict[str, str]] = []
        if not 1 <= page <= MAX_PAGE:
            errors.append(_out_of_range("page", 1, MAX_PAGE))
        errors.extend(_query_order_id_errors(order_id))
        normalized_query, query_error = _normalize_query(query)
        if query_error is not None:
            errors.append(query_error)
        if errors:
            _raise_validation(errors)

        return self._store.list_invoices(
            query=normalized_query,
            status=status,
            order_id=order_id,
            page=page,
            page_size=PAGE_SIZE,
        )

    def get(self, id: int) -> Invoice:
        """Return one invoice or raise the 404 problem."""
        if not 1 <= id <= MAX_ID:
            raise _not_found()
        invoice = self._store.get_invoice(id)
        if invoice is None:
            raise _not_found()
        return invoice

    def issue(self, order_id: int, expected_order_version: int | None) -> Invoice:
        """Issue the invoice of a confirmed order."""
        if not 1 <= order_id <= MAX_ID:
            raise _not_found()
        if expected_order_version is not None:
            errors = _version_errors(expected_order_version)
            if errors:
                _raise_validation(errors)
        try:
            invoice = self._store.issue_invoice(
                order_id,
                expected_order_version,
                self._clock.now(),
            )
        except (OrderNotFound, InvoiceNotFound) as error:
            raise _not_found() from error
        except VersionConflict as error:
            raise ApiError(409, "VERSION_CONFLICT", VERSION_CONFLICT_MESSAGE) from error
        self._send_notice(invoice)
        return invoice

    def pay(
        self,
        invoice_id: int,
        key: str | None,
        body: object,
        expected_version: int | None,
    ) -> PaymentOutcome:
        """Validate and register a payment, replaying a known key first."""
        invoice = self.get(invoice_id)
        now = self._clock.now()

        early = self._early_replay(invoice.id, key, body, now)
        if early is not None:
            return early

        errors: list[dict[str, str]] = []
        validated_key = self._validate_key_into(errors, key)
        attempt = self._validate_body(body, errors, now.date())
        if expected_version is not None:
            errors.extend(_version_errors(expected_version))
        if errors:
            _raise_validation(errors)
        assert validated_key is not None
        assert attempt is not None

        body_fingerprint = self._fingerprint_or_none(body)
        if body_fingerprint is None:
            _raise_validation([_invalid_format("body")])

        try:
            return self._store.register_payment(
                invoice.id,
                key=validated_key,
                fingerprint=body_fingerprint,
                expected_version=expected_version,
                attempt=attempt,
                respond=self._respond,
                now=now,
            )
        except (InvoiceNotFound, OrderNotFound) as error:
            raise _not_found() from error
        except VersionConflict as error:
            raise ApiError(409, "VERSION_CONFLICT", VERSION_CONFLICT_MESSAGE) from error

    def _early_replay(
        self,
        invoice_id: int,
        key: str | None,
        body: object,
        now: datetime,
    ) -> PaymentOutcome | None:
        if not key:
            return None
        try:
            validate_key(key)
        except ApiError:
            return None
        body_fingerprint = self._fingerprint_or_none(body)
        if body_fingerprint is None:
            return None
        stored = self._store.find_key(invoice_id, key, now)
        if stored is None:
            return None
        if stored.fingerprint != body_fingerprint:
            raise rules.key_reused()
        return PaymentOutcome(stored.response, True)

    def _validate_key_into(
        self,
        errors: list[dict[str, str]],
        key: str | None,
    ) -> str | None:
        if not key:
            validate_key(key)
            raise AssertionError("validate_key must raise for a missing key")
        try:
            return validate_key(key)
        except ApiError as error:
            errors.extend(error.errors or [])
            return None

    def _validate_body(
        self,
        body: object,
        errors: list[dict[str, str]],
        today: date,
    ) -> PaymentAttempt | None:
        if not isinstance(body, dict):
            errors.append(_invalid_format("body"))
            return None

        known = {"method", "amount", "card", "reference"}
        for field in body:
            if field not in known:
                errors.append(_invalid_format(field))

        method = body.get("method")
        if method is None:
            errors.append(_required("method"))
        elif not isinstance(method, str) or method not in _ALLOWED_METHODS:
            errors.append(_invalid_format("method"))

        amount = body.get("amount")
        if amount is None:
            errors.append(_required("amount"))
        elif not isinstance(amount, str) or _AMOUNT_PATTERN.fullmatch(amount) is None:
            errors.append(_invalid_format("amount"))

        parsed_card = self._validate_card(body, method, errors, today)
        reference = self._validate_reference(body, method, errors)
        if errors:
            return None

        assert isinstance(method, str)
        assert isinstance(amount, str)
        return PaymentAttempt(
            method=method,
            amount=quantize_money(Decimal(amount)),
            card_last4=parsed_card.last4 if parsed_card is not None else None,
            reference=reference,
        )

    def _validate_card(
        self,
        body: dict[str, Any],
        method: object,
        errors: list[dict[str, str]],
        today: date,
    ) -> Card | None:
        if method != "card":
            if "card" in body:
                errors.append(_invalid_format("card"))
            return None
        card = body.get("card")
        if card is None:
            errors.append(_required("card"))
            return None
        if not isinstance(card, dict):
            errors.append(_invalid_format("card"))
            return None

        card_errors: list[dict[str, str]] = []
        for name in _CARD_FIELDS:
            value = card.get(name)
            if value is None:
                card_errors.append(_required(f"card.{name}"))
            elif not isinstance(value, str):
                card_errors.append(_invalid_format(f"card.{name}"))
        for name in card:
            if name not in _CARD_FIELDS:
                card_errors.append(_invalid_format(f"card.{name}"))
        if card_errors:
            errors.extend(card_errors)
            return None

        try:
            return parse_card(card["number"], card["expiry"], card["cvc"], today)
        except ApiError as error:
            errors.extend(error.errors or [])
            return None

    def _validate_reference(
        self,
        body: dict[str, Any],
        method: object,
        errors: list[dict[str, str]],
    ) -> str | None:
        if method != "transfer":
            if "reference" in body:
                errors.append(_invalid_format("reference"))
            return None
        reference = body.get("reference")
        if reference is None:
            errors.append(_required("reference"))
            return None
        if not isinstance(reference, str):
            errors.append(_invalid_format("reference"))
            return None
        trimmed = reference.strip()
        if has_control_character(trimmed):
            errors.append(_invalid_format("reference"))
            return None
        try:
            validate_transfer_reference(trimmed)
        except ApiError as error:
            errors.extend(error.errors or [])
            return None
        return trimmed

    def _fingerprint_or_none(self, body: object) -> str | None:
        try:
            redacted = redact_card(body) if isinstance(body, dict) else body
            return fingerprint(self._secret, redacted)
        except (ValueError, TypeError, RecursionError):
            return None

    def _send_notice(self, invoice: Invoice) -> None:
        try:
            customer = self._customers.get(invoice.customer_id)
            if customer is None:
                logger.warning(
                    "Could not send the notice of invoice %s: customer %s not found",
                    invoice.number,
                    invoice.customer_id,
                )
                return
            self._mailer.invoice_issued(customer.email, invoice.number)
        except Exception:
            logger.warning(
                "Could not send the notice of invoice %s",
                invoice.number,
                exc_info=True,
            )

    def _respond(self, payment: Payment, invoice: Invoice) -> StoredResponse:
        if payment.status == PaymentStatus.APPROVED:
            result = schemas.PaymentResult(
                payment=self.payment_out(payment),
                invoice=self.invoice_out(invoice),
            )
            return StoredResponse(201, result.model_dump(mode="json"))
        if payment.status == PaymentStatus.DECLINED:
            error = rules.payment_declined(payment.id, payment.reason)
        else:
            error = rules.gateway_unavailable(payment.id, payment.reason)
        return StoredResponse(error.status, self._problem_body(error))

    @staticmethod
    def _problem_body(error: ApiError) -> dict[str, object]:
        response = problem_response(
            "",
            status=error.status,
            code=error.code,
            detail=error.detail,
            title=error.title,
            extra=error.extra,
        )
        return json.loads(response.body)

    def invoice_out(self, invoice: Invoice) -> schemas.Invoice:
        return schemas.Invoice(
            id=invoice.id,
            number=invoice.number,
            status=invoice.status,
            order_id=invoice.order_id,
            order_number=invoice.order_number,
            customer=schemas.InvoiceCustomer(
                id=invoice.customer_id,
                name=invoice.customer_name,
                tax_id=invoice.customer_tax_id,
                address=invoice.customer_address,
            ),
            lines=[
                schemas.InvoiceLine(
                    id=line.id,
                    product_id=line.product_id,
                    sku=line.sku,
                    name=line.name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_total=quantize_money(line.unit_price * line.quantity),
                )
                for line in invoice.lines
            ],
            subtotal=invoice.subtotal,
            tax_rate=invoice.tax_rate,
            tax=invoice.tax,
            total=invoice.total,
            payments=[self.payment_out(payment) for payment in invoice.payments],
            version=invoice.version,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
        )

    @staticmethod
    def payment_out(payment: Payment) -> schemas.Payment:
        return schemas.Payment(
            id=payment.id,
            method=payment.method,
            status=payment.status,
            amount=payment.amount,
            reference=payment.reference,
            card_last4=payment.card_last4,
            reason=payment.reason,
            created_at=payment.created_at,
        )
