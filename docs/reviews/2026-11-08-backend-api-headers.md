# Review: security headers on every API response (task 055, 2026-11-08)

- **Branch:** `w1/api-headers`, by Worker 1 (4 commits).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it does:** one pure ASGI middleware (`ApiResponseHeadersMiddleware`) that adds `X-Content-Type-Options: nosniff` and `Cache-Control: no-store` to every response under `/api/` and `/__test__/` (SPEC section 8), except the contract and the Swagger page, which only get `nosniff`; a route's own `Cache-Control` is kept. It wraps the **completed** middleware stack, not an `add_middleware` layer: the 500 of an unhandled error is built by Starlette's `ServerErrorMiddleware`, which sits outside the user stack, so only the wrapper reaches it. The comment in `main.py` says why.
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and the unit suite with the coverage floor exit 0 (1801 passed). Then `curl -i` against a live server started from the branch: the 200 list, the 401, the 404 of an unknown API path, the 422, the 413 of a body above the limit (an answer produced by another middleware), the controls reset, the CSV export (one `Cache-Control`, its own `no-store` kept), the health check carry both headers; `/api/openapi.json` and `/api/docs` carry only `nosniff`; `/robots.txt` carries neither.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The middleware imports `get_route_path` from `starlette._utils`, a private module; a Starlette upgrade could move it. | Accepted: the lockfile pins Starlette and the tests of every case would fail on a break. |
| 2 | Note | The exact path `/__test__` (no trailing slash) gets no headers, because the SPEC says the prefix `/__test__/`; it is a guard 404 anyway. | Accepted. |
| 3 | Note | The unhandled-error test registers `/api/explode` because the existing seam is outside the prefixes. | Accepted. |
