# LabApp backend

FastAPI backend for LabApp. It provides the health endpoint, request tracing and RFC 9457
problem responses, plus the authentication, customer, order and invoice modules over
PostgreSQL or in-memory devices (see below).

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)

## Install

```bash
cd backend
uv sync
```

## Run

```bash
SESSION_SECRET=dev-secret uv run uvicorn app.main:app --port 8000
```

The app refuses to start when `SESSION_SECRET` is empty or still `change-me`, unless
`TEST_MODE=1`. Settings are read from real environment variables first, then from
`backend/.env` and the repository-root `.env` (copy `../.env.example` to either place).
`backend/.env` wins over the repository-root `.env`, and real environment variables always
win over both files.

`TEST_MODE=1` is refused when the process runs on Vercel: `VERCEL_ENV` set to
`production` or `preview`, or `AWS_LAMBDA_FUNCTION_NAME` or `VERCEL` set (Vercel
functions run on AWS Lambda). The error names the variable that refused it.

Check the API:

```bash
curl -i localhost:8000/api/health
```

Every response carries an `X-Request-Id` header. Send your own `X-Request-Id` to have it
echoed; values must match `^[A-Za-z0-9._-]{1,64}$`, otherwise a new UUID4 is generated.

## OpenAPI contract

`docs/openapi.json` is the committed contract of the API: the document the owner's
automation and any other tool can read without starting the server. FastAPI generates it
for an application built with no database and no environment variables:

```bash
cd backend
uv run python -m app.cli openapi --output ../docs/openapi.json
```

Without `--output` the command prints the document to standard output.
`tests/test_openapi_contract.py` fails when the committed file and the application
disagree, and CI runs that test, so every change of the API regenerates the file and
commits it in the same change.

What a reader can rely on:

- **Errors.** Every error answer of every operation is `application/problem+json` and
  references the `Problem` component: `type`, `title`, `status`, `code` (stable),
  `detail` (Spanish) and the optional `errors[]` of `FieldError {field, code, message}`,
  `shortages[]`, `payment_id`, `reason` and `retry_after`. The description of each answer
  names the codes it can carry.
- **Answers that apply to every route.** Every operation documents only the guards it
  really passes through: 400 `MALFORMED_JSON` and 413 `PAYLOAD_TOO_LARGE` when it takes a
  body, 401 `UNAUTHENTICATED`/`SESSION_EXPIRED` when it needs a session, 403
  `CSRF_ORIGIN_MISMATCH` (and `FORBIDDEN` when it also needs a permission) on POST,
  PATCH, PUT and DELETE, 429 `RATE_LIMITED`, 500 `INTERNAL_ERROR` and 503 (`LOCK_TIMEOUT`,
  plus `SERVICE_BUSY` on login and `PAYMENT_GATEWAY_UNAVAILABLE` on payment). The feature
  answers (404, 409, 422 and the business codes) appear only where `docs/SPEC.md` says the
  operation can give them. `GET /api/health` is the exception: the rate limiter skips it
  and it never reaches the database, so it documents neither 429 nor 503.
- **Sessions.** The `cookieAuth` scheme is an `apiKey` in the `labapp_session` cookie.
  Every operation carries it except the three public ones: `POST /api/auth/login`,
  `POST /api/auth/logout` (idempotent, as the SPEC says) and `GET /api/health`.
- **Shapes.** Money is a string with two decimals (`^[0-9]+\.[0-9]{2}$`), with an example;
  the tax-rate input documents its own pattern. Ids and versions are integers from 1 to
  2147483647. The payment body is the `PaymentCreate` component (method, amount, card,
  reference) and describes which fields each method needs; the route still validates the
  raw body so that an idempotency replay is decided first.
- **Metadata.** `info.version` is the package version, the tags group the operations by
  module and `servers` has one relative entry, `{"url": "/"}`, because the web app and the
  API share one origin locally and online.
- **Examples.** The requests and the answers that matter carry named examples in the
  contract, written once in `app/openapi_examples.py` and proved by the tests, so "Try it
  out" fills a body that works.

### OpenAPI contract online

A running server serves the same document at `/api/openapi.json` and the Swagger UI at
`/api/docs`; both are public, so the contract can be read without a session. "Try it out"
calls the same-origin `/api/...` routes, so log in on the web app first and the browser
sends the session cookie. The old `/openapi.json`, `/docs` and `/redoc` paths answer 404:
the deployment sends only `/api/*` and `/__test__/*` to the API.

## PostgreSQL

Without `DATABASE_URL` the API stores everything in memory, which is the default for
tests. When it is set, the app builds one engine and uses the PostgreSQL adapters for
users, sessions, customers, orders, invoices and payments; the in-memory adapters remain
the test doubles. Creating the app and serving `GET /api/health` never opens a connection.

