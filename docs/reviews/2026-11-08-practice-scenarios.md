# Review: catalog of practice scenarios (task 049, 2026-11-08)

- **Branch:** `w2/practice-scenarios`, by Worker 2 (9 commits, documentation only: `docs/PRACTICE.md` and one pointer sentence in each README and in the automation guide).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it is:** 121 scenario rows in eight areas (customers, orders, invoices and payments, roles, session and security, concurrency and resilience, accessibility and appearance, test data and isolation), a learning path of 14 entries, a legend of levels and techniques, and a closing section on what is deliberately not there (no seeded bugs). 103 API rows carry a mark that Worker 2 ran them with `curl` against the in-memory API.
- **Verified by the supervisor:** the documentation linter exits 0 (links and the test ids cited); a script found no table row with a wrong number of columns. Then a sample was run for real against a live API (a fresh in-memory server in a detached checkout of `main`): 36 checks covering 20 rows (A-9, A-13, A-15, A-17, A-18, A-19, B-3, B-7, B-9, B-12, C-3, C-6, C-8, C-12, C-14, C-21, D-3, E-4, E-6, F-3, F-5 and H-2, with the clock control, the seed datasets, the idempotent payment and the permission matrix), every status code, error code, message, header and number matched the catalog.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | Three commits bundle two or three areas (roles with session, concurrency with accessibility with isolation) instead of one commit per area. | Accepted: the history is still small and readable. |
| 2 | Note | The name of the body member `retry_after` is assumed from the guide; only the `Retry-After: 60` header is asserted. | Accepted; the row asserts only what the specification names. |
| 3 | Note | The UI rows and the 24-hour key expiry row carry no mark: they were read from the specification and the catalog, not executed. | Accepted: the legend says so. |
| 4 | Follow-up | The catalog does not yet cover list sorting and the CSV export (tasks 050 to 053). | The rows are added when the screens exist. |
