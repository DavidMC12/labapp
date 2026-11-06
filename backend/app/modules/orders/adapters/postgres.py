"""PostgreSQL store for products, settings and orders.

Every mutation runs in one transaction and locks rows in this order: the order row
(``FOR UPDATE``), then the customer row (``FOR SHARE``), then the product rows
(``FOR UPDATE``, ascending product id). Methods that need fewer rows keep that relative
order. The version and the state are checked after locking.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, insert, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

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
from app.errors import ApiError
from app.infra.db import (
    as_utc,
    qualified_sequence_name,
    qualified_table_name,
    unique_violation_of,
)
from app.modules.customers.models import CustomerStatus
from app.modules.customers.search import normalize_for_search
from app.modules.customers.tables import customers
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
from app.modules.orders.tables import (
    order_lines,
    order_number_seq,
    orders,
    products,
)
from app.modules.orders.tables import (
    settings as settings_table,
)

_DUPLICATE_PRODUCT_MESSAGE = "Ese producto ya está en el pedido; edita su cantidad."
_LINE_PRODUCT_CONSTRAINT = "order_lines_order_product_key"


def _number_value(number: str) -> int:
    return int(number.rsplit("-", 1)[-1])


def _product_from_row(row: Mapping[str, Any]) -> Product:
    return Product(
        id=row["id"],
        sku=row["sku"],
        name=row["name"],
        price=row["price"],
        stock=row["stock"],
    )


def _line_from_row(row: Mapping[str, Any]) -> OrderLine:
    return OrderLine(
        id=row["id"],
        product_id=row["product_id"],
        sku=row["sku"],
        name=row["name"],
        quantity=row["quantity"],
        unit_price=row["unit_price"],
    )


def _order_from_row(row: Mapping[str, Any], lines: Iterable[OrderLine]) -> Order:
    return Order(
        id=row["id"],
        number=row["number"],
        status=OrderStatus(row["status"]),
        customer_id=row["customer_id"],
        lines=tuple(lines),
        tax_rate=row["tax_rate"],
        version=row["version"],
        created_at=as_utc(row["created_at"]),
        updated_at=as_utc(row["updated_at"]),
        invoice_id=row["invoice_id"],
    )


class PostgresOrderStore:
    """An order store backed by PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _lock_order(self, connection: Connection, id: int) -> Order | None:
        row = (
            connection.execute(select(orders).where(orders.c.id == id).with_for_update())
            .mappings()
            .first()
        )
        if row is None:
            return None
        lines = (
            connection.execute(
                select(order_lines).where(order_lines.c.order_id == id).order_by(order_lines.c.id)
            )
            .mappings()
            .all()
        )
        return _order_from_row(row, [_line_from_row(line) for line in lines])

    @staticmethod
    def _lock_customer(connection: Connection, customer_id: int) -> Mapping[str, Any] | None:
        return (
            connection.execute(
                select(customers.c.id, customers.c.status)
                .where(customers.c.id == customer_id)
                .with_for_update(read=True)
            )
            .mappings()
            .first()
        )

    def _lock_product(self, connection: Connection, product_id: int) -> Product | None:
        row = (
            connection.execute(
                select(products).where(products.c.id == product_id).with_for_update()
            )
            .mappings()
            .first()
        )
        return _product_from_row(row) if row is not None else None

    def _lock_products(
        self, connection: Connection, product_ids: Iterable[int]
    ) -> dict[int, Product]:
        locked: dict[int, Product] = {}
        for product_id in sorted(set(product_ids)):
            product = self._lock_product(connection, product_id)
            if product is None:
                raise ProductNotFound
            locked[product_id] = product
        return locked

    def _current_tax_rate(self, connection: Connection) -> Decimal:
        value = connection.execute(
            select(settings_table.c.value).where(settings_table.c.key == "tax_rate")
        ).scalar_one_or_none()
        return quantize_money(Decimal(value)) if value is not None else Decimal("0.00")

    def _upsert_tax_rate(self, connection: Connection, rate: Decimal) -> None:
        value = format(quantize_money(rate), "f")
        statement = postgres_insert(settings_table).values(key="tax_rate", value=value)
        statement = statement.on_conflict_do_update(
            index_elements=[settings_table.c.key],
            set_={"value": statement.excluded.value},
        )
        connection.execute(statement)

    def _reload_order(self, connection: Connection, id: int) -> Order:
        row = connection.execute(select(orders).where(orders.c.id == id)).mappings().one()
        lines = (
            connection.execute(
                select(order_lines).where(order_lines.c.order_id == id).order_by(order_lines.c.id)
            )
            .mappings()
            .all()
        )
        return _order_from_row(row, [_line_from_row(line) for line in lines])

    def _write_order(
        self,
        connection: Connection,
        order: Order,
        now: datetime,
        **values: object,
    ) -> Order:
        connection.execute(
            update(orders)
            .where(orders.c.id == order.id)
            .values(version=order.version + 1, updated_at=now, **values)
        )
        return self._reload_order(connection, order.id)

    def list_products(self) -> list[Product]:
        with self._engine.begin() as connection:
            rows = connection.execute(select(products).order_by(products.c.id)).mappings().all()
        return [_product_from_row(row) for row in rows]

    def get_product(self, id: int) -> Product | None:
        with self._engine.begin() as connection:
            row = connection.execute(select(products).where(products.c.id == id)).mappings().first()
        return _product_from_row(row) if row is not None else None

    def get_tax_rate(self) -> Decimal:
        with self._engine.begin() as connection:
            return self._current_tax_rate(connection)

    def set_tax_rate(self, rate: Decimal) -> None:
        with self._engine.begin() as connection:
            self._upsert_tax_rate(connection, rate)

    def list_orders(
        self,
        *,
        query: str | None,
        status: OrderStatus | None,
        customer_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Order, str]], int]:
        filters = []
        if status is not None:
            filters.append(orders.c.status == status.value)
        if customer_id is not None:
            filters.append(orders.c.customer_id == customer_id)
        if query is not None:
            normalized = normalize_for_search(query)
            filters.append(
                or_(
                    func.lower(orders.c.number).contains(normalized, autoescape=True),
                    customers.c.name_search.contains(normalized, autoescape=True),
                )
            )

        join = customers.c.id == orders.c.customer_id
        offset = (page - 1) * page_size
        with self._engine.begin() as connection:
            total = connection.execute(
                select(func.count()).select_from(orders).join(customers, join).where(*filters)
            ).scalar_one()
            rows = (
                connection.execute(
                    select(orders, customers.c.name.label("customer_name"))
                    .join(customers, join)
                    .where(*filters)
                    .order_by(orders.c.created_at.desc(), orders.c.id.desc())
                    .offset(offset)
                    .limit(page_size)
                )
                .mappings()
                .all()
            )
            order_ids = [row["id"] for row in rows]
            lines_by_order: dict[int, list[OrderLine]] = defaultdict(list)
            if order_ids:
                line_rows = connection.execute(
                    select(order_lines)
                    .where(order_lines.c.order_id.in_(order_ids))
                    .order_by(order_lines.c.id)
                ).mappings()
                for line_row in line_rows:
                    lines_by_order[line_row["order_id"]].append(_line_from_row(line_row))

        items = [
            (
                _order_from_row(row, lines_by_order.get(row["id"], [])),
                row["customer_name"],
            )
            for row in rows
        ]
        return items, total

    def get_order(self, id: int) -> Order | None:
        with self._engine.begin() as connection:
            row = connection.execute(select(orders).where(orders.c.id == id)).mappings().first()
            if row is None:
                return None
            lines = (
                connection.execute(
                    select(order_lines)
                    .where(order_lines.c.order_id == id)
                    .order_by(order_lines.c.id)
                )
                .mappings()
                .all()
            )
        return _order_from_row(row, [_line_from_row(line) for line in lines])

    def create_order(self, customer_id: int, now: datetime) -> Order:
        with self._engine.begin() as connection:
            customer = self._lock_customer(connection, customer_id)
            if customer is None:
                raise CustomerNotFound
            if customer["status"] != CustomerStatus.ACTIVE.value:
                raise CustomerInactive

            number = connection.execute(
                text("select nextval(:sequence_name)"),
                {"sequence_name": qualified_sequence_name(self._engine, order_number_seq)},
            ).scalar_one()
            row = (
                connection.execute(
                    insert(orders)
                    .values(
                        number=format_number("PED", number),
                        status=OrderStatus.DRAFT.value,
                        customer_id=customer_id,
                        tax_rate=None,
                        version=1,
                        created_at=now,
                        updated_at=now,
                        invoice_id=None,
                    )
                    .returning(*orders.c)
                )
                .mappings()
                .one()
            )
        return _order_from_row(row, [])

    def set_customer(
        self,
        id: int,
        customer_id: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._engine.begin() as connection:
            order = self._lock_order(connection, id)
            if order is None:
                raise OrderNotFound
            new_customer = self._lock_customer(connection, customer_id)
            if new_customer is None:
                raise CustomerNotFound
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            if new_customer["status"] != CustomerStatus.ACTIVE.value:
                raise CustomerInactive
            if order.customer_id == customer_id:
                return order
            return self._write_order(connection, order, now, customer_id=customer_id)

    def add_line(
        self,
        id: int,
        product_id: int,
        quantity: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._engine.begin() as connection:
            order = self._lock_order(connection, id)
            if order is None:
                raise OrderNotFound
            customer = self._lock_customer(connection, order.customer_id)
            if customer is None:
                raise CustomerNotFound
            product = self._lock_product(connection, product_id)
            if product is None:
                raise ProductNotFound
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            if customer["status"] != CustomerStatus.ACTIVE.value:
                raise CustomerInactive

            candidate = [DraftLineInput(line.product_id, line.quantity) for line in order.lines]
            candidate.append(DraftLineInput(product_id, quantity))
            validate_draft_lines(candidate)

            try:
                connection.execute(
                    insert(order_lines).values(
                        order_id=id,
                        product_id=product.id,
                        sku=product.sku,
                        name=product.name,
                        quantity=quantity,
                        unit_price=product.price,
                    )
                )
            except IntegrityError as error:
                if unique_violation_of(error, _LINE_PRODUCT_CONSTRAINT):
                    raise ApiError(
                        422,
                        "ORDER_DUPLICATE_PRODUCT",
                        _DUPLICATE_PRODUCT_MESSAGE,
                    ) from error
                raise
            return self._write_order(connection, order, now)

    def set_quantity(
        self,
        id: int,
        line_id: int,
        quantity: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._engine.begin() as connection:
            order = self._lock_order(connection, id)
            if order is None:
                raise OrderNotFound
            line = next((item for item in order.lines if item.id == line_id), None)
            if line is None:
                raise LineNotFound
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            customer = self._lock_customer(connection, order.customer_id)
            if customer is None:
                raise CustomerNotFound
            if customer["status"] != CustomerStatus.ACTIVE.value:
                raise CustomerInactive
            if line.quantity == quantity:
                return order

            connection.execute(
                update(order_lines)
                .where(order_lines.c.id == line_id, order_lines.c.order_id == id)
                .values(quantity=quantity)
            )
            return self._write_order(connection, order, now)

    def remove_line(
        self,
        id: int,
        line_id: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._engine.begin() as connection:
            order = self._lock_order(connection, id)
            if order is None:
                raise OrderNotFound
            if all(item.id != line_id for item in order.lines):
                raise LineNotFound
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            if order.status != OrderStatus.DRAFT:
                raise OrderNotEditable
            customer = self._lock_customer(connection, order.customer_id)
            if customer is None:
                raise CustomerNotFound
            if customer["status"] != CustomerStatus.ACTIVE.value:
                raise CustomerInactive

            connection.execute(
                delete(order_lines).where(
                    order_lines.c.id == line_id,
                    order_lines.c.order_id == id,
                )
            )
            return self._write_order(connection, order, now)

    def transition(
        self,
        id: int,
        action: OrderAction,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        with self._engine.begin() as connection:
            order = self._lock_order(connection, id)
            if order is None:
                raise OrderNotFound
            if expected_version is not None and expected_version != order.version:
                raise VersionConflict
            new_status = next_status(order.status, action)

            tax_rate = order.tax_rate
            if action == OrderAction.CONFIRM:
                customer = self._lock_customer(connection, order.customer_id)
                if customer is None:
                    raise CustomerNotFound
                locked_products = self._lock_products(
                    connection, [line.product_id for line in order.lines]
                )
                if customer["status"] != CustomerStatus.ACTIVE.value:
                    raise CustomerInactive
                ensure_confirmable(order.lines)
                stock = {
                    product_id: ProductStock(
                        sku=product.sku,
                        name=product.name,
                        available=product.stock,
                    )
                    for product_id, product in locked_products.items()
                }
                check_stock(
                    [DraftLineInput(line.product_id, line.quantity) for line in order.lines],
                    stock,
                )
                for line in order.lines:
                    product = locked_products[line.product_id]
                    connection.execute(
                        update(products)
                        .where(products.c.id == line.product_id)
                        .values(stock=product.stock - line.quantity)
                    )
                tax_rate = self._current_tax_rate(connection)
            elif action == OrderAction.CANCEL:
                if order.status == OrderStatus.CONFIRMED:
                    locked_products = self._lock_products(
                        connection, [line.product_id for line in order.lines]
                    )
                    for line in order.lines:
                        product = locked_products[line.product_id]
                        connection.execute(
                            update(products)
                            .where(products.c.id == line.product_id)
                            .values(stock=product.stock + line.quantity)
                        )
                tax_rate = self._current_tax_rate(connection)

            return self._write_order(
                connection,
                order,
                now,
                status=new_status.value,
                tax_rate=tax_rate,
            )

    def replace_all(
        self,
        product_rows: Iterable[Product],
        order_rows: Iterable[Order],
        tax_rate: Decimal,
    ) -> None:
        product_list = list(product_rows)
        order_list = list(order_rows)
        line_list = [(order.id, line) for order in order_list for line in order.lines]
        with self._engine.begin() as connection:
            connection.execute(delete(order_lines))
            connection.execute(delete(orders))
            connection.execute(delete(products))
            if product_list:
                connection.execute(
                    insert(products).values(
                        [
                            {
                                "id": product.id,
                                "sku": product.sku,
                                "name": product.name,
                                "price": product.price,
                                "stock": product.stock,
                            }
                            for product in product_list
                        ]
                    )
                )
            if order_list:
                connection.execute(
                    insert(orders).values(
                        [
                            {
                                "id": order.id,
                                "number": order.number,
                                "status": order.status.value,
                                "customer_id": order.customer_id,
                                "tax_rate": order.tax_rate,
                                "version": order.version,
                                "created_at": order.created_at,
                                "updated_at": order.updated_at,
                                "invoice_id": order.invoice_id,
                            }
                            for order in order_list
                        ]
                    )
                )
            if line_list:
                connection.execute(
                    insert(order_lines).values(
                        [
                            {
                                "id": line.id,
                                "order_id": order_id,
                                "product_id": line.product_id,
                                "sku": line.sku,
                                "name": line.name,
                                "quantity": line.quantity,
                                "unit_price": line.unit_price,
                            }
                            for order_id, line in line_list
                        ]
                    )
                )

            self._upsert_tax_rate(connection, tax_rate)

            next_order_id = max((order.id for order in order_list), default=0) + 1
            next_line_id = max((line.id for _, line in line_list), default=0) + 1
            next_number = max((_number_value(order.number) for order in order_list), default=0) + 1
            connection.execute(
                text(
                    "select setval(pg_get_serial_sequence(:table_name, 'id'), :next_value, false)"
                ),
                {
                    "table_name": qualified_table_name(self._engine, orders),
                    "next_value": next_order_id,
                },
            )
            connection.execute(
                text(
                    "select setval(pg_get_serial_sequence(:table_name, 'id'), :next_value, false)"
                ),
                {
                    "table_name": qualified_table_name(self._engine, order_lines),
                    "next_value": next_line_id,
                },
            )
            connection.execute(
                text("select setval(:sequence_name, :next_value, false)"),
                {
                    "sequence_name": qualified_sequence_name(self._engine, order_number_seq),
                    "next_value": next_number,
                },
            )


__all__ = ["PostgresOrderStore"]