- `DATABASE_URL` — the runtime connection string. It must point at the provider's
  pooler. A blank value means "no database".
- `DATABASE_URL_UNPOOLED` — a direct connection string, used only by the migrations.
  It is required when `DATABASE_SCHEMA` is set, because a session-level
  `SET search_path` cannot go through a transaction-mode pooler.
- `DATABASE_SCHEMA` — run everything in an isolated schema instead of the default
  `public`. Only lowercase letters, digits and underscores are allowed.

The placeholder form is `postgresql+psycopg://user:password@host/db`; `postgres://` and
`postgresql://` are accepted too and converted to the psycopg form.

Apply the migrations and load the demo data into empty tables:

```bash
uv run python -m app.cli migrate
uv run python -m app.cli seed
```

`seed` adds the four users only when the `users` table is empty, the ten customers only
when the `customers` table is empty, the 15 products, 7 orders and the tax rate when both
`products` and `orders` are empty, and the three invoices plus four payments when
`invoices` is empty (after the orders, so the links exist); running it twice changes
nothing. Startup never seeds.

The adapters follow two rules:

- Raw SQL that names a table uses `qualified_table_name(engine, table)`, which adds the
  translated schema. `schema_translate_map` only rewrites `Table` constructs, so an
  unqualified raw statement would run against `public`.
- Unique violations are mapped by index name with `unique_violation_of`.
  `customers_email_lower_key` becomes `EmailTaken` and `invoices_order_key` becomes
  `INVOICE_ALREADY_EXISTS`; every other database error propagates and answers 500
  `INTERNAL_ERROR`.

Products, orders, order lines and the tax rate use the `products`, `orders`,
`order_lines` and `settings` tables. Order numbers come from `order_number_seq`
(`nextval` inside the insert transaction: gaps are allowed, repeats are not). Every order
mutation is one transaction and locks the order row `FOR UPDATE`, then the customer row
`FOR SHARE`, then the product rows `FOR UPDATE` in ascending product id. Confirming locks
the customer and every product, checks stock against the locked rows, decrements it,
freezes the tax rate and sets the status atomically; cancelling a confirmed order returns
the stock; both cancels store the current rate. `replace_all` moves the identity sequences
and `order_number_seq` after the highest ids and numbers.

Invoices, invoice lines, payments and idempotency keys use the `invoices`,
`invoice_lines`, `payments` and `idempotency_keys` tables. Invoice numbers come from
`invoice_number_seq`. A partial unique index
(`uq_payments_one_approved_per_invoice`, migration `0005`) lets the database reject a
second approved payment of one invoice, while declined and failed attempts stay allowed.
`orders.invoice_id` has a foreign key to `invoices` that only the
migration declares (`fk_orders_invoice_id_invoices`): together with
`invoices.order_id -> orders` it is a cycle, and `ON DELETE SET NULL` lets `replace_all`
empty one table before the other. Every invoice mutation is one transaction and locks the
order row `FOR UPDATE` first, then the invoice row with `FOR NO KEY UPDATE`, then the
customer row `FOR SHARE` when the snapshot needs it. `FOR NO KEY UPDATE` is required:
a plain `FOR UPDATE` conflicts with the `FOR KEY SHARE` lock that inserting a payment or
an idempotency key takes on the invoice, and two payments that claimed their keys before
locking would deadlock. Cancelling a confirmed order locks its invoice the same way and
voids it before returning the stock, in the order transaction.

`register_payment` claims the idempotency key before the locks: it deletes every expired
key of that invoice (24 hours with the injected clock) and inserts the placeholder row
`status_code = 0` / `response = '{}'` with `ON CONFLICT DO NOTHING`. The
second concurrent request waits on that unique row, then replays the committed response
when the fingerprint matches or raises `IDEMPOTENCY_KEY_REUSED` when it does not. If the
conflicting row disappears between the conflict and the read, the claim retries up to
three times; the third failure answers 503 `LOCK_TIMEOUT`. A
request rejected after the claim (stale version, not payable, amount mismatch) rolls the
transaction back, claim included, so it does not consume the key. An approved payment,
the invoice becoming `paid` and the order becoming `paid` commit together; a declined or
failed attempt commits the payment row and the key and answers 402 or 503.

Database errors (`DBAPIError` and the bare `psycopg.Error`) have their own handler. It logs
the exception class, the SQLSTATE, the request id and the stack frames, never the driver
message, the statement or the bound parameters (the message can carry row values). Because it
is registered for those classes, Starlette answers with it and does not re-raise, so no server
log prints the message either.

