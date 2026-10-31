"""Roles, actions and the permission matrix from SPEC section 2."""

from __future__ import annotations

from enum import StrEnum

from app.errors import ApiError


class Role(StrEnum):
    """The four application roles."""

    ADMIN = "admin"
    SALES = "sales"
    FINANCE = "finance"
    READONLY = "readonly"


class Action(StrEnum):
    """One entry per row of the permission table."""

    VIEW = "view"
    MANAGE_CUSTOMERS = "manage_customers"
    EDIT_DRAFT_ORDERS = "edit_draft_orders"
    TRANSITION_ORDERS = "transition_orders"
    CREATE_INVOICES = "create_invoices"
    REGISTER_PAYMENTS = "register_payments"
    CHANGE_TAX_RATE = "change_tax_rate"


FORBIDDEN_MESSAGE = "No tienes permiso para realizar esta acción."

_ALLOWED: dict[Action, frozenset[Role]] = {
    Action.VIEW: frozenset(Role),
    Action.MANAGE_CUSTOMERS: frozenset({Role.ADMIN, Role.SALES}),
    Action.EDIT_DRAFT_ORDERS: frozenset({Role.ADMIN, Role.SALES}),
    Action.TRANSITION_ORDERS: frozenset({Role.ADMIN, Role.SALES}),
    Action.CREATE_INVOICES: frozenset({Role.ADMIN, Role.FINANCE}),
    Action.REGISTER_PAYMENTS: frozenset({Role.ADMIN, Role.FINANCE}),
    Action.CHANGE_TAX_RATE: frozenset({Role.ADMIN}),
}


def is_allowed(role: Role, action: Action) -> bool:
    """Return whether the role may perform the action."""
    return role in _ALLOWED.get(action, frozenset())


def require(role: Role, action: Action) -> None:
    """Raise FORBIDDEN when the role may not perform the action."""
    if not is_allowed(role, action):
        raise ApiError(403, "FORBIDDEN", FORBIDDEN_MESSAGE)
