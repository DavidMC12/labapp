"""Reusable behavioral tests for CustomerRepository adapters."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import Any

import pytest

from app.modules.customers.models import Customer, CustomerStatus, NewCustomer
from app.modules.customers.ports import CustomerNotFound, EmailTaken, VersionConflict

NOW = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def new_customer(
    *,
    name: str = "Acme Industrial",
    email: str = "acme@example.test",
    phone: str | None = None,
    tax_id: str | None = None,
    address: str | None = None,
) -> NewCustomer:
    """Build a validated customer payload for the contract tests."""
    return NewCustomer(name=name, email=email, phone=phone, tax_id=tax_id, address=address)


def customer(
    id: int,
    *,
    name: str = "Acme Industrial",
    email: str = "acme@example.test",
    status: CustomerStatus = CustomerStatus.ACTIVE,
    created_at: datetime = NOW,
    version: int = 1,
) -> Customer:
    """Build a stored customer for the contract tests."""
    return Customer(
        id=id,
        name=name,
        email=email,
        phone=None,
        tax_id=None,
        address=None,
        status=status,
        version=version,
        created_at=created_at,
        updated_at=created_at,
    )


class CustomerRepositoryContract:
    """The behavior every CustomerRepository adapter must share.

    A concrete test class provides ``repository``, a fresh empty repository.
    """

    @pytest.fixture
    def repository(self) -> Any:
        raise NotImplementedError

    def test_add_assigns_the_first_id_and_defaults(self, repository: Any) -> None:
        created = repository.add(new_customer(), NOW)

        assert created.id == 1
        assert created.status == CustomerStatus.ACTIVE
        assert created.version == 1
        assert created.created_at == NOW
        assert created.updated_at == NOW
        assert repository.get(1) == created

    def test_get_unknown_returns_none(self, repository: Any) -> None:
        assert repository.get(99) is None

    def test_email_is_unique_case_insensitively(self, repository: Any) -> None:
        repository.add(new_customer(email="acme@example.test"), NOW)

        with pytest.raises(EmailTaken):
            repository.add(new_customer(email="ACME@EXAMPLE.TEST"), NOW)

    def test_list_orders_by_created_at_then_id_descending(self, repository: Any) -> None:
        for index in range(5):
            repository.add(
                new_customer(name=f"Customer {index}", email=f"c{index}@example.test"),
                NOW + timedelta(seconds=index),
            )

        first, total = repository.list(query=None, status=None, page=1, page_size=2)
        second, _ = repository.list(query=None, status=None, page=2, page_size=2)
        third, _ = repository.list(query=None, status=None, page=3, page_size=2)
        empty, _ = repository.list(query=None, status=None, page=4, page_size=2)

        assert total == 5
        assert [item.id for item in first] == [5, 4]
        assert [item.id for item in second] == [3, 2]
        assert [item.id for item in third] == [1]
        assert empty == []

    def test_list_breaks_created_at_ties_by_id_descending(self, repository: Any) -> None:
        repository.add(new_customer(email="one@example.test"), NOW)
        repository.add(new_customer(email="two@example.test"), NOW)

        items, total = repository.list(query=None, status=None, page=1, page_size=20)

        assert total == 2
        assert [item.id for item in items] == [2, 1]

    def test_search_matches_name_and_email_ignoring_case_and_accents(
        self,
        repository: Any,
    ) -> None:
        repository.add(
            new_customer(name="Cafetería La Esquina", email="cafe@example.test"),
            NOW,
        )
        repository.add(
            new_customer(name="Other Customer", email="épsilon@example.test"),
            NOW + timedelta(seconds=1),
        )

        by_name, _ = repository.list(query="cafeteria", status=None, page=1, page_size=20)
        by_email, _ = repository.list(query="EPSILON", status=None, page=1, page_size=20)
        by_accent, _ = repository.list(query="CAFETERÍA", status=None, page=1, page_size=20)

        assert [item.name for item in by_name] == ["Cafetería La Esquina"]
        assert [item.email for item in by_email] == ["épsilon@example.test"]
        assert [item.name for item in by_accent] == ["Cafetería La Esquina"]

    @pytest.mark.parametrize(
        ("query", "expected"),
        [("%", "100% coverage"), ("_", "snake_case"), ("\\", "back\\slash")],
    )
    def test_search_treats_pattern_characters_literally(
        self,
        repository: Any,
        query: str,
        expected: str,
    ) -> None:
        repository.add(new_customer(name="Plain name", email="plain@example.test"), NOW)
        repository.add(
            new_customer(name="100% coverage", email="percent@example.test"),
            NOW + timedelta(seconds=1),
        )
        repository.add(
            new_customer(name="snake_case", email="underscore@example.test"),
            NOW + timedelta(seconds=2),
        )
        repository.add(
            new_customer(name="back\\slash", email="backslash@example.test"),
            NOW + timedelta(seconds=3),
        )

        items, total = repository.list(query=query, status=None, page=1, page_size=20)

        assert total == 1
        assert [item.name for item in items] == [expected]

    def test_list_filters_by_status(self, repository: Any) -> None:
        repository.replace_all(
            [
                customer(1, email="one@example.test", status=CustomerStatus.ACTIVE),
                customer(2, email="two@example.test", status=CustomerStatus.INACTIVE),
            ]
        )

        active, active_total = repository.list(
            query=None,
            status=CustomerStatus.ACTIVE,
            page=1,
            page_size=20,
        )
        inactive, inactive_total = repository.list(
            query=None,
            status=CustomerStatus.INACTIVE,
            page=1,
            page_size=20,
        )

        assert [item.id for item in active] == [1]
        assert active_total == 1
        assert [item.id for item in inactive] == [2]
        assert inactive_total == 1

    def test_update_checks_not_found_then_version_then_email(self, repository: Any) -> None:
        repository.add(new_customer(email="one@example.test"), NOW)
        repository.add(new_customer(email="two@example.test"), NOW + timedelta(seconds=1))

        with pytest.raises(CustomerNotFound):
            repository.update(99, {"email": "two@example.test"}, 99, NOW)

        with pytest.raises(VersionConflict):
            repository.update(1, {"email": "two@example.test"}, 99, NOW)

        with pytest.raises(EmailTaken):
            repository.update(1, {"email": "TWO@EXAMPLE.TEST"}, 1, NOW)

    def test_update_noop_keeps_version_and_updated_at(self, repository: Any) -> None:
        created = repository.add(new_customer(), NOW)

        result = repository.update(
            1,
            {"name": created.name, "phone": None},
            1,
            NOW + timedelta(minutes=5),
        )

        assert result == created
        assert result.version == 1
        assert result.updated_at == NOW

    def test_update_real_change_bumps_version_and_updated_at(self, repository: Any) -> None:
        created = repository.add(new_customer(), NOW)
        later = NOW + timedelta(minutes=5)

        result = repository.update(1, {"name": "New Name"}, 1, later)

        assert result.name == "New Name"
        assert result.version == 2
        assert result.created_at == created.created_at
        assert result.updated_at == later

    def test_set_status_noop_and_stale_version(self, repository: Any) -> None:
        created = repository.add(new_customer(), NOW)

        unchanged = repository.set_status(
            1,
            CustomerStatus.ACTIVE,
            1,
            NOW + timedelta(minutes=1),
        )
        assert unchanged == created
        assert unchanged.version == 1

        with pytest.raises(VersionConflict):
            repository.set_status(1, CustomerStatus.ACTIVE, 2, NOW + timedelta(minutes=2))

        deactivated = repository.set_status(
            1,
            CustomerStatus.INACTIVE,
            1,
            NOW + timedelta(minutes=3),
        )
        assert deactivated.status == CustomerStatus.INACTIVE
        assert deactivated.version == 2

    def test_set_status_unknown_id(self, repository: Any) -> None:
        with pytest.raises(CustomerNotFound):
            repository.set_status(99, CustomerStatus.INACTIVE, None, NOW)

    def test_replace_all_resets_the_next_id(self, repository: Any) -> None:
        repository.replace_all([customer(5), customer(2)])

        created = repository.add(new_customer(email="new@example.test"), NOW)

        assert created.id == 6

        repository.replace_all([])
        first = repository.add(new_customer(email="first@example.test"), NOW)
        assert first.id == 1

    def test_concurrent_updates_with_the_same_version_leaves_one_winner(
        self,
        repository: Any,
    ) -> None:
        created = repository.add(new_customer(), NOW)
        barrier = Barrier(2)

        def update(name: str) -> str:
            barrier.wait()
            try:
                repository.update(created.id, {"name": name}, 1, NOW + timedelta(minutes=1))
            except VersionConflict:
                return "conflict"
            return "updated"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(update, ["First", "Second"]))

        assert sorted(outcomes) == ["conflict", "updated"]
        stored = repository.get(created.id)
        assert stored is not None
        assert stored.version == 2
