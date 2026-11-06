"""The order tables reject what their constraints and indexes should reject."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import Connection, insert
from sqlalchemy.exc import IntegrityError

from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.tables import order_lines, orders, products

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def _product_values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "id": 99,
        "sku": "ZZ-1",
        "name": "Test product",
        "price": Decimal("1.00"),
        "stock": 1,
    }
    values.update(overrides)
    return values


def _order_values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "number": "PED-9999",
        "status": "draft",
        "customer_id": 1,
        "tax_rate": None,
        "version": 1,
        "created_at": NOW,
        "updated_at": NOW,
        "invoice_id": None,
    }
    values.update(overrides)
    return values


def _line_values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "order_id": 1,
        "product_id": 2,
        "sku": "MS-200",
        "name": "Mouse óptico",
        "quantity": 1,
        "unit_price": Decimal("9.50"),
    }
    values.update(overrides)
    return values


def _rejects(db: Connection, statement: Any, constraint: str) -> None:
    with pytest.raises(IntegrityError) as info:
        db.execute(statement)
    assert constraint in str(info.value)
    db.rollback()


def test_negative_price_is_rejected(db: Connection, order_store: PostgresOrderStore) -> None:
    _rejects(
        db,
        insert(products).values(**_product_values(price=Decimal("-1.00"))),
        "ck_products_price",
    )


def test_negative_stock_is_rejected(db: Connection, order_store: PostgresOrderStore) -> None:
    _rejects(
        db,
        insert(products).values(**_product_values(stock=-1)),
        "ck_products_stock",
    )


def test_repeated_sku_is_rejected(db: Connection, order_store: PostgresOrderStore) -> None:
    _rejects(
        db,
        insert(products).values(**_product_values(sku="KB-100")),
        "products_sku_key",
    )


def test_an_unknown_order_status_is_rejected(
    db: Connection, order_store: PostgresOrderStore
) -> None:
    _rejects(
        db,
        insert(orders).values(**_order_values(status="lost")),
        "ck_orders_status",
    )


def test_an_out_of_range_tax_rate_is_rejected(
    db: Connection, order_store: PostgresOrderStore
) -> None:
    _rejects(
        db,
        insert(orders).values(**_order_values(tax_rate=Decimal("101.00"))),
        "ck_orders_tax_rate",
    )


def test_an_unknown_customer_is_rejected(db: Connection, order_store: PostgresOrderStore) -> None:
    _rejects(
        db,
        insert(orders).values(**_order_values(customer_id=999)),
        "fk_orders_customer_id_customers",
    )


def test_a_repeated_order_number_is_rejected(
    db: Connection, order_store: PostgresOrderStore
) -> None:
    _rejects(
        db,
        insert(orders).values(**_order_values(number="PED-0001")),
        "orders_number_key",
    )


@pytest.mark.parametrize("quantity", [0, 1000])
def test_an_out_of_range_quantity_is_rejected(
    db: Connection, order_store: PostgresOrderStore, quantity: int
) -> None:
    _rejects(
        db,
        insert(order_lines).values(**_line_values(quantity=quantity)),
        "ck_order_lines_quantity",
    )


def test_a_repeated_product_is_rejected(db: Connection, order_store: PostgresOrderStore) -> None:
    _rejects(
        db,
        insert(order_lines).values(
            **_line_values(
                order_id=1,
                product_id=1,
                sku="KB-100",
                name="Teclado USB",
                quantity=1,
                unit_price=Decimal("19.90"),
            )
        ),
        "order_lines_order_product_key",
    )
