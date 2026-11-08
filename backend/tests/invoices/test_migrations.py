"""The invoice migration joins the chain and adds the partial unique index."""

from __future__ import annotations

import importlib.util
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = BACKEND_DIR / "migrations" / "versions"
REVISION_1_PATH = MIGRATIONS_DIR / "0001_initial.py"
REVISION_2_PATH = MIGRATIONS_DIR / "0002_orders.py"
REVISION_3_PATH = MIGRATIONS_DIR / "0003_invoices.py"
REVISION_4_PATH = MIGRATIONS_DIR / "0004_request_controls.py"
REVISION_5_PATH = MIGRATIONS_DIR / "0005_one_approved_payment.py"


def _load_revision(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_revision_chain_reaches_the_payment_status_index() -> None:
    first = _load_revision(REVISION_1_PATH, "migration_0001")
    second = _load_revision(REVISION_2_PATH, "migration_0002")
    third = _load_revision(REVISION_3_PATH, "migration_0003")
    fourth = _load_revision(REVISION_4_PATH, "migration_0004")
    fifth = _load_revision(REVISION_5_PATH, "migration_0005")

    assert second.down_revision == first.revision  # type: ignore[attr-defined]
    assert third.revision == "0003"  # type: ignore[attr-defined]
    assert third.down_revision == second.revision  # type: ignore[attr-defined]
    assert fourth.down_revision == third.revision  # type: ignore[attr-defined]
    assert fifth.revision == "0005"  # type: ignore[attr-defined]
    assert fifth.down_revision == fourth.revision  # type: ignore[attr-defined]
    assert callable(fifth.upgrade)  # type: ignore[attr-defined]
    assert callable(fifth.downgrade)  # type: ignore[attr-defined]


class _RecordingOp:
    """Record the statements of the migration without touching a database."""

    def __init__(self) -> None:
        self.created: list[tuple[str, str, list[str], bool, str | None]] = []
        self.dropped: list[tuple[str, str]] = []

    def create_index(
        self,
        name: str,
        table_name: str,
        columns: list[str],
        *,
        unique: bool = False,
        postgresql_where: object | None = None,
    ) -> None:
        self.created.append((name, table_name, columns, unique, str(postgresql_where)))

    def drop_index(self, name: str, *, table_name: str) -> None:
        self.dropped.append((name, table_name))


def test_the_migration_adds_and_drops_the_partial_unique_index() -> None:
    migration = _load_revision(REVISION_5_PATH, "migration_0005")
    recorder = _RecordingOp()
    migration.op = recorder  # type: ignore[attr-defined]

    migration.upgrade()  # type: ignore[attr-defined]
    migration.downgrade()  # type: ignore[attr-defined]

    assert recorder.created == [
        (
            "uq_payments_one_approved_per_invoice",
            "payments",
            ["invoice_id"],
            True,
            "status = 'approved'",
        )
    ]
    assert recorder.dropped == [("uq_payments_one_approved_per_invoice", "payments")]
