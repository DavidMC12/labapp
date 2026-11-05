# Task 012: backend PostgreSQL foundation

Assignee: Worker 1. Branch: `w1/postgres-foundation`. Reviewer: Supervisor.

## Goal

Everything stateful is in memory today (users, sessions, customers). The API will run on a serverless platform with no process that lives between requests, so the same ports must also have PostgreSQL adapters. This task lays the foundation only: configuration, the database engine, the tables, the migration, the migrate command and the integration-test harness. The adapters come in the next task (014), after the Supervisor has run this foundation against a real database. In-memory adapters stay the default and the test doubles; nothing in the running application changes in this task.

You have no PostgreSQL server and no connection string, so you cannot run the integration tests. Write them with care, run everything else, and say so in your report. The Supervisor runs the integration tests against a real database and sends back what fails. Because nobody can run this code until then, stick to the patterns given here instead of inventing your own.

## Base

Branch from `main` (`git switch -c w1/postgres-foundation main` in your worktree). Read first: `docs/SPEC.md` sections 4, 5 and 9, `backend/README.md`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/modules/auth/` (ports, models, seed, container), `backend/app/modules/customers/` (ports, models, search), `backend/tests/conftest.py` and `backend/tests/test_config.py`.

## Scope

You may create and edit files only under `backend/`. Add the dependencies `sqlalchemy` (2.x), `psycopg[binary]` (3.x) and `alembic` with `uv add`; if one of them has no wheel for Python 3.14, stop and report instead of changing the Python version. Do not touch `docs/`, `.env.example` or anything outside `backend/` (the Supervisor updates those).

## Requirements

### Configuration (`app/config.py`)

1. `database_url` becomes `str | None` with default `None`. Add `database_url_unpooled: str | None = None` (env `DATABASE_URL_UNPOOLED`; used only by migrations) and `database_schema: str | None = None` (env `DATABASE_SCHEMA`). A blank value (empty or only spaces) means `None`, because an empty `DATABASE_URL=` line must not select the database.
2. Hidden values. `Settings.session_secret` is a plain field today and shows up in `repr(Settings())`. Declare `session_secret`, `test_token`, `database_url` and `database_url_unpooled` with `Field(repr=False)`, and set `hide_input_in_errors=True` in the model config so a validation error never echoes a value. Tests: none of the four values appears in `repr`, `str` or a `ValidationError` message.
3. `normalize_database_url(url)` (in `app/infra/db.py`) accepts `postgres://`, `postgresql://` and `postgresql+psycopg://` and returns the `postgresql+psycopg://` form; query parameters such as `sslmode` and `channel_binding` pass through untouched. Anything else raises `ValueError("Unsupported database URL")` with that fixed message and nothing from the input.
4. `database_schema` is validated in `Settings`: it must fully match `[a-z_][a-z0-9_]{0,62}`, and `public`, anything starting with `pg_` and `information_schema` are rejected. It is quoted wherever it is used with `engine.dialect.identifier_preparer.quote_schema(name)`, never with an f-string of your own.
5. Existing tests that the change breaks are fixed in this task: `tests/auth/test_routes.py` line 274 compares `container.settings.database_url` (now possibly `None`); build the settings with an explicit fake URL (`postgresql+psycopg://user:password@host/db`) and assert the rendered text does not contain it. `tests/test_config.py` asserts that values are read from `.env`; it must enable the env files again for itself (`monkeypatch.setitem(Settings.model_config, "env_file", ("../.env", ".env"))`) because of item 6.

### Keeping the unit suite away from a database

6. A developer's `backend/.env` will contain `DATABASE_URL`, and `app/main.py` ends with a module-level `app = create_app()`, which builds `Settings()` the moment `tests/conftest.py` imports it. So the guard cannot be a fixture: it goes at the very top of `tests/conftest.py`, before any `app` import, next to the existing `SESSION_SECRET` line: remove `DATABASE_URL`, `DATABASE_URL_UNPOOLED` and `DATABASE_SCHEMA` from `os.environ`, and set `Settings.model_config["env_file"] = None` (import only `app.config` there). Test: with a `.env` file that contains a database URL in a temporary working directory and the env files re-enabled for that test, `Settings()` reads it; with the suite's default configuration `Settings().database_url is None`.

