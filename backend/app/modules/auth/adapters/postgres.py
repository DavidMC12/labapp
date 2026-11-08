"""PostgreSQL adapters for the authentication ports."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import nullcontext
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, cast, delete, func, literal, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.engine import Connection, Engine

from app.domain.permissions import Role
from app.infra.db import as_utc, qualified_table_name
from app.modules.auth.adapters.memory import MAX_SESSIONS
from app.modules.auth.models import Session, User
from app.modules.auth.tables import sessions, users

_SESSION_LOCK_KEY = 7_412_019_001


def _user_from_row(row: Mapping[str, Any]) -> User:
    return User(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        role=Role(row["role"]),
        password_hash=row["password_hash"],
        created_at=as_utc(row["created_at"]),
        version=row["version"],
    )


def _session_from_row(row: Mapping[str, Any]) -> Session:
    return Session(
        token_hash=row["token_hash"],
        user_id=row["user_id"],
        created_at=as_utc(row["created_at"]),
        last_seen_at=as_utc(row["last_seen_at"]),
    )


class PostgresUserRepository:
    """A user repository backed by PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        with self._engine.begin() as connection:
            row = (
                connection.execute(select(users).where(func.lower(users.c.email) == normalized))
                .mappings()
                .first()
            )
        return _user_from_row(row) if row is not None else None

    def get_by_id(self, id: int) -> User | None:
        with self._engine.begin() as connection:
            row = connection.execute(select(users).where(users.c.id == id)).mappings().first()
        return _user_from_row(row) if row is not None else None

    def replace_all(
        self,
        replacement: Iterable[User],
        *,
        connection: Connection | None = None,
    ) -> None:
        """Replace the users, keeping the sessions of the users that remain.

        With ``connection`` it runs inside the caller's transaction and does not open
        its own; without it, the replacement is one transaction.
        """
        replacements = list(replacement)
        ids = [user.id for user in replacements]
        next_id = max(ids, default=0) + 1
        context = nullcontext(connection) if connection is not None else self._engine.begin()
        with context as connection:
            if ids:
                connection.execute(delete(users).where(users.c.id.not_in(ids)))
            else:
                connection.execute(delete(users))
            if replacements:
                statement = postgres_insert(users).values(
                    [
                        {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role.value,
                            "password_hash": user.password_hash,
                            "created_at": user.created_at,
                            "version": user.version,
                        }
                        for user in replacements
                    ]
                )
                statement = statement.on_conflict_do_update(
                    index_elements=[users.c.id],
                    set_={
                        "name": statement.excluded.name,
                        "email": statement.excluded.email,
                        "role": statement.excluded.role,
                        "password_hash": statement.excluded.password_hash,
                        "created_at": statement.excluded.created_at,
                        "version": statement.excluded.version,
                    },
                )
                connection.execute(statement)
            connection.execute(
                text("select setval(pg_get_serial_sequence(:table_name, 'id'), :next_id, false)"),
                {
                    "table_name": qualified_table_name(self._engine, users),
                    "next_id": next_id,
                },
            )


class PostgresSessionStore:
    """A session store backed by PostgreSQL and bounded to a maximum."""

    def __init__(self, engine: Engine, max_sessions: int = MAX_SESSIONS) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be at least 1")
        self._engine = engine
        self._max_sessions = max_sessions

    def create(self, session: Session) -> None:
        with self._engine.begin() as connection:
            statement = postgres_insert(sessions).values(
                token_hash=session.token_hash,
                user_id=session.user_id,
                created_at=session.created_at,
                last_seen_at=session.last_seen_at,
            )
            statement = statement.on_conflict_do_update(
                index_elements=[sessions.c.token_hash],
                set_={
                    "user_id": statement.excluded.user_id,
                    "created_at": statement.excluded.created_at,
                    "last_seen_at": statement.excluded.last_seen_at,
                },
            )
            connection.execute(statement)

            # Only the count and the trim need the lock, so it is held for about three round
            # trips instead of six. Under READ COMMITTED each waiter counts after the previous
            # commit, so the last one trims to exactly the cap.
            connection.execute(
                select(func.pg_advisory_xact_lock(cast(_SESSION_LOCK_KEY, BigInteger)))
            )
            count = connection.execute(select(func.count()).select_from(sessions)).scalar_one()
            excess = count - self._max_sessions
            if excess > 0:
                doomed = (
                    select(sessions.c.token_hash)
                    .where(sessions.c.token_hash != session.token_hash)
                    .order_by(sessions.c.last_seen_at, sessions.c.token_hash)
                    .limit(excess)
                )
                connection.execute(delete(sessions).where(sessions.c.token_hash.in_(doomed)))

    def get(self, token_hash: str) -> Session | None:
        with self._engine.begin() as connection:
            row = (
                connection.execute(select(sessions).where(sessions.c.token_hash == token_hash))
                .mappings()
                .first()
            )
        return _session_from_row(row) if row is not None else None

    def touch(self, token_hash: str, when: datetime) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                update(sessions)
                .where(sessions.c.token_hash == token_hash)
                .values(
                    last_seen_at=func.greatest(
                        sessions.c.last_seen_at,
                        literal(when, sessions.c.last_seen_at.type),
                    )
                )
            )

    def delete(self, token_hash: str) -> None:
        with self._engine.begin() as connection:
            connection.execute(delete(sessions).where(sessions.c.token_hash == token_hash))

    def purge_older_than(self, cutoff: datetime) -> int:
        with self._engine.begin() as connection:
            result = connection.execute(delete(sessions).where(sessions.c.last_seen_at < cutoff))
        return result.rowcount


__all__ = ["PostgresSessionStore", "PostgresUserRepository"]
