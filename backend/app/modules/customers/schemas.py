"""Request and response schemas for customers."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.modules.customers.models import CustomerStatus
from app.openapi import ID_MAXIMUM, ID_MINIMUM


class CustomerOut(BaseModel):
    """The public customer representation."""

    id: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    name: str
    email: str
    phone: str | None
    tax_id: str | None
    address: str | None
    status: CustomerStatus
    version: int = Field(ge=ID_MINIMUM, le=ID_MAXIMUM)
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class CustomerListOut(BaseModel):
    """One page of customers."""

    items: list[CustomerOut]
    page: int
    page_size: int
    total: int


class CustomerCreate(BaseModel):
    """The creation payload; validation happens in the service."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    address: str | None = None


class CustomerPatch(BaseModel):
    """The partial update payload; only sent fields change."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    address: str | None = None
    version: int