Every transaction starts with `SET LOCAL lock_timeout`, 5 seconds by default
(`LOCK_TIMEOUT_MS`, 100 to 60000). `SET LOCAL` lasts only until the transaction ends, so it
also works behind a transaction-mode pooler, where a startup option would be rejected. A
request that waits longer for a row lock gets 503 `LOCK_TIMEOUT` (SQLSTATE 55P03) instead of
hanging until the platform kills the function; the log line carries the method and path.
A deadlock (40P01) is not mapped: it stays a 500 so that a locking bug shows up in the tests.
Every login takes one advisory lock for the count and the trim of the session cap, held for
about three round trips; a test that queues 20 logins over a slow link builds its engine with
a longer `lock_timeout_ms`.

The integration tests create a random schema, run the migrations there and drop the
schema when they finish. They are skipped unless `TEST_DATABASE_URL` is set to a direct,
unpooled URL:

```bash
TEST_DATABASE_URL='postgresql+psycopg://user:password@host/db' uv run pytest tests/integration
```

## Sorting

The customer, order and invoice lists and the product catalog accept optional `sort` and
`direction` query parameters. `sort` is one of the fields of that list (`created_at`, `name`
or `email` for customers; `created_at`, `number` or `customer` for orders; `created_at`,
`number`, `customer` or `total` for invoices; `id`, `sku`, `name`, `price` or `stock` for
products). `direction` is `asc` or `desc`. It defaults to `desc` for `created_at` and to
`asc` for every other field, and applies to the default field when `sort` is absent. Ties
are broken by `id` in the same direction, and the sort runs after the filters and before
the paging. The normal and accent-insensitive text comparison is the one used by `q`. An
unknown value answers 422 `VALIDATION_ERROR` with `sort` or `direction` in `errors[]`.

```bash
curl -b /tmp/labapp-cookies 'localhost:8000/api/customers?sort=name&direction=asc'
```

## CSV export

The customer, order and invoice lists have a read-only `export` route that returns every row of the list filters as a CSV file (section 8 of `docs/SPEC.md`): `GET /api/customers/export`, `GET /api/orders/export` and `GET /api/invoices/export`. They take the same filter and sort query parameters as the list (`q`, `status`, `sort` and `direction`, plus `customer_id` for orders and `order_id` for invoices), ignore `page` and need a session; every role may export. The answer is the file itself, with `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="<resource>-<YYYYMMDD>.csv"` (the UTC date of the application clock) and `Cache-Control: no-store`. Lines end with CRLF, the first line is the header, text fields follow RFC 4180 quoting, and a text field that starts with `=`, `+`, `-`, `@`, a tab or a carriage return gets a single quote in front of it so a spreadsheet never evaluates it.

```bash
curl -b /tmp/labapp-cookies 'localhost:8000/api/customers/export?status=active' -o customers.csv
```

## Limits

Request bodies are limited to 100 KB. A declared `Content-Length` above the limit is
rejected before reading the body; a chunked body without that header is rejected as soon
as the bytes received exceed the limit.

## Request guards

The outer middleware chain is, from outside to inside: `ApiResponseHeadersMiddleware`,
`RequestIdMiddleware`, `RateLimitMiddleware`, `ControlsGuardMiddleware`,
`RequestControlsMiddleware`, `BodySizeLimitMiddleware`, then the application. The order
matters: the response headers wrap every other answer (including the 413 of the size
limit, the 429 of the rate limit, the 404 of the controls guard and an unhandled 500);
the rate limit and the test-controls guard answer before the body is read or parsed; and
the size limit answers before the application validates the body.

## Response headers

Every response to a path that starts with `/api/` or `/__test__/`, whatever its status,
carries `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`: the answers
depend on the session or on the data, so a shared cache or a browser must never keep
them. The only exceptions are the public contract `GET /api/openapi.json` and the
Swagger page `GET /api/docs`, which carry only `nosniff`; a path outside those prefixes
gets neither header. A route that sets its own `Cache-Control` keeps its value: the
middleware never overwrites it or adds a second copy, as the three CSV exports do.

Rate limits are best effort per instance: 120 requests per minute and 10 login attempts
per minute for each client IP. They are off with `TEST_MODE=1` and for a request with a
valid `X-Test-Token`; `GET /api/health` is never limited. A rejected request gets 429
`RATE_LIMITED` with `Retry-After`. The client IP is the `X-Forwarded-For` entry
`TRUSTED_PROXY_COUNT` from the right (all header lines are joined first), or the socket
peer at 0. A serverless deployment keeps one set of counters per instance; the shared,
stateful alternative comes later.

State-changing requests with an `Origin` header must match `APP_ORIGIN` or one of the
`https://` origins built from `VERCEL_URL`, `VERCEL_BRANCH_URL` and
`VERCEL_PROJECT_PRODUCTION_URL`; otherwise the answer is 403 `CSRF_ORIGIN_MISMATCH`.
Requests without `Origin` are allowed. Malformed JSON is 400 `MALFORMED_JSON`.

