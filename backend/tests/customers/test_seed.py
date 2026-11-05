"""Tests for the seeded customers."""

from __future__ import annotations

from datetime import UTC, timedelta

from app.modules.customers.models import CustomerStatus
from app.modules.customers.seed import SEED_CREATED_AT, seed_customers


def test_seed_contains_the_ten_documented_customers() -> None:
    customers = seed_customers()

    assert len(customers) == 10
    assert [customer.id for customer in customers] == list(range(1, 11))
    assert [customer.email for customer in customers] == [
        "acme@example.test",
        "beta@example.test",
        "cafe@example.test",
        "delta@example.test",
        "epsilon@example.test",
        "fenix@example.test",
        "gamma@example.test",
        "hotel@example.test",
        "iberica@example.test",
        "joyeria@example.test",
    ]
    assert customers[0].name == "Acme Industrial S.A."
    assert customers[2].name == "Cafetería La Esquina"
    assert customers[4].status == CustomerStatus.INACTIVE
    assert customers[7].status == CustomerStatus.INACTIVE
    assert customers[7].tax_id is None
    assert customers[2].tax_id is None


def test_seed_timestamps_version_and_optional_fields() -> None:
    customers = seed_customers()

    for index, customer in enumerate(customers, start=1):
        expected = SEED_CREATED_AT + timedelta(minutes=index)
        assert customer.created_at == expected
        assert customer.updated_at == expected
        assert customer.version == 1

    assert customers[0].phone == "+1 555 010 0001"
    assert customers[0].address == "Av. Principal 100"
    assert all(customer.phone is None for customer in customers[1:])
    assert all(customer.address is None for customer in customers[1:])
    assert all(customer.created_at.tzinfo == UTC for customer in customers)


def test_the_long_gamma_name_has_115_characters() -> None:
    gamma = seed_customers()[6]

    assert len(gamma.name) == 115
    assert gamma.name.startswith("Grupo Gamma")
    assert gamma.name.endswith("Sociedad por Acciones Simplificada")


def test_seed_is_a_fresh_list() -> None:
    first = seed_customers()
    second = seed_customers()

    assert first is not second
    assert first == second
