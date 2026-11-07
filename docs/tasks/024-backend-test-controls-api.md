# Task 024: backend test-only endpoints and reset

Assignee: Worker 1. Branch: `w1/test-controls-api`. Reviewer: Supervisor, with a second-agent review because this code can erase a database.

**Base.** Branch from `main` after tasks 018, 019, 021 and 022 are merged. It uses the stores of task 022 (`ClockOffsetStore`, `FaultStore`), the guards of `app/guards/` (the controls middleware already answers 404 to every request under `/__test__` without the token), every adapter and seed of the other modules and the integration harness.

## Goal

Build the HTTP side of the test-only controls (`docs/ARCHITECTURE.md`, SPEC sections 3 and 9): `POST /__test__/reset`, `POST /__test__/seed`, `GET` and `POST /__test__/clock`, and `POST`, `GET` and `DELETE /__test__/faults`. They exist so that the owner's automated tests, which run against deployments on a serverless platform, can restore a known state, move the application's time and provoke latency and failures. Every piece of state lives in PostgreSQL; in-memory mode keeps working through the in-memory stores and is the test double of this task.

## Read first

`docs/SPEC.md` section 3, section 7 and section 9; `docs/SEED.md`; `docs/ARCHITECTURE.md` ("Test-only controls"); `docs/tasks/021-backend-postgres-invoices.md` and `docs/tasks/022-backend-request-controls.md`; `backend/app/guards/`, `backend/app/main.py`, `backend/app/cli.py`, `backend/app/modules/auth/container.py` and `adapters/postgres.py` (the session advisory-lock key), the ports, adapters and seeds of `auth`, `customers`, `orders`, `invoices` and `testcontrols`, `backend/tests/integration/`.

## Scope

You may create files under `backend/app/modules/testcontrols/` (the resetter and the router), `backend/tests/testcontrols/` and `backend/tests/integration/`; edit `backend/app/main.py`, `backend/app/cli.py`, `backend/app/modules/auth/container.py` and `backend/README.md`; and make **only this change** in the adapters of the other modules: every `replace_all` of the PostgreSQL adapters (and of the in-memory ones where it helps the tests) gains an optional keyword `connection` (an open SQLAlchemy connection or `None`): with a connection it runs inside that transaction and does not open its own. Do not change ports, services or routes of the other modules. No new dependencies.

## Requirements

1. **Resetter.** A `Resetter` that restores, as SPEC section 9 says: the data of every module (customers, products, orders with their lines, invoices with their lines and payments, idempotency keys), the number sequences (the next order is `PED-0008`, the next invoice `FAC-0004`, the next payment id 5, the next customer id 11), the tax rate (to `Settings.default_tax_rate` quantized), the clock offset (to `0`, upserting the `settings` row), the fault rules (all removed) and the rate-limit counters of the instance (the in-memory limiters; shared limits are a later task), and it **keeps the sessions**: the four users keep their ids (upsert and delete-missing, never touching sessions). Compute `demo_password_hash()` **before** opening the transaction.
   - In PostgreSQL the whole reset is **one transaction** (`engine.begin()` and the `connection=` keyword), so no request sees a half-restored database, and it takes a transaction advisory lock (a key different from the session lock key of the auth adapter) so two resets do not interleave.
   - The order of operations respects the foreign keys and uses only the adapters' own `replace_all`, never `TRUNCATE` and never a raw `DELETE` (Core statements only, so the schema mapping applies): (1) `invoices.replace_all([], [], connection=c)`, (2) `orders.replace_all([], [], rate, connection=c)`, (3) `customers.replace_all(seed, connection=c)`, (4) `orders.replace_all(seed..., connection=c)`, (5) `invoices.replace_all(seed..., connection=c)`, (6) users, settings, clock, faults. There are two implementations behind one `Resetter` Protocol: `MemoryResetter` calls the in-memory stores and passes no `connection`; `PostgresResetter` takes the advisory lock as its **first statement** (`lock_timeout` also bounds advisory waits, so a concurrent reset waits for the first), then does everything on one `engine.begin()` connection: the five `replace_all(..., connection=c)`, the users, its own Core statements on `c` for the clock row (`insert(settings)...on_conflict_do_update` to `'0'`) and for the faults (`delete(fault_rules)`). It never calls `ClockOffsetStore.set` or `FaultStore.clear` inside the transaction (they open their own transaction and would wait on the rows the reset already holds). The migration `0003` made `orders.invoice_id` an `ON DELETE SET NULL` reference for this reason.
   - A reset is meant for a quiet system: a request that runs during it may fail (409 or 503 `LOCK_TIMEOUT`), and a payment or an issue that commits in the middle can make the reset itself fail with a foreign key error: the router answers 409 and says to retry once. Tests only assert that after a successful reset everything is consistent.
   - `seed(dataset)`: `default` loads the same data as the reset without touching the clock, the faults or the rate-limit counters (the number sequences do restart, because `replace_all` restarts them); `empty` leaves only the four users and the settings (every other table emptied, sequences restarted, the tax rate restored, the clock row back to `'0'`).