`/__test__` and every path under it are guarded before routing and body handling:

| `TEST_MODE` | `X-Test-Token` header | Result |
|---|---|---|
| `1` | any | Allowed. |
| `0` | equals a non-empty `TEST_TOKEN` | Allowed. |
| `0` | missing or different | 404, as if the route did not exist. |
| `0` with an empty `TEST_TOKEN` | any | 404. |

```bash
# 400 for a malformed JSON body.
curl -i -H 'Content-Type: application/json' -d '{bad' localhost:8000/api/auth/login

# 429 after the per-IP general limit is full.
for _ in $(seq 1 120); do curl -s -o /dev/null localhost:8000/api/settings; done
curl -i localhost:8000/api/settings
```

## Request controls

The application clock and the fault injection are test-only. They run only when
`TEST_MODE=1` or `TEST_TOKEN` is non-empty; otherwise `RequestControlsMiddleware` does
nothing and `ControlledClock` never reads the database.

- **Clock.** The offset is the `settings` row `clock_offset_seconds`, a decimal number of
  seconds. In PostgreSQL two concurrent advances are one atomic `UPDATE`; `advance` also
  creates the row when it is absent, and `get` returns `0.0` without one. The offset is
  added to the system clock for sessions, card expiry and stored timestamps. A request
  gets its offset from the middleware; the exempt paths and the CLI read the store.
- **Fault rules.** The `fault_rules` table stores `route` and `gateway` rules. A route
  rule matches an HTTP method (or any method) and an exact path; a gateway rule has no
  method, path or status and may carry a latency. `remaining` is the number of times the
  rule can be consumed, or `null` until it is removed. At most 50 non-exhausted rules
  exist; adding deletes exhausted rows first, and the 51st is rejected. `take` and
  `take_gateway` consume a rule with one atomic statement, so N concurrent requests get
  exactly `remaining` decisions.
- **Gateway.** `FaultyGateway` wraps `FakeGateway`. A consumed gateway rule waits its
  latency (capped at 10 seconds) and answers `unavailable` with
  `GATEWAY_UNAVAILABLE` without calling the inner gateway; with no rule it delegates.
  When the controls are disabled it delegates directly and never reads the store.
- **Route faults.** A consumed route rule waits its latency and, when it has a status,
  answers a problem document with code `INJECTED_FAULT` before the application runs.
  `/__test__/*` and `GET /api/health` are exempt.
- **Cost.** In PostgreSQL mode an enabled request loads the clock and the fault through
  one extra database transaction and one threadpool hop; disabled controls add nothing.
  In memory mode the same path is a plain call. Latency is limited to 10 seconds per
  rule and status codes to 400-599.

## Test controls

`/__test__` exposes the clock and fault stores to the owner's automated tests. The
endpoints are left out of the OpenAPI schema, need no session and are guarded twice: the
`ControlsGuardMiddleware` of task 017 and a dependency that every route repeats.

| `TEST_MODE` | `X-Test-Token` header | Result |
|---|---|---|
| `1` | any | Allowed. |
| `0` | equals a non-empty `TEST_TOKEN` | Allowed. |
| `0` | missing or different | 404, as if the route did not exist. |
| `0` with an empty `TEST_TOKEN` | any | 404. |

| Method | Path | Body | Answer |
|---|---|---|---|
| `POST` | `/__test__/reset` | none | `200 {"status": "ok"}` |
| `POST` | `/__test__/seed` | `{"dataset": "default" \| "empty"}` | `200 {"dataset": "<value>"}` |
| `GET` | `/__test__/clock` | none | `200 {"now": "<ISO 8601 UTC Z>", "offset_seconds": <number>}` |
| `POST` | `/__test__/clock` | exactly one of `{"offset_seconds": <number>}` or `{"advance_seconds": <number>}` | the same shape as `GET` |
| `POST` | `/__test__/faults` | a rule: `target`, optional `method`, `path`, `latency_ms`, `status` and `times` | `201` with the stored rule and its `id` |
| `GET` | `/__test__/faults` | none | `200` with the non-exhausted rules and their `remaining` count |
| `DELETE` | `/__test__/faults` | none | `204` |

```bash
# With TEST_MODE=1, or with the matching header when TEST_TOKEN is set.
curl -s -X POST localhost:8000/__test__/reset
curl -s -X POST -H 'X-Test-Token: secret' -H 'Content-Type: application/json' \
  -d '{"dataset": "empty"}' localhost:8000/__test__/seed
curl -s localhost:8000/__test__/clock
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"advance_seconds": 3600}' localhost:8000/__test__/clock
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"target": "route", "method": "GET", "path": "/api/customers", "status": 500, "times": 2}' \
  localhost:8000/__test__/faults
curl -s localhost:8000/__test__/faults
curl -s -X DELETE localhost:8000/__test__/faults
```

