"""Contract tests for the in-memory invoice store."""

from __future__ import annotations

from decimal import Decimal
from threading import RLock

import pytest

from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.seed import seed_orders, seed_products
from tests.invoices.contract_store import CountingGateway, InvoiceStoreContract


class TestInMemoryInvoiceStore(InvoiceStoreContract):
    @pytest.fixture
    def customer_repository(self) -> InMemoryCustomerRepository:
        return InMemoryCustomerRepository(seed_customers())

    @pytest.fixture
    def shared_lock(self) -> RLock:
        return RLock()

    @pytest.fixture
    def order_store(
        self,
        customer_repository: InMemoryCustomerRepository,
        shared_lock: RLock,
    ) -> InMemoryOrderStore:
        store = InMemoryOrderStore(customer_repository, lock=shared_lock)
        store.replace_all(seed_products(), seed_orders(), Decimal("10.00"))
        return store

    @pytest.fixture
    def store(
        self,
        order_store: InMemoryOrderStore,
        customer_repository: InMemoryCustomerRepository,
        gateway: CountingGateway,
        shared_lock: RLock,
    ) -> InMemoryInvoiceStore:
        store = InMemoryInvoiceStore(
            order_store,
            customer_repository,
            gateway,
            lock=shared_lock,
        )
        store.replace_all(seed_invoices(), seed_payments())
        order_store.invoices = store
        return store
