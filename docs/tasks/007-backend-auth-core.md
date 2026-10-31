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

You may create files under `backend/app/infra/`, `backend/app/modules/auth/`, `backend/tests/infra/` and `backend/tests/auth/`; edit `backend/app/main.py` and `backend/app/config.py` only to wire what this task adds; and add a short "Authentication" section to `backend/README.md`. Every new folder needs an `__init__.py`. Do not change anything else (in particular not `backend/tests/conftest.py`: shared fixtures for the new tests go in `backend/tests/auth/conftest.py`). No new dependencies.

## Requirements

1. **Clock** (`app/infra/clock.py`). `Clock` is a `Protocol` with `now() -> datetime` (timezone-aware, UTC). `SystemClock` returns the real time. `OffsetClock(base: Clock)` returns the base time plus an offset that can be read (`offset`), replaced (`set_offset(delta)`) and increased (`advance(delta)`); it is safe to use from several threads. The application clock is an `OffsetClock` over a `SystemClock`; everything in this task that needs "now" receives a `Clock`, never calls `datetime.now()` itself.
2. **Models** (`app/modules/auth/models.py`). Frozen dataclasses: `User` (`id: int`, `name`, `email`, `role: Role`, `password_hash`, `created_at: datetime`, `version: int = 1`) and `Session` (`token_hash: str`, `user_id: int`, `created_at`, `last_seen_at`). The fields `password_hash` and `token_hash` use `field(repr=False)`, so they never appear in a `repr`, a log line or a test failure message. Never log an email, a password or a token.
3. **Ports** (`app/modules/auth/ports.py`), as `Protocol`s. `UserRepository`: `get_by_email(email) -> User | None` and `get_by_id(id) -> User | None`. `SessionStore`: `create(session)`, `get(token_hash) -> Session | None`, `touch(token_hash, when)`, `delete(token_hash)` and `purge_older_than(cutoff) -> int` (removes the sessions whose `last_seen_at` is strictly before `cutoff` and returns how many). `touch` and `delete` on an unknown key are no-ops: they never raise and never create an entry (a `touch` must not bring back a session that a concurrent `delete` just removed).
4. **In-memory adapters** (`app/modules/auth/adapters/memory.py`). Implementations of both ports protected by a `threading.Lock`. The user lookup by email is case-insensitive on the stored, already normalized email. The session store holds at most 10,000 sessions: when `create` would exceed that, it first removes the sessions with the oldest `last_seen_at` (until there is room), so memory stays bounded even though the demo password is public. It also offers `snapshot() -> list[Session]` for tests.
5. **Seed and hashes** (`app/modules/auth/seed.py`). `seed_users(password_hash: str) -> list[User]` returns the four users of `docs/SEED.md` with their ids (1 to 4, in the order listed), names, roles, emails and `created_at` of `2026-01-01T08:00:00Z`. The demo password `Demo-LabApp-2026!` is a constant in this file. Two process-wide functions, each decorated with `functools.cache`, compute the Argon2 hashes with the default production parameters, once per process: `demo_password_hash()` (the hash of the demo password, given to the four users) and `dummy_hash()` (the hash of a random, unguessable value made with `secrets.token_urlsafe(32)`). Never weaken the Argon2 parameters, not even in tests.
6. **Service** (`app/modules/auth/service.py`). `AuthService(users, sessions, clock, *, dummy_hash: str, verify=verify_password, max_concurrent_hashes: int = 2)`. Every `verify` call is made while holding a `threading.BoundedSemaphore(max_concurrent_hashes)`, because one Argon2 verification needs about 64 MiB and the free hosting instance has 512 MB.
   - `login(email, password, presented_token: str | None = None) -> tuple[User, str]`: the email is trimmed and lowercased before the lookup. For an unknown email it still verifies the password against `dummy_hash` and discards the result, so the response time does not reveal whether the account exists. An unknown email and a wrong password raise the same `ApiError(401, "INVALID_CREDENTIALS", "Email o contraseña incorrectos.")`. On success it deletes the session identified by `presented_token` if there is one (a login never keeps an older session alive), removes expired sessions by calling `purge_older_than(now - 32 hours)` (8 hours of idle time plus 24 hours of grace), creates a session with a fresh token (`secrets.token_urlsafe(32)`), stores only the SHA-256 hex digest of the token, and returns the user and the plain token.
   - `authenticate(token: str | None) -> User`, checked in this order: no token or an unknown token raises `ApiError(401, "UNAUTHENTICATED", "Inicia sesión para continuar.")`; a known session idle for 8 hours or more (`now - last_seen_at >= 8 hours`, measured with the clock) raises `ApiError(401, "SESSION_EXPIRED", "Tu sesión expiró. Inicia sesión de nuevo.")` whether or not the user still exists (expired sessions stay in the store until a login purges them, so the same token keeps answering `SESSION_EXPIRED`); a live session whose user no longer exists is deleted and raises `UNAUTHENTICATED`. A live session is touched (`last_seen_at = now`), which makes the window sliding.
   - `logout(token: str | None)`: deletes the session if it exists; it never raises for a missing or unknown token.
