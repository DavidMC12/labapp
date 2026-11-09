# Review: the READMEs and the screenshots refreshed (task 070, 2026-11-08)

- **Branch:** `w2/readme-refresh`, by Worker 2 (2 commits, plus one by the supervisor).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it does:** `README.md` and `README.es.md` say the same things in two voices: what the application does today (the four roles, sortable and filterable lists, CSV export and import, the test controls, idempotent payments, the OpenAPI contract and Swagger, the two themes), a "Where it stands" table with one row per area (sorting, CSV, the keyboard and 320 px audits, the automation guide, the practice catalog with its numbers, Dependabot and the dependency audits, the test numbers), and an honest roadmap (not deployed yet; the secrets of the nightly reset; the first Dependabot round). The seven old screenshots are replaced by nine, taken from a production build over the in-memory API with the seed: login, home summary, products, customers sorted by name (the arrow in the header), an order, an invoice in the dark theme, the customers list in the dark theme, the import screen with its table of errors and the orders list on a phone. Each image is 16 to 50 KB (285 KB in all); the old files are gone and no link points to them.
- **Verified by the supervisor:** the documentation linter and the documentation tests exit 0; the numbers were checked against the repository: the practice catalog has 233 rows in 10 areas (20, 21, 25, 11, 9, 14, 11, 10, 50 and 62), the frontend suite has **900 tests passing** in 79 files and the backend 1905 passed with 248 skipped; both READMEs were read, the Spanish one in natural Spanish with the same table rows; the sorted-customers, import-errors and dark-invoice screenshots were opened and show what their alt text says; no claim of a live URL.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | One row of the English table began with a confusing phrase ("List helpers of the audit kind: testable focus."). | Reworded by the supervisor (commit `411866f`). |
| 2 | Note | The old README was false by omission (no sorting, CSV, audits, catalog or Dependabot; the roadmap still listed finished modules as future). | Fixed. |
| 3 | Note | The import screenshot shows the browser's own "Choose File" button in English (headless Chromium has no Spanish language pack). | Accepted: it is the browser's control. |
| 4 | Note | The smoke test row is not in the table because `tools/smoke/` is not merged yet. | To be added when task 069 is merged. |
| 5 | Note | Worker 2 found two of its own development servers still running on ports 3200 and 8200 from earlier tasks and did not kill them. | Confirmed by process directory that they belonged to its worktree; the supervisor closed them. |
