# Review: sorting of the lists, backend (task 050, 2026-11-08)

- **Branch:** `w1/list-sorting`, by Worker 1 (14 commits, plus 3 for the review feedback) and one test fixture fix by the supervisor.
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge after the fixes below. No Critical findings.
- **What it does:** `sort` and `direction` on the four lists (customers, orders, invoices, products) as `docs/SPEC.md` defines them: one shared parser (`app/domain/sorting.py`), the four ports, services and routes, both adapters of each module, the shared contract tests and the route tests, the OpenAPI enums and a README paragraph. No schema change and no index (the lists are small).
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and the unit suite with the coverage floor exit 0 (1671 passed). The contract classes were run against a real PostgreSQL (Neon, random schema): 128 tests; 125 passed and 3 failed (below), all fixed and re-run green.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | Text sorts followed the database collation in PostgreSQL but the code point order in memory. Neon is `C.UTF-8`, so it would not show there, but a glibc locale such as the `en_US` of the CI image ignores spaces and punctuation and orders differently. | Fixed by Worker 1: `COLLATE "C"` on the customer name and email, the order and invoice customer name and the product SKU, with contract cases that distinguish the two orders (`a b`, `ab`, `a-c`, `ab-c`). |
| 2 | Important | Three contract tests failed only on PostgreSQL: they replaced customers (or orders) while the fixture's orders (or invoices) still referenced them (foreign key violation); the in-memory store has no foreign keys, so the unit run could not see it. | Fixed by the supervisor: the dependent rows are cleared first. Re-run on Neon: green. |
| 3 | Minor | `products.name` is sorted in Python after reading the whole catalog (the products table has no normalized column). | Accepted: the catalog is a fixed list of 15 rows and the order equals the in-memory one. |
| 4 | Note | The route declares the allowed values as a `Literal` and the service validates again with `parse_sort`. | Accepted: the second check is the one the unit tests of the service use; both give the same 422 body. |

## Lesson

The contract classes that run against both stores can only find foreign key mistakes on PostgreSQL. Every task that adds contract tests with `replace_all` must be run against a real database before the merge; the CI container does it afterwards.
