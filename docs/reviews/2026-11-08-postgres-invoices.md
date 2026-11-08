# Review: PostgreSQL invoice store (task 021, 2026-11-08)

- **Branch:** `w1/postgres-invoices`, by Worker 1 (18 commits, inside `backend/` and the migration), plus one fix by the supervisor.
- **Reviewer:** Supervisor. The brief had been through two rounds of the background Reviewer (4 Critical and 13 Important in the first, 9 Important in the second, all fixed before the work started).
- **Verdict:** With one fix by the supervisor (below), then ready to merge. No other Critical or Important findings.
- **Verified by the supervisor:**
  - the four backend commands re-run with real exit codes in a detached checkout (ruff, format, `pytest -q -W error`: 1251 passed, 184 integration tests skipped without a database);
  - the commit rules;
  - **all 184 integration tests against a real PostgreSQL 18 on Neon** (a random schema per run, 23 minutes over the network): the migration chain up and down, every constraint, the two-thread payments with the same key and with different keys released by a barrier (no deadlock), pay racing cancel, 20 concurrent issues without a repeated number, the seed twice, `replace_all` and the circular foreign key, the order helpers.
- **Not verified:** nothing left for this task; the same tests run in CI on a PostgreSQL service container after the merge.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | `_claim_key` decided whether it had won the key claim with `rowcount` of `INSERT ... ON CONFLICT DO NOTHING`. With this driver `rowcount` is -1 for that statement, which is truthy, so a replayed request believed it had claimed the key and went on to `INVOICE_NOT_PAYABLE` instead of replaying the stored response. Only the real database could show it (the in-memory store has no such statement). | Fixed by the supervisor: the claim uses `RETURNING` and checks for a row. All 184 integration tests pass with the fix. |
| 2 | Minor | The docstring of the port said `FOR UPDATE` for the invoice row; the adapter uses `FOR NO KEY UPDATE` as designed. | Fixed in the worker's first commit. |
| 3 | Minor | The seed re-links orders 3, 4 and 5 when only the invoices table is empty. | Accepted: follows the brief; the `replace_all` link step is idempotent. |