The bodies use `extra="forbid"` and strict types, so an unknown field, a string where a
number belongs, a boolean, a non-finite number or a value outside its range is a 422
`VALIDATION_ERROR` on the offending field. The clock offset and a cumulative advance must
stay within plus or minus ten years; the advance is a single `UPDATE ... WHERE
abs(value::float8 + :delta) <= :max`, so a refused advance changes nothing. A fault rule
is validated with the same function as the store: a route rule needs a path that starts
with `/` and a latency above 0 or a status; a gateway rule takes no method, path or
status. `times` is 1 to 1000 or `null`, and the 51st non-exhausted rule is a 422.

What is stored where:

- In PostgreSQL the offset is the `settings` row `clock_offset_seconds` and the rules are
  rows of `fault_rules`; every instance reads them per request. Without `DATABASE_URL`
  the same API runs against the in-memory `OffsetClock` and dictionary, which is the test
  double. Creating the app and `GET /api/health` still open no connection.
- A reset runs the five `replace_all` calls in this order, which respects the foreign
  keys: (1) invoices empty, (2) orders and products empty, (3) customers seed, (4) orders
  and products seed, (5) invoices and payments seed; then the four users are upserted, the
  tax rate is restored to `DEFAULT_TAX_RATE` (quantized), the clock row is set to `'0'`
  and every fault rule is deleted. PostgreSQL does all of it in one transaction after
  `pg_advisory_xact_lock` (a key different from the session and fault-rule locks), so no
  request sees a half-restored database. `TRUNCATE` and raw `DELETE` are never used.
- Every `replace_all` accepts `defer_sequences`. The reset collects the sequence
  restarts there and runs them as the last statements of the transaction, because
  `setval` is not undone by a rollback: a reset that fails in a data step leaves the
  sequences as they were instead of at 1.
- A reset keeps the sessions: the four users keep their ids (upsert and delete-missing,
  never touching `sessions`), so a stored cookie keeps working. It restores the data, the
  number sequences (the next order is `PED-0008`, the next invoice `FAC-0004`, the next
  payment id 5, the next customer id 11), the tax rate, the clock and the faults, and it
  clears the rate-limit counters of the instance that serves it. Those counters are
  per-instance and in memory; moving them to the database is not planned (the limits are best effort).
- `seed {"dataset": "default"}` loads the same rows without touching the clock, the faults
  or the rate-limit counters. `seed {"dataset": "empty"}` leaves the four users and the
  settings, empties every other table, restarts the sequences, restores the tax rate,
  sets the clock row to `'0'` and deletes the fault rules.
- A reset is meant for a quiet system. A request that runs during it may fail with 409 or
  503 `LOCK_TIMEOUT`, and a payment or an invoice that commits in the middle can make the
  reset fail with a foreign key error; `/__test__/reset` answers 409 and the caller retries
  once. A gateway fault with latency holds the invoice lock for up to 10 seconds, so a
  reset that needs that invoice can answer 409 or 503.

For local use the CLI has the same reset with three refusals:

```bash
TEST_MODE=1 uv run python -m app.cli reset --yes
TEST_MODE=1 uv run python -m app.cli reset --yes --allow-public
```

It refuses unless `TEST_MODE=1` and `--yes` are both given, refuses a host that is not
`localhost`, `127.0.0.1` or `::1` unless `--allow-remote` is also given, prints the host,
the database name and the schema it will touch, and refuses when `DATABASE_SCHEMA` is
unset (the public schema would be wiped) unless `--allow-public` is also given. It exits
with code 2 when it refuses.

## Test

```bash
uv run pytest -q
```

## Coverage

The suite measures branch coverage with `pytest-cov`:

```bash
uv run pytest --cov=app --cov-report=term-missing:skip-covered
```

The configuration lives in `pyproject.toml` (`[tool.coverage.run]` and
`[tool.coverage.report]`). `term-missing` prints the files below 100 percent and the lines
and branches they miss; `skip-covered` hides the files that are complete. The total of the
last line is the number the floor uses.

Without `TEST_DATABASE_URL` the PostgreSQL adapters are skipped, so that total is the
unit-only one. The floor is `fail_under = 85`: the unit-only total rounded down by two
points, low enough to hold on any machine that runs the unit tests. CI runs the same
command with the integration tests against a throwaway PostgreSQL, so its total is higher;
the report prints it, and only the floor gates the run. A change must not lower the floor:
when a new module or branch lowers the total, add tests in the same change. Raise the floor
only when the new total keeps the same two-point margin.

## Documents and code

`tests/docs/` keeps `docs/SEED.md` and the error, label, permission and transition
tables of `docs/SPEC.md` in agreement with the code. The tests read the Markdown
files and call the same pure functions the application uses; they do not start a
server or a database.

