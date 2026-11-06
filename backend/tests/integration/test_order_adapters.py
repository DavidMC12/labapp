"""The order store contract against PostgreSQL."""

from __future__ import annotations

import pytest

from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.orders.adapters.postgres import PostgresOrderStore
from tests.orders.contract_store import OrderStoreContract


class TestPostgresOrderStore(OrderStoreContract):
    @pytest.fixture
    def customer_repository(
        self, order_customers: PostgresCustomerRepository
    ) -> PostgresCustomerRepository:
        return order_customers

    @pytest.fixture
    def store(self, order_store: PostgresOrderStore) -> PostgresOrderStore:
        return order_store
