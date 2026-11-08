"""Command-line entry point for database maintenance."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

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
from app.modules.testcontrols.reset import PostgresResetter

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "migrations" / "alembic.ini"
OPENAPI_EXPORT_SECRET = "openapi-export"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def build_parser() -> argparse.ArgumentParser:
    """Return the parser for the database commands."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Apply the database migrations")
    subparsers.add_parser("seed", help="Load the demo data into an empty database")
    openapi = subparsers.add_parser(
        "openapi",
        help="Print the OpenAPI document of the application",
    )
    openapi.add_argument(
        "--output",
        metavar="FILE",
        help="Write the document to FILE instead of standard output",
    )
    reset = subparsers.add_parser(
        "reset",
        help="Restore the demo data (local use, requires TEST_MODE=1)",
        allow_abbrev=False,
    )
    reset.add_argument(
        "--yes",
        action="store_true",
        help="Confirm that the data will be replaced",
    )
    reset.add_argument(
        "--allow-public",
        action="store_true",
        help="Allow the reset when DATABASE_SCHEMA is unset (it wipes public)",
    )
    reset.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow the reset against a host other than localhost",
    )
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


def openapi_document() -> dict[str, Any]:
    """Build the OpenAPI document without a database and without environment variables."""
    # Importing app.main also builds its module-level application, whose startup guard
    # rejects an empty or default SESSION_SECRET; the playground secret below is enough for
    # that. The exported application is built again with no database and its own settings.
    previous = os.environ.get("SESSION_SECRET")
    os.environ["SESSION_SECRET"] = OPENAPI_EXPORT_SECRET
    try:
        from app.main import create_app
    finally:
        if previous is None:
            os.environ.pop("SESSION_SECRET", None)
        else:
            os.environ["SESSION_SECRET"] = previous
    application = create_app(Settings(session_secret=OPENAPI_EXPORT_SECRET, database_url=None))
    return application.openapi()


def render_openapi(document: Mapping[str, Any]) -> str:
    """Return the document as the JSON text that the command and the tests compare."""
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["settings"] = settings
    return config


def reset_refusal(
    *,
    test_mode: bool,
    schema: str | None,
    yes: bool,
    allow_public: bool,
    host: str | None = None,
    allow_remote: bool = False,
) -> str | None:
    """Say why a local reset must not run, or ``None`` to go ahead."""
    if not test_mode or not yes:
        return "Refusing to reset: TEST_MODE=1 and --yes are both required."
    if host is not None and host not in LOCAL_HOSTS and not allow_remote:
        return f"Refusing to reset: {host} is not a local host. Pass --allow-remote to allow it."
    if schema is None and not allow_public:
        return (
            "Refusing to reset: DATABASE_SCHEMA is unset and the public schema would "
            "be wiped. Pass --allow-public to allow it."
        )
    return None


def reset_database(settings: Settings) -> None:
    """Restore the demo data in the configured database."""
    engine = create_db_engine(settings)
    try:
        resetter = PostgresResetter(
            engine,
            customers=PostgresCustomerRepository(engine),
            orders=PostgresOrderStore(engine),
            invoices=PostgresInvoiceStore(engine, FakeGateway()),
            default_tax_rate=settings.default_tax_rate,
        )
        resetter.reset()
    finally:
        engine.dispose()


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
    elif arguments.command == "openapi":
        text = render_openapi(openapi_document())
        if arguments.output is None:
            sys.stdout.write(text)
        else:
            Path(arguments.output).write_text(text, encoding="utf-8")
    elif arguments.command == "reset":
        settings = Settings()
        url = make_url(settings.database_url) if settings.database_url is not None else None
        host = url.host if url is not None else None
        reason = reset_refusal(
            test_mode=settings.test_mode,
            schema=settings.database_schema,
            yes=arguments.yes,
            allow_public=arguments.allow_public,
            host=host,
            allow_remote=arguments.allow_remote,
        )
        if reason is not None:
            print(reason)
            return 2
        if url is None:
            print("Refusing to reset: DATABASE_URL is not set.")
            return 2
        database = url.database or "unknown"
        print(
            f"Resetting database {database} on host {host or 'local'} "
            f"schema {settings.database_schema or 'public'}."
        )
        reset_database(settings)
        print("Database reset complete.")
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
