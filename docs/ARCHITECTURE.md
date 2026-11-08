# Architecture

Status: v0.1, approved. Business rules are in [SPEC.md](SPEC.md); the testability contract is in [TESTABILITY.md](TESTABILITY.md).

## Principles

- **Modular monolith.** One backend, one frontend, one database. Modules are separated by folders and explicit interfaces, not by network calls.
- **Rules live in the backend only.** The frontend renders screens and calls the API. It never decides a business rule.
- **The OpenAPI document is the contract.** FastAPI generates `docs/openapi.json`, which is committed and checked in CI; the typed frontend client is not generated from it yet.
- **Deterministic by design.** Reset, seed, a controllable clock and fault injection exist for tests and are off unless explicitly enabled.

## Components

```
Browser
  |
Next.js (web)  --/api routed-->  FastAPI (API)  -->  PostgreSQL
                                     |
                                     +--> payment gateway port (fake adapter)
                                     +--> email port (logged only; no real email is sent)
                                     +--> clock port (system clock, or test offset)
```

## Backend modules

`auth`, `customers`, `products`, `orders`, `invoices`, `payments`, `settings` (tax rate). Each module owns its models, schemas, routes, services and internal tests. Cross-module calls go through service functions, never through another module's tables.

## Test-only controls

| Route | Purpose |
|---|---|
| `POST /__test__/reset` | Restore the seed data. |
| `POST /__test__/seed` | Load a named dataset. |
| `GET /__test__/clock` | Read the application time and the offset. |
| `POST /__test__/clock` | Set or advance the application clock. |
| `POST /__test__/faults` | Inject latency or errors on a given route, or make the payment gateway unavailable (target `gateway`). Latency is capped at 10 seconds. `/__test__/*` and `GET /api/health` are never affected, so a test cannot lock itself out. |
| `GET /__test__/faults` | List the active fault rules with their remaining count. |
| `DELETE /__test__/faults` | Remove every fault rule. |

They are always registered under `/__test__` at the root of the API (not under `/api`) and guarded like this:

| `TEST_MODE` | `X-Test-Token` header | Result |
|---|---|---|
| `1` | any | Allowed. |
| `0` | equals a non-empty `TEST_TOKEN` | Allowed. |
| `0` | missing or different | 404, as if the route did not exist. |
| `0` with an empty `TEST_TOKEN` | any | 404. |

The local start script sets `TEST_MODE=1`; every public deployment keeps it at 0. Online, the project routes `/__test__/*` to the API as well, and the guard (planned) answers 404 to anything without the token, so the controls will be reachable only with it. The token is compared in constant time. Rate limiting is off when `TEST_MODE=1` and, otherwise, skipped for a valid token (SPEC section 3). The clock offset and the fault rules are stored in the database (a later task), so they survive restarts and are shared by every instance. What a reset restores and keeps is defined in SPEC section 9 and [SEED.md](SEED.md).

## Sessions and security

HTTP-only session cookie with SameSite=Lax, same origin (locally the web dev server forwards `/api` to the API; online the platform routes it), an `Origin` check on state-changing requests, argon2 password hashes, permissions checked on the server, request rate limiting and body size limits on the public demo (details in [SPEC.md](SPEC.md) section 3). Secrets only in environment variables.

## Operational rules

- **Health and warm-up:** `GET /api/health` answers 200 `{"status": "ok"}` without authentication. It doubles as the warm-up request: a Vercel function starts on demand, so the first request after a quiet period can be slower (a cold start).
- **Startup guard:** the API refuses to start when `SESSION_SECRET` is empty or `change-me`, unless `TEST_MODE=1`. `SESSION_SECRET` is the application secret: it keys the idempotency fingerprints, while session tokens are random, opaque and stored only as a SHA-256 digest.
- **Password hashing:** Argon2id with the library's production parameters. One verification needs about 64 MiB, so the number of concurrent verifications is capped (2 by default) and the routes that verify are plain `def`, running in the thread pool instead of blocking the event loop. A request waits for a free slot at most 2 seconds and then answers 503 `SERVICE_BUSY`, so a flood of logins cannot keep every pool thread waiting.
- **Clocks:** the application clock (an offset over the system clock) drives session expiry, card expiry and the dates the system writes. The rate limiter uses the real monotonic clock, so moving the application clock in a test never resets or fills a rate-limit window.
- **PostgreSQL version:** Neon runs PostgreSQL 18; the development database is a Neon branch of the same major version.
- **Settings defined by the spec:** `APP_ORIGIN` (allowed origin and `Secure` cookie), `TRUSTED_PROXY_COUNT` (client IP from `X-Forwarded-For`) and `DEFAULT_TAX_RATE`, besides the ones already in `.env.example`. Online, set `TRUSTED_PROXY_COUNT=1`: at the default 0 every visitor shares the proxy's address, and with it one rate-limit bucket (10 logins a minute for everybody).
- **Frontend toolchain:** TypeScript is pinned to 6.x because `typescript-eslint` does not support TypeScript 7 yet; revisit when it does.

## Deployment

| Piece | Local | Online |
|---|---|---|
| Web | Next.js dev server | Vercel |
| API | uvicorn | Vercel (Python function, same project) |
| Database | Neon development branch | Neon |
| Fake email | logged only | logged only |

The web app and the API are two services of one Vercel project (Vercel Services): `/api/*` and `/__test__/*` go to the API and everything else to the web app, so the browser sees a single origin and the session cookie works. Migrations run in the API build over a direct (unpooled) database connection. Nothing stateful may live in a process, because instances are started, frozen, replaced and run in parallel at the platform's will, so memory is neither shared nor durable. Users, sessions and customers are already stored in PostgreSQL when `DATABASE_URL` is set; the clock offset, fault rules, idempotency keys and a shared rate-limit state move there in later tasks, and until then the in-memory rate limits are best effort (each instance counts for itself, with the monotonic clock of the process). A scheduled GitHub Actions workflow resets the online data every night.

## Repository layout

`backend/`, `frontend/`, `tests/` (reserved for the owner's automation suite), `tools/audit/` (test-id and accessibility audits), `docs/`.
