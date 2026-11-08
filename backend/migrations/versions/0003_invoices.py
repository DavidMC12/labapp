"""Create the invoices, invoice lines, payments and idempotency key tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("order_number", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.Text(), nullable=False),
        sa.Column("customer_name_search", sa.Text(), nullable=False),
        sa.Column("customer_tax_id", sa.Text(), nullable=False),
        sa.Column("customer_address", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_invoices"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_invoices_order_id_orders",
        ),
        sa.CheckConstraint(
            "status IN ('issued', 'paid', 'void')",
            name=op.f("ck_invoices_status"),
        ),
    )
    op.create_index("invoices_number_key", "invoices", ["number"], unique=True)
    op.create_index("invoices_order_key", "invoices", ["order_id"], unique=True)
    op.create_index(
        "invoices_created_at_id_idx",
        "invoices",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_invoice_lines"),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_invoice_lines_invoice_id_invoices",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("card_last4", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_payments_invoice_id_invoices",
        ),
        sa.CheckConstraint(
            "method IN ('card', 'transfer', 'cash')",
            name=op.f("ck_payments_method"),
        ),
        sa.CheckConstraint(
            "status IN ('approved', 'declined', 'failed')",
            name=op.f("ck_payments_status"),
        ),
        sa.CheckConstraint(
            "card_last4 IS NULL OR card_last4 ~ '^[0-9]{4}$'",
            name=op.f("ck_payments_card_last4"),
        ),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("invoice_id", "key", name="pk_idempotency_keys"),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_idempotency_keys_invoice_id_invoices",
        ),
    )

    op.execute("CREATE SEQUENCE invoice_number_seq START WITH 1")

    # The cycle orders.invoice_id -> invoices.order_id. ON DELETE SET NULL lets a
    # replace_all empty one table before the other.
    op.create_foreign_key(
        op.f("fk_orders_invoice_id_invoices"),
        "orders",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_orders_invoice_id_invoices"), "orders", type_="foreignkey")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index("invoices_created_at_id_idx", table_name="invoices")
    op.drop_index("invoices_order_key", table_name="invoices")
    op.drop_index("invoices_number_key", table_name="invoices")
    op.drop_table("invoices")
    op.execute("DROP SEQUENCE invoice_number_seq")
