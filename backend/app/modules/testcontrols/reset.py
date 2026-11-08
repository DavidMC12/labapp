"""Restore the demo data for the test-only controls.

A reset and the ``default`` seed load the same rows; a reset additionally clears the
clock offset, the fault rules and the per-instance rate-limit counters. The four users
keep their ids and the sessions of those users survive, so a stored login keeps working.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Literal, Protocol

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.engine import Connection, Engine

from app.domain.money import quantize_money
from app.modules.auth.adapters.postgres import PostgresUserRepository
from app.modules.auth.models import User
from app.modules.auth.seed import demo_password_hash, seed_users
from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.seed import seed_orders, seed_products
from app.modules.orders.tables import settings as settings_table
from app.modules.testcontrols.memory import (
    InMemoryClockOffsetStore,
    InMemoryFaultStore,
)
from app.modules.testcontrols.postgres import CLOCK_OFFSET_KEY
from app.modules.testcontrols.tables import fault_rules

Dataset = Literal["default", "empty"]
RESET_LOCK_KEY = 7_500_024_001
RESET_CONFLICT = "RESET_CONFLICT"
RESET_CONFLICT_DETAIL = (
    "No se pudo reiniciar porque hay una operación en curso. Inténtalo de nuevo."
)


class Resetter(Protocol):
    """Restore the demo data on one application instance or database."""

    def reset(self) -> None:
        """Restore the data, the sequences, the tax rate, the clock and the faults."""
        ...

    def seed(self, dataset: Dataset) -> None:
        """Load the ``default`` data or leave only the users and the settings."""
        ...


class MemoryResetter:
    """Reset the in-memory stores, which are the test double of the controls."""

    def __init__(
        self,
        *,
        customers: InMemoryCustomerRepository,
        orders: InMemoryOrderStore,
        invoices: InMemoryInvoiceStore,
        clock_store: InMemoryClockOffsetStore,
        fault_store: InMemoryFaultStore,
        default_tax_rate: Decimal,
        reset_limiters: Callable[[], None] | None = None,
    ) -> None:
        self._customers = customers
        self._orders = orders
        self._invoices = invoices
        self._clock_store = clock_store
        self._fault_store = fault_store
        self._tax_rate = quantize_money(default_tax_rate)
        self._reset_limiters = reset_limiters

    def reset(self) -> None:
        self._restore_default()
        self._clock_store.set(0.0)
        self._fault_store.clear()
        if self._reset_limiters is not None:
            self._reset_limiters()

    def seed(self, dataset: Dataset) -> None:
        if dataset == "default":
            self._restore_default()
        elif dataset == "empty":
            self._restore_empty()
        else:
            raise ValueError(f"Unknown dataset: {dataset}")

    def _restore_default(self) -> None:
        self._invoices.replace_all([], [])
        self._orders.replace_all([], [], self._tax_rate)
        self._customers.replace_all(seed_customers())
        self._orders.replace_all(seed_products(), seed_orders(), self._tax_rate)
        self._invoices.replace_all(seed_invoices(), seed_payments())

    def _restore_empty(self) -> None:
        self._invoices.replace_all([], [])
        self._orders.replace_all([], [], self._tax_rate)
        self._customers.replace_all([])
        self._clock_store.set(0.0)
        self._fault_store.clear()


class PostgresResetter:
    """Reset PostgreSQL in one transaction, behind a transaction advisory lock."""

    def __init__(
        self,
        engine: Engine,
        *,
        customers: PostgresCustomerRepository,
        orders: PostgresOrderStore,
        invoices: PostgresInvoiceStore,
        default_tax_rate: Decimal,
    ) -> None:
        self._engine = engine
        self._users = PostgresUserRepository(engine)
        self._customers = customers
        self._orders = orders
        self._invoices = invoices
        self._tax_rate = quantize_money(default_tax_rate)

    def reset(self) -> None:
        # Argon2 is slow; compute the hash outside the transaction that holds locks.
        users = seed_users(demo_password_hash())
        with self._engine.begin() as connection:
            self._lock(connection)
            self._restore_default(connection)
            self._users.replace_all(users, connection=connection)
            self._write_clock(connection)
            connection.execute(delete(fault_rules))

    def seed(self, dataset: Dataset) -> None:
        users = seed_users(demo_password_hash())
        with self._engine.begin() as connection:
            self._lock(connection)
            if dataset == "default":
                self._restore_default(connection)
                self._users.replace_all(users, connection=connection)
            elif dataset == "empty":
                self._restore_empty(connection, users)
            else:
                raise ValueError(f"Unknown dataset: {dataset}")

    @staticmethod
    def _lock(connection: Connection) -> None:
        connection.execute(
            text("select pg_advisory_xact_lock(:key)"),
            {"key": RESET_LOCK_KEY},
        )

    def _restore_default(self, connection: Connection) -> None:
        self._invoices.replace_all([], [], connection=connection)
        self._orders.replace_all([], [], self._tax_rate, connection=connection)
        self._customers.replace_all(seed_customers(), connection=connection)
        self._orders.replace_all(
            seed_products(),
            seed_orders(),
            self._tax_rate,
            connection=connection,
        )
        self._invoices.replace_all(seed_invoices(), seed_payments(), connection=connection)

    def _restore_empty(self, connection: Connection, users: list[User]) -> None:
        self._invoices.replace_all([], [], connection=connection)
        self._orders.replace_all([], [], self._tax_rate, connection=connection)
        self._customers.replace_all([], connection=connection)
        self._users.replace_all(users, connection=connection)
        self._write_clock(connection)
        connection.execute(delete(fault_rules))

    @staticmethod
    def _write_clock(connection: Connection) -> None:
        statement = postgres_insert(settings_table).values(
            key=CLOCK_OFFSET_KEY,
            value="0",
        )
        statement = statement.on_conflict_do_update(
            index_elements=[settings_table.c.key],
            set_={"value": statement.excluded.value},
        )
        connection.execute(statement)


__all__ = [
    "Dataset",
    "MemoryResetter",
    "PostgresResetter",
    "RESET_CONFLICT",
    "RESET_CONFLICT_DETAIL",
    "RESET_LOCK_KEY",
    "Resetter",
]
