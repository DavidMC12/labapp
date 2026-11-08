"""The seeded users and customers of docs/SEED.md."""

from __future__ import annotations

from app.domain.permissions import Role
from app.modules.auth.seed import seed_users
from app.modules.customers.seed import seed_customers

from . import support

ROLE_BY_DOCUMENT_NAME = {
    "Admin": Role.ADMIN,
    "Sales": Role.SALES,
    "Finance": Role.FINANCE,
    "Read-only": Role.READONLY,
}


def test_the_four_demo_users_match_the_document() -> None:
    rows = support.seed_table("Users", "Email", "Name", "Role")
    users = seed_users("test-hash")

    assert len(rows) == len(users) == 4
    for row, user in zip(rows, users, strict=True):
        assert row["Email"] == user.email
        assert row["Name"] == user.name
        assert ROLE_BY_DOCUMENT_NAME[row["Role"]] == user.role


def test_the_ten_customers_match_the_document() -> None:
    rows = support.seed_table(
        "Customers",
        "Id",
        "Name",
        "Email",
        "Tax ID",
        "Status",
        "Why it exists",
    )
    customers = seed_customers()

    assert len(rows) == len(customers) == 10
    for row, customer in zip(rows, customers, strict=True):
        assert int(row["Id"]) == customer.id
        assert row["Name"] == customer.name
        assert row["Email"] == customer.email
        expected_tax_id = None if row["Tax ID"] == "none" else row["Tax ID"]
        assert customer.tax_id == expected_tax_id
        assert row["Status"] == customer.status.value
