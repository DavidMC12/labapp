"""Command-line entry point for database maintenance."""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import Settings

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "migrations" / "alembic.ini"


def build_parser() -> argparse.ArgumentParser:
    """Return the parser; only ``migrate`` is available in this task."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Apply the database migrations")
    return parser


def _alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["settings"] = settings
    return config


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "migrate":
        command.upgrade(_alembic_config(Settings()), "head")
        print("Database migrated to the latest revision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
