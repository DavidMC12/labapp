"""Rows used by the PostgreSQL integration tests."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Connection, text

from app.modules.customers.search import normalize_for_search

NOW = datetime(2026, 1, 2, 12, 0, 0, 123456, tzinfo=UTC)


def table_names(connection: Connection, schema: str) -> set[str]:
    rows = connection.execute(
        text("select table_name from information_schema.tables where table_schema = :schema"),
        {"schema": schema},
    )
    return set(rows.scalars())


def insert_user(
    connection: Connection,
    *,
    email: str = "user@example.test",
    role: str = "admin",
    user_id: int | None = None,
    name: str = "Test User",
    password_hash: str = "test-hash",
    created_at: datetime = NOW,
) -> int:
    columns = ["name", "email", "role", "password_hash", "created_at"]
    values: dict[str, object] = {
        "name": name,
        "email": email,
        "role": role,
        "password_hash": password_hash,
        "created_at": created_at,
    }
    if user_id is not None:
        columns.insert(0, "id")
        values["id"] = user_id
    statement = text(
        f"INSERT INTO users ({', '.join(columns)}) "
        f"VALUES ({', '.join(f':{column}' for column in columns)}) "
        "RETURNING id"
    )
    return connection.execute(statement, values).scalar_one()


def insert_session(
    connection: Connection,
    *,
    user_id: int,
    token_hash: str = "test-token-hash",
    created_at: datetime = NOW,
    last_seen_at: datetime = NOW,
) -> None:
    connection.execute(
        text(
            "INSERT INTO sessions (token_hash, user_id, created_at, last_seen_at) "
            "VALUES (:token_hash, :user_id, :created_at, :last_seen_at)"
        ),
        {
            "token_hash": token_hash,
            "user_id": user_id,
            "created_at": created_at,
            "last_seen_at": last_seen_at,
        },
    )


def insert_customer(
    connection: Connection,
    *,
    email: str = "customer@example.test",
    status: str = "active",
    name: str = "Test Customer",
    version: int = 1,
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
) -> int:
    statement = text(
        "INSERT INTO customers "
        "(name, email, status, version, created_at, updated_at, name_search, email_search) "
        "VALUES (:name, :email, :status, :version, :created_at, :updated_at, "
        ":name_search, :email_search) "
        "RETURNING id"
    )
    return connection.execute(
        statement,
        {
            "name": name,
            "email": email,
            "status": status,
            "version": version,
            "created_at": created_at,
            "updated_at": updated_at,
            "name_search": normalize_for_search(name),
            "email_search": normalize_for_search(email),
        },
    ).scalar_one()
