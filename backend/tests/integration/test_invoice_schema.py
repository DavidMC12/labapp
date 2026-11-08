"""The invoice migration builds the expected schema and the circular foreign key."""

from __future__ import annotations

from sqlalchemy import Connection, text

from tests.integration.helpers import table_names

INVOICE_TABLES = {
    "invoices",
    "invoice_lines",
    "payments",
    "idempotency_keys",
}


def test_the_invoice_tables_exist_in_the_test_schema(db: Connection, database_schema: str) -> None:
    assert INVOICE_TABLES <= table_names(db, database_schema)
    assert table_names(db, "public").isdisjoint(INVOICE_TABLES)


def test_the_circular_foreign_key_sets_the_order_invoice_to_null(
    db: Connection, database_schema: str
) -> None:
    action = db.execute(
        text(
            "select constraint_row.confdeltype "
            "from pg_constraint constraint_row "
            "join pg_class relation on relation.oid = constraint_row.conrelid "
            "join pg_namespace namespace on namespace.oid = relation.relnamespace "
            "where constraint_row.conname = 'fk_orders_invoice_id_invoices' "
            "and namespace.nspname = :schema"
        ),
        {"schema": database_schema},
    ).scalar_one()

    assert action == "n"
