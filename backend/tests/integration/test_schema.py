"""The migration builds the expected schema inside the test schema."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, text

from tests.integration.helpers import table_names

APP_TABLES = {
    "users",
    "sessions",
    "customers",
    "products",
    "orders",
    "order_lines",
    "settings",
}
APP_INDEXES = {
    "users_email_lower_key",
    "sessions_last_seen_at_idx",
    "customers_email_lower_key",
    "customers_created_at_id_idx",
    "products_sku_key",
    "orders_number_key",
    "orders_created_at_id_idx",
    "ix_orders_customer_id",
    "order_lines_order_product_key",
    "ix_order_lines_order_id",
}
APP_CHECKS = {
    "ck_users_role",
    "ck_customers_status",
    "ck_products_price",
    "ck_products_stock",
    "ck_orders_status",
    "ck_orders_tax_rate",
    "ck_order_lines_quantity",
}


def _index_names(connection: Connection, schema: str) -> set[str]:
    rows = connection.execute(
        text("select indexname from pg_indexes where schemaname = :schema"),
        {"schema": schema},
    )
    return set(rows.scalars())


def _check_names(connection: Connection, schema: str) -> set[str]:
    rows = connection.execute(
        text(
            "select constraint_row.conname "
            "from pg_constraint constraint_row "
            "join pg_class relation on relation.oid = constraint_row.conrelid "
            "join pg_namespace namespace on namespace.oid = relation.relnamespace "
            "where constraint_row.contype = 'c' and namespace.nspname = :schema"
        ),
        {"schema": schema},
    )
    return set(rows.scalars())


def test_upgrade_creates_the_tables_in_the_test_schema(
    db: Connection, database_schema: str
) -> None:
    assert APP_TABLES <= table_names(db, database_schema)
    assert table_names(db, "public").isdisjoint(APP_TABLES)


def test_upgrade_creates_the_named_indexes_and_checks(db: Connection, database_schema: str) -> None:
    assert APP_INDEXES <= _index_names(db, database_schema)
    assert APP_CHECKS <= _check_names(db, database_schema)


def test_downgrade_then_upgrade_works(
    database_engine: Engine, alembic_config: Config, database_schema: str
) -> None:
    command.downgrade(alembic_config, "base")
    with database_engine.connect() as connection:
        assert table_names(connection, database_schema).isdisjoint(APP_TABLES)

    command.upgrade(alembic_config, "head")
    with database_engine.connect() as connection:
        assert APP_TABLES <= table_names(connection, database_schema)


def test_two_concurrent_migrations_wait_for_each_other(
    database_engine: Engine, alembic_config: Config, database_schema: str
) -> None:
    """Two builds that migrate at once must both succeed: the second waits on the lock."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    command.downgrade(alembic_config, "base")
    environment = {
        **os.environ,
        "DATABASE_URL_UNPOOLED": os.environ["TEST_DATABASE_URL"],
        "DATABASE_SCHEMA": database_schema,
        "SESSION_SECRET": "test-secret",
    }
    environment.pop("DATABASE_URL", None)
    backend_dir = Path(__file__).resolve().parents[2]
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "app.cli", "migrate"],
            cwd=backend_dir,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for _ in range(2)
    ]
    outputs = [process.communicate(timeout=120)[0] for process in processes]

    assert [process.returncode for process in processes] == [0, 0], outputs
    with database_engine.connect() as connection:
        assert APP_TABLES <= table_names(connection, database_schema)
