# Review: login screen and application shell (task 005, 2026-10-31)

- **Branch:** `w2/auth-shell`, by Worker 2 (16 commits plus 2 fixes, all under `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the reviewer:** `pnpm install --frozen-lockfile`, `pnpm lint` (zero warnings), `pnpm typecheck`, `pnpm test` (80 tests) and `pnpm build` re-run independently; scope limited to `frontend/`; the single allowed dependency; commit messages and authorship; then, after merging, all of it again on a clean clone of the remote.

## What the work did well

The hard rules of the brief were met exactly: `Accept` and `Content-Type: application/json` on requests, the criterion for a problem document, a rejected `fetch` turned into an `INTERNAL_ERROR` problem, the user written to the cache before navigating (no login bounce), the cache cleared on logout whatever the answer, `noValidate`, trimming, the double-submit guard in the handler, focus after a failure and `replace` instead of `push`.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | A 2xx answer whose body is not JSON (for example HTML from a proxy) made `response.json()` throw a `SyntaxError` that the shell did not handle: a blank page with no alert, retry or redirect. | Fixed: `apiFetch` turns it into an `INTERNAL_ERROR` problem and the shell treats every non-401 error as the error branch; both have tests. |
| 2 | Minor | The INTERNAL_ERROR text was typed again in the login page. | Fixed: the shared constant is used. |

Process note: the worker stopped once at a permission prompt for an absolute path that did not exist, caused by relative paths in the review message; the request was rejected and the paths were clarified.
