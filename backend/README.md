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
`TEST_MODE=1`. Copy `../.env.example` to `backend/.env` to configure all variables locally;
pydantic-settings reads that file.

Check the API:

```bash
curl -i localhost:8000/api/health
```

Every response carries an `X-Request-Id` header. Send your own `X-Request-Id` to have it echoed.

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