When one fails, change the document and the code in the same commit. Do not edit
the test to accept the difference. `tests/docs/test_field_errors.py` also checks
that every message of the field-level table appears in `app/` as a literal or an
f-string template, so a message that lives only in the document fails too.

## Lint and format

```bash
uv run ruff check .
uv run ruff format --check .
```

`uv run ruff format .` applies the formatting.

## Layout

```
backend/
  app/
    config.py      Settings read from environment variables
    cli.py         the database and OpenAPI commands
    errors.py      ApiError, problem+json rendering and exception handlers
    infra/db.py    engine, metadata and URL helpers
    main.py        create_app() and the application instance
    middleware.py  request id and request body size limit
  migrations/      Alembic configuration and revisions
  tests/           pytest suite
  pyproject.toml   dependencies, ruff and pytest configuration
```

## Domain

`app/domain/` contains the pure business rules that later HTTP modules call. It performs no
I/O and raises `ApiError` for rule violations.

- `money.py` — money rounding, order totals and tax-rate validation.
- `numbering.py` — `PED-` and `FAC-` number formatting.
- `labels.py` — Spanish labels for states, payment methods and roles.
- `permissions.py` — the role and action matrix from SPEC section 2.
- `orders.py` — order transitions, draft line validation and stock checks.
- `payments.py` — Luhn and card validation, transfer references and the fake gateway.

Tests mirror these modules in `tests/domain/`.

## Security

`app/security/` holds the pure guards and helpers used by the authentication and payment
modules. They take clocks, secrets and configuration as arguments and perform no I/O.

- `passwords.py` — Argon2id hashing, verification and rehash detection.
- `origin.py` — the CSRF origin check and the `Secure` cookie decision.
- `client_ip.py` — client IP from `X-Forwarded-For` with trusted proxy counts.
- `ratelimit.py` — the in-memory sliding-window limiter and the 429 error.
- `controls_guard.py` — the test-controls and rate-limiting guard table.
- `idempotency.py` — key validation, canonical fingerprints and card redaction.

Tests mirror these modules in `tests/security/`.

## Authentication

`app/modules/auth/` implements the login, logout and current-user endpoints under
`/api/auth`.

- `routes.py` — `/login`, `/logout` and `/me`. Routes and dependencies are plain `def`, so
  FastAPI runs them in its thread pool; an Argon2 verification never blocks the event loop.
- `service.py` — credential checks, opaque session tokens stored only as SHA-256 digests,
  the 8-hour sliding idle window and the 32-hour purge on login.
- `ports.py` — `UserRepository` and `SessionStore` protocols.
- `adapters/memory.py` — in-memory adapters (at most 10,000 sessions) used until PostgreSQL
  is available.
- `seed.py` — the four demo users and the process-wide cached Argon2 hashes.
- `dependencies.py` — the current-user and action-permission dependencies.
- `app/infra/clock.py` — the application clock; session expiry uses it, so tests can advance
  time without sleeping.

Run the API and log in with any seeded email (`admin@labapp.test`, `sales@labapp.test`,
`finance@labapp.test` or `readonly@labapp.test`) and the demo password
`Demo-LabApp-2026!`. A PostgreSQL adapter later only implements the two ports; the service,
routes and tests stay unchanged.

Two Argon2 verifications run at a time (about 64 MiB each), with room for two more waiting.
Everything beyond that answers 503 `SERVICE_BUSY` immediately instead of queueing behind the
thread pool; the per-IP login limit from task 008 is the other protection. The session cap can
still be flooded by design because the demo password is public: at roughly 54 logins per
second the oldest sessions are evicted, so the per-IP limit is what makes that impractical.

## Customers

`app/modules/customers/` implements the customer API under `/api/customers`.

- `routes.py` — the seven endpoints, all plain `def`, so FastAPI runs every one in its
  thread pool. Reads need a session; writes need the customer-management permission.
- `service.py` — validation, paging, literal search parameters and the translation of the
  repository exceptions to problem responses.
- `validation.py` — trimming, normalization and the field limits of SPEC section 4.
- `search.py` — `normalize_for_search`, the single definition of case- and accent-insensitive
  matching.
- `ports.py` — `CustomerRepository` with its three exceptions; `adapters/memory.py` is the
  in-memory implementation.
- `seed.py` — the ten documented customers.

The port is written for a PostgreSQL adapter. `add` must be atomic and enforce the unique
lowercase email with a unique index; `update` and `set_status` must lock the row with
`SELECT ... FOR UPDATE` before checking existence, version and email, in that order. `list`
orders by `created_at` then `id` descending, returns the total separately from the page, and
treats `q` as literal text: escape `%`, `_` and `\`. Search must use the normalized forms of
name and email stored at write time, never database collations or `unaccent`.
`replace_all` replaces the content and restarts the next id at the highest existing id plus
one.

```bash
# Log in as sales and keep the session cookie.
curl -i -c /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -d '{"email":"sales@labapp.test","password":"Demo-LabApp-2026!"}' \
  localhost:8000/api/auth/login

