"""Storage ports for the customers module."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from app.domain.sorting import SortSpec
from app.modules.customers.models import Changes, Customer, CustomerStatus, NewCustomer


class CustomerNotFound(Exception):
    """The requested customer does not exist."""


class VersionConflict(Exception):
    """The stored version differs from the expected version."""


class EmailTaken(Exception):
    """Another customer already uses the email."""


class CustomerRepository(Protocol):
    """Storage for customers."""

    def list(
        self,
        *,
        query: str | None,
        status: CustomerStatus | None,
        page: int,
        page_size: int,
        sort: SortSpec | None = None,
    ) -> tuple[list[Customer], int]:
        """Return one page of matches and the total number of matches.

        Results follow ``sort`` (``created_at`` descending when it is absent),
        with ties broken by ``id`` in the same direction.
        ``query`` is already trimmed and non-empty when given. It is literal text:
        ``%``, ``_`` and ``\\`` have no special meaning (a SQL adapter must escape
        them). It matches a contains search on the name or email, using the search
        form of each value stored at write time. The search form is
        ``normalize_for_search(text)``: a SQL adapter keeps those normalized values
        in columns and never relies on database collations or ``unaccent``, so the
        semantics are identical everywhere.
        """
        ...

    def get(self, id: int) -> Customer | None:
        """Return the customer with that id, or ``None``."""
        ...

    def export_rows(
        self,
        *,
        query: str | None,
        status: CustomerStatus | None,
        sort: SortSpec | None = None,
    ) -> list[Customer]:
        """Return every match of the list filters, in one read.

        The filters and the order are exactly those of ``list`` with the same
        ``query``, ``status`` and ``sort``, without a page: the result is the
        concatenation of every page of ``list``. A SQL adapter reads it in one
        statement, so a concurrent write cannot repeat or skip a row between pages.
        """
        ...

    def add(self, data: NewCustomer, now: datetime) -> Customer:
        """Store a new active customer atomically.

        The next id is assigned, ``version`` is 1, and ``created_at`` and
        ``updated_at`` are both ``now``. Raise ``EmailTaken`` if another customer
        already has the same lowercase email. A SQL adapter enforces this with a
        unique index and maps the violation, never with check-then-insert.
        """
        ...

    def add_many(self, new_customers: Iterable[NewCustomer], now: datetime) -> list[Customer]:
        """Store every customer of an import in one atomic step.

        The ids are assigned in file order and are consecutive; every row gets
        ``status`` active, ``version`` 1 and the same ``now``. Raise
        ``EmailTaken`` when an email belongs to an earlier row of the batch or to
        a stored customer; in that case nothing is stored. A SQL adapter uses one
        transaction (and one insert statement) and maps the unique-index
        violation, never check-then-insert.
        """
        ...

    def existing_emails(self, emails: Iterable[str]) -> set[str]:
        """Return the lowercase emails of the batch that a customer already uses."""
        ...

    def update(
        self,
        id: int,
        changes: Changes,
        expected_version: int | None,
        now: datetime,
    ) -> Customer:
        """Update a customer atomically after locking the row.

        In SQL the adapter starts with ``SELECT ... FOR UPDATE``. The checks happen
        in this order: ``CustomerNotFound`` for an unknown id; ``VersionConflict``
        when ``expected_version`` is not ``None`` and differs from the stored
        version; ``EmailTaken`` when the new email belongs to another customer.
        If the changes leave every field as it already is, return the stored
        customer untouched (no new version, no new ``updated_at``). Otherwise apply
        the changes, increase ``version`` by 1 and set ``updated_at`` to ``now``.
        """
        ...

    def set_status(
        self,
        id: int,
        status: CustomerStatus,
        expected_version: int | None,
        now: datetime,
    ) -> Customer:
        """Change a customer's status atomically after locking the row.

        The checks have the same rules and order as ``update``: ``CustomerNotFound``,
        then ``VersionConflict``, then no change when the status already matches.
        A stale ``expected_version`` is a conflict even when the status already
        matches. A real change increases ``version`` by 1 and sets ``updated_at``.
        """
        ...

    def replace_all(self, customers: Iterable[Customer]) -> None:
        """Replace the whole content and set the next id to the highest id plus one.

        The next id is 1 when the iterable is empty.
        """
        ...
