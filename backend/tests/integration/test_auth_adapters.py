"""The authentication ports against PostgreSQL."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import Connection, Engine, func, insert, select

from app.domain.permissions import Role
from app.modules.auth.adapters.postgres import PostgresSessionStore, PostgresUserRepository
from app.modules.auth.tables import sessions, users
from tests.auth.contract_sessions import NOW, SessionStoreContract, session
from tests.auth.contract_users import UserRepositoryContract, user


class TestPostgresUserRepository(UserRepositoryContract):
    @pytest.fixture
    def user_repository(
        self, db: Connection, unpinned_database_engine: Engine
    ) -> PostgresUserRepository:
        repository = PostgresUserRepository(unpinned_database_engine)
        repository.replace_all([user()])
        return repository


@pytest.fixture
def session_user(db: Connection, unpinned_database_engine: Engine) -> None:
    PostgresUserRepository(unpinned_database_engine).replace_all([user()])


class TestPostgresSessionStore(SessionStoreContract):
    @pytest.fixture
    def session_store(
        self, session_user: None, unpinned_database_engine: Engine
    ) -> PostgresSessionStore:
        return PostgresSessionStore(unpinned_database_engine)

    @pytest.fixture
    def session_store_factory(
        self, session_user: None, unpinned_database_engine: Engine
    ) -> Callable[[int], PostgresSessionStore]:
        def factory(max_sessions: int) -> PostgresSessionStore:
            return PostgresSessionStore(unpinned_database_engine, max_sessions=max_sessions)

        return factory


def test_get_by_email_finds_a_user_whatever_the_case(
    db: Connection, unpinned_database_engine: Engine
) -> None:
    repository = PostgresUserRepository(unpinned_database_engine)
    repository.replace_all([user()])

    assert repository.get_by_email("  ADMIN@LABAPP.TEST ") == user()


def test_replace_all_keeps_sessions_of_kept_users_and_deletes_the_rest(
    db: Connection, unpinned_database_engine: Engine
) -> None:
    repository = PostgresUserRepository(unpinned_database_engine)
    other = user(id=2, name="Other Demo", email="other@labapp.test", role=Role.SALES)
    repository.replace_all([user(), other])
    store = PostgresSessionStore(unpinned_database_engine)
    store.create(session("keep", user_id=1))
    store.create(session("gone", user_id=2))

    repository.replace_all([user()])

    assert store.get("keep") is not None
    assert store.get("gone") is None
    assert repository.get_by_id(2) is None
    assert repository.get_by_id(1) is not None


def test_replace_all_moves_the_identity_sequence(
    db: Connection, unpinned_database_engine: Engine
) -> None:
    repository = PostgresUserRepository(unpinned_database_engine)
    repository.replace_all(
        [
            user(id=10, email="ten@labapp.test"),
            user(id=3, name="Third Demo", email="third@labapp.test", role=Role.FINANCE),
        ]
    )

    with unpinned_database_engine.begin() as connection:
        new_id = connection.execute(
            insert(users)
            .values(
                name="Generated",
                email="generated@labapp.test",
                role=Role.ADMIN.value,
                password_hash="hash",
                created_at=NOW,
            )
            .returning(users.c.id)
        ).scalar_one()

    assert new_id == 11


def test_a_stale_touch_does_not_move_last_seen_back(
    db: Connection, unpinned_database_engine: Engine
) -> None:
    PostgresUserRepository(unpinned_database_engine).replace_all([user()])
    store = PostgresSessionStore(unpinned_database_engine)
    later = NOW + timedelta(minutes=5)
    store.create(session("token", later, user_id=1))

    store.touch("token", NOW)

    stored = store.get("token")
    assert stored is not None
    assert stored.last_seen_at == later


def test_concurrent_creates_respect_the_cap(
    db: Connection, unpinned_database_engine: Engine
) -> None:
    PostgresUserRepository(unpinned_database_engine).replace_all([user()])
    store = PostgresSessionStore(unpinned_database_engine, max_sessions=5)
    barrier = Barrier(20)

    def create(index: int) -> None:
        barrier.wait()
        store.create(session(f"token-{index}", NOW + timedelta(seconds=index), user_id=1))

    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(create, range(20)))

    with unpinned_database_engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(sessions)).scalar_one()

    assert count == 5
