# LabApp backend

Minimal FastAPI skeleton for LabApp. It provides the health endpoint, request tracing and
RFC 9457 problem responses that every later backend module builds on. There is no database,
authentication or business logic yet.

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

Check the API:

```bash
curl -i localhost:8000/api/health
```

Every response carries an `X-Request-Id` header. Send your own `X-Request-Id` to have it
echoed; values must match `^[A-Za-z0-9._-]{1,64}$`, otherwise a new UUID4 is generated.

## PostgreSQL

Without `DATABASE_URL` the API stores everything in memory, which is the default for
tests. When it is set, the app builds one engine and uses the PostgreSQL adapters for
users, sessions, customers and orders; the in-memory adapters remain the test doubles.
Creating the app and serving `GET /api/health` never opens a connection.

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
when the `customers` table is empty, and the 15 products, 7 orders and the tax rate when
both `products` and `orders` are empty; running it twice changes nothing. Startup never
seeds.

The adapters follow two rules:

- Raw SQL that names a table uses `qualified_table_name(engine, table)`, which adds the
  translated schema. `schema_translate_map` only rewrites `Table` constructs, so an
  unqualified raw statement would run against `public`.
- Unique violations are mapped by index name with `unique_violation_of`. Only
  `customers_email_lower_key` becomes `EmailTaken`; every other database error
  propagates and answers 500 `INTERNAL_ERROR`.

Products, orders, order lines and the tax rate use the `products`, `orders`,
`order_lines` and `settings` tables. Order numbers come from `order_number_seq`
(`nextval` inside the insert transaction: gaps are allowed, repeats are not). Every order
mutation is one transaction and locks the order row `FOR UPDATE`, then the customer row
`FOR SHARE`, then the product rows `FOR UPDATE` in ascending product id. Confirming locks
the customer and every product, checks stock against the locked rows, decrements it,
freezes the tax rate and sets the status atomically; cancelling a confirmed order returns
the stock; both cancels store the current rate. `replace_all` moves the identity sequences
and `order_number_seq` after the highest ids and numbers.

For database errors the unexpected-error handler logs only the exception class, the
SQLSTATE and the request id: never the message, the statement or the bound parameters.

The integration tests create a random schema, run the migrations there and drop the
schema when they finish. They are skipped unless `TEST_DATABASE_URL` is set to a direct,
unpooled URL:

```bash
TEST_DATABASE_URL='postgresql+psycopg://user:password@host/db' uv run pytest tests/integration
```

## Limits

Request bodies are limited to 100 KB. A declared `Content-Length` above the limit is
rejected before reading the body; a chunked body without that header is rejected as soon
as the bytes received exceed the limit.

## Request guards

The outer middleware chain is, from outside to inside: `RequestIdMiddleware`,
`RateLimitMiddleware`, `ControlsGuardMiddleware`, `BodySizeLimitMiddleware`, then the
application. The order matters: the rate limit and the test-controls guard answer before
the body is read or parsed, and the size limit answers before the application validates
the body.

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

## Test

```bash
uv run pytest -q
```

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
    cli.py         the migrate and seed commands
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

- `routes.py` — the six endpoints, all plain `def`. Reads need a session; writes need the
  customer-management permission.
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
