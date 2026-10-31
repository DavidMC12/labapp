# Task 007: backend authentication core

Assignee: Worker 1. Branch: `w1/auth-core`. Reviewer: Supervisor, with a second-agent review because this is security code.

## Goal

Implement login, logout and the current-user endpoint, the session handling, the permission dependency and the application clock, on top of the pure building blocks that already exist (`app/domain/`, `app/security/`). Storage goes through small interfaces ("ports") with in-memory adapters, because no PostgreSQL server is available yet; the PostgreSQL adapters will be added later behind the same ports without touching the service or the routes. This task covers the authentication itself; the request guards (origin check, rate limits, malformed JSON, test controls) are task 008.

## Read first

- `docs/SPEC.md`: section 2 (roles), section 3 (authentication and sessions), section 7 (error catalog and order of checks) and section 8 (formats).
- `docs/SEED.md`: the four users, their ids, names and creation time, and the demo password.
- `docs/ARCHITECTURE.md`: "Sessions and security" and "Operational rules".
- `backend/app/errors.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/domain/permissions.py` and `backend/app/security/` (`passwords.py`, `origin.py`): what you reuse.

## Scope

You may create files under `backend/app/platform/`, `backend/app/modules/auth/`, `backend/tests/platform/` and `backend/tests/auth/`; edit `backend/app/main.py` and `backend/app/config.py` only to wire what this task adds; and add a short "Authentication" section to `backend/README.md`. Every new folder needs an `__init__.py`. Do not change anything else. No new dependencies.

## Requirements

1. **Clock** (`app/platform/clock.py`). `Clock` is a `Protocol` with `now() -> datetime` (timezone-aware, UTC). `SystemClock` returns the real time. `OffsetClock(base: Clock)` returns the base time plus an offset that can be read (`offset`), replaced (`set_offset(delta)`) and increased (`advance(delta)`); it is safe to use from several threads. The application clock is an `OffsetClock` over a `SystemClock`; everything in this task that needs "now" receives a `Clock`, never calls `datetime.now()` itself.
2. **Models** (`app/modules/auth/models.py`). Frozen dataclasses: `User` (`id: int`, `name`, `email`, `role: Role`, `password_hash`, `created_at: datetime`, `version: int = 1`) with a `public()` method returning the dictionary `{id, name, email, role}` where `role` is the string value (`admin`, `sales`, `finance`, `readonly`); `Session` (`token_hash: str`, `user_id: int`, `created_at`, `last_seen_at`).
3. **Ports** (`app/modules/auth/ports.py`). `UserRepository` (`get_by_email(email) -> User | None`, `get_by_id(id) -> User | None`) and `SessionStore` (`create(session)`, `get(token_hash) -> Session | None`, `touch(token_hash, when)`, `delete(token_hash)`, `purge_older_than(cutoff)`), as `Protocol`s.
4. **In-memory adapters** (`app/modules/auth/adapters/memory.py`). Thread-safe implementations of both ports. The user lookup by email is case-insensitive on the stored, already normalized email.
5. **Seed** (`app/modules/auth/seed.py`). `seed_users(password_hash: str) -> list[User]` returns the four users of `docs/SEED.md` with their ids (1 to 4, in the order listed), names, roles, emails and `created_at` of `2026-01-01T08:00:00Z`. The demo password `Demo-LabApp-2026!` is a constant in this file. The application hashes it once at start-up and gives the same hash to the four users.
6. **Service** (`app/modules/auth/service.py`). `AuthService(users, sessions, clock, verify=verify_password, dummy_hash=...)`.
   - `login(email, password) -> tuple[User, str]`: the email is trimmed and lowercased before the lookup. For an unknown email it still verifies the password against `dummy_hash` (a real hash created once at start-up), so the response time does not reveal whether the account exists. An unknown email and a wrong password raise the same `ApiError(401, "INVALID_CREDENTIALS", "Email o contraseña incorrectos.")`. On success it creates a session with a fresh random token (`secrets.token_urlsafe(32)`), stores only the SHA-256 hex digest of the token, and returns the user and the plain token.
   - `authenticate(token: str | None) -> User`: no token, an unknown token or a token whose user no longer exists raise `ApiError(401, "UNAUTHENTICATED", "Inicia sesión para continuar.")`. A known session idle for 8 hours or more (`now - last_seen_at >= 8h`, measured with the clock) raises `ApiError(401, "SESSION_EXPIRED", "Tu sesión expiró. Inicia sesión de nuevo.")`; expired sessions stay in the store (so the same token keeps answering `SESSION_EXPIRED`) until they are older than 24 hours past their expiry, when `purge_older_than` removes them. A live session is touched (`last_seen_at = now`), which makes the window sliding.
   - `logout(token: str | None)`: deletes the session if it exists; it never raises for a missing or unknown token.
