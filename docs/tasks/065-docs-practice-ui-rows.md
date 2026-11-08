# Task 065: practice scenarios for the sort headers, the export links and the import screen (UI rows)

Assignee: Worker 2. Branch: `w2/practice-ui-rows`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

`docs/PRACTICE.md` has area **I** (sorting, CSV export and response headers) and area **J** (customers import), both with API rows only: the screens did not exist when they were written. They exist now. Add the UI rows, at the same standard as the rest: every row has the exact expected result, and every row is **run in a real browser** before it is written down.

## Read first

`docs/PRACTICE.md` (the legend, the row format, the UI rows of areas A to C as a model, and the end of areas I and J where yours go), `docs/AUTOMATION_GUIDE.md` (the sections on sorting, downloads and uploading: the ids, the states and the traps), `docs/TESTIDS.md` (the ids of the four lists, the export links and `/customers/import`), `docs/SPEC.md` (the Sorting, CSV export and Import rules), `frontend/README.md` (the Sorting, CSV export and Customers import paragraphs), `backend/tests/docs/test_practice_catalog.py` (the tests that check the rows).

## Scope

You may edit `docs/PRACTICE.md` only (new rows at the end of areas I and J; the learning path and the counts only if a row belongs there), and `backend/tests/docs/test_practice_catalog.py` **only** if a check needs a minimal adjustment to accept a UI row (the checks of existing rows stay exactly as strict: explain any change in the report). No code, no other document, no `tests/`.

## Requirements

1. **Area I, UI rows (at least 10), ids continuing after the last row of the area** (`I-34`, ...), level `UI` (or `Both` when the same behavior is observable through the API): 
   - each list's sort buttons: the first click sorts ascending (descending for the created columns), `aria-sort` and `data-state` follow, the URL carries `sort` and `direction`, the hidden status text announces it, a second click flips, there is no unsorted state; the **order of the rows** after a click on a text column (names with an accent) and on a numeric column (invoice total, product price); sorting returns to page 1 and keeps the filters; opening the sorted URL directly arrives sorted; an invalid `sort` in the URL falls back to the default list;
   - the export links: the `href` of each link follows the applied filters and sort and never carries `page`; text typed in the search box and not applied does not change it; clicking downloads a file whose name is `<resource>-<YYYYMMDD>.csv` and whose number of data rows equals the list's total (and the clock control moves the date in the name);
   - the sorted table at 320 px still has no sideways scroll of the page (the table scrolls inside its region).
2. **Area J, UI rows (at least 10), ids continuing after the last row of the area** (`J-31`, ...), level `UI`: the link "Importar CSV" on the customers list for Admin and Sales and its absence for Finance and Read-only; the page for Read-only (the permission notice, no form); the submit button disabled until a file is chosen; a good file (the result text, `data-state` `success`, the emptied input, the customers in the list afterwards); a rejected file (the alert with the focus, the table with line, field and message for a name error, an email error, a taken email, a repeated email and a short row; nothing created); a whole-file error (`.txt`: line "—", field "Archivo"); a file of 120 KB (the 413 message, no table); a second attempt clears the result of the first; choosing another file returns the form to `idle`; the 320 px layout.
3. **Each row** uses the ids of `docs/TESTIDS.md` in its steps, states the exact texts (Spanish messages, the table cells, the result sentence) and the attributes to assert, copied from what you observed. Seed-dependent rows name the exact records and say when a reset is needed first (`POST /__test__/reset`, as the other rows do).
4. **Run every row.** Drive the real application in Chromium over the DevTools protocol (the browser audit and the supervisor's scripts show how: real clicks on the real ids, `DOM.setFileInputFiles` for the uploads, `Browser.setDownloadBehavior` for the downloads), with the dev servers started as `tools/audit/README.md` says (in-memory API, `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`; another process may hold the ports: check first). Keep your script and its sample files **outside the repository**. A row you could not run is not written. The legend says UI rows carry no `✔`: keep that convention, and say in the report how many UI rows you ran and which ones, with the observed texts of the three most delicate.
5. **Exactness and hygiene.** Every status, code, message, id and number comes from what you saw or from the SPEC, never from memory; every row has the same number of columns as the header; the catalog tests (`uv run pytest -q tests/docs/test_practice_catalog.py` from `backend/`) and `node tools/audit/docs-lint.mjs` pass. **If a row behaves differently from the guide or the SPEC, do not write the row as the code does: stop and report it** (what you did, what you saw, what the document says).

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -W error --cov=app --cov-report=term` pass; from the repository root: `node tools/audit/docs-lint.mjs` exits 0. The supervisor re-runs a sample of the UI rows in a real browser.

## Rules for this task

- Commit as you go, in small real steps (about 5 to 8 commits: sorting, export, import rows). Conventional Commits, in English (`docs(practice): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the number of rows added per area, which rows you ran, the observed texts of the three most delicate, any row that differed from the documents, the exact commands you ran with their exit codes, and any deviation or open question.
