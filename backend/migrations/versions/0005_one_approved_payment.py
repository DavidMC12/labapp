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

DUPLICATES_QUERY = (
    "SELECT invoice_id FROM payments WHERE status = 'approved' "
    "GROUP BY invoice_id HAVING count(*) > 1 ORDER BY invoice_id"
)


def _refuse_duplicates() -> None:
    """Fail with a readable message before the index build hides the cause."""
    rows = op.get_bind().execute(sa.text(DUPLICATES_QUERY))
    invoice_ids = [row[0] for row in rows]
    if invoice_ids:
        listed = ", ".join(str(identifier) for identifier in invoice_ids)
        raise RuntimeError(
            "Cannot create the one-approved-payment index: invoices with more than one "
            f"approved payment: {listed}. Resolve them before migrating."
        )


def upgrade() -> None:
    _refuse_duplicates()
    op.create_index(
        "uq_payments_one_approved_per_invoice",
        "payments",
        ["invoice_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )


def downgrade() -> None:
    op.drop_index("uq_payments_one_approved_per_invoice", table_name="payments")
