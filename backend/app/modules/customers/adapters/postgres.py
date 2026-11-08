"""PostgreSQL adapter for the customer repository port."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from contextlib import nullcontext
from datetime import datetime
from typing import Any

from sqlalchemy import Table, delete, func, insert, or_, select, text, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from app.domain.sorting import SortSpec
from app.infra.db import as_utc, qualified_table_name, unique_violation_of
from app.modules.customers.models import Changes, Customer, CustomerStatus, NewCustomer
from app.modules.customers.ports import CustomerNotFound, EmailTaken, VersionConflict
from app.modules.customers.search import normalize_for_search
from app.modules.customers.tables import customers

_FIELDS = ("name", "email", "phone", "tax_id", "address")
_EMAIL_CONSTRAINT = "customers_email_lower_key"
_DEFAULT_SORT = SortSpec("created_at", True)
# Text sorts must follow Python's code point order, not the database collation.
_SORT_COLUMNS = {
    "created_at": customers.c.created_at,
    "name": customers.c.name_search.collate("C"),
    "email": customers.c.email_search.collate("C"),
}


def _customer_from_row(row: Mapping[str, Any]) -> Customer:
    return Customer(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        phone=row["phone"],
        tax_id=row["tax_id"],
        address=row["address"],
        status=CustomerStatus(row["status"]),
        version=row["version"],
        created_at=as_utc(row["created_at"]),
        updated_at=as_utc(row["updated_at"]),
    )


def _values(data: NewCustomer, now: datetime) -> dict[str, Any]:
    """The stored columns of a new customer, search forms included."""
    return {
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "tax_id": data.tax_id,
        "address": data.address,
        "status": CustomerStatus.ACTIVE.value,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "name_search": normalize_for_search(data.name),
        "email_search": normalize_for_search(data.email),
    }


def _filters(query: str | None, status: CustomerStatus | None) -> list[Any]:
    """Return the WHERE clauses shared by ``list`` and ``export_rows``."""
    filters: list[Any] = []
    if status is not None:
        filters.append(customers.c.status == status.value)
    if query is not None:
        normalized = normalize_for_search(query)
        filters.append(
            or_(
                customers.c.name_search.contains(normalized, autoescape=True),
                customers.c.email_search.contains(normalized, autoescape=True),
            )
        )
    return filters


def _ordering(spec: SortSpec) -> tuple[Any, Any]:
    """Return the primary and tie-break ORDER BY expressions of a sort."""
    column = _SORT_COLUMNS[spec.field]
    primary = column.desc() if spec.descending else column.asc()
    secondary = customers.c.id.desc() if spec.descending else customers.c.id.asc()
    return primary, secondary


class PostgresCustomerRepository:
    """A customer repository backed by PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _locked(self, connection: Connection, id: int) -> Customer | None:
        row = (
            connection.execute(select(customers).where(customers.c.id == id).with_for_update())
            .mappings()
            .first()
        )
        return _customer_from_row(row) if row is not None else None

    def _email_taken(self, connection: Connection, email: str, exclude_id: int) -> bool:
        query = (
            select(customers.c.id)
            .where(
                func.lower(customers.c.email) == email.lower(),
                customers.c.id != exclude_id,
            )
            .limit(1)
        )
        return connection.execute(query).first() is not None

    def list(
        self,
        *,
        query: str | None,
        status: CustomerStatus | None,
        page: int,
        page_size: int,
        sort: SortSpec | None = None,
    ) -> tuple[list[Customer], int]:
        spec = sort or _DEFAULT_SORT
        filters = _filters(query, status)
        primary, secondary = _ordering(spec)

        offset = (page - 1) * page_size
        with self._engine.begin() as connection:
            total = connection.execute(
                select(func.count()).select_from(customers).where(*filters)
            ).scalar_one()
            rows = (
                connection.execute(
                    select(customers)
                    .where(*filters)
                    .order_by(primary, secondary)
                    .offset(offset)
                    .limit(page_size)
                )
                .mappings()
                .all()
            )
        return [_customer_from_row(row) for row in rows], total

    def export_rows(
        self,
        *,
        query: str | None,
        status: CustomerStatus | None,
        sort: SortSpec | None = None,
    ) -> list[Customer]:
        """Read every match in one statement, without paging or counting."""
        spec = sort or _DEFAULT_SORT
        primary, secondary = _ordering(spec)
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(customers).where(*_filters(query, status)).order_by(primary, secondary)
                )
                .mappings()
                .all()
            )
        return [_customer_from_row(row) for row in rows]

    def get(self, id: int) -> Customer | None:
        with self._engine.begin() as connection:
            row = (
                connection.execute(select(customers).where(customers.c.id == id)).mappings().first()
            )
        return _customer_from_row(row) if row is not None else None

    def add(self, data: NewCustomer, now: datetime) -> Customer:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        insert(customers).values(**_values(data, now)).returning(*customers.c)
                    )
                    .mappings()
                    .one()
                )
        except IntegrityError as error:
            if unique_violation_of(error, _EMAIL_CONSTRAINT):
                raise EmailTaken from error
            raise
        return _customer_from_row(row)

    def add_many(self, new_customers: Iterable[NewCustomer], now: datetime) -> list[Customer]:
        batch = list(new_customers)
        if not batch:
            return []
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        insert(customers)
                        .values([_values(data, now) for data in batch])
                        .returning(*customers.c)
                    )
                    .mappings()
                    .all()
                )
        except IntegrityError as error:
            if unique_violation_of(error, _EMAIL_CONSTRAINT):
                raise EmailTaken from error
            raise
        return sorted((_customer_from_row(row) for row in rows), key=lambda item: item.id)

    def existing_emails(self, emails: Iterable[str]) -> set[str]:
        wanted = {email.lower() for email in emails}
        if not wanted:
            return set()
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(func.lower(customers.c.email)).where(
                    func.lower(customers.c.email).in_(wanted)
                )
            ).scalars()
            return set(rows)

    def update(
        self,
        id: int,
        changes: Changes,
        expected_version: int | None,
        now: datetime,
    ) -> Customer:
        known = {key: value for key, value in changes.items() if key in _FIELDS}
        try:
            with self._engine.begin() as connection:
                stored = self._locked(connection, id)
                if stored is None:
                    raise CustomerNotFound
                if expected_version is not None and expected_version != stored.version:
                    raise VersionConflict

                new_email = known.get("email")
                if new_email is not None and self._email_taken(connection, new_email, id):
                    raise EmailTaken

                if all(getattr(stored, key) == value for key, value in known.items()):
                    return stored

                values: dict[str, Any] = {field: getattr(stored, field) for field in _FIELDS}
                values.update(known)
                row = (
                    connection.execute(
                        update(customers)
                        .where(customers.c.id == id)
                        .values(
                            **values,
                            name_search=normalize_for_search(values["name"]),
                            email_search=normalize_for_search(values["email"]),
                            version=stored.version + 1,
                            updated_at=now,
                        )
                        .returning(*customers.c)
                    )
                    .mappings()
                    .one()
                )
                return _customer_from_row(row)
        except IntegrityError as error:
            if unique_violation_of(error, _EMAIL_CONSTRAINT):
                raise EmailTaken from error
            raise

    def set_status(
        self,
        id: int,
        status: CustomerStatus,
        expected_version: int | None,
        now: datetime,
    ) -> Customer:
        with self._engine.begin() as connection:
            stored = self._locked(connection, id)
            if stored is None:
                raise CustomerNotFound
            if expected_version is not None and expected_version != stored.version:
                raise VersionConflict
            if stored.status == status:
                return stored

            row = (
                connection.execute(
                    update(customers)
                    .where(customers.c.id == id)
                    .values(status=status.value, version=stored.version + 1, updated_at=now)
                    .returning(*customers.c)
                )
                .mappings()
                .one()
            )
            return _customer_from_row(row)

    def replace_all(
        self,
        replacement: Iterable[Customer],
        *,
        connection: Connection | None = None,
        defer_sequences: list[Callable[[Connection], None]] | None = None,
    ) -> None:
        """Replace every customer and restart the id sequence.

        With ``connection`` it runs inside the caller's transaction and does not open
        its own; without it, the replacement is one transaction. With
        ``defer_sequences`` the sequence restart is appended to that list instead of
        running now, so the caller can run it once every data step succeeded
        (``setval`` is not undone by a rollback).
        """
        replacements = list(replacement)
        next_id = max((customer.id for customer in replacements), default=0) + 1
        context = nullcontext(connection) if connection is not None else self._engine.begin()
        with context as connection:
            connection.execute(delete(customers))
            if replacements:
                connection.execute(
                    insert(customers).values(
                        [
                            {
                                "id": customer.id,
                                "name": customer.name,
                                "email": customer.email,
                                "phone": customer.phone,
                                "tax_id": customer.tax_id,
                                "address": customer.address,
                                "status": customer.status.value,
                                "version": customer.version,
                                "created_at": customer.created_at,
                                "updated_at": customer.updated_at,
                                "name_search": normalize_for_search(customer.name),
                                "email_search": normalize_for_search(customer.email),
                            }
                            for customer in replacements
                        ]
                    )
                )
            restart_sequence = _sequence_restart(self._engine, customers, next_id)
            if defer_sequences is None:
                restart_sequence(connection)
            else:
                defer_sequences.append(restart_sequence)


def _sequence_restart(
    engine: Engine,
    table: Table,
    next_id: int,
) -> Callable[[Connection], None]:
    """Build the ``setval`` call that restarts a table's id sequence."""

    def restart(connection: Connection) -> None:
        connection.execute(
            text("select setval(pg_get_serial_sequence(:table_name, 'id'), :next_id, false)"),
            {
                "table_name": qualified_table_name(engine, table),
                "next_id": next_id,
            },
        )

    return restart


__all__ = ["PostgresCustomerRepository"]
