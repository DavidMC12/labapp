# Review: backend fixes from the second-agent review (task 066, 2026-11-08)

- **Branch:** `w1/review-fixes`, by Worker 1 (9 commits).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings left.
- **What it fixes** (the numbers are those of `docs/reviews/2026-11-08-batch-security-review.md`): the CSV reader runs with `strict=True`, so an unclosed or misplaced quote is a whole-file `INVALID_FORMAT` and nothing is created (finding 1: before, the following rows were swallowed and the import answered 201); route tests for hostile import input (finding 5: a plain form field named `file`, two `file` parts where the last wins, an empty filename, a lone `\r`, a NUL byte, a BOM in the middle, a record of 20 000 cells, 200 rows of the longest values that exceed 100 KB); the export reads every match in **one statement** through a new `export_rows` port method in the three modules, in memory and in PostgreSQL, and the page loop is gone (finding 3); a deadlock (SQLSTATE `40P01`) answers the retryable 503 `LOCK_TIMEOUT` (finding 7); the real 400 of a malformed multipart body is documented and pinned (finding 9); migration 0005 refuses duplicate approved payments with a readable message (finding 10); the misplaced comment is moved (finding 12).
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and the unit suite with the coverage floor exit 0 (1905 passed). The reviewer's scenario was replayed with `curl -F` against a live server: an unclosed quote in the last column, in a middle column and a closing quote followed by text each answer 422 with `{file, INVALID_FORMAT}` and the customer count stays at 10; a bare quote inside an unquoted field (`5" pipe`) is still accepted. The exports of the three resources and the sorting and filtering of the lists were re-checked live and match. The integration tests ran against a real PostgreSQL (Neon, random schema): the customer, order and invoice adapter contracts (including the three new tests that the export equals every page of the list for each sort field and a filter), the end-to-end import over HTTP and the invoice schema: 141 passed.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | The 400 for a malformed multipart body is `BAD_REQUEST` with "No se pudo completar la solicitud."; it is not in the table of SPEC section 7. | Documented as it is; the SPEC table can list it later. |
| 2 | Note | A BOM that is not at the start is accepted and stays in the value (the SPEC speaks only of the initial BOM). | Accepted; it becomes a practice row. |
| 3 | Note | The migration preflight has a unit test with the existing seam but no integration test on a real pre-0005 schema. | Accepted. |
| 4 | Note | The export of orders is one `SELECT` with a left join to the lines (no paging); memory use grows with the table (the SPEC has no row limit). | Accepted: consistent and linear; a cap is a product decision. |
