# Task 014: backend PostgreSQL adapters

Assignee: Worker 1. Branch: `w1/postgres-adapters`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 012 (the PostgreSQL foundation) is merged. It uses `app/infra/db.py`, the `tables.py` of the auth and customers modules, the migration `0001`, the Alembic environment and the integration harness of `tests/integration/`.

## Goal

Add the PostgreSQL adapters for the three ports that are in memory today (users, sessions, customers), a `seed` command, and the configuration switch that selects them. The in-memory adapters stay the default and the test doubles. The adapters must pass the same contract tests as the in-memory ones, and they must be correct under concurrency, because the production deployment is serverless: several function instances can act on the same rows at once.

You still have no database. Write the integration tests carefully; the Supervisor runs them against a real PostgreSQL and sends back what fails (the foundation task showed this works). Stick to the patterns given here.

## Read first

`docs/SPEC.md` sections 4, 5 (concurrency) and 9 (a reset keeps sessions), `backend/README.md` (the "PostgreSQL" section), `backend/app/infra/db.py`, `backend/app/modules/auth/` (ports, memory adapter, models, seed, container, tables), `backend/app/modules/customers/` (ports with their docstrings, memory adapter, search, tables), `backend/tests/auth/contract_users.py`, `backend/tests/auth/contract_sessions.py`, `backend/tests/customers/contract_repository.py`, `backend/tests/integration/` (conftest and helpers), `backend/app/errors.py` and `backend/app/main.py`.

## Scope

You may create and edit files under `backend/app/modules/auth/adapters/`, `backend/app/modules/customers/adapters/`, `backend/app/infra/`, `backend/tests/` and `backend/migrations/` only if a test proves the schema needs it; edit `backend/app/cli.py`, `backend/app/main.py`, `backend/app/errors.py`, `backend/app/modules/auth/container.py` and `backend/README.md`. Do not change the ports, the services, the routes or the in-memory adapters. No new dependencies.

## Requirements

### Common rules for every adapter

1. SQLAlchemy Core (`select`, `insert`, `update`, `delete`) on the existing `Table` objects, engine passed to the constructor, one transaction per port method (`with engine.begin() as connection`). Timestamps read from the database go through `as_utc`; timestamps written are the aware values received.
2. **Raw SQL must name its schema.** `schema_translate_map` rewrites only `Table` constructs. Anything you write as text or as a function argument that names a table (`pg_get_serial_sequence`, `setval`, advisory-lock keys are fine) must be qualified: add a helper in `app/infra/db.py`, `qualified_table_name(engine, table)`, that returns the identifier-quoted `"schema"."table"` when the engine's `schema_translate_map` has a schema and the plain quoted table name otherwise (use `engine.dialect.identifier_preparer`). Never concatenate a name yourself. In production there is no schema, so the unqualified name resolves in `public`.
3. **Unique violations are mapped by constraint name.** A helper `unique_violation_of(error, constraint_name) -> bool` checks `isinstance(error.orig, psycopg.errors.UniqueViolation)` and `error.orig.diag.constraint_name == constraint_name`. A violation of anything else is not mapped and propagates. Unit-test the helper with fake exceptions.
4. **Database errors must not leak values.** PostgreSQL puts the offending values in the `DETAIL` of the error (a unique violation prints the email, a check or not-null violation prints the whole failing row, including the password hash). `app/errors.py` logs unhandled exceptions with their traceback and message. Change that handler so that for `sqlalchemy.exc.DBAPIError` (and any `psycopg.Error`) it logs only the exception class, the SQLSTATE (`error.orig.sqlstate` when available) and the request id, never the message, the statement or the parameters; the response stays the 500 `INTERNAL_ERROR` problem. Test it: raise a fake `IntegrityError` whose message contains an email and a password hash from a route and assert with `caplog` that neither text appears in any log record.

### Users and sessions (`app/modules/auth/adapters/postgres.py`)

