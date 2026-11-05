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

## Limits

The 100 KB request body limit only inspects the `Content-Length` header; chunked requests
without that header are not limited yet.

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
    errors.py      ApiError, problem+json rendering and exception handlers
    main.py        create_app() and the application instance
    middleware.py  request id and request body size limit
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

Two Argon2 verifications run at a time (about 64 MiB each). A login that cannot get a slot
within two seconds answers 503 `SERVICE_BUSY`; the per-IP login limit from task 008 is the
other protection. The session cap can still be flooded by design because the demo password is
public: at roughly 54 logins per second the oldest sessions are evicted, so the per-IP limit is
what makes that impractical.
