# Task 017: backend stateless request guards

Assignee: Worker 1. Branch: `w1/request-guards`. Reviewer: Supervisor, with a second-agent review because this is security code.

**Base.** Branch from `main` after tasks 010, 012 and 015 are merged. It uses `app/security/` (already merged and tested), `app/middleware.py`, `app/errors.py`, `app/main.py` and `app/modules/auth/container.py`.

## Goal

Wire into the running application the guards that need no stored state: the origin check on state-changing requests, the mapping of malformed JSON, a real body size limit, the rate limits (in memory, best effort: on a serverless deployment each instance has its own counters, and a stateful alternative comes later), and the reusable guard dependency of the test-only controls. The test controls themselves (reset, seed, clock, faults) come in a later task because their state must live in the database.

## Read first

- `docs/SPEC.md`: section 3 (origin check, rate limits, client IP, test token), section 7 (the error catalog and the order of checks: rate limit and body size, then malformed JSON, then session and origin, then permission, then validation).
- `docs/ARCHITECTURE.md`: "Test-only controls" (the guard table).
- `backend/app/security/` (`origin.py`, `client_ip.py`, `ratelimit.py`, `controls_guard.py`) and their tests: the building blocks you wire, do not rewrite them. `backend/app/middleware.py`, `backend/app/errors.py`, `backend/app/main.py`, `backend/app/modules/auth/container.py`.

## Scope

You may create files under `backend/app/http/` and `backend/tests/http/`; edit `backend/app/main.py`, `backend/app/middleware.py`, `backend/app/errors.py` and `backend/app/modules/auth/container.py` only to wire or extend what this task needs; and add a "Request guards" section to `backend/README.md`. Every new folder needs an `__init__.py`. Do not change anything else. No new dependencies. Name no module `test_*.py` unless it is a test.

## Requirements

1. **Rate limits** (`app/http/ratelimit_middleware.py`, a pure ASGI middleware, not `BaseHTTPMiddleware`). It applies only to paths under `/api/` and never to `GET /api/health`. It computes the client IP with `client_ip(peer, x-forwarded-for, settings.trusted_proxy_count)` (the peer is `scope["client"][0]`, or `"unknown"` if absent). Limits are enabled only when `rate_limiting_enabled(settings.test_mode, settings.test_token, x-test-token header)` is true. When enabled, every `/api/` request is counted against the general limiter (`GENERAL_LIMIT`), and `POST /api/auth/login` is also counted against the login limiter (`LOGIN_LIMIT`); a rejected request gets the 429 `RATE_LIMITED` problem document of `rate_limited_error` and a `Retry-After` header with the `retry_after` seconds (the extra member stays in the body too). Both limiters use the real monotonic clock (`time.monotonic`, injectable for tests), not the application clock. The limiters live in the container so tests can reach them, and a bounded number of tracked IPs keeps memory from growing without limit (reuse what `ratelimit.py` offers; if it has no bound, add one with a test).
2. **Origin check.** A global FastAPI dependency (registered with `FastAPI(dependencies=[...])`, plain `def`) that calls `check_origin(request.method, request.headers.get("origin"), settings.app_origin)` for every `/api/` route. Because it is a dependency it runs after the body is parsed and before the route's own checks, which is the order of SPEC section 7. It does not apply to `/__test__` routes (which do not exist yet; the dependency must skip any path outside `/api/`).
3. **Malformed JSON.** In `app/errors.py`, a `RequestValidationError` that contains an error of type `json_invalid` becomes a 400 `MALFORMED_JSON` problem with the message "El cuerpo de la solicitud no es un JSON válido." (SPEC section 7); every other validation error keeps its current 422 behavior. Today a broken body gives a 422 whose error field is `[1]`; the tests must pin the new behavior.
4. **Body size.** `BodySizeLimitMiddleware` only checks the declared `Content-Length`; a chunked request without it is not limited. Make it enforce the 100 KB limit while the body streams (count the bytes received through `receive`, and answer the 413 problem document as soon as the limit is exceeded, without passing the rest on). Keep the declared-length fast path. Write the failing test first (a streamed body without `Content-Length` of 100 KB plus one byte).
5. **Test-controls guard** (`app/http/controls.py`): a plain `def` FastAPI dependency `require_test_controls(request)` that calls `controls_allowed(settings.test_mode, settings.test_token, x-test-token header)` and, when it is false, raises the 404 `NOT_FOUND` problem so the routes look absent. The later task attaches it to the `/__test__` router; here it is covered by tests that mount a tiny router of their own.
6. **Middleware order.** From outside to inside: request id, body size, rate limit, the application. State this order in the README and cover it with a test (a request over the size limit that is also rate limited answers 413 first; a rate-limited request that also carries malformed JSON answers 429 first).
7. **Container.** Extend the container with `limiters` (general and login) and a `reset_limiters()` method that clears both; do not reach into private attributes from outside.
8. **Tests** (`backend/tests/http/`), deterministic: inject the monotonic function, never sleep for real. Cover:
   - Rate limits: the general limit at the boundary (the 120th request in a window allowed, the 121st rejected with `Retry-After`), the login limit (10th allowed, 11th rejected), health never limited, limits off with `TEST_MODE=1` and with a valid token, still on with a wrong token, separate buckets per client IP, the client IP taken from `X-Forwarded-For` with `TRUSTED_PROXY_COUNT` 0, 1 and 2 (and a spoofed leftmost entry ignored), the window moving with the monotonic clock only, and the bound on tracked IPs.
   - Origin: a different origin is 403 `CSRF_ORIGIN_MISMATCH` on POST, PUT, PATCH and DELETE; a matching origin and a missing origin pass; GET is never checked; the order against malformed JSON (a malformed body with a wrong origin answers 400 first) and against the session check (wrong origin and no session answers 403, as SPEC section 7 says).
   - Malformed JSON: 400 `MALFORMED_JSON` for broken JSON on a customers route and on the login route; valid JSON with a missing field is still 422.
   - Body size: declared and streamed, at the limit (allowed) and one byte above (413).
   - Guard: the four rows of the guard table (`TEST_MODE` 0 or 1, token missing, wrong, right, and an empty configured token never matching), with the token compared exactly.
9. **Docs.** The README section: the middleware order, the guard table, the best-effort note for the rate limits on serverless, and an example `curl` for the 429 and the 400.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

and, manually, with the server started as in the backend README, show with `curl -i` the 400 for `-d '{bad'` on the login route, the 403 for `-H 'Origin: http://evil.test'` on a POST, and the 413 for a 200 KB body sent with chunked encoding.

## Rules for this task

- Commit as you go, in small real steps (about 14 to 20 commits): the limiter bound, the rate limit middleware, the origin dependency, the JSON mapping, the streaming size limit, the controls guard, the container methods, then tests next to each piece and the README. Conventional Commits, in English, for example `feat(backend): add the rate limit middleware`.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
