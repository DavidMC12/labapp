"""Order service: validation, view building and port error translation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import NoReturn

from app.domain.csv_export import (
    EXPORT_PAGE_SIZE,
    CsvExport,
    csv_export_filename,
    write_csv,
)
from app.domain.money import (
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    LineInput,
    compute_totals,
    quantize_money,
)
from app.domain.orders import (
    MAX_LINE_QUANTITY,
    MIN_LINE_QUANTITY,
    OrderAction,
    OrderStatus,
)
from app.domain.sorting import SortSpec, parse_sort
from app.errors import ERROR_MESSAGES, NOT_FOUND, ApiError
from app.infra.clock import Clock
from app.modules.customers.models import Customer
from app.modules.customers.ports import CustomerRepository
from app.modules.customers.validation import has_control_character
from app.modules.orders.models import Order, OrderLine, Product
from app.modules.orders.ports import (
    CustomerInactive,
    CustomerNotFound,
    LineNotFound,
    OrderNotEditable,
    OrderNotFound,
    OrderStore,
    ProductNotFound,
    VersionConflict,
)

PAGE_SIZE = 20
MAX_PAGE = 1_000_000
MAX_ID = 2_147_483_647
MAX_QUERY_LENGTH = 100
ORDER_SORT_FIELDS = ("created_at", "number", "customer")
PRODUCT_SORT_FIELDS = ("id", "sku", "name", "price", "stock")
ORDER_COLUMNS = (
    "id",
    "number",
    "status",
    "customer_id",
    "customer_name",
    "subtotal",
    "tax_rate",
    "tax",
    "total",
    "invoice_id",
    "created_at",
    "updated_at",
)

VALIDATION_DETAIL = "Revisa los datos ingresados."
VERSION_CONFLICT_MESSAGE = "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."
ORDER_NOT_EDITABLE_MESSAGE = "Solo se puede editar un pedido en borrador."
CUSTOMER_INACTIVE_MESSAGE = "El cliente está desactivado y no puede recibir pedidos."
REFERENCE_NOT_FOUND_MESSAGE = "El registro indicado no existe."

_TAX_RATE_PATTERN = re.compile(r"[0-9]{1,3}(\.[0-9]{1,2})?")
_STORE_ERRORS = (
    OrderNotFound,
    LineNotFound,
    ProductNotFound,
    CustomerNotFound,
    VersionConflict,
    OrderNotEditable,
    CustomerInactive,
)


@dataclass(frozen=True)
class OrderLineView:
    """A line with its computed total."""

    line: OrderLine
    line_total: Decimal


@dataclass(frozen=True)
class OrderView:
    """Everything the order response needs, already computed."""

    order: Order
    customer: Customer
    lines: tuple[OrderLineView, ...]
    tax_rate: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class OrderSummaryView:
    """One row of the order list."""

    order: Order
    customer_name: str
    subtotal: Decimal
    tax_rate: Decimal
    tax: Decimal
    total: Decimal


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


def _reference_not_found(field: str) -> dict[str, str]:
    return _error(field, "REFERENCE_NOT_FOUND", REFERENCE_NOT_FOUND_MESSAGE)


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


def _body_id_errors(value: object | None, field: str) -> list[dict[str, str]]:
    if value is None:
        return [_required(field)]
    if not isinstance(value, int) or isinstance(value, bool):
        return [_invalid_format(field)]
    if not 1 <= value <= MAX_ID:
        return [_reference_not_found(field)]
    return []


def _query_customer_id_errors(value: object | None) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, int) or isinstance(value, bool):
        return [_invalid_format("customer_id")]
    if not 1 <= value <= MAX_ID:
        return [_out_of_range("customer_id", 1, MAX_ID)]
    return []


def _quantity_errors(value: object | None) -> list[dict[str, str]]:
    if value is None:
        return [_required("quantity")]
    if not isinstance(value, int) or isinstance(value, bool):
        return [_invalid_format("quantity")]
    if not MIN_LINE_QUANTITY <= value <= MAX_LINE_QUANTITY:
        return [_out_of_range("quantity", MIN_LINE_QUANTITY, MAX_LINE_QUANTITY)]
    return []


def _tax_rate_error(value: object | None) -> dict[str, str] | None:
    if value is None:
        return _required("tax_rate")
    if not isinstance(value, str):
        return _invalid_format("tax_rate")
    if _TAX_RATE_PATTERN.fullmatch(value) is None:
        return _invalid_format("tax_rate")
    rate = Decimal(value)
    if rate < MIN_TAX_RATE or rate > MAX_TAX_RATE:
        return _out_of_range("tax_rate", "0", "100")
    return None


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


class OrderService:
    """Order operations over the store port."""

    def __init__(
        self,
        store: OrderStore,
        clock: Clock,
        customers: CustomerRepository,
    ) -> None:
        self._store = store
        self._clock = clock
        self._customers = customers

    def list_products(
        self,
        sort: str | None = None,
        direction: str | None = None,
    ) -> list[Product]:
        """Return the catalog following the requested sort."""
        sort_spec = parse_sort(
            sort,
            direction,
            allowed=PRODUCT_SORT_FIELDS,
            default="id",
        )
        return self._store.list_products(sort=sort_spec)

    def get_tax_rate(self) -> Decimal:
        """Return the current tax rate."""
        return self._store.get_tax_rate()

    def set_tax_rate(self, value: str | None) -> Decimal:
        """Validate and store the tax rate, returning it with two decimals."""
        error = _tax_rate_error(value)
        if error is not None:
            _raise_validation([error])
        assert value is not None
        rate = quantize_money(Decimal(value))
        self._store.set_tax_rate(rate)
        return rate

    def list_orders(
        self,
        page: int,
        query: str | None,
        status: OrderStatus | None,
        customer_id: int | None,
        sort: str | None = None,
        direction: str | None = None,
    ) -> tuple[list[OrderSummaryView], int]:
        """Validate the list parameters and return one page plus the total."""
        normalized_query, sort_spec = self._list_params(page, query, customer_id, sort, direction)
        items, total = self._store.list_orders(
            query=normalized_query,
            status=status,
            customer_id=customer_id,
            page=page,
            page_size=PAGE_SIZE,
            sort=sort_spec,
        )
        return [self._summary(order, customer_name) for order, customer_name in items], total

    def export_orders(
        self,
        query: str | None,
        status: OrderStatus | None,
        customer_id: int | None,
        sort: str | None = None,
        direction: str | None = None,
    ) -> CsvExport:
        """Validate the list filters and render every match as CSV."""
        normalized_query, sort_spec = self._list_params(None, query, customer_id, sort, direction)
        summaries = self._all_order_summaries(normalized_query, status, customer_id, sort_spec)
        rows = [
            (
                summary.order.id,
                summary.order.number,
                summary.order.status,
                summary.order.customer_id,
                summary.customer_name,
                summary.subtotal,
                summary.tax_rate,
                summary.tax,
                summary.total,
                summary.order.invoice_id,
                summary.order.created_at,
                summary.order.updated_at,
            )
            for summary in summaries
        ]
        return CsvExport(
            filename=csv_export_filename("orders", self._clock.now()),
            text=write_csv(ORDER_COLUMNS, rows),
        )

    def _list_params(
        self,
        page: int | None,
        query: str | None,
        customer_id: int | None,
        sort: str | None,
        direction: str | None,
    ) -> tuple[str | None, SortSpec]:
        """Validate the filters, the sort and (when given) the page."""
        errors: list[dict[str, str]] = []
        if page is not None and not 1 <= page <= MAX_PAGE:
            errors.append(_out_of_range("page", 1, MAX_PAGE))
        errors.extend(_query_customer_id_errors(customer_id))
        normalized_query, query_error = _normalize_query(query)
        if query_error is not None:
            errors.append(query_error)
        if errors:
            _raise_validation(errors)

        sort_spec = parse_sort(
            sort,
            direction,
            allowed=ORDER_SORT_FIELDS,
            default="created_at",
        )
        return normalized_query, sort_spec

    def _all_order_summaries(
        self,
        query: str | None,
        status: OrderStatus | None,
        customer_id: int | None,
        sort: SortSpec,
    ) -> list[OrderSummaryView]:
        """Read every match page by page, without the list's page limit."""
        summaries: list[OrderSummaryView] = []
        page = 1
        while True:
            items, _ = self._store.list_orders(
                query=query,
                status=status,
                customer_id=customer_id,
                page=page,
                page_size=EXPORT_PAGE_SIZE,
                sort=sort,
            )
            summaries.extend(self._summary(order, customer_name) for order, customer_name in items)
            if len(items) < EXPORT_PAGE_SIZE:
                return summaries
            page += 1

    def get(self, id: int) -> OrderView:
        """Return one order with its current customer and totals."""
        if not 1 <= id <= MAX_ID:
            raise _not_found()
        order = self._store.get_order(id)
        if order is None:
            raise _not_found()
        return self._view(order)

    def create(self, customer_id: int | None) -> OrderView:
        """Create a draft."""
        errors = _body_id_errors(customer_id, "customer_id")
        if errors:
            _raise_validation(errors)
        assert customer_id is not None
        try:
            order = self._store.create_order(customer_id, self._clock.now())
        except _STORE_ERRORS as error:
            self._translate(error)
        return self._view(order)

    def set_customer(
        self,
        id: int,
        customer_id: int | None,
        version: int | None,
    ) -> OrderView:
        """Change the customer of a draft."""
        errors = _body_id_errors(customer_id, "customer_id") + _version_errors(version)
        if errors:
            _raise_validation(errors)
        assert customer_id is not None
        assert version is not None
        try:
            order = self._store.set_customer(id, customer_id, version, self._clock.now())
        except _STORE_ERRORS as error:
            self._translate(error)
        return self._view(order)

    def add_line(
        self,
        id: int,
        product_id: int | None,
        quantity: int | None,
        version: int | None,
    ) -> OrderView:
        """Add a line to a draft."""
        errors = (
            _body_id_errors(product_id, "product_id")
            + _quantity_errors(quantity)
            + _version_errors(version)
        )
        if errors:
            _raise_validation(errors)
        assert product_id is not None
        assert quantity is not None
        assert version is not None
        try:
            order = self._store.add_line(id, product_id, quantity, version, self._clock.now())
        except _STORE_ERRORS as error:
            self._translate(error)
        return self._view(order)

    def set_quantity(
        self,
        id: int,
        line_id: int,
        quantity: int | None,
        version: int | None,
    ) -> OrderView:
        """Change a line quantity of a draft."""
        errors = _quantity_errors(quantity) + _version_errors(version)
        if errors:
            _raise_validation(errors)
        assert quantity is not None
        assert version is not None
        try:
            order = self._store.set_quantity(id, line_id, quantity, version, self._clock.now())
        except _STORE_ERRORS as error:
            self._translate(error)
        return self._view(order)

    def remove_line(
        self,
        id: int,
        line_id: int,
        expected_version: int | None,
    ) -> OrderView:
        """Remove a line from a draft."""
        if expected_version is not None:
            errors = _version_errors(expected_version)
            if errors:
                _raise_validation(errors)
        try:
            order = self._store.remove_line(id, line_id, expected_version, self._clock.now())
        except _STORE_ERRORS as error:
            self._translate(error)
        return self._view(order)

    def confirm(self, id: int, expected_version: int | None) -> OrderView:
        """Confirm a draft."""
        return self._transition(id, OrderAction.CONFIRM, expected_version)

    def cancel(self, id: int, expected_version: int | None) -> OrderView:
        """Cancel a draft or a confirmed order."""
        return self._transition(id, OrderAction.CANCEL, expected_version)

    def ship(self, id: int, expected_version: int | None) -> OrderView:
        """Ship a paid order."""
        return self._transition(id, OrderAction.SHIP, expected_version)

    def _transition(
        self,
        id: int,
        action: OrderAction,
        expected_version: int | None,
    ) -> OrderView:
        if expected_version is not None:
            errors = _version_errors(expected_version)
            if errors:
                _raise_validation(errors)
        try:
            order = self._store.transition(id, action, expected_version, self._clock.now())
        except _STORE_ERRORS as error:
            self._translate(error)
        return self._view(order)

    def _translate(self, error: Exception) -> NoReturn:
        if isinstance(error, (OrderNotFound, LineNotFound)):
            raise _not_found() from error
        if isinstance(error, VersionConflict):
            raise ApiError(409, "VERSION_CONFLICT", VERSION_CONFLICT_MESSAGE) from error
        if isinstance(error, OrderNotEditable):
            raise ApiError(409, "ORDER_NOT_EDITABLE", ORDER_NOT_EDITABLE_MESSAGE) from error
        if isinstance(error, CustomerInactive):
            raise ApiError(422, "CUSTOMER_INACTIVE", CUSTOMER_INACTIVE_MESSAGE) from error
        if isinstance(error, CustomerNotFound):
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                VALIDATION_DETAIL,
                errors=[_reference_not_found("customer_id")],
            ) from error
        if isinstance(error, ProductNotFound):
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                VALIDATION_DETAIL,
                errors=[_reference_not_found("product_id")],
            ) from error
        raise error

    def _view(self, order: Order) -> OrderView:
        rate = order.tax_rate if order.tax_rate is not None else self._store.get_tax_rate()
        lines = tuple(
            OrderLineView(
                line=line,
                line_total=quantize_money(line.unit_price * line.quantity),
            )
            for line in sorted(order.lines, key=lambda item: item.id)
        )
        totals = compute_totals(
            [LineInput(line.line.unit_price, line.line.quantity) for line in lines],
            rate,
        )
        customer = self._customers.get(order.customer_id)
        if customer is None:
            raise RuntimeError("Order has no customer")
        return OrderView(
            order=order,
            customer=customer,
            lines=lines,
            tax_rate=rate,
            subtotal=totals.subtotal,
            tax=totals.tax,
            total=totals.total,
        )

    def _summary(self, order: Order, customer_name: str) -> OrderSummaryView:
        rate = order.tax_rate if order.tax_rate is not None else self._store.get_tax_rate()
        totals = compute_totals(
            [LineInput(line.unit_price, line.quantity) for line in order.lines],
            rate,
        )
        return OrderSummaryView(
            order=order,
            customer_name=customer_name,
            subtotal=totals.subtotal,
            tax_rate=rate,
            tax=totals.tax,
            total=totals.total,
        )
