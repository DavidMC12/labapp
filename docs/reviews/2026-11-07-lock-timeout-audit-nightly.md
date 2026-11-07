# Review: lock timeout, theme audit and nightly reset (2026-11-07)

- **Branches:** `feat/lock-timeout`, `feat/audit-themes`, `feat/nightly-reset`, by the Supervisor.
- **Reviewer:** a second Claude process in the background, read-only. Every finding was checked against the code before it was applied.
- **Verdict:** With fixes in round 1 (no Critical), all fixed, then merged.
- **Verified by the supervisor:** the full backend unit suite (1042 tests), ruff and format; the integration tests of the lock timeout and of the session store against a real PostgreSQL (20 passed); the browser audit over 18 states in the light and the dark theme (0 failures), plus a negative run proving that it fails when the theme is not applied; the new Node tests of the audit arguments; the reset script against a fake server for 200, 404, a redirect, a refused connection, a missing token and bad URLs.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The 30 second wait for the session lock was hard coded, ignored `LOCK_TIMEOUT_MS`, covered the whole login transaction, and its only trigger was a 20 thread test over a slow link. | Fixed: the constant is gone; the lock is taken after the upsert so it is held for the count and the trim only (about three round trips instead of six, still exact under READ COMMITTED); the test builds its engine with a longer `lock_timeout_ms`. |
| 2 | Important | Registering a `DBAPIError` handler silently changed the 500 path: the exception is no longer re-raised, so the server log lost its frames. (It also fixed a latent leak: the re-raised exception printed the driver message, which can carry row values.) | Decided on purpose: one handler for `DBAPIError` and `psycopg.Error` logs class, SQLSTATE, request id and the stack frames, never the message; tests pin the behavior, including the default test client and the log content. |
| 3 | Important | The reset workflow counted a redirect as success. | Fixed: the status is read with `--write-out` and only an exact 200 passes; redirects are not followed. |
| 4 | Important | The dark audit run never checked that the dark theme was applied, and a malformed `--theme` silently ran unpinned. | Fixed: the storage key is read from `theme.ts`, every state asserts `<html data-theme>`, bad arguments exit with code 2 (tested), CI runs both themes even if one fails and without rate limits. |
| 5 | Minor | A bare psycopg lock error, the missing method and path in the log, `LOCK_TIMEOUT_MS` missing from `.env.example` and DEPLOYMENT, a wrong task number, the fixture annotation, bounds tests, the schema-translated engine test, the retry flags, "not configured" shown as green, the 60 day schedule limit, credentials in the URL, the congested cron minute. | Fixed. |
| 6 | Minor | CI runs no integration tests (no PostgreSQL service). | Open: planned as a separate CI task. |
| 7 | Minor | `lock_timeout` does not cover slow statements; payments with a gateway latency above 5 seconds can hit the timeout. | Noted for the payments tasks (021, 022). |
