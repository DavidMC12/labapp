# Review: backend authentication core (task 007, 2026-11-04)

- **Branch:** `w1/auth-core`, by Worker 1 (16 commits plus 10 fixes, all inside the allowed backend folders).
- **Reviewers:** Supervisor, and a second agent that ran the code, because this is security code.
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the supervisor:** the acceptance commands re-run with real exit codes (452 tests with warnings as errors); the server run for real (cookie attributes, identical error bodies for an unknown email and a wrong password, 41 ms against 41 ms); the attack of the second review replayed before and after the final fix; the same checks on a clean clone before pushing.

## What the work did well

Tokens of 256 bits stored only as SHA-256 digests, no session fixation, the exact 8-hour idle boundary, a dummy hash that equalizes login timing (about 37 ms for an unknown email, a wrong password and a success, also with a 90 KB password), plain `def` routes with the health check still `async`, deterministic tests with an injected clock, and no race found in a 16-thread stress run.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | Threads waiting for a password-hash slot occupy thread-pool threads: 200 concurrent bad logins delayed `/api/auth/me` by 4.7 s. | A bounded wait did not fix it (measured again: 4.4 s). Fixed by load shedding: at most 2 running and 2 waiting checks, everything else gets 503 `SERVICE_BUSY` at once. Measured after: 194 of 200 answered 503, `/api/auth/me` in 1 ms, a legitimate login right after succeeds. |
| 2 | Important | The login request and the container printed the password, the session secret and the database URL in their `repr`. | Fixed with hidden fields, and tests. |
| 3 | Important | The storage ports were documented only in the in-memory adapter. | Fixed: documented rules, a monotonic `touch`, and contract tests that a PostgreSQL adapter can reuse. |
| 4 | Minor | `SameSite` was lowercase. | Fixed. |
| 5 | Minor | Logout with duplicated session cookies left a session alive. | Fixed: every value is revoked. |
| 6 | Minor | A test asserted the email in a `repr`; no guard kept the handlers `def`; no odd-input tests; a duplicated test clock. | Fixed. |

Deferred, by design: the OpenAPI description of the 422 body (a global fix), the strength of the thread-safety tests, and the per-process application clock offset and in-memory sessions, which the PostgreSQL adapters must replace on the serverless deployment. The session cap can be flooded because the demo password is public; the per-IP rate limits of a later task are the other protection.
