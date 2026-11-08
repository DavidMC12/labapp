# Task 037: hardening of the test controls after the second-agent review

Assignee: Worker 1. Branch: `w1/controls-hardening`. Reviewer: Supervisor.

**Base.** Branch from the tip of your latest branch (`w1/openapi-quality`, which contains tasks 021, 022, 024, 030 and 036). It changes code of tasks 022 and 024.

## Goal

A second agent (a Claude process) reviewed the code of tasks 022 and 024, which can erase a database. It found no way for a request without the token to reach a control or to wipe the wrong data, but it found three Important defects and several Minor ones. The supervisor checked each against the code; all are real. Fix them, with tests. Each fix is its own commit.

## Read first

`docs/tasks/022-backend-request-controls.md`, `docs/tasks/024-backend-test-controls-api.md`, `backend/app/modules/testcontrols/` (all), `backend/app/guards/controls.py`, `backend/app/guards/request_controls.py`, `backend/app/guards/ratelimit_middleware.py`, `backend/app/main.py`, `backend/app/errors.py`, `backend/app/cli.py`, `backend/app/config.py`, every `replace_all` of the PostgreSQL adapters (customers, orders, invoices, auth) and `backend/tests/integration/test_reset.py`.

## Scope

You may edit files under `backend/` (application code of the modules and guards named above, tests, the README) and `docs/SPEC.md` **only** to add error-table rows if a new code is needed (it should not be). No new dependencies. Do not change an answer of the public API.

## Requirements

### Important

1. **A failed reset must not leave the sequences restarted.** `setval` is not undone by a rollback (PostgreSQL docs): each `replace_all` restarts its sequences with `setval` while the data steps are still running, so when a later step fails (a `LockNotAvailable` on the customers delete, for example) the data rolls back to rows such as `PED-0012` and `FAC-0009` but the sequences stay at 1, and the next insert collides until another reset succeeds. Fix: every `replace_all` that takes the `connection` keyword also takes `defer_sequences: list | None = None`; when a list is given it **appends** its sequence restarts to it (as small callables that take the connection) instead of running them; the `PostgresResetter` passes one list to all of its `replace_all` calls and runs everything in it as the **last statements of the transaction**, after every data step succeeded. Without the keyword the behavior is unchanged (the seed command and the standalone calls). Document the rule in the README and in the docstring of the resetter.
2. **A test that can tell one transaction from several, and a failing step.** In `tests/integration/test_reset.py`: start the atomicity test from a **non-empty, different** state (for example 3 customers, 1 order and 1 invoice created through the stores) and let the reader thread poll **one statement that returns several counts** (`select (select count(*) from customers), (select count(*) from orders), (select count(*) from invoices)`): only the old triple and the new triple may ever appear. Add a test that makes the **last** data step raise (monkeypatch one `replace_all` of the resetter's stores) and asserts that the row counts **and the sequence values** (read with `last_value` and `is_called` from the sequences) are exactly what they were before. Add the same failing-step test for `PostgresResetter` with an exception raised in the deferred sequence step, asserting nothing partial remains.
3. **Database errors in the request controls middleware.** `load_request_controls` runs outside FastAPI's exception handlers, so a lock timeout in it becomes a 500 and its log carries the driver message. Wrap the load in `try/except (DBAPIError, psycopg.Error)`: answer 503 `LOCK_TIMEOUT` (with the problem document of `errors.py`) for a lock timeout (`is_lock_timeout`), and a 500 `INTERNAL_ERROR` problem for any other database error, logging **only** the exception class, the SQLSTATE and the request id (never the message). Never let the exception reach the server error middleware. Tests with a store that raises each kind of error, in memory mode (a fake store) and checking the log text.

### Minor

4. **One path for the guards.** The controls guard, the rate limiter and the request-controls exemption compare the raw `scope["path"]`. Use the same path the router uses (`starlette._utils.get_route_path(scope)`, or the equivalent of the installed Starlette) in all three, and make the controls guard answer 404 to a `websocket` scope under `/__test__`. Tests: the guard answers 404 without the token for `GET`, `POST`, `HEAD` and `OPTIONS`, for the trailing slash (`/__test__/reset/`), the double slash (`//__test__/reset`), a case variant (`/__TEST__/reset`), a percent-encoded variant, and with `root_path` set on the scope (`/prefix` + `/__test__/reset`).
5. **The reset error mapping.** In the router: log the exception class and SQLSTATE (never the message) when a reset or a seed fails with an `IntegrityError`; apply the same 409 `RESET_CONFLICT` mapping to `seed` as to `reset`; map SQLSTATE `40P01` (deadlock) to the same 409; any other database error stays a 500 through the common handler. Tests with injected errors.
6. **Rule paths.** `validate_rule` rejects a path that contains a control character or a lone surrogate, is longer than 2048 characters, begins with `/__test__`, or is `/api/health` (they can never match: the middleware exempts them), each with a 422 on the field `path` and a message in Spanish. The 51st-rule 422 gets an `errors[]` entry (`field: "target"`, code `OUT_OF_RANGE` is not right: use `INVALID_FORMAT` with the message "Ya hay 50 reglas activas. Elimina alguna con DELETE /__test__/faults."). The body validation reports **all** problems of the body together (`times` and the rule fields in one answer). Tests for each.
7. **Only API requests pay for the controls.** The request controls middleware runs only for paths under `/api/` (the same predicate as the rate limiter) and exempts `HEAD /api/health` as well as `GET`. Tests.
8. **The CLI reset.** Print the **host and the database name** (never the user or the password) next to the schema; refuse a host that is not `localhost`, `127.0.0.1` or `::1` unless `--allow-remote` is also given; build the subparser with `allow_abbrev=False`. Tests for the refusal, the flag and the abbreviation.
9. **`TEST_MODE` online.** `Settings` also refuses `TEST_MODE=1` when `AWS_LAMBDA_FUNCTION_NAME` or `VERCEL` is set (Vercel functions run on AWS Lambda, and `VERCEL_ENV` is exposed only with a project setting), with a message that names the variable. README line.
10. **Small ones.** Migration `0004` inserts its `settings` row with `ON CONFLICT DO NOTHING` (a new migration is not needed: edit `0004` only if it is not applied anywhere yet; it is not, say so in your report); `GET /__test__/clock` reads the offset once and derives `now` from it (one read, not two); a README line: "a gateway fault with latency holds the invoice lock for up to 10 seconds, so a reset that needs that invoice can answer 409 or 503".

## Acceptance criteria

From `backend/`, all of these pass (without `TEST_DATABASE_URL` the integration directory is skipped):

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
uv run python -m app.cli openapi --output ../docs/openapi.json && git diff --exit-code ../docs/openapi.json
```

## Rules for this task

- Commit as you go, in small real steps (about 14 to 20 commits, each fix in its own commit with its tests). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Never print, log or write a connection string or the test token anywhere.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the brief is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, what you could not run (the integration tests need the Supervisor), and any deviation or open question.
