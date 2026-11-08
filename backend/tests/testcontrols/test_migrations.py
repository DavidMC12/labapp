"""The request controls migration joins the chain after the invoice migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = BACKEND_DIR / "migrations" / "versions"
REVISION_3_PATH = MIGRATIONS_DIR / "0003_invoices.py"
REVISION_4_PATH = MIGRATIONS_DIR / "0004_request_controls.py"


def _load_revision(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_revision_chain_is_0003_then_0004() -> None:
    third = _load_revision(REVISION_3_PATH, "migration_0003")
    fourth = _load_revision(REVISION_4_PATH, "migration_0004")

    assert fourth.revision == "0004"  # type: ignore[attr-defined]
    assert fourth.down_revision == third.revision  # type: ignore[attr-defined]
    assert callable(fourth.upgrade)  # type: ignore[attr-defined]
    assert callable(fourth.downgrade)  # type: ignore[attr-defined]


class _RecordingOp:
    """Record the statements of the migration without touching a database."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def create_table(self, *args: object, **kwargs: object) -> None:
        pass

    def drop_table(self, *args: object, **kwargs: object) -> None:
        pass

    def f(self, name: str) -> str:
        return name

    def execute(self, statement: object) -> None:
        self.statements.append(str(statement))


def test_the_migration_keeps_an_existing_clock_row() -> None:
    migration = _load_revision(REVISION_4_PATH, "migration_0004")
    recorder = _RecordingOp()
    migration.op = recorder  # type: ignore[attr-defined]

    migration.upgrade()  # type: ignore[attr-defined]

    inserts = [
        statement for statement in recorder.statements if "INSERT INTO settings" in statement
    ]
    assert len(inserts) == 1
    assert "ON CONFLICT (key) DO NOTHING" in inserts[0]
