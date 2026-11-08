"""In-memory adapter for the customer repository port."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime
from threading import Lock

from app.domain.sorting import SortSpec
from app.modules.customers.models import Changes, Customer, CustomerStatus, NewCustomer
from app.modules.customers.ports import CustomerNotFound, EmailTaken, VersionConflict
from app.modules.customers.search import normalize_for_search

_FIELDS = ("name", "email", "phone", "tax_id", "address")
_DEFAULT_SORT = SortSpec("created_at", True)


class InMemoryCustomerRepository:
    """A thread-safe customer repository backed by dictionaries."""

    def __init__(self, customers: Iterable[Customer] = ()) -> None:
        self._lock = Lock()
        self._customers: dict[int, Customer] = {}
        self._search: dict[int, tuple[str, str]] = {}
        self._next_id = 1
        self.replace_all(customers)

    def _remember(self, customer: Customer) -> None:
        self._search[customer.id] = (
            normalize_for_search(customer.name),
            normalize_for_search(customer.email),
        )

    def list(
        self,
        *,
        query: str | None,
        status: CustomerStatus | None,
        page: int,
        page_size: int,
        sort: SortSpec | None = None,
    ) -> tuple[list[Customer], int]:
        with self._lock:
            matches = self._matches(query, status, sort)
            start = (page - 1) * page_size
            return matches[start : start + page_size], len(matches)

    def export_rows(
        self,
        *,
        query: str | None,
        status: CustomerStatus | None,
        sort: SortSpec | None = None,
    ) -> list[Customer]:
        with self._lock:
            return self._matches(query, status, sort)

    def _matches(
        self,
        query: str | None,
        status: CustomerStatus | None,
        sort: SortSpec | None,
    ) -> list[Customer]:
        """Return every match in the requested order; the caller holds the lock."""
        spec = sort or _DEFAULT_SORT
        matches = [
            customer
            for customer in self._customers.values()
            if status is None or customer.status == status
        ]
        if query is not None:
            normalized = normalize_for_search(query)
            matches = [
                customer
                for customer in matches
                if normalized in self._search[customer.id][0]
                or normalized in self._search[customer.id][1]
            ]
        matches.sort(key=self._sort_key(spec.field), reverse=spec.descending)
        return matches

    def _sort_key(self, field: str):
        if field == "name":
            return lambda customer: (self._search[customer.id][0], customer.id)
        if field == "email":
            return lambda customer: (self._search[customer.id][1], customer.id)
        return lambda customer: (customer.created_at, customer.id)

    def get(self, id: int) -> Customer | None:
        with self._lock:
            return self._customers.get(id)

    def add(self, data: NewCustomer, now: datetime) -> Customer:
        with self._lock:
            email = data.email.lower()
            if any(customer.email.lower() == email for customer in self._customers.values()):
                raise EmailTaken
            return self._insert(data, now)

    def add_many(self, new_customers: Iterable[NewCustomer], now: datetime) -> list[Customer]:
        batch = list(new_customers)
        with self._lock:
            stored_emails = {customer.email.lower() for customer in self._customers.values()}
            batch_emails = [data.email.lower() for data in batch]
            if len(set(batch_emails)) != len(batch_emails) or any(
                email in stored_emails for email in batch_emails
            ):
                raise EmailTaken
            return [self._insert(data, now) for data in batch]

    def existing_emails(self, emails: Iterable[str]) -> set[str]:
        wanted = {email.lower() for email in emails}
        if not wanted:
            return set()
        with self._lock:
            return {
                customer.email.lower()
                for customer in self._customers.values()
                if customer.email.lower() in wanted
            }

    def _insert(self, data: NewCustomer, now: datetime) -> Customer:
        identifier = self._next_id
        self._next_id += 1
        customer = Customer(
            id=identifier,
            name=data.name,
            email=data.email,
            phone=data.phone,
            tax_id=data.tax_id,
            address=data.address,
            status=CustomerStatus.ACTIVE,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._customers[identifier] = customer
        self._remember(customer)
        return customer

    def update(
        self,
        id: int,
        changes: Changes,
        expected_version: int | None,
        now: datetime,
    ) -> Customer:
        with self._lock:
            customer = self._customers.get(id)
            if customer is None:
                raise CustomerNotFound
            if expected_version is not None and expected_version != customer.version:
                raise VersionConflict

            known_changes = {key: value for key, value in changes.items() if key in _FIELDS}
            new_email = known_changes.get("email")
            if new_email is not None:
                email = new_email.lower()
                if any(
                    other_id != id and other.email.lower() == email
                    for other_id, other in self._customers.items()
                ):
                    raise EmailTaken

            if all(getattr(customer, key) == value for key, value in known_changes.items()):
                return customer

            values = {key: getattr(customer, key) for key in _FIELDS}
            values.update(known_changes)
            updated = replace(
                customer,
                **values,
                version=customer.version + 1,
                updated_at=now,
            )
            self._customers[id] = updated
            self._remember(updated)
            return updated

    def set_status(
        self,
        id: int,
        status: CustomerStatus,
        expected_version: int | None,
        now: datetime,
    ) -> Customer:
        with self._lock:
            customer = self._customers.get(id)
            if customer is None:
                raise CustomerNotFound
            if expected_version is not None and expected_version != customer.version:
                raise VersionConflict
            if customer.status == status:
                return customer

            updated = replace(
                customer,
                status=status,
                version=customer.version + 1,
                updated_at=now,
            )
            self._customers[id] = updated
            return updated

    def replace_all(self, customers: Iterable[Customer]) -> None:
        with self._lock:
            self._customers = {customer.id: customer for customer in customers}
            self._search = {}
            for customer in self._customers.values():
                self._remember(customer)
            self._next_id = max(self._customers, default=0) + 1
