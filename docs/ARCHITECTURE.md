# Architecture

Status: v0.1, approved. Business rules are in [SPEC.md](SPEC.md); the testability contract is in [TESTABILITY.md](TESTABILITY.md).

## Principles

- **Modular monolith.** One backend, one frontend, one database. Modules are separated by folders and explicit interfaces, not by network calls.
- **Rules live in the backend only.** The frontend renders screens and calls the API. It never decides a business rule.
- **The OpenAPI document is the contract.** FastAPI generates it; the typed frontend client is generated from it; CI fails if the generated files drift.
- **Deterministic by design.** Reset, seed, a controllable clock and fault injection exist for tests and are off unless explicitly enabled.

## Components

```
Browser
  |
Next.js (web)  --/api rewrite-->  FastAPI (API)  -->  PostgreSQL
                                     |
                                     +--> payment gateway port (fake adapter)
                                     +--> email port (Mailpit locally, log online)
                                     +--> clock port (system clock, or test offset)
```

## Backend modules

`auth`, `customers`, `products`, `orders`, `invoices`, `payments`, `settings` (tax rate). Each module owns its models, schemas, routes, services and internal tests. Cross-module calls go through service functions, never through another module's tables.

## Test-only controls

| Route | Purpose |
|---|---|
| `POST /__test__/reset` | Restore the seed data. |
| `POST /__test__/seed` | Load a named dataset. |
| `POST /__test__/clock` | Set or advance the application clock. |
| `POST /__test__/faults` | Inject latency or errors on a given route, or make the payment gateway unavailable (target `gateway`). Latency is capped at 10 seconds. `/__test__/*` and `GET /api/health` are never affected, so a test cannot lock itself out. |

They are always registered under `/__test__` at the root of the API (not under `/api`) and guarded like this:

| `TEST_MODE` | `X-Test-Token` header | Result |
|---|---|---|
| `1` | any | Allowed. |
| `0` | equals a non-empty `TEST_TOKEN` | Allowed. |
| `0` | missing or different | 404, as if the route did not exist. |
| `0` with an empty `TEST_TOKEN` | any | 404. |

Docker Compose sets `TEST_MODE=1` for local development; every public deployment keeps it at 0. The web app proxies only `/api/*`, so online the controls are reachable only by calling the API host directly with the token. The token is compared in constant time. Rate limiting is off when `TEST_MODE=1` and, otherwise, skipped for a valid token (SPEC section 3). The clock offset and the fault rules are stored in the database, so they survive restarts. What a reset restores and keeps is defined in SPEC section 9 and [SEED.md](SEED.md).

## Sessions and security

HTTP-only session cookie with SameSite=Lax, same origin (the web app proxies `/api` to the API), an `Origin` check on state-changing requests, argon2 password hashes, permissions checked on the server, request rate limiting and body size limits on the public demo (details in [SPEC.md](SPEC.md) section 3). Secrets only in environment variables.

## Operational rules

- **Health and warm-up:** `GET /api/health` answers 200 `{"status": "ok"}` without authentication. It doubles as the warm-up request for a sleeping Render instance, which can take about a minute to wake.
- **Startup guard:** the API refuses to start when `SESSION_SECRET` is empty or `change-me`, unless `TEST_MODE=1`. `SESSION_SECRET` is the application secret: it keys the idempotency fingerprints, while session tokens are random, opaque and stored only as a SHA-256 digest.
- **Password hashing:** Argon2id with the library's production parameters. One verification needs about 64 MiB, so the number of concurrent verifications is capped (2 by default) and the routes that verify are plain `def`, running in the thread pool instead of blocking the event loop. A request waits for a free slot at most 2 seconds and then answers 503 `SERVICE_BUSY`, so a flood of logins cannot keep every pool thread waiting.
- **Clocks:** the application clock (an offset over the system clock) drives session expiry, card expiry and the dates the system writes. The rate limiter uses the real monotonic clock, so moving the application clock in a test never resets or fills a rate-limit window.
- **PostgreSQL version:** pin the same major version in Docker Compose and on Neon when Compose is added in M1.
- **Settings defined by the spec:** `APP_ORIGIN` (allowed origin and `Secure` cookie), `TRUSTED_PROXY_COUNT` (client IP from `X-Forwarded-For`) and `DEFAULT_TAX_RATE`, besides the ones already in `.env.example`.
- **Frontend toolchain:** TypeScript is pinned to 6.x because `typescript-eslint` does not support TypeScript 7 yet; revisit when it does.

## Deployment

| Piece | Local | Online |
|---|---|---|
| Web | Next.js dev or container | Vercel |
| API | Container | Render (Docker) |
| Database | PostgreSQL container | Neon |
| Fake email | Mailpit | logged only |

A scheduled GitHub Actions workflow resets the online data every night. The free Render service sleeps after inactivity, so a warm-up request is available on demand.

## Repository layout

`backend/`, `frontend/`, `tests/` (reserved for the owner's automation suite), `tools/audit/` (test-id and accessibility audits), `docs/`.
