"""In-memory order store (a test double and development aid)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from threading import RLock

from app.domain.money import quantize_money
from app.domain.numbering import format_number
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
from app.modules.customers.models import Customer, CustomerStatus
from app.modules.customers.ports import CustomerRepository
from app.modules.customers.search import normalize_for_search
from app.modules.orders.models import Order, OrderLine, Product
from app.modules.orders.ports import (
    CustomerInactive,
    CustomerNotFound,
    LineNotFound,
    OrderNotEditable,
    OrderNotFound,
    ProductNotFound,
    VersionConflict,
)


def _number_value(number: str) -> int:
    return int(number.rsplit("-", 1)[-1])


class InMemoryOrderStore:
    """A thread-safe order store backed by dictionaries."""

    def __init__(
        self,
        customers: CustomerRepository,
        lock: RLock | None = None,
        invoices: object | None = None,
    ) -> None:
        self._customers = customers
        self._lock = lock if lock is not None else RLock()
        self.invoices = invoices
        self._products: dict[int, Product] = {}
        self._orders: dict[int, Order] = {}
        self._tax_rate = Decimal("0.00")
        self._next_order_id = 1
        self._next_number = 1
        self._next_line_id = 1

    def list_products(self) -> list[Product]:
        with self._lock:
            return [self._products[id] for id in sorted(self._products)]

    def get_product(self, id: int) -> Product | None:
        with self._lock:
            return self._products.get(id)

    def get_tax_rate(self) -> Decimal:
        with self._lock:
            return self._tax_rate

    def set_tax_rate(self, rate: Decimal) -> None:
        with self._lock:
            self._tax_rate = quantize_money(rate)

    def list_orders(
        self,
        *,
        query: str | None,
        status: OrderStatus | None,
        customer_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Order, str]], int]:
        with self._lock:
            matches: list[tuple[Order, str]] = []
            for order in self._orders.values():
                if status is not None and order.status != status:
                    continue
                if customer_id is not None and order.customer_id != customer_id:
                    continue
                customer = self._customers.get(order.customer_id)
                customer_name = customer.name if customer is not None else ""
                if query is not None:
                    needle = normalize_for_search(query)
                    if needle not in normalize_for_search(
                        order.number
                    ) and needle not in normalize_for_search(customer_name):
                        continue
                matches.append((order, customer_name))
            matches.sort(key=lambda pair: (pair[0].created_at, pair[0].id), reverse=True)
            start = (page - 1) * page_size
            return matches[start : start + page_size], len(matches)

    def get_order(self, id: int) -> Order | None:
        with self._lock:
            return self._orders.get(id)

    def create_order(self, customer_id: int, now: datetime) -> Order:
        with self._lock:
            self._active_customer(customer_id)
            order = Order(
                id=self._next_order_id,
                number=format_number("PED", self._next_number),
                status=OrderStatus.DRAFT,
                customer_id=customer_id,
                lines=(),
                tax_rate=None,
                version=1,
                created_at=now,
                updated_at=now,
                invoice_id=None,
            )
            self._next_order_id += 1
            self._next_number += 1
            self._orders[order.id] = order
            return order

    def set_customer(
        self,
        id: int,
        customer_id: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._lock:
            order = self._require_order(id)
            new_customer = self._customers.get(customer_id)
            if new_customer is None:
                raise CustomerNotFound
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            if new_customer.status != CustomerStatus.ACTIVE:
                raise CustomerInactive
            if order.customer_id == customer_id:
                return order
            return self._update_order(order, now, customer_id=customer_id)

    def add_line(
        self,
        id: int,
        product_id: int,
        quantity: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._lock:
            order = self._require_order(id)
            product = self._products.get(product_id)
            if product is None:
                raise ProductNotFound
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            self._active_customer(order.customer_id)

            candidate = [DraftLineInput(line.product_id, line.quantity) for line in order.lines]
            candidate.append(DraftLineInput(product_id, quantity))
            validate_draft_lines(candidate)

            line = OrderLine(
                id=self._next_line_id,
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                quantity=quantity,
                unit_price=product.price,
            )
            self._next_line_id += 1
            return self._update_order(order, now, lines=order.lines + (line,))

    def set_quantity(
        self,
        id: int,
        line_id: int,
        quantity: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._lock:
            order = self._require_order(id)
            line = self._require_line(order, line_id)
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            self._active_customer(order.customer_id)
            if line.quantity == quantity:
                return order
            updated_line = replace(line, quantity=quantity)
            lines = tuple(
                updated_line if existing.id == line_id else existing for existing in order.lines
            )
            return self._update_order(order, now, lines=lines)

    def remove_line(
        self,
        id: int,
        line_id: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._lock:
            order = self._require_order(id)
            self._require_line(order, line_id)
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            self._active_customer(order.customer_id)
            lines = tuple(line for line in order.lines if line.id != line_id)
            return self._update_order(order, now, lines=lines)

    def transition(
        self,
        id: int,
        action: OrderAction,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._lock:
            order = self._require_order(id)
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            new_status = next_status(order.status, action)

            tax_rate = order.tax_rate
            if action == OrderAction.CONFIRM:
                self._active_customer(order.customer_id)
                ensure_confirmable(order.lines)
                stock = {
                    line.product_id: ProductStock(
                        sku=self._products[line.product_id].sku,
                        name=self._products[line.product_id].name,
                        available=self._products[line.product_id].stock,
                    )
                    for line in order.lines
                }
                check_stock(
                    [DraftLineInput(line.product_id, line.quantity) for line in order.lines],
                    stock,
                )
                for line in order.lines:
                    product = self._products[line.product_id]
                    self._products[line.product_id] = replace(
                        product, stock=product.stock - line.quantity
                    )
                tax_rate = self._tax_rate
            elif action == OrderAction.CANCEL:
                if order.status == OrderStatus.CONFIRMED:
                    for line in order.lines:
                        product = self._products[line.product_id]
                        self._products[line.product_id] = replace(
                            product, stock=product.stock + line.quantity
                        )
                    if self.invoices is not None:
                        self.invoices.void_for_order(order.id, now)
                else:
                    # A confirmed order keeps the rate frozen at confirmation.
                    tax_rate = self._tax_rate

            return self._update_order(order, now, status=new_status, tax_rate=tax_rate)

    def replace_all(
        self,
        products: Iterable[Product],
        orders: Iterable[Order],
        tax_rate: Decimal,
    ) -> None:
        product_list = list(products)
        order_list = list(orders)
        with self._lock:
            self._products = {product.id: product for product in product_list}
            self._orders = {order.id: order for order in order_list}
            self._tax_rate = quantize_money(tax_rate)
            self._next_order_id = max((order.id for order in order_list), default=0) + 1
            self._next_number = (
                max((_number_value(order.number) for order in order_list), default=0) + 1
            )
            self._next_line_id = (
                max(
                    (line.id for order in order_list for line in order.lines),
                    default=0,
                )
                + 1
            )

    def attach_invoice(self, order_id: int, invoice_id: int, now: datetime) -> Order:
        with self._lock:
            order = self._require_order(order_id)
            return self._update_order(order, now, invoice_id=invoice_id)

    def mark_paid(self, order_id: int, now: datetime) -> Order:
        with self._lock:
            order = self._require_order(order_id)
            next_status(order.status, OrderAction.PAY)
            return self._update_order(order, now, status=OrderStatus.PAID)

    def link_invoices(self, links: Mapping[int, int]) -> None:
        with self._lock:
            for order_id, order in list(self._orders.items()):
                self._orders[order_id] = replace(order, invoice_id=links.get(order_id))

    def _require_order(self, id: int) -> Order:
        order = self._orders.get(id)
        if order is None:
            raise OrderNotFound
        return order

    @staticmethod
    def _require_line(order: Order, line_id: int) -> OrderLine:
        for line in order.lines:
            if line.id == line_id:
                return line
        raise LineNotFound

    def _active_customer(self, customer_id: int) -> Customer:
        customer = self._customers.get(customer_id)
        if customer is None:
            raise CustomerNotFound
        if customer.status != CustomerStatus.ACTIVE:
            raise CustomerInactive
        return customer

    def _update_order(self, order: Order, now: datetime, **changes: object) -> Order:
        updated = replace(
            order,
            version=order.version + 1,
            updated_at=now,
            **changes,
        )
        self._orders[order.id] = updated
        return updated
