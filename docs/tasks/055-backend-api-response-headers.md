# Task 055: security headers on every API response

Assignee: Worker 1. Branch: `w1/api-headers`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

The web app sends security headers (task 045) but the API answers carry only what each route set by itself: `Cache-Control: no-store` appears on login, logout, `me` and the CSV exports, and nowhere else, and no response says `X-Content-Type-Options: nosniff`. The answers of the API depend on the session and on the data; a shared cache or a browser must not keep them. Add one rule for every API response, exactly as the new bullet **API response headers** in `docs/SPEC.md` section 8 says, including the error answers that other middleware produces before a route runs.

## Read first

`docs/SPEC.md` section 8 (the bullet **API response headers**), `backend/app/middleware.py` (the existing pure ASGI middleware: request id, body size limit), `backend/app/main.py` (the order in which the middleware are added: `add_middleware` wraps, so the last one added is the outermost), `backend/app/guards/` (the rate limit and the `/__test__` guard that answer before a route), `backend/app/errors.py` (`problem_response`).

## Scope

You may edit under `backend/`: `app/middleware.py` (or a new small module next to it), `app/main.py` (to register it), the tests, `backend/README.md` (one short paragraph). Do not edit `docs/SPEC.md`, the frontend, `tools/` or `tests/`. No new dependency. Do not change a status code, a message or any other header.

## Requirements

1. **One pure ASGI middleware** (`http` scopes only, like the others; do not use `BaseHTTPMiddleware`, which buffers and breaks streaming) that adds the headers to the `http.response.start` message: `X-Content-Type-Options: nosniff` and `Cache-Control: no-store` for every path that starts with `/api/` or `/__test__/`, except that `GET /api/openapi.json` and `GET /api/docs` get only `nosniff`. The decision uses the request path as the application sees it (read how the other middleware read it). A response that already has a `Cache-Control` keeps its own value (do not overwrite, do not duplicate the header). Paths outside those two prefixes get nothing.
2. **It must be the outermost middleware**, so that the answers produced by the others (the 413 of the body size limit, the 429 of the rate limit, the 404 of the controls guard, the 5xx of an unhandled error) carry the headers too. Say in a comment in `main.py` why the order matters, and prove it with the tests below.
3. **Tests.** For each of these requests, assert both headers (or only `nosniff` where the SPEC says so) and that `Cache-Control` appears exactly once: a successful read (`GET /api/customers` with a session), `GET /api/health`, an unauthenticated `GET /api/customers` (401), an unknown `GET /api/nope` (404), a validation error (422), a body above the limit (413), a rate-limited login (429; read how the existing rate-limit tests trigger it), `POST /__test__/reset` without the token (404) and with it (200), a CSV export (200, its own `no-store` is kept and not duplicated), an unhandled error (use the existing test seam that makes a route raise, if there is one; if not, say so in the report), `GET /api/openapi.json` and `GET /api/docs` (only `nosniff`), a path outside the prefixes such as `GET /robots.txt` (none of the two headers). A test that the middleware is the outermost one is covered by the 413 and 429 cases.
4. **Contract.** The contract documents nothing new (headers on every response are not repeated per route); do not touch `docs/openapi.json` unless a test of yours shows it must change.
5. **README.** One paragraph in `backend/README.md`: which paths, which headers, and that a route's own `Cache-Control` is kept.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass (the coverage floor holds). The supervisor also looks at the headers of each case with `curl -i` against a live server.

## Rules for this task

- Commit as you go, in small real steps (about 4 to 6 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the middleware order of `main.py` after your change, and any deviation or open question.
