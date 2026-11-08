"""Allow at most one approved payment per invoice.

The demo seed has no invoice with two approved payments: invoices 2 and 3 have
one each and invoice 1 only has a declined and a failed attempt, so the index can
be built on the existing data.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_payments_one_approved_per_invoice",
        "payments",
        ["invoice_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )


def downgrade() -> None:
    op.drop_index("uq_payments_one_approved_per_invoice", table_name="payments")
