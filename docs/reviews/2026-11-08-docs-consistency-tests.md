# Review: tests that keep the documents and the code in agreement (task 033, 2026-11-08)

- **Branch:** `w1/docs-consistency`, by Worker 1 (13 commits, tests under `backend/tests/docs/` and one README section).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the four backend commands re-run with real exit codes on the branch merged with `main` (ruff, format, `pytest -q -W error`: 1520 passed, 1 expected failure, 211 integration tests skipped without a database);
  - the commit rules;
  - what the 55 tests compare: the seeded users, customers, products, orders (the totals **recomputed** with the money rules, which also checks the half-up notes of the seed document), invoices and payments against `docs/SEED.md`; the next numbers after the seed; every error code of the SPEC against the application code and the status and message of each against the builders that produce them; the label table; the permission matrix; the order transitions.
- **Result:** the documents and the code already agreed; no disagreement was found.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | One test is `xfail(strict=True)`: the SPEC table of field-level messages cannot be compared with a single table in the code, because only two of the nine messages live in `app/errors.py` (the others are built in the validation modules). It is a limit of how the code is organized, not a disagreement. | Accepted for now; a follow-up changes it to check that every message of the table appears in the application source. |
