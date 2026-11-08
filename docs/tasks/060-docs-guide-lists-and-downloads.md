# Task 060: the automation guide, sorting, downloads and response headers

Assignee: Worker 2. Branch: `w2/guide-lists`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

`docs/AUTOMATION_GUIDE.md` teaches the locators, the flows, the waiting, the test controls and the API. Three things were added after it was written and are missing from it: the sortable column headers of the four lists, the CSV export (a file download, a classic exercise) and the security headers of every API response. Add them, as recipes a reader can copy, and make every claim true.

## Read first

`docs/AUTOMATION_GUIDE.md` (all of it: the style, the numbering, how a recipe is laid out, the sections 2, 6, 7, 10, 12 and the closing section), `docs/SPEC.md` (the **Sorting** sentences of the lists and `GET /api/products`; section 8: **CSV export** and **API response headers**), `docs/TESTIDS.md` (the ids: `*-list-sort-*-button`, `*-list-sort-text`, `*-list-export-link`), `frontend/README.md` (the Sorting and CSV export paragraphs), `docs/PRACTICE.md` (the area I rows, if they are merged by then).

## Scope

You may edit `docs/AUTOMATION_GUIDE.md` only (and, if a link line needs it, `README.md` / `README.es.md`: only if the guide's description there is now wrong). No code. No `tests/`. Write in English, tight, with short lists and tables, like the existing sections. Keep the existing section numbers stable: add the new material as new subsections or as one new section placed where it reads naturally, and renumber the later ones only if you also fix every cross-reference to them (the documentation linter checks links and anchors).

## Requirements

1. **Sorting, in the UI.** A subsection with: the locator of each sort button (`customers-list-sort-name-button`, ..., the 14 ids, as a table by list with the field each sorts by); what a click does (first click: the default direction of the field, `created_at` descending and the others ascending; a second click flips; no unsorted state); how to assert it (`aria-sort` on the `<th>`, `data-state` on the button, the URL `?page=1&sort=name&direction=asc` and that the default sort leaves both parameters out, the hidden status text `*-list-sort-text`); and how to assert the **order of the rows** (read the cells of one column, compare with the expected order: show a Playwright sketch that reads `customers-list-created-cell-N` or the table's first column and checks it is sorted, labelled "illustrative, not run in CI"); the traps: sorting returns to page 1, the filters survive, the sort lives in the URL so a test can open the sorted list directly, and text columns compare the normalized text (accents and case ignored), so `Álvaro` sorts with `A`.
2. **Sorting, in the API.** `sort` and `direction` per list with the allowed fields (a table), the defaults, the 422 for an invalid value and a `curl` example for each list (with the first three values you get on the seed, run them). Say that ties break by `id` in the same direction.
3. **Downloading a file.** The export links (`customers-list-export-link`, `orders-list-export-link`, `invoices-list-export-link`): what the `href` carries (the applied filters and sort, never `page`), that it is a plain download link, a Playwright sketch with `page.waitForEvent('download')`, `download.suggestedFilename()` matching `customers-YYYYMMDD.csv` (and that the date comes from the application clock, so the clock control changes it), saving the file and parsing it (a small CSV parser snippet in TypeScript that handles quotes and CRLF, or a note to use a library, your choice), and the assertions worth making: the header line, the number of rows equals the list's total, the same sort. A `curl` recipe that downloads the three files with a session cookie and `--output`, and what the file looks like (CRLF endings, no byte order mark, the formula guard: a field that starts with `=`, `+`, `-` or `@` gets a leading quote: say why).
4. **Response headers.** A short subsection or table: which headers every API answer carries (`X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, `X-Request-Id`), the two exceptions (`/api/openapi.json` and `/api/docs` carry only `nosniff`), and a `curl -i` recipe plus a Playwright `request` sketch that asserts them on a success and on a 401. Mention that the web pages carry their own set (`X-Frame-Options`, `Content-Security-Policy` in production only, task 045) and that the API paths do not receive the web app's policy.
5. **Cross-references.** Update the "what is next" / "what to read next" lists and any place that says the lists have a fixed order or that there is no export so that they are true now; link the practice catalog area I if it exists in `docs/PRACTICE.md` when you merge (check; if it is not there, do not link it).
6. **Run it.** Every `curl` recipe you write must be run against a local API (`DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`, or start only the backend on a port of your own: another process may hold 8000) and its output must match what you wrote; put what you could not run in the report. Playwright sketches are labelled as not run, and must still be consistent with the ids and attributes of the real page (read `docs/TESTIDS.md`).

## Acceptance criteria

`node tools/audit/docs-lint.mjs` exits 0 (links, anchors and the test ids cited), and from `backend/` `uv run pytest -q tests/docs` passes (the documentation tests read the guide). The supervisor re-runs a sample of the `curl` recipes against a live server.

## Rules for this task

- Commit as you go, in small real steps (about 5 to 8 commits, one per subsection). Conventional Commits, in English (`docs(guide): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, what you could not run, and any deviation or open question.
