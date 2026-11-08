# Task 050: sorting of the lists (backend)

Assignee: Worker 1. Branch: `w1/list-sorting`. Reviewer: Supervisor.

**Base.** Branch from `main` after the supervisor has merged `docs/sorting-spec` (the SPEC text below), which he does before sending you this brief.

## Goal

Every serious table in a business application can be sorted, and "click the header and check the order" is one of the first things a QA engineer automates. The four lists of LabApp (customers, orders, invoices, products) are fixed-order today. Add the `sort` and `direction` query parameters exactly as `docs/SPEC.md` now defines them. This task is the backend only: the frontend headers come later (task 051), and this task must not change any screen.

## Read first

`docs/SPEC.md`: the **Sorting** sentences in the customers list rule (section 4), the orders list rule, the invoices list rule and the `GET /api/products` row (search for "Sorting" and "`sort`"), and section 7 for the error format. Then, for each module, `routes.py`, `service.py`, `ports.py`, `adapters/memory.py`, `adapters/postgres.py` and the shared store contract tests under `backend/tests/<module>/` (`contract_store.py`, `test_routes_*.py`). The customers' normalized search columns (`name_search`, `email_search` in `app/modules/customers/tables.py`) and how the PostgreSQL adapter fills them.

## Scope

You may edit under `backend/`: the four modules, their tests, `backend/README.md` (a short "Sorting" paragraph), and `docs/openapi.json` regenerated with the command `backend/README.md` gives (the contract drift test fails if you forget). You may add one Alembic migration only if you decide you need an index (you probably do not: say why in the report). Do not edit `docs/SPEC.md`, the frontend, `tools/` or `tests/`. No new dependency.

## Requirements

1. **One small shared type.** A frozen dataclass (for example `SortSpec(field: str, descending: bool)`) and a helper that parses and validates `sort` and `direction` for a list of allowed fields with a per-field default direction (`created_at` descends, every other field ascends) and returns a `SortSpec`; an invalid value raises the same 422 `VALIDATION_ERROR` with `errors[]` of `field` `sort` or `direction`, code `INVALID_FORMAT`, message "El formato no es válido." as the `status` filter does. Put it where the modules can share it without importing each other (read how the code already shares the pagination or the normalization helpers) and unit-test it.
2. **Ports, services, routes.** Thread the `SortSpec` through the four list calls (customers, orders, invoices, products). Query parameters are optional. Declare them so that the OpenAPI document shows the allowed values of `sort` and `direction` as enums. A request without them behaves exactly as today (the existing tests must pass unchanged).
3. **Adapters.** In memory and in PostgreSQL, implement the fields of the SPEC: customers `created_at`, `name`, `email` (the normalized text of the search columns); orders `created_at`, `number` (the numeric part of the number, as an integer), `customer` (the customer's name normalized as for `q`); invoices `created_at`, `number` (numeric part), `customer` (the snapshot name, normalized), `total` (numeric); products `id`, `sku`, `name` (normalized), `price` and `stock` (numeric). Ties are broken by `id` in the same direction as the sort. In SQL use `ORDER BY <expression> <dir>, id <dir>` and keep the filters and the paging as they are; for the numeric part of a number use a cast of the digits (for example `CAST(substring(number FROM '[0-9]+') AS integer)`), never a text comparison. Memory and PostgreSQL must give the same order for the same data (the shared contract tests prove it).
4. **Contract tests for both adapters** (add them to each module's shared `contract_store.py`): every field in both directions on the seed data; a tie (two customers with the same name differing only in case or accent, two invoices with the same total) ordered by id in the direction of the sort; an accented name (`Álvaro` among `A...` names) sorts with its plain letter; `number` sorts as an integer (create or replace-in data with `PED-0009`, `PED-0010`, `PED-0100`: the order is 9, 10, 100, not 10, 100, 9); sorting combined with `q` and with `status`; page 2 continues page 1 under a sort (use enough rows: replace the data with 45 rows).
5. **Route tests.** For each of the four endpoints: a valid `sort` and `direction` (check the order of the returned items by value), the defaults of `direction` (`created_at` descending, others ascending, `direction` without `sort` applies to `created_at`), an invalid `sort`, an invalid `direction` (422 with the exact `errors[]`), an empty value (`sort=`) is invalid (say how the existing `status=` case behaves and follow it), and no change without the parameters. Permission and the order of checks of SPEC section 7 are unchanged (an unauthenticated request is 401 before the validation).
6. **The contract.** Regenerate `docs/openapi.json`; the drift test passes; the new parameters appear on the four routes with their enums.
7. **README.** `backend/README.md`: a "Sorting" paragraph with one `curl` example.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass (the coverage floor holds). The integration tests (the contract classes run against PostgreSQL when `TEST_DATABASE_URL` is set) are skipped on your side; the supervisor runs them against a real database. Say which tests are integration-only.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits: the helper, then each module, then the contract and the README). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, which tests are integration-only, whether you added an index and why, and any deviation or open question.
