"""The permission matrix of SPEC section 2 and app/domain/permissions.py."""

from __future__ import annotations

from app.domain.permissions import Action, Role, is_allowed

from . import support

ACTION_BY_DOCUMENT_NAME = {
    "View customers, products, orders, invoices, payments": Action.VIEW,
    "Create, edit, deactivate and reactivate customers": Action.MANAGE_CUSTOMERS,
    "Create and edit Draft orders": Action.EDIT_DRAFT_ORDERS,
    "Confirm, cancel and mark orders as Shipped": Action.TRANSITION_ORDERS,
    "Create invoices": Action.CREATE_INVOICES,
    "Register payments": Action.REGISTER_PAYMENTS,
    "Change the tax rate": Action.CHANGE_TAX_RATE,
}

ROLE_BY_COLUMN = {
    "Admin": Role.ADMIN,
    "Sales": Role.SALES,
    "Finance": Role.FINANCE,
    "Read-only": Role.READONLY,
}


def test_the_permission_matrix_matches_the_document() -> None:
    rows = support.spec_permission_rows()

    assert {ACTION_BY_DOCUMENT_NAME[row["Action"]] for row in rows} == set(Action)
    for row in rows:
        action = ACTION_BY_DOCUMENT_NAME[row["Action"]]
        for column, role in ROLE_BY_COLUMN.items():
            value = row[column]
            assert value in {"yes", "no"}, row["Action"]
            assert is_allowed(role, action) is (value == "yes"), (row["Action"], column)
