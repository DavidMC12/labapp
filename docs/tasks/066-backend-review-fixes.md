# Task 066: backend fixes from the second-agent review of the new features

Assignee: Worker 1. Branch: `w1/review-fixes`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

A background reviewer read the CSV import, the CSV export, the sorting, the response headers and the payments hardening (`docs/reviews/2026-11-08-batch-security-review.md`). It found no Critical issue and the supervisor confirmed its Important findings by reproducing them. This task fixes the backend ones. Read each finding as a requirement; the supervisor re-checks every one against a live server.

## Read first

`docs/reviews/2026-11-08-batch-security-review.md` (written by the supervisor; the findings that are yours are listed below), `docs/SPEC.md` (the **Import** rule of the Customers API, the **CSV export** bullet of section 8, and the row `Lock wait above 5 seconds, or a deadlock between two requests` of section 7: the SPEC was updated for this task), `backend/app/domain/csv_import.py` and `csv_export.py`, the three services' `export_*` methods and the adapters' `list` methods, `backend/app/infra/db.py` and `backend/app/errors.py` (the database error handler and how `LOCK_TIMEOUT` is produced), `backend/migrations/versions/0005_one_approved_payment.py`, `backend/tests/domain/test_csv_import.py`, `backend/tests/customers/test_routes_import.py`.

## Scope

Under `backend/` (the domain, the three modules, `infra/db.py` / `errors.py`, the migration, the tests, `backend/README.md` for a sentence) and `docs/openapi.json` regenerated. Do not edit `docs/SPEC.md`, the frontend, `tools/` or `tests/`. No new dependency.

## Requirements

1. **An unclosed or misplaced quote must be rejected, not swallowed (Important: silent data loss).** `csv.reader` runs with the default `strict=False`: a file `name,email,address` with a row `Ana,ana@x.co,"Calle 1` followed by `Beto,beto@x.co,Calle 2` is read as ONE record, the second row disappears into the address, and the import answers 201. `"a"b` is read as `ab`. Use `strict=True` so that the existing `csv.Error` branch answers the whole-file `{file, INVALID_FORMAT}` of the SPEC; keep a bare quote inside an unquoted field valid (`5" pipe`). Tests in `test_csv_import.py` and the route tests: the unclosed quote in the last column, in a middle column and at the start of a field at the end of the file; `"a"b`; the bare quote that stays valid; and that nothing is created in the rejected cases.
2. **The test gap for hostile import input (Important).** Add route-level tests for: a plain form field named `file` (no filename: 422 `INVALID_FORMAT` on `file`, not a crash), two `file` parts (the last wins, say so in the test), an empty filename (what a browser sends for an empty file input: say what the application answers and pin it), a lone `\r` as the line ending, a NUL byte in a value (rejected by the creation rules: pin the exact entry), a BOM in the middle of the file, a record with 20 000 cells (it must answer, with a `rows[N]` `INVALID_FORMAT` or the header rule, in reasonable time), and a file at the edge where the 100 KB limit and the 200-row limit meet (about 200 short rows is far below the limit: show that 200 rows of the longest allowed values exceeds 100 KB and answers 413, not a crash). Where the application's answer is not what the SPEC says, stop and report it instead of pinning it.
3. **The export must read a consistent snapshot in one query (Important).** Today the export reads 500-row pages through `list`, each page its own transaction with its own `COUNT(*)` and `OFFSET`: an insert or a status change between two pages repeats or skips a row, the cost grows quadratically, and the SPEC has no row limit. Add one port method per module (for example `export_rows(...)` returning every match in the requested order, with the same filters and sort as `list`, no `page`, no `COUNT`) implemented in the in-memory and PostgreSQL stores as **one** statement (one `SELECT` with the filters, the join for orders and the `ORDER BY` with the `COLLATE "C"` and `id` tie-break of the sort), and make the three `export_*` services use it instead of the page loop (remove the loop and `EXPORT_PAGE_SIZE` if nothing else uses it). Contract tests for both stores in each module: the export rows equal the concatenation of every page of `list` for the same filters and sort (use more than 20 rows), for each sort field and for a filter. A unit test that the service never calls the paged `list` for an export.
4. **A deadlock is a retryable 503 (Minor).** Two concurrent imports whose emails overlap in a different order can deadlock in PostgreSQL (SQLSTATE `40P01`); the database error handler answers 500 today and only `55P03` becomes 503. Map `40P01` (`deadlock_detected`) to the same 503 `LOCK_TIMEOUT` answer, with a unit test next to the existing mapping tests (a fake `DBAPIError` carrying that SQLSTATE) and the log line the handler already writes for the other cases (class and SQLSTATE, no message). Do not reorder the rows of `add_many`: the ids must follow the file order.
5. **The import route documents the wrong 400 (Minor).** `documented_responses(body=True)` publishes "not valid JSON, `MALFORMED_JSON`" for the import. A malformed multipart body gets FastAPI's own 400: send one (a wrong boundary) to the application, read the exact status, `code` and `detail` it answers, write that as the documented 400 of this route, and add a test that pins the real answer. Regenerate `docs/openapi.json`.
6. **Migration 0005 must fail clearly on duplicates (Minor).** Before creating the unique index, the migration checks `SELECT invoice_id FROM payments WHERE status = 'approved' GROUP BY invoice_id HAVING count(*) > 1` and, when it finds rows, raises an error whose message lists the invoice ids and says to resolve them first (so a deploy build fails with a readable reason instead of a bare `could not create unique index`). A test of that preflight (use the seams of `tests/invoices/test_migrations.py`; an integration test that inserts two approved payments in a pre-0005 schema is welcome if the harness allows it).
7. **A misplaced comment (Minor).** `backend/app/modules/orders/adapters/postgres.py` and `memory.py`, in `transition`: the comment "A confirmed order keeps the rate frozen at confirmation" sits above the `else` branch that freezes the **current** rate of a **draft**. Move or reword it so it describes the branch it is on; no logic change.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass (the coverage floor holds). The integration tests (the new contract classes against PostgreSQL, the migration preflight) are skipped on your side; the supervisor runs them against a real database and repeats the unclosed-quote upload with `curl -F`.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits, one per requirement or per module). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If the spec is ambiguous, or an answer differs from the SPEC, do not guess: write it in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, which tests are integration-only, any answer that differed from the SPEC, and any deviation or open question.
