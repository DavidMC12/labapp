# Review: frontend home summary (task 026, 2026-11-07)

- **Branch:** `w2/home-summary`, by Worker 2 (6 commits, all inside `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the five frontend commands and the test id audit re-run with real exit codes in the worker's tree (595 tests in 62 files, 57 files and 269 ids audited, 0 problems);
  - the commit rules;
  - the data layer read in full: each counter is the `total` of a list request through the existing list hooks and query keys, so a failing request breaks only its card;
  - the page in a real browser against the running API, in both themes and at 1280 and 390 pixels: the customer and order counters equal the `total` that the API returns (8 and 2 customers; 1, 3, 1, 1 and 1 orders), the invoice counters show "—" with a retry button because the invoices API does not exist yet, and the page does not scroll horizontally.
- **Not verified yet:** the invoice counters against a real invoices API (task 019 is not merged).

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The grammar of test ids gained a module, `home`, which the brief did not list. | Accepted: the ids of the brief need it; `docs/TESTABILITY.md` updated. |
| 2 | Minor | Five order counters on a four column grid leave "Cancelado" alone on a second row. | Noted for the polish pass. |
| 3 | Minor | On a phone the shell navigation now has four links and scrolls sideways inside its own row ("Configuración" is cut off until swiped). The page itself does not scroll. | Noted for the polish pass (a result of task 025, not of this one). |
