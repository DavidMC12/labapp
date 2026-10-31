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
- `test_guard.py` — the test-controls and rate-limiting guard table.
- `idempotency.py` — key validation, canonical fingerprints and card redaction.

Tests mirror these modules in `tests/security/`.
