"""FastAPI dependencies for the customers module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.modules.customers.models import Customer
from app.modules.customers.ports import CustomerRepository
from app.modules.customers.service import CustomerService


def get_service(request: Request) -> CustomerService:
    """Return the customer service built by create_app."""
    return request.app.state.customers


def get_repository(request: Request) -> CustomerRepository:
    """Return the customer repository built by create_app."""
    return request.app.state.customer_repository


def get_customer(
    id: int,
    service: Annotated[CustomerService, Depends(get_service)],
) -> Customer:
    """Load the customer or raise the 404 problem before body validation."""
    return service.get(id)
