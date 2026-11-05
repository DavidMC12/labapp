"""Tests for the customer service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.errors import ApiError
from app.infra.clock import OffsetClock
from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.models import CustomerStatus
from app.modules.customers.seed import seed_customers
from app.modules.customers.service import CustomerService
from tests.infra.helpers import FixedClock

NOW = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)


def _service() -> CustomerService:
    repository = InMemoryCustomerRepository(seed_customers())
    return CustomerService(repository, OffsetClock(FixedClock(NOW)))


def test_list_trims_the_query_and_ignores_an_empty_one() -> None:
    service = _service()

    items, total = service.list_customers(1, "  cafeteria  ", None)
    assert total == 1
    assert [customer.name for customer in items] == ["Cafetería La Esquina"]

    items, total = service.list_customers(1, "   ", None)
    assert total == 10
    assert len(items) == 10


class RecordingRepository:
    """A repository that records the query it receives."""

    def __init__(self) -> None:
        self.query: str | None | object = object()

    def list(
        self,
        *,
        query: str | None,
        status: CustomerStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[object], int]:
        self.query = query
        return [], 0


def test_list_passes_none_for_an_empty_query() -> None:
    repository = RecordingRepository()
    service = CustomerService(repository, OffsetClock(FixedClock(NOW)))  # type: ignore[arg-type]

    service.list_customers(1, "   ", None)

    assert repository.query is None


@pytest.mark.parametrize("page", [0, 1_000_001])
def test_page_out_of_range(page: int) -> None:
    service = _service()

    with pytest.raises(ApiError) as error:
        service.list_customers(page, None, None)

    assert error.value.status == 422
    assert error.value.errors == [
        {
            "field": "page",
            "code": "OUT_OF_RANGE",
            "message": "El valor debe estar entre 1 y 1000000.",
        }
    ]


def test_query_too_long() -> None:
    service = _service()

    with pytest.raises(ApiError) as error:
        service.list_customers(1, "a" * 101, None)

    assert error.value.errors == [
        {
            "field": "q",
            "code": "TOO_LONG",
            "message": "Debe tener como máximo 100 caracteres.",
        }
    ]


def test_query_with_a_control_character() -> None:
    service = _service()

    with pytest.raises(ApiError) as error:
        service.list_customers(1, "acme\u0000", None)

    assert error.value.errors == [
        {
            "field": "q",
            "code": "INVALID_FORMAT",
            "message": "El formato no es válido.",
        }
    ]


def test_list_filters_by_status() -> None:
    service = _service()

    items, total = service.list_customers(1, None, CustomerStatus.INACTIVE)

    assert total == 2
    assert {customer.id for customer in items} == {5, 8}


@pytest.mark.parametrize("customer_id", [0, 2_147_483_648])
def test_get_with_an_out_of_range_id_is_not_found(customer_id: int) -> None:
    service = _service()

    with pytest.raises(ApiError) as error:
        service.get(customer_id)

    assert error.value.status == 404
    assert error.value.code == "NOT_FOUND"


def test_get_unknown_id_is_not_found() -> None:
    service = _service()

    with pytest.raises(ApiError) as error:
        service.get(99)

    assert error.value.status == 404
    assert error.value.code == "NOT_FOUND"
    assert error.value.detail == "No se encontró el recurso solicitado."


def test_update_version_out_of_range() -> None:
    service = _service()

    with pytest.raises(ApiError) as error:
        service.update(1, {"name": "New Name"}, 0)

    assert error.value.status == 422
    assert error.value.errors == [
        {
            "field": "version",
            "code": "OUT_OF_RANGE",
            "message": "El valor debe estar entre 1 y 2147483647.",
        }
    ]


def test_create_with_a_duplicate_email() -> None:
    service = _service()

    with pytest.raises(ApiError) as error:
        service.create(
            {
                "name": "Another Acme",
                "email": "ACME@EXAMPLE.TEST",
                "phone": None,
                "tax_id": None,
                "address": None,
            }
        )

    assert error.value.status == 409
    assert error.value.code == "CUSTOMER_EMAIL_TAKEN"
    assert error.value.detail == "Ya existe un cliente con ese email."


def test_update_with_a_stale_version() -> None:
    service = _service()
    service.update(1, {"name": "New Name"}, 1)

    with pytest.raises(ApiError) as error:
        service.update(1, {"name": "Other Name"}, 1)

    assert error.value.status == 409
    assert error.value.code == "VERSION_CONFLICT"
    assert error.value.detail == (
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."
    )


def test_deactivate_and_reactivate() -> None:
    service = _service()

    deactivated = service.deactivate(1, 1)
    assert deactivated.status == CustomerStatus.INACTIVE
    assert deactivated.version == 2

    reactivated = service.reactivate(1, 2)
    assert reactivated.status == CustomerStatus.ACTIVE
    assert reactivated.version == 3
