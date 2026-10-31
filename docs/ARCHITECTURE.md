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
| `POST /__test__/faults` | Inject latency or errors on a given route. |

They are mounted only when `TEST_MODE=1` (local default). Online they stay off unless the request carries a valid `X-Test-Token`; otherwise they answer 404. The clock offset and the fault rules are stored in the database, so they survive restarts.

## Sessions and security

HTTP-only session cookie, same origin (the web app proxies `/api` to the API), argon2 password hashes, permissions checked on the server, request rate limiting and body size limits on the public demo. Secrets only in environment variables.

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