### Engine (`app/infra/db.py`)

7. One `MetaData` with a naming convention for constraints, and `create_db_engine(settings, *, pin_search_path=False)` returning a SQLAlchemy 2 engine with: `poolclass=NullPool` (each serverless instance connects through the provider's pooler), `hide_parameters=True` (SQL errors must not print bound values such as password hashes, token hashes or customer data; the application logs full tracebacks), `connect_args={"prepare_threshold": None}` (the pooler runs in transaction mode and does not support prepared statements), and, when `database_schema` is set, `execution_options(schema_translate_map={None: schema})`. It builds the engine from `database_url` and raises a fixed-message `RuntimeError("Database is not configured")` when that is `None`. Creating the engine must not open a connection.
8. `pin_search_path=True` is used by the integration tests only. It adds `connect_args["options"] = f"-c search_path={schema}"` (the schema is already validated) and is refused (`ValueError`) when no schema is set. Reason: `schema_translate_map` rewrites SQLAlchemy `Table` constructs only; any raw SQL (`TRUNCATE`, `pg_get_serial_sequence`, `setval`) resolves names through `search_path`. The pooler rejects startup options, so production never pins; the adapters of task 014 will qualify raw SQL explicitly.
9. Timestamps are `timestamptz`; a helper `as_utc(value)` returns `value.astimezone(UTC)` for what the driver returns.

### Tables and migration

10. One `tables.py` per module (`app/modules/auth/tables.py`, `app/modules/customers/tables.py`) with SQLAlchemy Core `Table` objects on the shared `MetaData`. Explicit names for everything the adapters will depend on:
   - `users`: `id integer generated by default as identity` primary key, `name text`, `email text`, `role text` with a check for the four values of `Role`, `password_hash text`, `created_at timestamptz`, `version integer default 1`, all not null; unique index `users_email_lower_key` on `lower(email)`.
   - `sessions`: `token_hash text` primary key, `user_id integer` references `users(id)` on delete cascade, `created_at timestamptz`, `last_seen_at timestamptz` (all not null); index `sessions_last_seen_at_idx` on `last_seen_at`.
   - `customers`: `id integer generated by default as identity` primary key, `name text not null`, `email text not null`, `phone`, `tax_id` and `address` as nullable `text`, `status text not null` with a check for `active` and `inactive`, `version integer not null`, `created_at` and `updated_at` as `timestamptz not null`, `name_search text not null` and `email_search text not null` (the `normalize_for_search` form of each, written by the adapter at write time, never computed by the database); unique index `customers_email_lower_key` on `lower(email)`; index `customers_created_at_id_idx` on `(created_at desc, id desc)`.
11. Alembic in `backend/migrations/` with `alembic.ini` (no URL in it; resolve its path from `__file__` in code, never from the working directory). One hand-written revision `0001` (no autogenerate) creating these tables, indexes and checks with those exact names, and a `downgrade` that drops them. `env.py` follows this pattern exactly:
    - It takes the settings from `config.attributes["settings"]` when present (the tests pass them this way) and otherwise builds `Settings()`. It never uses `config.set_main_option` for the URL (ConfigParser would interpolate `%` in an encoded password).
    - The URL is `database_url_unpooled`; when it is missing it falls back to `database_url` **only if no schema is set**. With a schema and no unpooled URL it raises `RuntimeError("DATABASE_URL_UNPOOLED is required with DATABASE_SCHEMA")` (a session-level `SET` through a transaction-mode pooler would leak across clients).
    - It builds its own plain engine (`create_engine(url, poolclass=NullPool, hide_parameters=True)`), not the one from `create_db_engine`.
    - With a schema:
      ```python
      with engine.connect() as connection:
          connection.exec_driver_sql(f"SET search_path TO {quoted_schema}")
          connection.commit()  # SQLAlchemy 2 autobegins; without this Alembic believes an outer transaction is open and rolls everything back
          context.configure(connection=connection, target_metadata=metadata)
          with context.begin_transaction():
              context.run_migrations()
      ```
      Without a schema the same block without the `SET` and the `commit`. The version table is not qualified: it lands in the first schema of the search path.
12. `app/cli.py`, run as `uv run python -m app.cli migrate`: runs `alembic upgrade head` through `alembic.command.upgrade` with the settings in `config.attributes`. It prints a short result and never a URL or a secret. (`seed` comes in task 014.)

### Tests

13. Unit tests (run everywhere): `normalize_database_url` (all accepted forms, query parameters kept, a fixed-message error that does not contain the input); the blank values; the schema validator (accepts `t_0123456789abcdef`, rejects `public`, `pg_x`, uppercase, quotes, semicolons, 64 characters); hidden values; `create_db_engine` (no connection is opened, `NullPool`, `hide_parameters`, the translate map present only with a schema, `pin_search_path` refused without a schema, the error without a URL); the metadata (table and index names, checks) compiled with the PostgreSQL dialect to strings (`CreateTable`, `CreateIndex`) and compared against the expected fragments, including `generated by default as identity`, `lower(email)` and `created_at DESC, id DESC`; the migration module has `upgrade` and `downgrade`, and `alembic.ini` resolves from any working directory; the CLI parses `migrate` and rejects anything else.
14. Integration tests in `tests/integration/` (with `__init__.py`): a `conftest.py` that adds a skip marker to every test of the directory when `TEST_DATABASE_URL` (a direct, unpooled URL, read from the process environment only) is missing, so the directory is reported as skipped. A session-scoped fixture creates the schema `t_<16 random hex>`, builds `Settings(database_url=..., database_url_unpooled=..., database_schema=...)` from `TEST_DATABASE_URL` with keyword arguments, runs `alembic.command.upgrade(config, "head")` with `config.attributes["settings"] = settings`, yields an engine from `create_db_engine(settings, pin_search_path=True)`, and at the end drops the schema with `DROP SCHEMA ... CASCADE` only if `re.fullmatch(r"t_[0-9a-f]{16}", schema)` holds immediately before the statement. A function-scoped fixture first asserts `select current_schema()` equals the test schema and only then truncates the three tables with `RESTART IDENTITY CASCADE`. Tests: upgrade creates the three tables, the named indexes and the checks in the test schema and nothing in `public`; downgrade then upgrade again works; an explicit id can be inserted into an identity column and the next generated id continues after the sequence was moved; a bad `role` or `status` is rejected; deleting a user deletes the user's sessions; two emails differing only in case collide on `lower(email)` in both users and customers (assert the constraint name in the error); `timestamptz` values round trip with their microseconds and come back timezone-aware.

### Docs

15. A "PostgreSQL" section in `backend/README.md`: the variables (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `DATABASE_SCHEMA`) and what each is for, the `migrate` command, and how to run the integration tests (`TEST_DATABASE_URL=... uv run pytest tests/integration`). Use only the placeholder `postgresql+psycopg://user:password@host/db`.

## Acceptance criteria

From `backend/`, all of these pass (without `TEST_DATABASE_URL` the integration directory is reported as skipped, not as an error):

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

## Rules for this task

- Commit as you go, in small real steps (about 14 to 20 commits): the configuration, each validator, the engine, each table, the migration, `env.py`, the CLI, the conftest guard, each group of tests, the README. Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Never print, log or write a connection string anywhere, not even a placeholder that looks real (only `postgresql+psycopg://user:password@host/db`).
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory.
- If the spec or a port is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, what you could not run, and any deviation or open question.
