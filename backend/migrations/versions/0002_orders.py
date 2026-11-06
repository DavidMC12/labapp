"""Create the products, orders, order lines and settings tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.CheckConstraint("price > 0", name=op.f("ck_products_price")),
        sa.CheckConstraint("stock >= 0", name=op.f("ck_products_stock")),
    )
    op.create_index("products_sku_key", "products", ["sku"], unique=True)

    op.execute("CREATE SEQUENCE order_number_seq START WITH 1")

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_orders_customer_id_customers",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'paid', 'shipped', 'cancelled')",
            name=op.f("ck_orders_status"),
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name=op.f("ck_orders_tax_rate"),
        ),
    )
    op.create_index("orders_number_key", "orders", ["number"], unique=True)
    op.create_index(
        "orders_created_at_id_idx",
        "orders",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_order_lines"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_order_lines_order_id_orders",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_order_lines_product_id_products",
        ),
        sa.CheckConstraint(
            "quantity >= 1 AND quantity <= 999",
            name=op.f("ck_order_lines_quantity"),
        ),
    )
    op.create_index(
        "order_lines_order_product_key",
        "order_lines",
        ["order_id", "product_id"],
        unique=True,
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"])

    op.create_table(
        "settings",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_settings"),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_index("order_lines_order_product_key", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_index("orders_created_at_id_idx", table_name="orders")
    op.drop_index("orders_number_key", table_name="orders")
    op.drop_table("orders")
    op.execute("DROP SEQUENCE order_number_seq")
    op.drop_index("products_sku_key", table_name="products")
    op.drop_table("products")
