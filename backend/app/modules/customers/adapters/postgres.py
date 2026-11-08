"""PostgreSQL adapter for the customer repository port."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import nullcontext
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, insert, or_, select, text, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from app.infra.db import as_utc, qualified_table_name, unique_violation_of
from app.modules.customers.models import Changes, Customer, CustomerStatus, NewCustomer
from app.modules.customers.ports import CustomerNotFound, EmailTaken, VersionConflict
from app.modules.customers.search import normalize_for_search
from app.modules.customers.tables import customers

_FIELDS = ("name", "email", "phone", "tax_id", "address")
_EMAIL_CONSTRAINT = "customers_email_lower_key"


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
    ) -> tuple[list[Customer], int]:
        filters = []
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

        offset = (page - 1) * page_size
        with self._engine.begin() as connection:
            total = connection.execute(
                select(func.count()).select_from(customers).where(*filters)
            ).scalar_one()
            rows = (
                connection.execute(
                    select(customers)
                    .where(*filters)
                    .order_by(customers.c.created_at.desc(), customers.c.id.desc())
                    .offset(offset)
                    .limit(page_size)
                )
                .mappings()
                .all()
            )
        return [_customer_from_row(row) for row in rows], total

    def get(self, id: int) -> Customer | None:
        with self._engine.begin() as connection:
            row = (
                connection.execute(select(customers).where(customers.c.id == id)).mappings().first()
            )
        return _customer_from_row(row) if row is not None else None

    def add(self, data: NewCustomer, now: datetime) -> Customer:
        values = {
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
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(insert(customers).values(**values).returning(*customers.c))
                    .mappings()
                    .one()
                )
        except IntegrityError as error:
            if unique_violation_of(error, _EMAIL_CONSTRAINT):
                raise EmailTaken from error
            raise
        return _customer_from_row(row)

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
    ) -> None:
        """Replace every customer and restart the id sequence.

        With ``connection`` it runs inside the caller's transaction and does not open
        its own; without it, the replacement is one transaction.
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
            connection.execute(
                text("select setval(pg_get_serial_sequence(:table_name, 'id'), :next_id, false)"),
                {
                    "table_name": qualified_table_name(self._engine, customers),
                    "next_id": next_id,
                },
            )


__all__ = ["PostgresCustomerRepository"]
