# Review: frontend customers screens (task 011, 2026-11-04)

- **Branch:** `w2/customers`, by Worker 2 (14 commits plus 2 fixes, all inside `frontend/`).
- **Reviewer:** Supervisor. The brief itself went through the background Reviewer before the work started (9 Important findings fixed).
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the supervisor:** the five acceptance commands re-run with real exit codes (178 tests, lint with zero warnings, typecheck, production build); the whole diff read (hooks, API layer, URL parsing, form, list, detail, edit and create pages); the API layer of the frontend run against the real backend through a temporary same-origin proxy (list filters, accent-insensitive search, `q=R&D`, create, duplicate email, field errors, update with the captured version, stale version, status changes with a quoted `If-Match`, 404). Not done: a browser run, because the browser extension was not connected. The same checks on a clean clone before pushing.

## What the work did well

The id in every query key is a number parsed once with the strict pattern, so a status change updates the detail without a reload. The edit form sends the version captured when it was initialized or reset, so a background refetch cannot overwrite another user's change, and the test uses a real TanStack refetch. The list URL is built with `URLSearchParams` (`page` always, `q` and `status` only when set). A page beyond the last is replaced by the last. After a failed status change the customer is refetched, so the next click sends the fresh version. Any 401 clears the session cache entry. Every test id comes from the table of the brief and passes `isValidTestId`.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | After a failed submit with the same error as the previous one (the name still empty, or the email taken twice), the effect that moves the focus did not run, so the focus stayed on the button. | Fixed with a failure counter that every failed submit increments; tests for a repeated client-side error and a repeated 409. |
| 2 | Minor | `?page=2000000` was sent to the API, which answers 422 `OUT_OF_RANGE`, shown as an error that "Reintentar" cannot fix. | Fixed: a page above 1000000 falls back to page 1; boundary tested. |

Deferred: "Volver a clientes" and "Cancelar" drop the page and filter of the list; the edit page also loads the customer for a role that cannot manage customers; the screens are unstyled until the design task (Libro mayor, light theme first, dark mode afterwards).
