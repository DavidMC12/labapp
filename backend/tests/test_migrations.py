from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory

import app.cli as cli_module
from app.cli import _alembic_config, build_parser
from app.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
REVISION_PATH = MIGRATIONS_DIR / "versions" / "0001_initial.py"


def _load_revision() -> object:
    spec = importlib.util.spec_from_file_location("migration_0001", REVISION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_is_the_initial_one_and_has_both_directions() -> None:
    module = _load_revision()

    assert module.revision == "0001"  # type: ignore[attr-defined]
    assert module.down_revision is None  # type: ignore[attr-defined]
    assert callable(module.upgrade)  # type: ignore[attr-defined]
    assert callable(module.downgrade)  # type: ignore[attr-defined]


def test_alembic_ini_resolves_from_any_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    config = _alembic_config(Settings())

    assert config.config_file_name is not None
    assert Path(config.config_file_name).resolve() == MIGRATIONS_DIR / "alembic.ini"
    assert config.get_main_option("sqlalchemy.url") is None
    script = ScriptDirectory.from_config(config)
    assert Path(script.dir).resolve() == MIGRATIONS_DIR
    assert script.get_heads() == ["0001"]


def test_cli_parses_migrate() -> None:
    arguments = build_parser().parse_args(["migrate"])

    assert arguments.command == "migrate"


def test_cli_parses_seed() -> None:
    arguments = build_parser().parse_args(["seed"])

    assert arguments.command == "seed"


def test_cli_dispatches_seed_without_a_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setattr(cli_module, "seed_database", calls.append)

    assert cli_module.main(["seed"]) == 0

    assert len(calls) == 1


@pytest.mark.parametrize("argv", [[], ["unknown"], ["migrate", "extra"]])
def test_cli_rejects_anything_else(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as info:
        build_parser().parse_args(argv)

    assert info.value.code == 2
