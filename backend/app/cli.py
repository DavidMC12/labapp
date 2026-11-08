"""Command-line entry point for database maintenance."""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from app.config import Settings
from app.domain.money import quantize_money
from app.infra.db import create_db_engine
from app.modules.auth.adapters.postgres import PostgresUserRepository
from app.modules.auth.seed import demo_password_hash, seed_users
from app.modules.auth.tables import users
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.customers.seed import seed_customers
from app.modules.customers.tables import customers
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.invoices.tables import invoices as invoices_table
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.seed import seed_orders, seed_products
from app.modules.orders.tables import orders as orders_table
from app.modules.orders.tables import products as products_table

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "migrations" / "alembic.ini"


def build_parser() -> argparse.ArgumentParser:
    """Return the parser for the database commands."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Apply the database migrations")
    subparsers.add_parser("seed", help="Load the demo data into an empty database")
    deploy = subparsers.add_parser(
        "deploy",
        help="Migrate and seed an empty database (the platform build hook)",
    )
    deploy.add_argument(
        "--production-only",
        action="store_true",
        help="Do nothing on a preview deployment (VERCEL_ENV is set and is not production)",
    )
    return parser


def skip_reason(production_only: bool, environment: Mapping[str, str]) -> str | None:
    """Say why a deployment hook must not touch the database, or ``None`` to go ahead.

    Preview deployments of a branch share the database unless the platform gives each one its
    own branch of it, so a new or destructive migration of an unmerged branch would change the
    schema that production uses. ``RUN_MIGRATIONS_ON_PREVIEW=1`` opts in once every preview
    has its own database.
    """
    if not production_only or environment.get("RUN_MIGRATIONS_ON_PREVIEW") == "1":
        return None
    deployment = environment.get("VERCEL_ENV")
    if deployment and deployment != "production":
        return f"Skipping the database setup on a {deployment} deployment."
    return None


def _alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["settings"] = settings
    return config


def seed_database(settings: Settings) -> None:
    """Fill empty tables, leaving existing data untouched."""
    engine = create_db_engine(settings)
    try:
        with engine.begin() as connection:
            users_empty = (
                connection.execute(select(func.count()).select_from(users)).scalar_one() == 0
            )
            customers_empty = (
                connection.execute(select(func.count()).select_from(customers)).scalar_one() == 0
            )
            products_empty = (
                connection.execute(select(func.count()).select_from(products_table)).scalar_one()
                == 0
            )
            orders_empty = (
                connection.execute(select(func.count()).select_from(orders_table)).scalar_one() == 0
            )
            invoices_empty = (
                connection.execute(select(func.count()).select_from(invoices_table)).scalar_one()
                == 0
            )
        if users_empty:
            PostgresUserRepository(engine).replace_all(seed_users(demo_password_hash()))
        if customers_empty:
            PostgresCustomerRepository(engine).replace_all(seed_customers())
        if products_empty and orders_empty:
            PostgresOrderStore(engine).replace_all(
                seed_products(),
                seed_orders(),
                quantize_money(settings.default_tax_rate),
            )
        if invoices_empty:
            PostgresInvoiceStore(engine, FakeGateway()).replace_all(
                seed_invoices(),
                seed_payments(),
            )
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
    elif arguments.command == "deploy":
        reason = skip_reason(arguments.production_only, os.environ)
        if reason is not None:
            print(reason)
            return 0
        settings = Settings()
        command.upgrade(_alembic_config(settings), "head")
        seed_database(settings)
        print("Database migrated and seeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