5. `PostgresUserRepository(engine)`: `get_by_email(email)` compares `lower(email) = :email` after `strip().lower()` of the argument; `get_by_id(id)`. Not part of the port: `replace_all(users)` for the seed and the future reset, which upserts the given users (`INSERT ... ON CONFLICT (id) DO UPDATE`), deletes the users that are not in the list, and never deletes sessions of the users it keeps (SPEC section 9: a reset keeps sessions; sessions of deleted users go with them through the `ON DELETE CASCADE`), then moves the identity sequence to `max(id) + 1` (1 when empty) with `select setval(pg_get_serial_sequence(<qualified name>, 'id'), :next, false)`.
6. `PostgresSessionStore(engine, max_sessions=MAX_SESSIONS)` follows the port docstrings exactly:
   - `create` is one transaction that starts with `pg_advisory_xact_lock(:key)` and a constant integer key (so concurrent creates serialize without touching the pooler's session state), inserts the session with `ON CONFLICT (token_hash) DO UPDATE` (an existing token is replaced, like the in-memory store), counts the rows and deletes the oldest by `last_seen_at` (ties broken by `token_hash`) until the count is at most the cap, never deleting the session just written.
   - `get` returns a `Session` or `None`; `touch` is `UPDATE ... SET last_seen_at = greatest(last_seen_at, :when) WHERE token_hash = :hash` (an unknown token matches nothing); `delete` ignores unknown tokens; `purge_older_than(cutoff)` deletes strictly older rows and returns the row count.
   - The foreign key requires the user to exist: `create` for an unknown user raises the database error; that is correct and is not mapped.

### Customers (`app/modules/customers/adapters/postgres.py`)

7. `PostgresCustomerRepository(engine)` implementing every sentence of the docstrings in `ports.py` (read them twice):
   - `add`: one `INSERT ... RETURNING`; the unique index `customers_email_lower_key` is the only duplicate check, and a violation of exactly that constraint becomes `EmailTaken`. Fill `name_search` and `email_search` with `normalize_for_search`.
   - `update` and `set_status`: one transaction that starts with `SELECT ... FOR UPDATE` on the row, then the checks in the documented order (not found, version, email taken, no change), then the `UPDATE`. The email-taken check is a query inside the transaction, but a concurrent transaction can still commit the same email between that query and the `UPDATE`; map a violation of `customers_email_lower_key` raised by the `UPDATE` to `EmailTaken` as well. A request that changes nothing returns the stored customer untouched. Keep the search columns in step with `name` and `email`.
   - `list`: `q` is literal text, so use `Column.contains(normalize_for_search(q), autoescape=True)` on `name_search` and `email_search` (combined with `or_`); filter by status; order by `created_at desc, id desc`; the total is a separate `select count(*)` with the same filters; `offset` and `limit` from `page` and `page_size`.
   - `replace_all`: inside one transaction `DELETE` then `INSERT` the given customers with explicit ids and their search columns, then move the identity sequence to `max(id) + 1` (1 when empty) as in point 5.

### Seed command and wiring

8. `app/cli.py` gets `seed`: it opens the engine from the settings and loads the four seed users (`seed_users(demo_password_hash())`) only when the `users` table is empty, and the ten seed customers (`seed_customers()`) only when the `customers` table is empty, moving the sequences; running it twice changes nothing. It prints a short result and never a URL or a secret.
9. Wiring in `app/modules/auth/container.py` and `app/main.py`: when `settings.database_url` is `None` nothing changes. When it is set, build the engine once (stored in `app.state.engine`) and use the PostgreSQL adapters for users, sessions and customers (`app.state.customer_repository` keeps its name and meaning). Creating the app and serving `GET /api/health` must not open a connection, and seeding never happens at startup.

### Tests

10. Changes to the existing contract tests, which the first review showed cannot run unchanged on PostgreSQL: in `tests/customers/contract_repository.py` the `replace_all` test must use customers with distinct emails (the in-memory store did not check, the unique index does); the users contract fixture is documented as "a fresh repository with the user returned by `user()`", so the PostgreSQL fixture calls `replace_all([user()])`; the sessions contract uses `user_id=1`, so the PostgreSQL fixture first ensures that user 1 exists (and any other user id a test uses). Keep the in-memory test classes passing unchanged otherwise.
11. Unit tests: `qualified_table_name` (with and without a schema, quoting), `unique_violation_of`, the error-logging change, the wiring (a bogus `database_url` builds the app, serves `/api/health` and uses the PostgreSQL classes; `None` uses the in-memory ones), the `seed` argument handling.
12. Integration tests (`tests/integration/`): run the three contract classes against the PostgreSQL adapters, and use for them an engine built **without** `pin_search_path` (only the schema translate map), so that any raw SQL that forgot to qualify its table fails against the empty `public` schema; the fixture that truncates may keep using the pinned engine. Add: `seed` twice leaves the same data; users `replace_all` keeps the sessions of kept users and removes those of deleted users; the session cap under 20 concurrent creates with a cap of 5 leaves exactly 5; a stale session `touch` never moves `last_seen_at` back; two threads updating the same customer with the same `expected_version` give exactly one winner; two threads creating customers with the same email give exactly one `EmailTaken`; a concurrent update to an email another thread just created gives `EmailTaken`, not an unhandled error; a search with accents (`q=cafeteria` finds "Cafetería"), `q=%`, `q=_` and `q=\` each match only text that really contains them; the identity sequence continues after `replace_all`; `get_by_email` finds a user whatever the case of the argument.
13. **Docs.** Extend the "PostgreSQL" section of `backend/README.md`: the adapters, the `seed` command, the rules for raw SQL and error mapping, and how to run the integration tests.

## Acceptance criteria

From `backend/`, all of these pass (without `TEST_DATABASE_URL` the integration directory is skipped, not an error):

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

## Rules for this task

- Commit as you go, in small real steps (about 18 to 26 commits): the helpers, each adapter method group, the logging change, the seed command, the wiring, each group of tests, the README. Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Never print, log or write a connection string anywhere (only `postgresql+psycopg://user:password@host/db`).
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec or a port is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, what you could not run, and any deviation or open question.
