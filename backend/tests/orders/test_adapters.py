"""Contract tests for the in-memory order store."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.seed import seed_orders, seed_products
from tests.orders.contract_store import OrderStoreContract


class TestInMemoryOrderStore(OrderStoreContract):
    @pytest.fixture
    def customer_repository(self) -> InMemoryCustomerRepository:
        return InMemoryCustomerRepository(seed_customers())

    @pytest.fixture
    def store(self, customer_repository: InMemoryCustomerRepository) -> InMemoryOrderStore:
        store = InMemoryOrderStore(customer_repository)
        store.replace_all(seed_products(), seed_orders(), Decimal("10.00"))
        return store
