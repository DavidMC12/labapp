"""Create the users, sessions and customers tables.

Revision ID: 0001
Revises:
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.CheckConstraint(
            "role IN ('admin', 'sales', 'finance', 'readonly')",
            name="ck_users_role",
        ),
    )
    op.create_index(
        "users_email_lower_key",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("token_hash", name="pk_sessions"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_sessions_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index("sessions_last_seen_at_idx", "sessions", ["last_seen_at"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("tax_id", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name_search", sa.Text(), nullable=False),
        sa.Column("email_search", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_customers_status"),
    )
    op.create_index(
        "customers_email_lower_key",
        "customers",
        [sa.text("lower(email)")],
        unique=True,
    )
    op.create_index(
        "customers_created_at_id_idx",
        "customers",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("customers_created_at_id_idx", table_name="customers")
    op.drop_index("customers_email_lower_key", table_name="customers")
    op.drop_table("customers")
    op.drop_index("sessions_last_seen_at_idx", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("users_email_lower_key", table_name="users")
    op.drop_table("users")
