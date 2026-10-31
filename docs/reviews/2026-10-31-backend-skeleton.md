# Review: backend skeleton (task 001, 2026-10-31)

- **Branch:** `w1/backend-skeleton`, by Worker 1 (17 commits, all under `backend/`).
- **Reviewer:** Supervisor.
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the reviewer:** `uv sync`, `ruff check`, `ruff format --check` and `pytest` re-run independently (29 tests, warnings treated as errors), scope limited to `backend/`, commit messages and authorship checked.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | Errors with a status outside the table exposed English texts as `detail`. | Fixed: 405 has its own code and a Spanish message; other statuses use a generic Spanish message. |
| 2 | Important | The top-level message of `VALIDATION_ERROR` differed from the error catalog (the catalog entry was added after the branch was cut). | Fixed: "Revisa los datos ingresados." |
| 3 | Important | An incoming `X-Request-Id` was echoed without validation. | Fixed: only `^[A-Za-z0-9._-]{1,64}$` is accepted, otherwise a UUID4 is generated; tests added. |
| 4 | Important | The brief asked for `httpx`, which Starlette 1.10 reports as deprecated in favor of `httpx2`. This was an error in the brief, not in the work. | Fixed: dev dependency replaced; the test run has no warnings. |
| 5 | Minor | `.env` was only read from the current directory. | Fixed. A second round corrected the file precedence, which the review had specified backwards: `backend/.env` now wins over the repository-root `.env`, and a test covers it. |
| 6 | Minor | The 100 KB body limit only inspects `Content-Length`. | Documented in the code and the README; a streaming limit is deferred. |

## Decisions taken from the open questions

- The problem document keeps `type` as `about:blank` and an English HTTP phrase as `title`; `title` is stable and never shown to users. Recorded in SPEC section 8.
- Statuses outside the catalog render a generic Spanish message; 405 `METHOD_NOT_ALLOWED` was added to the catalog.
- A request id from the client is validated as described above.
