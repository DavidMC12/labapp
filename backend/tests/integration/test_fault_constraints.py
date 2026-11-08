"""The fault rules table rejects what its constraints should reject."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import Connection, insert, select
from sqlalchemy.exc import IntegrityError

from app.modules.testcontrols.tables import fault_rules


def _values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "target": "route",
        "method": "GET",
        "path": "/api/orders",
        "latency_ms": 0,
        "status": 500,
        "remaining": None,
    }
    values.update(overrides)
    return values


def _rejects(db: Connection, constraint: str, **overrides: Any) -> None:
    with pytest.raises(IntegrityError) as info:
        db.execute(insert(fault_rules).values(**_values(**overrides)))
    assert constraint in str(info.value)
    db.rollback()


def test_an_unknown_target_is_rejected(db: Connection) -> None:
    _rejects(db, "ck_fault_rules_target", target="database")


def test_an_unknown_method_is_rejected(db: Connection) -> None:
    _rejects(db, "ck_fault_rules_method", method="HEAD")


@pytest.mark.parametrize("latency", [-1, 10_001])
def test_an_out_of_range_latency_is_rejected(db: Connection, latency: int) -> None:
    _rejects(db, "ck_fault_rules_latency_ms", latency_ms=latency)


@pytest.mark.parametrize("status", [399, 600])
def test_an_out_of_range_status_is_rejected(db: Connection, status: int) -> None:
    _rejects(db, "ck_fault_rules_status", status=status)


def test_a_negative_remaining_is_rejected(db: Connection) -> None:
    _rejects(db, "ck_fault_rules_remaining", remaining=-1)


def test_latency_and_created_at_have_their_defaults(db: Connection) -> None:
    row = (
        db.execute(
            insert(fault_rules)
            .values(target="route", path="/api/orders")
            .returning(fault_rules.c.latency_ms, fault_rules.c.created_at)
        )
        .mappings()
        .one()
    )

    assert row["latency_ms"] == 0
    assert row["created_at"] is not None
    db.rollback()


def test_a_rule_with_until_removed_remains_active(db: Connection) -> None:
    db.execute(insert(fault_rules).values(**_values(remaining=None)))

    row = db.execute(select(fault_rules.c.remaining)).scalar_one()

    assert row is None
    db.rollback()
