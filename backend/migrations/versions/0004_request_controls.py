"""Create the fault rules table and the clock offset setting.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fault_rules",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("remaining", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fault_rules"),
        sa.CheckConstraint("target IN ('route', 'gateway')", name=op.f("ck_fault_rules_target")),
        sa.CheckConstraint(
            "method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')",
            name=op.f("ck_fault_rules_method"),
        ),
        sa.CheckConstraint(
            "latency_ms >= 0 AND latency_ms <= 10000",
            name=op.f("ck_fault_rules_latency_ms"),
        ),
        sa.CheckConstraint(
            "status >= 400 AND status <= 599",
            name=op.f("ck_fault_rules_status"),
        ),
        sa.CheckConstraint("remaining >= 0", name=op.f("ck_fault_rules_remaining")),
    )
    op.execute("INSERT INTO settings (key, value) VALUES ('clock_offset_seconds', '0')")


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'clock_offset_seconds'")
    op.drop_table("fault_rules")
