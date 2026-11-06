"""Reusable behavioral tests for OrderStore adapters."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from typing import Any

import pytest

from app.domain.orders import OrderAction, OrderStatus
from app.errors import ApiError
from app.modules.customers.models import CustomerStatus, NewCustomer
from app.modules.customers.ports import CustomerRepository
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

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=1)
SEED_RATE = Decimal("10.00")


def _deactivate(customers: CustomerRepository, customer_id: int) -> None:
    customers.set_status(customer_id, CustomerStatus.INACTIVE, None, NOW)


class OrderStoreContract:
    """The behavior every OrderStore adapter must share.

    A concrete test class provides ``customer_repository`` (seeded with the ten
    customers) and ``store`` (a fresh store with the seeded products and orders).
    """

    @pytest.fixture
    def customer_repository(self) -> Any:
        raise NotImplementedError

    @pytest.fixture
    def store(self, customer_repository: CustomerRepository) -> Any:
        raise NotImplementedError

    def test_products_are_ordered_by_id(self, store: Any) -> None:
        products = store.list_products()

        assert [product.id for product in products] == list(range(1, 16))
        assert products[0].sku == "KB-100"
        assert products[0].price == Decimal("19.90")
        assert store.get_product(99) is None

    def test_tax_rate(self, store: Any) -> None:
        assert store.get_tax_rate() == SEED_RATE

        store.set_tax_rate(Decimal("7"))

        assert store.get_tax_rate() == Decimal("7.00")

    def test_list_orders_orders_by_created_at_then_id_descending(self, store: Any) -> None:
        items, total = store.list_orders(
            query=None, status=None, customer_id=None, page=1, page_size=20
        )

        assert total == 7
        assert [order.id for order, _ in items] == [7, 6, 5, 4, 3, 2, 1]
        assert items[0][1] == "Cafetería La Esquina"

    def test_list_orders_pages(self, store: Any) -> None:
        first, total = store.list_orders(
            query=None, status=None, customer_id=None, page=1, page_size=3
        )
        second, _ = store.list_orders(
            query=None, status=None, customer_id=None, page=2, page_size=3
        )
        third, _ = store.list_orders(query=None, status=None, customer_id=None, page=3, page_size=3)
        empty, _ = store.list_orders(query=None, status=None, customer_id=None, page=4, page_size=3)

        assert total == 7
        assert [order.id for order, _ in first] == [7, 6, 5]
        assert [order.id for order, _ in second] == [4, 3, 2]
        assert [order.id for order, _ in third] == [1]
        assert empty == []

    def test_list_orders_filters_by_status_and_customer(self, store: Any) -> None:
        drafts, draft_total = store.list_orders(
            query=None, status=OrderStatus.DRAFT, customer_id=None, page=1, page_size=20
        )
        confirmed, _ = store.list_orders(
            query=None,
            status=OrderStatus.CONFIRMED,
            customer_id=None,
            page=1,
            page_size=20,
        )
        customer, customer_total = store.list_orders(
            query=None, status=None, customer_id=1, page=1, page_size=20
        )
        missing, missing_total = store.list_orders(
            query=None, status=None, customer_id=999, page=1, page_size=20
        )

        assert draft_total == 1
        assert [order.id for order, _ in drafts] == [1]
        assert [order.id for order, _ in confirmed] == [7, 3, 2]
        assert customer_total == 1
        assert [order.id for order, _ in customer] == [1]
        assert missing == []
        assert missing_total == 0

    def test_list_orders_searches_number_and_customer_name(self, store: Any) -> None:
        by_number, _ = store.list_orders(
            query="ped-0001", status=None, customer_id=None, page=1, page_size=20
        )
        by_name, _ = store.list_orders(
            query="cafeteria", status=None, customer_id=None, page=1, page_size=20
        )
        by_case, _ = store.list_orders(
            query="ACME", status=None, customer_id=None, page=1, page_size=20
        )

        assert [order.id for order, _ in by_number] == [1]
        assert [order.id for order, _ in by_name] == [7]
        assert [order.id for order, _ in by_case] == [1]

    def test_list_orders_uses_the_current_customer_name(self, store: Any) -> None:
        store.set_customer(1, 2, None, NOW)

        items, total = store.list_orders(
            query="beta comercial", status=None, customer_id=None, page=1, page_size=20
        )

        assert total == 2
        assert [order.id for order, _ in items] == [2, 1]
        assert [name for _, name in items] == ["Beta Comercial Ltda."] * 2

    def test_list_orders_treats_pattern_characters_literally(
        self, store: Any, customer_repository: CustomerRepository
    ) -> None:
        percent = customer_repository.add(
            NewCustomer(
                name="100% coverage",
                email="percent@example.test",
                phone=None,
                tax_id=None,
                address=None,
            ),
            NOW,
        )
        underscore = customer_repository.add(
            NewCustomer(
                name="snake_case",
                email="underscore@example.test",
                phone=None,
                tax_id=None,
                address=None,
            ),
            NOW,
        )
        backslash = customer_repository.add(
            NewCustomer(
                name="back\\slash",
                email="backslash@example.test",
                phone=None,
                tax_id=None,
                address=None,
            ),
            NOW,
        )
        for customer in (percent, underscore, backslash):
            store.create_order(customer.id, NOW)

        for query, expected_customer in (
            ("%", percent),
            ("_", underscore),
            ("\\", backslash),
        ):
            items, total = store.list_orders(
                query=query, status=None, customer_id=None, page=1, page_size=20
            )

            assert total == 1
            assert [order.customer_id for order, _ in items] == [expected_customer.id]

    def test_create_order_assigns_the_next_number_and_defaults(self, store: Any) -> None:
        order = store.create_order(1, NOW)

        assert order.id == 8
        assert order.number == "PED-0008"
        assert order.status == OrderStatus.DRAFT
        assert order.customer_id == 1
        assert order.lines == ()
        assert order.tax_rate is None
        assert order.version == 1
        assert order.created_at == NOW
        assert order.updated_at == NOW
        assert store.get_order(8) == order

        assert store.create_order(2, LATER).number == "PED-0009"

    def test_create_order_rejects_unknown_and_inactive_customers(self, store: Any) -> None:
        with pytest.raises(CustomerNotFound):
            store.create_order(99, NOW)
        with pytest.raises(CustomerInactive):
            store.create_order(5, NOW)

    def test_set_customer_checks_in_the_documented_order(
        self, store: Any, customer_repository: CustomerRepository
    ) -> None:
        with pytest.raises(OrderNotFound):
            store.set_customer(99, 1, None, NOW)
        with pytest.raises(CustomerNotFound):
            store.set_customer(1, 99, 99, NOW)
        with pytest.raises(VersionConflict):
            store.set_customer(1, 5, 99, NOW)
        with pytest.raises(OrderNotEditable):
            store.set_customer(2, 1, None, NOW)

        _deactivate(customer_repository, 1)
        with pytest.raises(CustomerInactive):
            store.set_customer(1, 1, None, NOW)

    def test_set_customer_noop_and_real_change(self, store: Any) -> None:
        original = store.get_order(1)
        assert original is not None

        unchanged = store.set_customer(1, 1, 1, LATER)
        assert unchanged == original
        assert unchanged.version == 1
        assert unchanged.updated_at == original.updated_at

        changed = store.set_customer(1, 2, 1, LATER)
        assert changed.customer_id == 2
        assert changed.version == 2
        assert changed.updated_at == LATER

    def test_set_customer_allows_an_inactive_old_customer(
        self, store: Any, customer_repository: CustomerRepository
    ) -> None:
        _deactivate(customer_repository, 1)

        changed = store.set_customer(1, 2, None, LATER)

        assert changed.customer_id == 2

    def test_add_line_checks_in_the_documented_order(
        self, store: Any, customer_repository: CustomerRepository
    ) -> None:
        with pytest.raises(OrderNotFound):
            store.add_line(99, 1, 1, None, NOW)
        with pytest.raises(ProductNotFound):
            store.add_line(1, 99, 1, 99, NOW)
        with pytest.raises(VersionConflict):
            store.add_line(1, 2, 1, 99, NOW)
        with pytest.raises(OrderNotEditable):
            store.add_line(2, 6, 1, None, NOW)

        _deactivate(customer_repository, 1)
        with pytest.raises(CustomerInactive):
            store.add_line(1, 2, 1, None, NOW)

    def test_add_line_copies_the_product_and_assigns_the_next_line_id(self, store: Any) -> None:
        changed = store.add_line(1, 2, 3, 1, LATER)

        assert changed.version == 2
        assert changed.updated_at == LATER
        assert changed.lines[-1].id == 10
        assert changed.lines[-1].product_id == 2
        assert changed.lines[-1].sku == "MS-200"
        assert changed.lines[-1].name == "Mouse óptico"
        assert changed.lines[-1].quantity == 3
        assert changed.lines[-1].unit_price == Decimal("9.50")

    def test_add_line_rejects_a_duplicate_and_the_eleventh_line(self, store: Any) -> None:
        with pytest.raises(ApiError) as duplicate:
            store.add_line(1, 1, 1, None, NOW)
        assert duplicate.value.code == "ORDER_DUPLICATE_PRODUCT"

        for product_id in range(2, 11):
            store.add_line(1, product_id, 1, None, NOW)
        with pytest.raises(ApiError) as too_many:
            store.add_line(1, 11, 1, None, NOW)
        assert too_many.value.code == "ORDER_TOO_MANY_LINES"

    def test_set_quantity_checks_in_the_documented_order(
        self, store: Any, customer_repository: CustomerRepository
    ) -> None:
        with pytest.raises(OrderNotFound):
            store.set_quantity(99, 1, 2, None, NOW)
        with pytest.raises(LineNotFound):
            store.set_quantity(1, 99, 2, None, NOW)
        with pytest.raises(VersionConflict):
            store.set_quantity(1, 1, 2, 99, NOW)
        with pytest.raises(OrderNotEditable):
            store.set_quantity(2, 2, 2, None, NOW)

        _deactivate(customer_repository, 1)
        with pytest.raises(CustomerInactive):
            store.set_quantity(1, 1, 2, None, NOW)

    def test_set_quantity_noop_and_real_change(self, store: Any) -> None:
        original = store.get_order(1)
        assert original is not None

        unchanged = store.set_quantity(1, 1, 2, 1, LATER)
        assert unchanged == original

        changed = store.set_quantity(1, 1, 3, 1, LATER)
        assert changed.version == 2
        assert changed.updated_at == LATER
        assert changed.lines[0].quantity == 3
        assert changed.lines[0].unit_price == Decimal("19.90")

    def test_remove_line_checks_in_the_documented_order(
        self, store: Any, customer_repository: CustomerRepository
    ) -> None:
        with pytest.raises(OrderNotFound):
            store.remove_line(99, 1, None, NOW)
        with pytest.raises(LineNotFound):
            store.remove_line(1, 99, None, NOW)
        with pytest.raises(VersionConflict):
            store.remove_line(1, 1, 99, NOW)
        with pytest.raises(OrderNotEditable):
            store.remove_line(2, 2, None, NOW)

        _deactivate(customer_repository, 1)
        with pytest.raises(CustomerInactive):
            store.remove_line(1, 1, None, NOW)

    def test_remove_line_removes_it_and_bumps_the_version(self, store: Any) -> None:
        changed = store.remove_line(1, 1, 1, LATER)

        assert changed.lines == ()
        assert changed.version == 2
        assert changed.updated_at == LATER

    @pytest.mark.parametrize(
        ("order_id", "action", "expected"),
        [
            (1, OrderAction.CONFIRM, OrderStatus.CONFIRMED),
            (1, OrderAction.PAY, None),
            (1, OrderAction.SHIP, None),
            (1, OrderAction.CANCEL, OrderStatus.CANCELLED),
            (2, OrderAction.CONFIRM, None),
            (2, OrderAction.PAY, OrderStatus.PAID),
            (2, OrderAction.SHIP, None),
            (2, OrderAction.CANCEL, OrderStatus.CANCELLED),
            (4, OrderAction.CONFIRM, None),
            (4, OrderAction.PAY, None),
            (4, OrderAction.SHIP, OrderStatus.SHIPPED),
            (4, OrderAction.CANCEL, None),
            (5, OrderAction.CONFIRM, None),
            (5, OrderAction.PAY, None),
            (5, OrderAction.SHIP, None),
            (5, OrderAction.CANCEL, None),
            (6, OrderAction.CONFIRM, None),
            (6, OrderAction.PAY, None),
            (6, OrderAction.SHIP, None),
            (6, OrderAction.CANCEL, None),
        ],
    )
    def test_full_transition_matrix(
        self,
        store: Any,
        order_id: int,
        action: OrderAction,
        expected: OrderStatus | None,
    ) -> None:
        if expected is not None:
            assert store.transition(order_id, action, None, NOW).status == expected
            return

        with pytest.raises(ApiError) as error:
            store.transition(order_id, action, None, NOW)

        assert error.value.code == "INVALID_TRANSITION"

    @pytest.mark.parametrize(
        ("order_id", "action", "expected"),
        [
            (1, OrderAction.CONFIRM, OrderStatus.CONFIRMED),
            (1, OrderAction.CANCEL, OrderStatus.CANCELLED),
            (2, OrderAction.CANCEL, OrderStatus.CANCELLED),
            (4, OrderAction.SHIP, OrderStatus.SHIPPED),
        ],
    )
    def test_allowed_transitions(
        self, store: Any, order_id: int, action: OrderAction, expected: OrderStatus
    ) -> None:
        changed = store.transition(order_id, action, 1, LATER)

        assert changed.status == expected
        assert changed.version == 2
        assert changed.updated_at == LATER

    @pytest.mark.parametrize(
        ("order_id", "action"),
        [
            (2, OrderAction.CONFIRM),
            (4, OrderAction.CANCEL),
            (5, OrderAction.CANCEL),
            (6, OrderAction.CANCEL),
            (1, OrderAction.SHIP),
        ],
    )
    def test_invalid_transitions(self, store: Any, order_id: int, action: OrderAction) -> None:
        with pytest.raises(ApiError) as error:
            store.transition(order_id, action, None, NOW)

        assert error.value.status == 409
        assert error.value.code == "INVALID_TRANSITION"

    def test_invalid_transition_message_uses_spanish_labels(self, store: Any) -> None:
        with pytest.raises(ApiError) as error:
            store.transition(5, OrderAction.CANCEL, None, NOW)

        assert error.value.detail == "No se puede pasar el pedido de enviado a cancelado."

    def test_confirm_decrements_stock_and_freezes_the_current_rate(self, store: Any) -> None:
        store.set_tax_rate(Decimal("7"))

        changed = store.transition(1, OrderAction.CONFIRM, None, NOW)

        assert changed.tax_rate == Decimal("7.00")
        assert store.get_product(1) is not None
        assert store.get_product(1).stock == 118

    def test_cancel_confirmed_returns_stock_and_stores_the_current_rate(self, store: Any) -> None:
        store.transition(1, OrderAction.CONFIRM, None, NOW)
        store.set_tax_rate(Decimal("7"))

        changed = store.transition(1, OrderAction.CANCEL, None, NOW)

        assert store.get_product(1).stock == 120
        assert changed.tax_rate == Decimal("7.00")
        assert changed.status == OrderStatus.CANCELLED

    def test_cancel_draft_changes_no_stock_and_stores_the_current_rate(self, store: Any) -> None:
        store.set_tax_rate(Decimal("7"))

        changed = store.transition(1, OrderAction.CANCEL, None, NOW)

        assert store.get_product(1).stock == 120
        assert changed.tax_rate == Decimal("7.00")
        assert changed.status == OrderStatus.CANCELLED

    def test_confirm_is_all_or_nothing_with_several_shortages(self, store: Any) -> None:
        order = store.create_order(1, NOW)
        store.add_line(order.id, 7, 4, None, NOW)
        store.add_line(order.id, 9, 1, None, NOW)
        version = store.get_order(order.id).version

        with pytest.raises(ApiError) as error:
            store.transition(order.id, OrderAction.CONFIRM, None, NOW)

        assert error.value.code == "INSUFFICIENT_STOCK"
        assert error.value.extra["shortages"] == [
            {
                "product_id": 7,
                "sku": "WC-720",
                "name": "Cámara web HD",
                "available": 3,
                "requested": 4,
            },
            {
                "product_id": 9,
                "sku": "PR-400",
                "name": "Impresora láser",
                "available": 0,
                "requested": 1,
            },
        ]
        assert store.get_product(7).stock == 3
        assert store.get_product(9).stock == 0
        assert store.get_order(order.id).version == version

    def test_set_tax_rate_does_not_change_frozen_orders(self, store: Any) -> None:
        store.set_tax_rate(Decimal("7"))

        confirmed = store.get_order(2)
        draft = store.get_order(1)
        assert confirmed is not None
        assert draft is not None
        assert confirmed.tax_rate == SEED_RATE
        assert draft.tax_rate is None

    def test_replace_all_resets_content_and_sequences(
        self, store: Any, customer_repository: CustomerRepository
    ) -> None:
        product = Product(
            id=5,
            sku="NEW-1",
            name="Product",
            price=Decimal("2.00"),
            stock=9,
        )
        order = Order(
            id=4,
            number="PED-0004",
            status=OrderStatus.DRAFT,
            customer_id=1,
            lines=(OrderLine(7, 5, "NEW-1", "Product", 2, Decimal("2.00")),),
            tax_rate=None,
            version=1,
            created_at=NOW,
            updated_at=NOW,
            invoice_id=None,
        )

        store.replace_all([product], [order], Decimal("5.00"))

        assert store.list_products() == [product]
        assert store.get_tax_rate() == Decimal("5.00")
        items, total = store.list_orders(
            query=None, status=None, customer_id=None, page=1, page_size=20
        )
        assert total == 1
        assert items[0][0] == order

        created = store.create_order(1, LATER)
        assert created.id == 5
        assert created.number == "PED-0005"
        changed = store.add_line(created.id, 5, 1, None, LATER)
        assert changed.lines[0].id == 8

    def test_concurrent_confirms_of_the_same_order_leave_one_winner(self, store: Any) -> None:
        barrier = Barrier(2)

        def confirm() -> str:
            barrier.wait()
            try:
                store.transition(1, OrderAction.CONFIRM, 1, NOW)
            except VersionConflict:
                return "conflict"
            return "confirmed"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(confirm) for _ in range(2)]
            outcomes = [future.result(timeout=10) for future in futures]

        assert sorted(outcomes) == ["confirmed", "conflict"]
        assert store.get_order(1).version == 2
        assert store.get_product(1).stock == 118

    def test_two_orders_competing_for_the_last_units_leave_one_winner(self, store: Any) -> None:
        first = store.create_order(1, NOW)
        second = store.create_order(2, NOW)
        store.add_line(first.id, 7, 2, None, NOW)
        store.add_line(second.id, 7, 2, None, NOW)
        barrier = Barrier(2)

        def confirm(order_id: int) -> str:
            barrier.wait()
            try:
                store.transition(order_id, OrderAction.CONFIRM, None, NOW)
            except ApiError as error:
                if error.code == "INSUFFICIENT_STOCK":
                    return "shortage"
                raise
            return "confirmed"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(confirm, first.id),
                executor.submit(confirm, second.id),
            ]
            outcomes = [future.result(timeout=10) for future in futures]

        assert sorted(outcomes) == ["confirmed", "shortage"]
        assert store.get_product(7).stock == 1
