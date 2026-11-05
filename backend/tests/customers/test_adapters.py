"""Tests for the in-memory customer repository."""

from __future__ import annotations

import pytest

from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from tests.customers.contract_repository import CustomerRepositoryContract


class TestInMemoryCustomerRepository(CustomerRepositoryContract):
    @pytest.fixture
    def repository(self) -> InMemoryCustomerRepository:
        return InMemoryCustomerRepository()