7. **Routes** (`app/modules/auth/routes.py`), registered under `/api/auth`:
   - `POST /login` with JSON `{email, password}` (both required strings; use a pydantic model so a missing field becomes a `REQUIRED` field error through the existing handler). On success: 200 with the public user JSON and `Set-Cookie: labapp_session=<token>` with `HttpOnly`, `SameSite=Lax`, `Path=/`, no `Max-Age` (a session cookie) and `Secure` only when `cookie_secure(settings.app_origin)` is true.
   - `POST /logout`: 204, and a `Set-Cookie` that expires `labapp_session` (`Max-Age=0`, same `Path`, `HttpOnly`, `SameSite=Lax`).
   - `GET /me`: the public user JSON.
8. **Dependencies** (`app/modules/auth/dependencies.py`). `get_current_user` reads the `labapp_session` cookie and calls `authenticate`; `require_action(action)` returns a dependency that depends on `get_current_user` and calls `permissions.require(user.role, action)` (so a forbidden action raises the 403 of SPEC section 2). Both are used by the routes above where applicable (`/me` needs a session; `/login` and `/logout` and `GET /api/health` do not).
9. **Wiring.** `create_app(settings=None, *, clock=None)` keeps working for existing callers. It builds the container (clock, repositories, `AuthService`) once, stores it in `app.state`, hashes the demo password once, and includes the auth router. Add to `Settings`: `app_origin: str = "http://localhost:3000"` and `trusted_proxy_count: int = 0` (the latter is used by task 008). Existing tests must keep passing without changes to their fixtures other than what the new wiring needs.
10. **Tests** (`backend/tests/platform/`, `backend/tests/auth/`), deterministic: the application is built with an injected `OffsetClock`, never sleeps and never calls the real clock for time-dependent behavior. Cover: the clock (offset, advance, thread safety); the adapters; the seed (four users with the documented data); the service (success, trimmed and uppercase email, wrong password, unknown email with the same error and with `verify` called on the dummy hash, token never stored in clear, sliding expiry at 7h59 and at 8h00, `SESSION_EXPIRED` repeated for the same token, purge after 24 hours past expiry, `UNAUTHENTICATED` for missing, unknown and orphaned tokens, logout idempotent); the routes through `TestClient` (cookie attributes with an `http` origin and with an `https` origin, `/me` with and without cookie, logout clears the cookie, missing field errors as `REQUIRED`, the unchanged existing tests, request id on every response); the permission dependency through a small route registered only inside the test (all four roles against one allowed and one forbidden action).
11. **Docs.** Add a short "Authentication" section to `backend/README.md`: the layers (routes, service, ports, adapters), how to run with the demo users, and how a later PostgreSQL adapter plugs in.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

and, manually, with the server started as in the backend README:

```bash
curl -i -c /tmp/cj -H 'Content-Type: application/json' -d '{"email":"admin@labapp.test","password":"Demo-LabApp-2026!"}' localhost:8000/api/auth/login
curl -i -b /tmp/cj localhost:8000/api/auth/me
```

## Rules for this task

- Commit as you go, in small real steps (about 12 to 16 commits): for example the clock, models and ports, adapters, seed, service, routes, dependencies, wiring, then tests next to each piece and the README. Messages follow Conventional Commits, in English, for example `feat(backend): add session store port`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
