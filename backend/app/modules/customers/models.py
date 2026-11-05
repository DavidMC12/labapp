"""Customer models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CustomerStatus(StrEnum):
    """The two customer states."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class Customer:
    """A stored customer."""

    id: int
    name: str
    email: str
    phone: str | None
    tax_id: str | None
    address: str | None
    status: CustomerStatus
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewCustomer:
    """Already validated and normalized values for a new customer."""

    name: str
    email: str
    phone: str | None
    tax_id: str | None
    address: str | None


Changes = Mapping[str, str | None]
