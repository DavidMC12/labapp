"""Constraints, identity columns and timestamps against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from app.infra.db import as_utc
from tests.integration.helpers import insert_customer, insert_session, insert_user


def test_identity_accepts_explicit_ids_and_continues_after_the_sequence_moves(
    db: Connection,
) -> None:
    assert insert_user(db, user_id=100, email="explicit@example.test") == 100

    db.execute(text("select setval(pg_get_serial_sequence('users', 'id'), 101, false)"))

    assert insert_user(db, email="generated@example.test") == 101
    db.commit()


def test_a_role_outside_the_four_is_rejected(db: Connection) -> None:
    with pytest.raises(IntegrityError) as info:
        insert_user(db, role="owner")

    assert "ck_users_role" in str(info.value)
    db.rollback()


def test_a_status_outside_the_two_is_rejected(db: Connection) -> None:
    with pytest.raises(IntegrityError) as info:
        insert_customer(db, status="archived")

    assert "ck_customers_status" in str(info.value)
    db.rollback()


def test_deleting_a_user_deletes_their_sessions(db: Connection) -> None:
    user_id = insert_user(db)
    insert_session(db, user_id=user_id)

    db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})

    assert db.execute(text("SELECT count(*) FROM sessions")).scalar_one() == 0
    db.commit()


def test_user_emails_collide_ignoring_case(db: Connection) -> None:
    insert_user(db, email="Case@Example.test")

    with pytest.raises(IntegrityError) as info:
        insert_user(db, email="case@example.test")

    assert "users_email_lower_key" in str(info.value)
    db.rollback()


def test_customer_emails_collide_ignoring_case(db: Connection) -> None:
    insert_customer(db, email="Case@Example.test")

    with pytest.raises(IntegrityError) as info:
        insert_customer(db, email="case@example.test")

    assert "customers_email_lower_key" in str(info.value)
    db.rollback()


def test_timestamptz_round_trips_microseconds_and_timezone(db: Connection) -> None:
    created_at = datetime(2026, 1, 2, 3, 4, 5, 654321, tzinfo=UTC)

    user_id = insert_user(db, created_at=created_at)
    db.commit()

    stored = db.execute(
        text("SELECT created_at FROM users WHERE id = :id"),
        {"id": user_id},
    ).scalar_one()

    assert stored.tzinfo is not None
    assert stored.utcoffset() == timedelta(0)
    assert stored.microsecond == 654321
    assert as_utc(stored) == created_at
