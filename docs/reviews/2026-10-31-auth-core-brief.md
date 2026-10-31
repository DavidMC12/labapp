# Review: auth core brief (2026-10-31)

- **Scope:** the brief `docs/tasks/007-backend-auth-core.md` and the record of the security primitives review.
- **Reviewer:** a second agent, read-only, run in the background at the same effort level as the author.
- **Verdict:** With fixes. No Critical findings. The reviewer found the design sound and consistent with the spec, with no hole exploitable as written, and checked that the seed data, codes, messages, cookie attributes and the 8-hour boundary match `docs/SPEC.md` and `docs/SEED.md`.

## Important findings and what happened to them

| # | Finding | Disposition |
|---|---|---|
| 1 | Sync or async was unspecified: an `async def` login would run a 64 MiB Argon2 verification on the event loop and stall every request, including the warm-up health check. | Fixed: routes and dependencies are plain `def`; locks are `threading.Lock`; recorded in the architecture notes. |
| 2 | Session lifecycle gaps: nobody purged expired sessions, a login did not revoke the session already presented, and the public demo password allowed unbounded sessions. | Fixed: purge on login with a 32-hour cutoff, revocation of the presented session, a cap of 10,000 sessions in the in-memory store. |
| 3 | `touch` and `delete` on unknown keys were undefined and could resurrect a logged-out session. | Fixed: both are no-ops, with tests. |
| 4 | Logout without a session contradicted the spec. | Fixed: SPEC section 3 now lists logout as idempotent and public. |
| 5 | Hashing the demo password on every application creation would slow the whole test suite. | Fixed: process-wide cached hashes, a random dummy hash, no weakened parameters, no test imports of the global app. |
| 6 | The response shape and the wiring names were open. | Fixed: a `UserOut` model with a role enum, declared 401 responses, and a named `Container` stored in `app.state`. |

## Minor findings

Applied: a required dummy hash with its result discarded and a test for an unknown email with the right password, hidden hashes in `repr`, a logout cookie that mirrors the login cookie, `Cache-Control: no-store`, the order of the expiry and orphan checks, explicit `app_origin` and a separate `conftest.py` in tests, the package renamed from `platform` to `infra`, the role of `SESSION_SECRET`, the cap on concurrent hash verifications (about 64 MiB each on a 512 MB host), and the decision that the rate limiter uses the real monotonic clock (for task 008).

Declined to judge by the reviewer: the request guards (task 008), the PostgreSQL adapters, the Argon2 parameter choice and the measured suite time (read-only review).