# List, optionally with a literal, accent-insensitive query.
curl -i -b /tmp/labapp-cookies 'localhost:8000/api/customers?q=cafeteria'

# Create a customer; the answer carries Location and ETag.
curl -i -b /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -d '{"name":"Nuevo Cliente","email":"nuevo@example.test"}' \
  localhost:8000/api/customers

# Patch it with the version returned by the previous call.
curl -i -b /tmp/labapp-cookies -X PATCH \
  -H 'Content-Type: application/json' \
  -d '{"name":"Nuevo Cliente S.A.","version":1}' \
  localhost:8000/api/customers/11
```

### Customer import

`POST /api/customers/import` creates the customers of a CSV file from one
`multipart/form-data` part named `file`, all or nothing. The file is UTF-8 (an optional byte
order mark is ignored), its name ends in `.csv` (any case), and it uses a comma separator
with RFC 4180 quoting and CRLF or LF line ends. The header names `name`, `email`, `phone`,
`tax_id` and `address` at most once, and `name` and `email` are required. The following
non-blank lines are 1 to 200 data rows; each one follows the creation rules, an empty
optional value is stored as `null`, and the email is trimmed and lowercased. While any row
is invalid the answer is 422 `VALIDATION_ERROR` with every error in file order (at most 100
entries, `rows[N]` names the physical line), and nothing is created. Otherwise the answer is
201 `{created, items}` and an email taken between the validation and the insert is 409
`CUSTOMER_EMAIL_TAKEN`. The whole request shares the 100 KB body limit. A body that is
not valid `multipart/form-data` (a wrong boundary) is the framework's own 400
`BAD_REQUEST` with the generic detail.

```bash
curl -i -b /tmp/labapp-cookies \
  -F 'file=@customers.csv;type=text/csv' \
  localhost:8000/api/customers/import
```

## Orders

`app/modules/orders/` implements the read-only product catalog, the tax-rate setting and
the order API under `/api/products`, `/api/settings` and `/api/orders`.

- `routes.py` — the product, settings and order endpoints, all plain `def`. Reads need a
  session; draft edits need the draft-edit permission; confirm, cancel and ship need the
  transition permission; the tax rate is Admin only.
- `service.py` — body and query validation, the port exception translation, and the view
  building: totals from `app.domain.money`, the current rate for a draft and the frozen
  rate for every other state.
- `ports.py` — `OrderStore` with its exceptions. Every method states the rules a
  PostgreSQL adapter must honour.
- `adapters/memory.py` — the thread-safe in-memory store used as a test double and
  development aid.
- `models.py`, `schemas.py`, `seed.py` — the domain records, the JSON shapes (money as
  strings with two decimals) and the 15 products plus the 7 orders of `docs/SEED.md`.

A PostgreSQL adapter must guarantee the same behaviour as the in-memory one:

- Every order mutation locks the order row first (`SELECT ... FOR UPDATE`), then the
  customer row (`FOR SHARE`), then the affected product rows in ascending id order. The
  version and the state are checked after locking.
- Confirming is all-or-nothing: check every shortage, then decrement every line, freeze
  the current tax rate and the totals and set the status in one transaction. Cancelling a
  confirmed order returns every line's stock; both cancels store the current tax rate.
- The next `PED` number is assigned inside the same transaction as the insert and
  continues after the highest existing number. Line ids use one sequence for all orders.
- Search uses the normalized forms of the order number and the customer's current name
  stored at write time, and treats `%`, `_` and `\` as literal text.

```bash
# Log in as sales and keep the session cookie (if not done already).
curl -i -c /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -d '{"email":"sales@labapp.test","password":"Demo-LabApp-2026!"}' \
  localhost:8000/api/auth/login

# Read the catalog and the current tax rate (every role).
curl -b /tmp/labapp-cookies localhost:8000/api/products
curl -b /tmp/labapp-cookies localhost:8000/api/settings

# Create a draft for customer 1. The answer carries Location and ETag: "1".
curl -i -b /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":1}' \
  localhost:8000/api/orders

# Add two units of product 1; the answer carries ETag: "2".
curl -i -b /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -d '{"product_id":1,"quantity":2,"version":1}' \
  localhost:8000/api/orders/8/lines

# Product 1 stock before confirming.
curl -b /tmp/labapp-cookies localhost:8000/api/products

# Confirm the draft; the answer carries ETag: "3".
curl -i -b /tmp/labapp-cookies -X POST \
  -H 'If-Match: "2"' \
  localhost:8000/api/orders/8/confirm

