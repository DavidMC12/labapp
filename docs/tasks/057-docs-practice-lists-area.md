# Task 057: practice scenarios for sorting, CSV export and response headers

Assignee: Worker 1. Branch: `w1/practice-lists`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

`docs/PRACTICE.md` has eight areas (A to H) and no scenario for three features added afterwards: the sorting of the lists (`sort` and `direction`), the CSV export of the lists and the security headers of every API response. Add them as a ninth area, **I. Lists: sorting, CSV export and response headers**, at the same standard as the rest: every row has the exact expected result, and every API row was run. Running them is also a black-box test of those three features: **if a row does not behave as the specification says, do not change the row to match the code: stop and report it** (the request, the answer you got and the specification text), because it may be a defect.

## Read first

`docs/PRACTICE.md` (the legend, the format of the rows and a few rows of areas A to C, so that yours read the same), `docs/SPEC.md` (the **Sorting** sentences of the customers, orders and invoices lists and of `GET /api/products`; section 8: **CSV export** and **API response headers**; section 7 for the error format), `docs/SEED.md` (the data after a reset), `docs/AUTOMATION_GUIDE.md` (the controls: reset, the clock), `backend/tests/docs/test_practice_catalog.py` (the tests that will check your rows: codes, messages, endpoints, statuses).

## Scope

You may edit `docs/PRACTICE.md` (the new area, the table of contents or learning path only if a row belongs in it, and the sentence that says how many areas or rows there are, if any) and `backend/tests/docs/test_practice_catalog.py` / its helpers (only to accept the area letter `I`: the checks of the existing areas must stay exactly as strict). No code, no other document, no `tests/`. API rows only: the screens for sorting and export are not merged yet (a later task adds the UI rows).

## Requirements

1. **At least 30 rows**, ids `I-1` to `I-n`, consecutive, the same seven columns, level `API` (a `Both` or `UI` row only if the behavior is observable through the API alone, then it is `API`). Group them in this order and say so in a short introduction of the area:
   - **Sorting** (about 14 rows): each sortable field of each list in both directions with the first three values expected on the seed; the defaults of `direction` (`created_at` descending, others ascending; `direction` without `sort`); an invalid `sort` and an invalid `direction` (422 `INVALID_FORMAT` on the field) on each of the four lists; an empty `sort=`; a tie broken by `id` in the direction of the sort; an accented name sorted with its plain letter; `number` sorted as an integer (create orders until `PED-0010` exists and show 9 before 10); the sort combined with `q` and with `status`; page 2 continues page 1 under a sort; unauthenticated is 401 before the validation.
   - **CSV export** (about 12 rows): the three routes with the exact header line and a data row from the seed; the file name with the date from the clock control (`POST /__test__/clock` then the name changes); the number of data rows equals the `total` of the list with the same filters and is not capped at 20 (create enough customers to pass one page); the same filters and sort as the list; a `page` is ignored; a name that starts with `=`, `+`, `-` or `@` is exported with a leading quote; a field with a comma, a quote and a line break is quoted as RFC 4180 says; the file has CRLF endings and no byte order mark; `Content-Type`, `Content-Disposition`, `Cache-Control`; 401 without a session; the same 422 as the list for an invalid `status`; every role can export.
   - **Response headers** (about 6 rows): `X-Content-Type-Options: nosniff` and `Cache-Control: no-store` on a success, on a 401, on a 404 of an unknown API path, on a 422 and on a 413 (a body above 100 KB); only `nosniff` on `GET /api/openapi.json` and `GET /api/docs`; none of the two on a path outside `/api/`.
2. **Run every row** with `curl` (or a script outside the repository) against a local in-memory API (`DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`, or start only the backend as that script does, on a port of your own: another process may hold 8000), and mark the `ID` cell of each row you ran and found as written with `✔`, like the other areas. A row you could not run has no mark and the report says why.
3. **Exactness.** Status codes, error codes, Spanish messages, header names and values, file names and column lists come from the SPEC or from the answer you saw; never from memory. Seed-dependent rows name the exact record and say when a reset is needed first. The new rows must pass `backend/tests/docs/test_practice_catalog.py` (codes, messages, endpoints, statuses) and `node tools/audit/docs-lint.mjs`.
4. **Table hygiene.** Every row has the same number of columns as the header; the area has its own table with the same header as the others.
5. **The test file.** Accept the area letter `I` (the regular expression of the id, the list of required areas, the consecutive numbering) without loosening any check; add a test that the new area exists and has at least 30 rows.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass; from the repository root `node tools/audit/docs-lint.mjs` exits 0. The supervisor re-runs a sample of at least 12 of your rows against a live server.

## Rules for this task

- Commit as you go, in small real steps (about 5 to 8 commits: the test file first, then the three groups, then the pointers). Conventional Commits, in English (`docs(practice): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, or a row behaves differently from the SPEC, do not guess and do not fix the row: write it in your report.
- When done, reply with: the branch, the commit range, the number of rows per group, how many rows you ran (and the rows that differ from the specification, if any, with request, answer and SPEC text), the exact commands you ran with their exit codes, and any deviation or open question.
