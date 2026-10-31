# Task 001: backend skeleton

Assignee: Worker 1. Branch: `w1/backend-skeleton`. Reviewer: Supervisor.

## Goal

Create the minimal FastAPI project that every later backend module builds on. It has no database, no login and no business logic yet. It must already behave the way [SPEC.md](../SPEC.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) require for the cross-cutting parts.

## Read first

- `docs/SPEC.md`: section 7 (errors, `problem+json`, common codes) and section 8 (request tracing).
- `docs/ARCHITECTURE.md`: sections "Sessions and security" and "Test-only controls" (only the startup guard matters here).
- `.env.example`: the environment variable names to read.

## Scope

You may create and edit files only under `backend/`. Do not touch the repository root, `docs/`, `frontend/` or any workflow.

## Requirements

1. **Project.** A `uv` project in `backend/` (`pyproject.toml` and `uv.lock`), Python `>=3.13`. Runtime dependencies: `fastapi`, `uvicorn[standard]`, `pydantic-settings`. Dev dependencies: `pytest`, `httpx`, `ruff`.
2. **Layout.** `backend/app/main.py` exposes `create_app()` and `app = create_app()`. Settings live in `backend/app/config.py`; error handling in `backend/app/errors.py`. Tests live in `backend/tests/`.
3. **Settings.** A `Settings` class (pydantic-settings) with `database_url`, `session_secret`, `test_mode` (bool), `test_token`, `default_tax_rate` (`Decimal`), reading the variable names from `.env.example` (`DATABASE_URL`, `SESSION_SECRET`, `TEST_MODE`, `TEST_TOKEN`, `DEFAULT_TAX_RATE`).
4. **Startup guard.** `create_app()` must refuse to start (raise an error with a clear message) when `session_secret` is empty or equals `change-me`, unless `test_mode` is true.
5. **Health.** `GET /api/health` returns 200 and `{"status": "ok"}`, with no authentication.
6. **Request id.** Every response carries an `X-Request-Id` header. If the request sends one, echo it; otherwise generate a UUID4.
7. **Errors.** All errors are `application/problem+json` with `type`, `title`, `status`, `code` and `detail`, using the codes and Spanish messages from SPEC section 7:
   - Unknown route: 404 `NOT_FOUND`.
   - Request body above 100 KB (check `Content-Length`): 413 `PAYLOAD_TOO_LARGE`.
   - Request validation failure: 422 `VALIDATION_ERROR` with `errors[]` entries of `{field, code, message}`. A missing field is `REQUIRED`; any other pydantic failure is `INVALID_FORMAT`. Use the Spanish messages from the field-level table.
   - Any unhandled exception: 500 `INTERNAL_ERROR`, without leaking internals.
   - Provide an `ApiError` exception (status, code, detail, optional `errors` and extra members) that later modules will raise; it must render the same way.
   - The error responses also carry `X-Request-Id`.
8. **Tooling.** `ruff` configured in `pyproject.toml` (line length 100; rules E, F, I, B, UP). The code must pass `ruff check` and `ruff format --check`.
9. **Tests.** pytest tests that cover: health, request id echo and generation, the 404 body, the 413 body, the 422 body (register a small route inside the test to trigger it), the 500 body, `ApiError` rendering, and the startup guard (both the refusal and the `test_mode` exception).
10. **Docs.** `backend/README.md` with the commands to install, run and test.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
SESSION_SECRET=dev-secret uv run uvicorn app.main:app --port 8000   # then: curl -i localhost:8000/api/health
```

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits): project init, settings, startup guard, request id, health, each error handler, tests, readme. Messages follow Conventional Commits, in English, for example `feat(backend): add request id middleware`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.

## Errata (added after the review)

- The startup guard and the health endpoint are described under "Operational rules" in `docs/ARCHITECTURE.md`, not under "Sessions and security" or "Test-only controls".
- Use `httpx2` instead of `httpx` as the dev dependency (Starlette reports `httpx` as deprecated) and make the test run finish with no warnings.
- `Settings` defaults: `database_url` defaults to the URL in `.env.example`, `test_token` to an empty string and `default_tax_rate` to 10. `session_secret` has no safe default and is checked by the guard. Tests set `SESSION_SECRET` in `conftest.py` before importing the module-level `app`.
- The last acceptance command starts a server and does not exit: stop it with Ctrl+C after the `curl` check.
- The request body limit is 100 KB, that is 102,400 bytes, and only the `Content-Length` header is inspected.
- The problem document uses `type` set to `about:blank` and the English HTTP phrase as `title`. Statuses outside the catalog render a generic Spanish message (SPEC section 7). `field` paths drop the framework prefix (`body`) and use the `lines[0].quantity` notation.
- An incoming `X-Request-Id` is accepted only if it matches `^[A-Za-z0-9._-]{1,64}$`.
- Environment files: `backend/.env` wins over the repository-root `.env`, and real environment variables win over both.