7. **Routes** (`app/modules/auth/routes.py`), registered under `/api/auth`. **All routes and dependencies are plain `def`, not `async def`**: FastAPI then runs them in its thread pool, and a ~100 ms Argon2 verification does not stall the event loop and every other request (including the health check that wakes a sleeping host).
   - `POST /login` with JSON `{email, password}` (both required strings, in a pydantic model so a missing field becomes a `REQUIRED` field error through the existing handler). It reads the `labapp_session` cookie only to pass it as `presented_token`. On success: 200 with a `UserOut` response model (`id: int`, `name`, `email`, `role` as a four-value enum of `Role`) and `Set-Cookie: labapp_session=<token>` with `HttpOnly`, `SameSite=Lax`, `Path=/`, no `Max-Age` (a session cookie), no `Domain`, and `Secure` only when `cookie_secure(settings.app_origin)` is true.
   - `POST /logout`: 204, with or without a session (it is idempotent), and a `Set-Cookie` that expires `labapp_session` (`Max-Age=0`, `Path=/`, `HttpOnly`, `SameSite=Lax`, no `Domain`, and `Secure` under the same condition as at login).
   - `GET /me`: 200 with the same `UserOut`; `Cache-Control: no-store` on this response and on the login response.
   - Declare `responses={401: ...}` with the problem shape on the routes that can answer it, so the generated OpenAPI describes the errors.
8. **Dependencies** (`app/modules/auth/dependencies.py`), plain `def`. `get_current_user` reads the `labapp_session` cookie and calls `authenticate`; `require_action(action)` returns a dependency that depends on `get_current_user` and calls `permissions.require(user.role, action)`, so a forbidden action raises the 403 of SPEC section 2. `/me` uses `get_current_user`; `/login`, `/logout` and `GET /api/health` do not.
9. **Wiring.** `create_app(settings=None, *, clock: OffsetClock | None = None)` keeps working for existing callers. It builds a `Container` dataclass once and stores it as `app.state.container` with these attributes: `settings`, `clock` (the `OffsetClock`), `users`, `sessions` and `auth` (the `AuthService`). Task 008 and the tests rely on exactly these names. It seeds the in-memory user repository with `seed_users(demo_password_hash())` and includes the auth router. The module-level `app = create_app()` stays; the cached hashes make its cost a single hash per process. Add to `Settings`: `app_origin: str = "http://localhost:3000"` and `trusted_proxy_count: int = 0` (the latter is used by task 008).
10. **Tests** (`backend/tests/infra/`, `backend/tests/auth/`), deterministic: build applications with `create_app(Settings(session_secret="test-secret", app_origin=...), clock=OffsetClock(...))`, passing `app_origin` explicitly because `Settings()` also reads `../.env`; never sleep, never import the global `app`, and never call the real clock for time-dependent behavior. Service-level tests may inject a fast fake `verify`; route-level tests use the real hashes. Cover:
    - the clock (offset, advance, thread safety);
    - the adapters (case-insensitive lookup, `touch` and `delete` on unknown keys do nothing, `purge_older_than` boundary, the 10,000 cap, thread safety);
    - the seed (four users with the documented data, the hashes are cached and the dummy hash is not the hash of the demo password);
    - the service: success; trimmed and uppercase email; wrong password; unknown email gives the same error and calls `verify` on the dummy hash; an unknown email with the correct demo password still gives 401; the token is not stored in clear (inspect `snapshot()`); sliding expiry at 7 h 59 min and at exactly 8 h; `SESSION_EXPIRED` repeated for the same token and also when the user was removed; `UNAUTHENTICATED` for a missing, an unknown and an orphaned token; the purge on login with the 32-hour cutoff; the presented session is revoked by a new login; logout is idempotent; `repr` of the models hides the hashes; no more than `max_concurrent_hashes` verifications run at the same time;
    - the routes through `TestClient`: success with the cookie attributes under an `http://` origin and, by asserting only the `Set-Cookie` header (the test client does not send `Secure` cookies back over http), under an `https://` origin; `/me` with and without a cookie; logout with and without a session and the expiring cookie; a missing field as `REQUIRED`; `Cache-Control: no-store`; the request id on every response; the OpenAPI document contains the `UserOut` schema;
    - the permission dependency through a small route registered only inside the test, with all four roles against one allowed and one forbidden action.
11. **Docs.** Add a short "Authentication" section to `backend/README.md`: the layers (routes, service, ports, adapters), why routes are plain `def`, how to run with the demo users, and how a later PostgreSQL adapter plugs in.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

and, manually, with the server started as in the backend README (`SESSION_SECRET=dev-secret uv run uvicorn app.main:app --port 8000`), stopping it afterwards with Ctrl+C:

```bash
curl -i -c /tmp/cj -H 'Content-Type: application/json' -d '{"email":"admin@labapp.test","password":"Demo-LabApp-2026!"}' localhost:8000/api/auth/login
curl -i -b /tmp/cj localhost:8000/api/auth/me
```

## Rules for this task

- Commit as you go, in small real steps (about 14 to 18 commits): for example the clock, models and ports, adapters, seed, service, routes, dependencies, wiring, then tests next to each piece and the README. Messages follow Conventional Commits, in English, for example `feat(backend): add session store port`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