# Product 1 stock after confirming (two units fewer).
curl -b /tmp/labapp-cookies localhost:8000/api/products

# Read the order.
curl -i -b /tmp/labapp-cookies localhost:8000/api/orders/8

# Cancel it; the stock comes back and the answer carries ETag: "4".
curl -i -b /tmp/labapp-cookies -X POST \
  -H 'If-Match: "3"' \
  localhost:8000/api/orders/8/cancel
```

## Invoices and payments

`app/modules/invoices/` implements the invoice and payment API under
`/api/invoices` and `POST /api/orders/{id}/invoice`.

- `routes.py` — the four endpoints, all plain `def`. Reads need a session; issuing
  an invoice and registering a payment need the create-invoices and
  register-payments permissions (Admin and Finance).
- `service.py` — list and body validation, the early idempotency replay, the
  translation of the port exceptions and the rendering of the stored responses.
  Money is a string with two decimals; `PaymentOutcome` carries the rendered
  `StoredResponse` and whether it was replayed.
- `ports.py` — `InvoiceStore` with its exceptions. Every method states the rules a
  PostgreSQL adapter must honour.
- `adapters/memory.py` — the thread-safe in-memory store used as a test double and
  development aid.
- `rules.py` — every invoice and payment business error (status, code and Spanish
  message) in one place; the in-memory adapter and the future SQL adapter call it.
- `gateway.py`, `mail.py` — the fake gateway and the mailer that only writes the
  invoice number to the log.
- `models.py`, `schemas.py`, `seed.py` — the records, the JSON shapes and the three
  invoices plus four payments of `docs/SEED.md`.

The in-memory order store and invoice store share one `RLock`. The gateway is
called while that lock is held, so a gateway with injected latency also stalls
unrelated reads and writes for the same process. The seed links the three seeded
invoices with `link_invoices`, not `attach_invoice`, so the seeded orders keep
`version` 1 and `updated_at == created_at`.

A PostgreSQL adapter must guarantee the same behaviour as the in-memory one:

- Every invoice mutation locks the order row first (`SELECT ... FOR UPDATE`), then
  the invoice row, then the customer row (`FOR SHARE`) when it is needed. The
  version and the state are checked after locking.
- `issue_invoice` checks the version, `INVOICE_ALREADY_EXISTS`,
  `ORDER_NOT_INVOICEABLE` and `CUSTOMER_TAX_ID_REQUIRED`, takes the next `FAC`
  number and links the order in one transaction.
- The idempotency key is claimed with a unique `(invoice_id, key)` row before the
  locks and looked up again after them, so two concurrent requests with one key
  make one payment and the second replays the first response. Keys live 24 hours
  and only an approved, declined or failed payment consumes one.
- An approved payment, the invoice becoming `paid` and the order becoming `paid`
  are one transaction. A declined or failed attempt is stored and answered with a
  402 or 503 problem that carries `payment_id` and `reason`.
- Only the last four digits of a card are ever stored; the number and the CVC
  never reach the store or a response.

This module runs in memory only when `DATABASE_URL` is unset; when it is set,
`PostgresInvoiceStore` runs instead.

```bash
# Log in as finance and keep the session cookie.
curl -i -c /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -d '{"email":"finance@labapp.test","password":"Demo-LabApp-2026!"}' \
  localhost:8000/api/auth/login

# Issue the invoice of order 2 (PED-0002). The answer carries Location and ETag: "1".
curl -i -b /tmp/labapp-cookies -X POST \
  localhost:8000/api/orders/2/invoice

# Read it and the list.
curl -i -b /tmp/labapp-cookies localhost:8000/api/invoices/4
curl -b /tmp/labapp-cookies 'localhost:8000/api/invoices?status=issued'

# Pay it with the approved test card. The answer carries ETag: "2".
curl -i -b /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: pay-0001' \
  -d '{"method":"card","amount":"121.00","card":{"number":"4242 4242 4242 4242","expiry":"12/30","cvc":"123"}}' \
  localhost:8000/api/invoices/4/payments

# Repeat the same request: same status and body, Idempotency-Replayed: true.
curl -i -b /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: pay-0001' \
  -d '{"method":"card","amount":"121.00","card":{"number":"4242 4242 4242 4242","expiry":"12/30","cvc":"123"}}' \
  localhost:8000/api/invoices/4/payments

# The order is now paid.
curl -b /tmp/labapp-cookies localhost:8000/api/orders/2

# FAC-0001 is declined by the test card ending in 0002: 402 with payment_id and reason.
curl -i -b /tmp/labapp-cookies \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: pay-0002' \
  -d '{"method":"card","amount":"327.80","card":{"number":"4000 0000 0000 0002","expiry":"12/30","cvc":"123"}}' \
  localhost:8000/api/invoices/1/payments
```
