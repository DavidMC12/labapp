"""Tests for the full role and action permission matrix."""

from __future__ import annotations

import pytest

from app.domain.permissions import Action, Role, is_allowed, require
from app.errors import ApiError

PERMISSION_MATRIX = [
    # Admin
    (Role.ADMIN, Action.VIEW, True),
    (Role.ADMIN, Action.MANAGE_CUSTOMERS, True),
    (Role.ADMIN, Action.EDIT_DRAFT_ORDERS, True),
    (Role.ADMIN, Action.TRANSITION_ORDERS, True),
    (Role.ADMIN, Action.CREATE_INVOICES, True),
    (Role.ADMIN, Action.REGISTER_PAYMENTS, True),
    (Role.ADMIN, Action.CHANGE_TAX_RATE, True),
    # Sales
    (Role.SALES, Action.VIEW, True),
    (Role.SALES, Action.MANAGE_CUSTOMERS, True),
    (Role.SALES, Action.EDIT_DRAFT_ORDERS, True),
    (Role.SALES, Action.TRANSITION_ORDERS, True),
    (Role.SALES, Action.CREATE_INVOICES, False),
    (Role.SALES, Action.REGISTER_PAYMENTS, False),
    (Role.SALES, Action.CHANGE_TAX_RATE, False),
    # Finance
    (Role.FINANCE, Action.VIEW, True),
    (Role.FINANCE, Action.MANAGE_CUSTOMERS, False),
    (Role.FINANCE, Action.EDIT_DRAFT_ORDERS, False),
    (Role.FINANCE, Action.TRANSITION_ORDERS, False),
    (Role.FINANCE, Action.CREATE_INVOICES, True),
    (Role.FINANCE, Action.REGISTER_PAYMENTS, True),
    (Role.FINANCE, Action.CHANGE_TAX_RATE, False),
    # Read-only
    (Role.READONLY, Action.VIEW, True),
    (Role.READONLY, Action.MANAGE_CUSTOMERS, False),
    (Role.READONLY, Action.EDIT_DRAFT_ORDERS, False),
    (Role.READONLY, Action.TRANSITION_ORDERS, False),
    (Role.READONLY, Action.CREATE_INVOICES, False),
    (Role.READONLY, Action.REGISTER_PAYMENTS, False),
    (Role.READONLY, Action.CHANGE_TAX_RATE, False),
]


@pytest.mark.parametrize(("role", "action", "allowed"), PERMISSION_MATRIX)
def test_permission_matrix(role: Role, action: Action, allowed: bool) -> None:
    assert is_allowed(role, action) is allowed

    if allowed:
        assert require(role, action) is None
    else:
        with pytest.raises(ApiError) as error:
            require(role, action)

        assert error.value.status == 403
        assert error.value.code == "FORBIDDEN"
        assert error.value.detail == "No tienes permiso para realizar esta acción."


def test_the_matrix_covers_every_role_and_action() -> None:
    assert len(PERMISSION_MATRIX) == len(Role) * len(Action)


def test_enum_values_match_the_specification() -> None:
    assert {role.value for role in Role} == {"admin", "sales", "finance", "readonly"}
    assert {action.value for action in Action} == {
        "view",
        "manage_customers",
        "edit_draft_orders",
        "transition_orders",
        "create_invoices",
        "register_payments",
        "change_tax_rate",
    }
