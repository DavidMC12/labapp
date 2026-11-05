# Review: PostgreSQL layer brief (task 012, 2026-11-04)

- **Subject:** the first version of the brief for the PostgreSQL adapters, before any work started.
- **Reviewer:** a second agent that read the brief against the ports, the contract tests, the configuration and the tests.
- **Verdict:** With fixes, three Critical findings. The Supervisor checked each claim against the code before acting; all three Critical and the Important ones were confirmed.
- **Decision:** the brief was split. Task 012 is the foundation (configuration, engine, tables, migration, migrate command, integration harness) that the Supervisor validates against a real database; task 014 (adapters, seed, wiring, contract runs) is written afterwards, with the findings below carried into it. Nobody can run this code until the Supervisor does, so the first step has to be small.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Critical | `schema_translate_map` only rewrites `Table` constructs, so a raw `TRUNCATE`, `pg_get_serial_sequence` or `setval` would run against `public` and could wipe real tables. | 012: the integration engine pins `search_path` through a connection option (direct connection only), the fixture asserts `current_schema()` before any `TRUNCATE`, and the schema drop is guarded by a positive pattern. 014: raw SQL is qualified explicitly. |
| 2 | Critical | `SET search_path` autobegins a transaction in SQLAlchemy 2, so Alembic would believe an outer transaction was open and roll the whole migration back while reporting success. | 012: the exact `env.py` pattern with a `commit()` after the `SET`; settings passed through `config.attributes`, never `set_main_option`. |
| 3 | Critical | The contract tests cannot run unchanged: `replace_all` in the customers contract creates two rows with the same email, the users contract expects the row `user()`, and the sessions contract needs user 1 for the foreign key. | 014: change the contract to distinct emails, make the fixtures call `replace_all([user()])` and create user 1 before any session. |
| 4 | Important | `replace_all` for users deleted sessions, against SPEC section 9 (a reset keeps sessions). | 014: upsert the users and delete the missing ones, never touching sessions. |
| 5 | Important | The guard that keeps the unit suite away from a developer's `.env` was a fixture, but `tests/conftest.py` imports a module-level `app = create_app()` first; it also broke `tests/test_config.py`. | 012: the guard goes at the top of `conftest.py`; `test_config.py` re-enables the env files for itself. |
| 6 | Important | Making `database_url` optional breaks `tests/auth/test_routes.py` (a `None` in a `not in`), and `.env.example` would select PostgreSQL on a fresh checkout; an empty `DATABASE_URL=` would crash. | 012: the test is fixed, blank means `None`. The Supervisor updates `.env.example` and the docs. |
| 7 | Important | Leak and injection paths: SQL errors print bound parameters and tracebacks are logged; `session_secret` was never hidden in `repr`; the schema name went into `SET search_path` unvalidated; a pooled `SET` would leak across clients. | 012: `hide_parameters`, hidden fields, a validated and quoted schema, and no fallback to the pooled URL when a schema is set. |
| 8 | Important | A unique violation during `update` (a concurrent create) was not mapped and would be a 500. | 014: map it to `EmailTaken` by constraint name, in `add` and `update`. |
| 9 | Important | The task was too big to write blind. | Split in two (see above). |
| 10 | Minor | `replace_all` must fill the search columns; `get_by_email` should compare `lower(email)`; `tests/integration/__init__.py` and skip markers; non-ASCII `lower()` depends on the database locale; `list` and `count` are two statements. | 014 and 012 as appropriate; the rest accepted. |

Deferred: the latency of opening a connection per request with `NullPool` (decided on purpose, measured later), the in-memory rate limiter, idempotency store and clock offset, which are the next serverless tasks, and an integration job in CI.
