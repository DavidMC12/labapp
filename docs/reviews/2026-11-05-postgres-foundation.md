# Review: backend PostgreSQL foundation (task 012, 2026-11-05)

- **Branch:** `w1/postgres-foundation`, by Worker 1 (21 commits, all inside `backend/` plus the brief and its review record).
- **Reviewer:** Supervisor. The brief was reviewed twice by a second agent before and during the work (first version: 3 Critical findings, split into two tasks; second version: a missing URL normalization and a test-mock collision, both resolved).
- **Verdict:** With one fix in round 1, then ready to merge. No Critical findings in the code.
- **Verified by the supervisor:** the four acceptance commands re-run with real exit codes (667 passed, 10 skipped without a database, lint and format clean); the whole configuration, engine, Alembic environment, migration, CLI and table code read; the 10 integration tests run against a real PostgreSQL 18 development database (a random test schema per run), first 9 of 10 passing and then 10 of 10 after the fix; afterwards the database held no leftover test schema and `public` was empty; the same checks on a clean clone before pushing.

## What the work did well

The Alembic environment follows the prescribed pattern (the `commit()` after `SET search_path`, settings through `config.attributes`, a plain engine, no fallback to the pooled URL with a schema), and the migration really creates the tables in the test schema and none in `public`. The engine is lazy, uses `NullPool`, `prepare_threshold=None` and `hide_parameters`, and the schema is validated and quoted by the dialect. The unit suite cannot reach a database even with a `.env` that has one, and the settings never show secrets in `repr`. The integration harness refuses to touch `public` and drops only schemas that match the generated pattern.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The check constraints were created as `ck_users_ck_users_role` and `ck_customers_ck_customers_status`: Alembic applies the metadata naming convention to plain-string names, and the `ck` convention already adds the prefix. Found only by the integration test against a real database. | Fixed: `op.f(...)` keeps the names as written. |

Carried into task 014 (adapters): database errors put the offending values in their `DETAIL`, so unhandled database errors must be logged without their message; raw SQL must name its schema explicitly; the adapter integration tests must run on an engine without the pinned search path so a forgotten qualification fails.

Deferred: an integration job in CI, and the latency of one connection per request with `NullPool` (to be measured on the first online deployment).
