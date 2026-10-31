# Task 006: backend security primitives

Assignee: Worker 1. Branch: `w1/security-primitives`. Reviewer: Supervisor.

## Goal

Implement, as pure Python, the small security and request-guard building blocks that the authentication and payment modules will call: password hashing, the origin check, the client IP, the rate limiter, the test-controls guard and the idempotency helpers. There is no database, no HTTP route and no global state in this task, so every rule can be tested exhaustively and deterministically, with clocks and secrets passed in.

## Read first

- `docs/SPEC.md`: section 3 (authentication and sessions: origin check, rate limits, client IP, test token), section 6 (the idempotency rules) and section 7 (error catalog, order of checks).
- `docs/ARCHITECTURE.md`: "Test-only controls" (the guard table) and "Operational rules".
- `.env.example`: `TEST_MODE`, `TEST_TOKEN`, `APP_ORIGIN`, `TRUSTED_PROXY_COUNT`.
- `backend/app/errors.py` (`ApiError`) and `backend/app/domain/` (the style of the previous task).

## Scope

You may create files only under `backend/app/security/` and `backend/tests/security/`, add a short "Security" section to `backend/README.md`, and add the dependency `argon2-cffi` to `backend/pyproject.toml` (and update `backend/uv.lock`). Do not change other existing files. Both new folders need an `__init__.py`.

## Requirements

1. **Passwords** (`app/security/passwords.py`): `hash_password(password: str) -> str` and `verify_password(hash: str, password: str) -> bool` with Argon2id through `argon2-cffi`; `verify_password` returns `False` (never raises) for a wrong password or a malformed hash; `needs_rehash(hash: str) -> bool`.
2. **Origin check** (`app/security/origin.py`): `check_origin(method, origin, app_origin)` for the methods POST, PUT, PATCH and DELETE: when an `Origin` header is present it must equal `app_origin` (compare scheme, host and port after removing a trailing slash), otherwise raise `ApiError(403, "CSRF_ORIGIN_MISMATCH", "La solicitud no proviene de la aplicación.")`. A missing origin is allowed, and GET, HEAD and OPTIONS are never checked. Also `cookie_secure(app_origin) -> bool`: true when the origin starts with `https://`.
3. **Client IP** (`app/security/client_ip.py`): `client_ip(peer: str, forwarded_for: str | None, trusted_proxy_count: int) -> str`. With a count of 0, or no header, return `peer`. Otherwise split the header on commas, strip spaces and return the entry that is `trusted_proxy_count` entries from the right; if the header has fewer entries than that, return the left-most entry. Ignore entries that are not valid IP addresses by returning `peer` in that case. Reject a negative count with `ValueError`.
4. **Rate limiter** (`app/security/ratelimit.py`): `SlidingWindowLimiter(limit: int, window_seconds: float, clock: Callable[[], float])` with `hit(key: str) -> RateDecision(allowed: bool, retry_after: int)`, where `retry_after` is the whole number of seconds (rounded up, at least 1) until the oldest hit leaves the window when the request is rejected, and 0 when it is allowed. Memory for a key must not grow without bound: drop hits that left the window. Add `rate_limited_error(retry_after: int) -> ApiError` that builds the 429 `RATE_LIMITED` error of SPEC section 3 and carries `retry_after` as an extra member so the HTTP layer can set the `Retry-After` header. Provide `GENERAL_LIMIT = (120, 60)` and `LOGIN_LIMIT = (10, 60)` constants.
5. **Test controls guard** (`app/security/test_guard.py`):
   - `has_valid_test_token(test_token: str, header: str | None) -> bool`: true only when `test_token` is non-empty and the header equals it, compared in constant time (`hmac.compare_digest`).
   - `test_controls_allowed(test_mode: bool, test_token: str, header: str | None) -> bool` implementing the four-row table in `docs/ARCHITECTURE.md`.
   - `rate_limiting_enabled(test_mode: bool, test_token: str, header: str | None) -> bool`: false when `test_mode` is true or the request has a valid token, true otherwise (SPEC section 3).
6. **Idempotency** (`app/security/idempotency.py`):
   - `validate_key(key: str | None) -> str`: a missing or empty key raises `ApiError(422, "IDEMPOTENCY_KEY_REQUIRED", "Falta la cabecera Idempotency-Key.")`; a key that is longer than 64 characters or has characters outside `[A-Za-z0-9._-]` raises `ApiError(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", errors=[{"field": "Idempotency-Key", "code": "INVALID_FORMAT", "message": "El formato no es válido."}])`; otherwise return the key.
   - `canonical_json(body: object) -> bytes`: UTF-8 JSON with sorted keys, no spaces, `ensure_ascii=False`, rejecting `NaN` and infinities.
   - `fingerprint(secret: bytes, body: object) -> str`: hex HMAC-SHA-256 of `canonical_json(body)`.
   - `same_request(secret, stored_fingerprint, body) -> bool` using constant-time comparison.
   - `redact_card(body: dict) -> dict`: returns a copy of a payment request body in which `card.number` is replaced by its last four digits and `card.cvc` is removed, to be stored with the response (SPEC section 6: neither the number nor the CVC is stored).
7. **Tests** (`backend/tests/security/`), one file per module, exhaustive and deterministic (inject the clock, never sleep): hash/verify round trip, wrong password, malformed hash, two hashes of one password differ; every method with a matching, a different, a trailing-slash and a missing origin; client IP for counts 0, 1, 2, 3, a short header, spaces, an invalid entry; the limiter at the limit, one over, after the window moves, `retry_after` rounding, independent keys and bounded memory; the full guard table for every combination (`test_mode` true/false, token empty/set, header missing/right/wrong); idempotency keys of 1, 64 and 65 characters, bad characters, canonical form ignoring key order and whitespace, fingerprints differing for different bodies and for different secrets, and redaction (the stored copy contains no card number beyond the last four digits and no CVC).
8. **Style.** Type hints everywhere, short docstrings, no I/O and no global state, no module-level secrets. `ruff check` and `ruff format --check` must pass.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits): for example one per module plus its tests, then the README section. Messages follow Conventional Commits, in English, for example `feat(backend): add sliding window rate limiter`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
