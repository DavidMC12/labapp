"""Command-line entry point for database maintenance."""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from app.config import Settings
from app.infra.db import create_db_engine
from app.modules.auth.adapters.postgres import PostgresUserRepository
from app.modules.auth.seed import demo_password_hash, seed_users
from app.modules.auth.tables import users
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.customers.tables import customers

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "migrations" / "alembic.ini"


def build_parser() -> argparse.ArgumentParser:
    """Return the parser for the database commands."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Apply the database migrations")
    subparsers.add_parser("seed", help="Load the demo data into an empty database")
    return parser


def _alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["settings"] = settings
    return config


def seed_database(settings: Settings) -> None:
    """Fill empty users and customers tables, leaving existing data untouched."""
    engine = create_db_engine(settings)
    try:
        with engine.begin() as connection:
            users_empty = (
                connection.execute(select(func.count()).select_from(users)).scalar_one() == 0
            )
            customers_empty = (
                connection.execute(select(func.count()).select_from(customers)).scalar_one() == 0
            )
        if users_empty:
            PostgresUserRepository(engine).replace_all(seed_users(demo_password_hash()))
        if customers_empty:
            PostgresCustomerRepository(engine).replace_all(seed_customers())
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "migrate":
        command.upgrade(_alembic_config(Settings()), "head")
        print("Database migrated to the latest revision.")
    elif arguments.command == "seed":
        seed_database(Settings())
        print("Database seed complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
