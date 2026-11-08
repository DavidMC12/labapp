"""The invoice migration joins the chain after the orders migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = BACKEND_DIR / "migrations" / "versions"
REVISION_1_PATH = MIGRATIONS_DIR / "0001_initial.py"
REVISION_2_PATH = MIGRATIONS_DIR / "0002_orders.py"
REVISION_3_PATH = MIGRATIONS_DIR / "0003_invoices.py"


def _load_revision(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_revision_chain_is_0001_then_0002_then_0003() -> None:
    first = _load_revision(REVISION_1_PATH, "migration_0001")
    second = _load_revision(REVISION_2_PATH, "migration_0002")
    third = _load_revision(REVISION_3_PATH, "migration_0003")

    assert second.down_revision == first.revision  # type: ignore[attr-defined]
    assert third.revision == "0003"  # type: ignore[attr-defined]
    assert third.down_revision == second.revision  # type: ignore[attr-defined]
    assert callable(third.upgrade)  # type: ignore[attr-defined]
    assert callable(third.downgrade)  # type: ignore[attr-defined]
