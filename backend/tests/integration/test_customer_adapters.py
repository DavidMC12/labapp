"""The customer repository port against PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import Connection, Engine

from app.errors import ApiError
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.customers.ports import EmailTaken
from app.modules.customers.service import CustomerService
from tests.customers.contract_repository import (
    NOW,
    CustomerRepositoryContract,
    customer,
    new_customer,
)
from tests.infra.helpers import FixedClock


class TestPostgresCustomerRepository(CustomerRepositoryContract):
    @pytest.fixture
    def repository(
        self, db: Connection, unpinned_database_engine: Engine
    ) -> PostgresCustomerRepository:
        return PostgresCustomerRepository(unpinned_database_engine)


@pytest.fixture
def customer_repository(
    db: Connection, unpinned_database_engine: Engine
) -> PostgresCustomerRepository:
    return PostgresCustomerRepository(unpinned_database_engine)


def test_search_is_accent_insensitive_and_treats_patterns_literally(
    customer_repository: PostgresCustomerRepository,
) -> None:
    customer_repository.add(
        new_customer(name="Cafetería La Esquina", email="cafe@example.test"), NOW
    )
    customer_repository.add(
        new_customer(name="100% coverage", email="percent@example.test"),
        NOW + timedelta(seconds=1),
    )
    customer_repository.add(
        new_customer(name="snake_case", email="underscore@example.test"),
        NOW + timedelta(seconds=2),
    )
    customer_repository.add(
        new_customer(name="back\\slash", email="backslash@example.test"),
        NOW + timedelta(seconds=3),
    )

    cases = [
        ("cafeteria", "Cafetería La Esquina"),
        ("%", "100% coverage"),
        ("_", "snake_case"),
        ("\\", "back\\slash"),
    ]
    for query, expected in cases:
        items, total = customer_repository.list(query=query, status=None, page=1, page_size=20)

        assert total == 1
        assert [item.name for item in items] == [expected]


def test_update_keeps_the_search_columns_in_step(
    customer_repository: PostgresCustomerRepository,
) -> None:
    created = customer_repository.add(new_customer(name="Old Name", email="old@example.test"), NOW)

    customer_repository.update(
        created.id,
        {"name": "Cafetería Nueva", "email": "nueva@example.test"},
        1,
        NOW + timedelta(minutes=1),
    )

    by_name, _ = customer_repository.list(query="cafeteria", status=None, page=1, page_size=20)
    by_email, _ = customer_repository.list(query="nueva@", status=None, page=1, page_size=20)

    assert [item.id for item in by_name] == [created.id]
    assert [item.id for item in by_email] == [created.id]


def test_identity_sequence_continues_after_replace_all(
    customer_repository: PostgresCustomerRepository,
) -> None:
    customer_repository.replace_all(
        [
            customer(5, email="five@example.test"),
            customer(2, email="two@example.test"),
        ]
    )

    created = customer_repository.add(new_customer(email="six@example.test"), NOW)

    assert created.id == 6


def test_concurrent_imports_of_the_same_email_leave_one_winner(
    customer_repository: PostgresCustomerRepository,
) -> None:
    service = CustomerService(customer_repository, FixedClock(NOW))
    barrier = Barrier(2)
    files = {
        "winner": (
            "name,email\nWinner A,race@example.test\nWinner Only,winner-only@example.test\n"
        ),
        "loser": ("name,email\nLoser A,race@example.test\nLoser Only,loser-only@example.test\n"),
    }

    def import_file(name: str) -> str:
        barrier.wait()
        try:
            service.import_customers(files[name].encode("utf-8"), f"{name}.csv")
        except ApiError as error:
            assert error.code == "CUSTOMER_EMAIL_TAKEN"
            assert error.status in (409, 422)
            return "rejected"
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(import_file, files))

    assert sorted(outcomes) == ["created", "rejected"]
    items, total = customer_repository.list(query=None, status=None, page=1, page_size=20)
    assert total == 2
    emails = {item.email for item in items}
    assert "race@example.test" in emails
    assert len(emails & {"winner-only@example.test", "loser-only@example.test"}) == 1


def test_concurrent_adds_of_the_same_email_leave_one_winner(
    customer_repository: PostgresCustomerRepository,
) -> None:
    barrier = Barrier(2)

    def create(_: int) -> str:
        barrier.wait()
        try:
            customer_repository.add(new_customer(email="race@example.test"), NOW)
        except EmailTaken:
            return "email_taken"
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(create, range(2)))

    assert sorted(outcomes) == ["created", "email_taken"]


def test_concurrent_updates_to_the_same_email_map_to_email_taken(
    customer_repository: PostgresCustomerRepository,
) -> None:
    first = customer_repository.add(new_customer(name="First", email="first@example.test"), NOW)
    second = customer_repository.add(
        new_customer(name="Second", email="second@example.test"), NOW + timedelta(seconds=1)
    )
    barrier = Barrier(2)

    def update(item: tuple[int, str]) -> str:
        customer_id, email = item
        barrier.wait()
        try:
            customer_repository.update(
                customer_id, {"email": email}, None, NOW + timedelta(minutes=1)
            )
        except EmailTaken:
            return "email_taken"
        return "updated"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                update,
                [
                    (first.id, "race@example.test"),
                    (second.id, "race@example.test"),
                ],
            )
        )

    assert sorted(outcomes) == ["email_taken", "updated"]
