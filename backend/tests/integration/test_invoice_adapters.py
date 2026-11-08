"""The invoice store contract against PostgreSQL."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine

from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.orders.adapters.postgres import PostgresOrderStore
from tests.invoices.contract_store import CountingGateway, InvoiceStoreContract


class TestPostgresInvoiceStore(InvoiceStoreContract):
    @pytest.fixture
    def customer_repository(
        self, order_customers: PostgresCustomerRepository
    ) -> PostgresCustomerRepository:
        return order_customers

    @pytest.fixture
    def order_store(self, postgres_order_store: PostgresOrderStore) -> PostgresOrderStore:
        return postgres_order_store

    @pytest.fixture
    def store(
        self,
        postgres_order_store: PostgresOrderStore,
        gateway: CountingGateway,
        unpinned_database_engine: Engine,
    ) -> PostgresInvoiceStore:
        store = PostgresInvoiceStore(unpinned_database_engine, gateway)
        store.replace_all(seed_invoices(), seed_payments())
        return store