2. **Router** (`app/modules/testcontrols/routes.py`), mounted at `/__test__` (not under `/api`), `include_in_schema=False`, all plain `def` handlers, JSON bodies with `extra="forbid"` and strict types. The guard of task 017 stays in front of everything, and **the router adds its own defense**: a dependency on every route repeats `controls_allowed(...)` and answers 404 (a test that builds the application with a token and without one proves both layers).
   - `POST /__test__/reset` answers 200 `{"status": "ok"}`.
   - `POST /__test__/seed` takes `{"dataset": "default" | "empty"}` (any other value is a 422 `VALIDATION_ERROR` on `dataset`) and answers 200 `{"dataset": "<value>"}`.
   - `GET /__test__/clock` answers `{"now": "<ISO 8601 UTC with Z>", "offset_seconds": <number>}`; `POST /__test__/clock` takes exactly one of `{"offset_seconds": number}` (replace) or `{"advance_seconds": number}` (add, through `ClockOffsetStore.advance`); anything else, a non-finite number, a boolean, an offset beyond plus or minus ten years, is a 422; a cumulative `advance_seconds` must also keep the offset within plus or minus ten years (otherwise the clock leaves the range of `datetime` and every request becomes a 500 until a reset): `ClockOffsetStore.advance` takes the limit and, in SQL, adds `WHERE abs(value::float8 + :delta) <= :max`; no row updated means a 422; the answer has the same shape as the `GET`.
   - `POST /__test__/faults` adds a rule and answers 201 with the rule and its `id`. Body: `{"target": "route" | "gateway", "method": "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | null, "path": string | null, "latency_ms": integer 0 to 10000 (default 0), "status": integer 400 to 599 | null, "times": integer 1 to 1000 | null}`, validated with the rule validation of task 022 (a 422 on the offending field); a 51st rule (`TooManyFaultRules`) is a 422. `GET /__test__/faults` lists the rules with their remaining count; `DELETE /__test__/faults` removes all of them (204).
3. **CLI.** `python -m app.cli reset` calls the resetter for local use. It **refuses** unless `TEST_MODE=1` and `--yes` are both given, prints the schema it will touch, and refuses when `DATABASE_SCHEMA` is unset (it would wipe `public`) unless `--allow-public` is also given.
4. **Wiring** (`main.py`, `container.py`): choose the in-memory or the PostgreSQL implementations by `settings.database_url`; keep `app.state.resetter`; creating the application and the health check open no connection.
5. **Tests.** Unit (in memory): every endpoint and every validation (bodies at their boundaries, unknown fields, the two clock bodies, booleans and non-finite numbers, the fault rules table, the 51st rule), the guard (with and without the token, `TEST_MODE` 0 and 1, and the router's own dependency), reset (modify a customer, an order, an invoice, the rate, the clock, add a fault, log in; reset; everything is back and the session still works), seed `empty` and `default` (after `empty`, create a customer first, then an order: `PED-0001`), the CLI refusals. Integration (PostgreSQL): the reset is atomic (a reader thread polling the customers count during a reset only ever sees the old or the new total, never a mix) and keeps the sessions; the sequences restart; reset twice in a row is idempotent; two concurrent resets both finish; **a reset against the real test schema while the engine's `search_path` is pinned to a decoy schema that holds same-named tables with sentinel rows leaves the decoy rows untouched**; the orders' `invoice_id` links are back (orders 3, 4, 5 point to invoices 1, 2, 3 with `version` 1) after a reset that followed an issue and a payment.
6. **Docs.** A "Test controls" section in `backend/README.md`: each endpoint with an example `curl`, the guard table, what is stored where, what a reset keeps, the order of operations of the reset, the CLI refusals, and the note that the shared rate-limit counters are a later task.

## Acceptance criteria

From `backend/`, all of these pass (without `TEST_DATABASE_URL` the integration directory is skipped):

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

and, manually, with the server started as in the backend README with `TEST_MODE=0 TEST_TOKEN=secret`: `POST /__test__/reset` without the token answers 404 and with `X-Test-Token: secret` answers 200; advance the clock one hour and show it; add a fault of 500 on `GET /api/customers` with `times` 2 and show two 500s and then a 200; reset and show the customers back.

## Rules for this task

- Commit as you go, in small real steps (about 20 to 26 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Never print, log or write a connection string, the test token or a card number anywhere.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec or a port is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, what you could not run, and any deviation or open question.
