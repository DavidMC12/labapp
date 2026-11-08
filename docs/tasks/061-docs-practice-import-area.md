# Task 061: practice scenarios for the customers CSV import

Assignee: Worker 1. Branch: `w1/practice-import`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

`docs/PRACTICE.md` has nine areas (A to I). The customers import (`POST /api/customers/import`, a multipart upload of a CSV file, the **Import** rule of `docs/SPEC.md` section 4) has none. Add area **J. Customers import (file upload)** at the same standard as the others: exact expected results, every API row run. Running them is again a black-box test of a new feature: **if a row does not behave as the specification says, do not change the row to match the code: stop and report it** (the request, the answer you got and the specification text).

## Read first

`docs/PRACTICE.md` (the legend, the row format and the rows of area I, whose layout yours must follow), `docs/SPEC.md` (the **Import** rule of the Customers API and the rules of customer creation above it; section 7 for the error format and the order of the checks), `docs/SEED.md` (the ten customers and their emails after a reset), `docs/AUTOMATION_GUIDE.md` (the controls), `backend/tests/docs/test_practice_catalog.py` (the tests that will check your rows) and `backend/README.md` (the "Customer import" paragraph with the `curl` example).

## Scope

You may edit `docs/PRACTICE.md` (the new area, the learning path only if a row belongs in it) and `backend/tests/docs/test_practice_catalog.py` / its helpers (only to accept the area letter `J`, like the letter `I` was accepted: the checks of the existing areas stay exactly as strict). No code, no other document, no `tests/`. API rows only: the import screen is not merged yet (a later task adds the UI rows).

## Requirements

1. **At least 24 rows**, ids `J-1` to `J-n`, consecutive, the same seven columns, level `API`. Cover, in this order and with a short introduction of the area that says how to upload a file with `curl -F` and that the sample files are made up on the fly:
   - **The good upload** (about 3 rows): a clean file of three rows (201, `created` 3, the ids 11 to 13 in file order, emails lowercased and trimmed, an empty optional value is `null`, a quoted field with a comma and one with a line break); the response headers (`nosniff`, `no-store`) and the shape `{created, items}`; the next customer created by hand after an import takes the next id (the sequence goes on); a file with only the required columns (`name,email`) and one with the optional columns in another order.
   - **The whole file is wrong** (about 8 rows, each with its exact `errors[]` entry on `file`): no part `file`; an empty file; a name that does not end in `.csv` (and `.CSV` accepted); invalid UTF-8; an unknown column; a duplicated column; a missing `email` column; a header only (`OUT_OF_RANGE`, "El valor debe estar entre 1 y 200."); 201 data rows against exactly 200 (accepted).
   - **A row is wrong** (about 6 rows): a name of one letter, a bad email, a phone with letters, a name of 121 characters; a short row (fewer cells than the header) as `rows[N]`; several errors in several rows listed in file order with the right line numbers; the line numbers after blank lines and after a quoted field with a line break; the cap of 100 entries (150 bad rows); **nothing is created** after any rejection (read the list before and after).
   - **Emails** (about 3 rows): an email that exists in the seed in another case (`ACME@example.test`), an email repeated inside the file (the second occurrence is reported, the first is not), and the same email in a row that has another error (what the SPEC says about the first occurrence).
   - **Who may upload and what is stored** (about 4 rows): the permission matrix (Admin and Sales 201; Finance and Read-only 403, and the 403 even when the file is invalid); 401 without a session; a file of 120 KB is 413 `PAYLOAD_TOO_LARGE`; text that starts with `=`, `+`, `-` or `@`, and one that starts with a single quote, are stored as the file gives them (the export adds the quote, the import does not remove it).
   - **The exported file is not an import file** (1 row): download `GET /api/customers/export` and upload it as is: it has the columns `id`, `status`, ... so the answer is 422 `INVALID_FORMAT` on `file`; remove the extra columns and the rows fail with `CUSTOMER_EMAIL_TAKEN` (they exist). A good exercise for a test author.
2. **Run every row** with `curl` (or a script outside the repository) against a local in-memory API (`DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`, or start only the backend on a port of your own: another process may hold 8000), and mark the `ID` cell of each row you ran and found as written with `✔`, like the other areas. A row you could not run has no mark and the report says why.
3. **Exactness.** Status codes, error codes, Spanish messages, field names (`rows[3].email`), header names and values come from the SPEC or from the answer you saw; never from memory. Seed-dependent rows name the exact record and say when a reset is needed first. The new rows must pass `backend/tests/docs/test_practice_catalog.py` (codes, messages, endpoints, statuses) and `node tools/audit/docs-lint.mjs`.
4. **Table hygiene.** Every row has the same number of columns as the header; the area has its own table with the same header as the others.
5. **The test file.** Accept the area letter `J` (the regular expression of the id, the list of required areas, the consecutive numbering) without loosening any check; a test that the new area exists and has at least 24 rows.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass; from the repository root `node tools/audit/docs-lint.mjs` exits 0. The supervisor re-runs a sample of your rows against a live server.

## Rules for this task

- Commit as you go, in small real steps (about 4 to 7 commits: the test file first, then the groups). Conventional Commits, in English (`docs(practice): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, or a row behaves differently from the SPEC, do not guess and do not fix the row: write it in your report.
- When done, reply with: the branch, the commit range, the number of rows per group, how many rows you ran (and the rows that differ from the specification, if any, with request, answer and SPEC text), the exact commands you ran with their exit codes, and any deviation or open question.
