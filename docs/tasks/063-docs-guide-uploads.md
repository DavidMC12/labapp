# Task 063: the automation guide, uploading a file

Assignee: Worker 1. Branch: `w1/guide-uploads`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

`docs/AUTOMATION_GUIDE.md` now teaches sorting, downloads and the response headers. The customers import (`/customers/import` in the UI, `POST /api/customers/import` in the API) is the one classic exercise it does not cover: uploading a file, in a browser and over HTTP, and reading a rejection that is a table of errors. Add it, as recipes a reader can copy, and make every claim true.

## Read first

`docs/AUTOMATION_GUIDE.md` (all of it: the style, the numbering, how a recipe is laid out, especially the subsections on downloads, sorting and the API), `docs/SPEC.md` (the **Import** rule of the Customers API, section 4: every error shape and limit), `docs/TESTIDS.md` (the section of `/customers/import`: `customers-import-*`, `customers-list-import-link`), `frontend/README.md` (the "Customers import" paragraph: the states and the ids), `docs/PRACTICE.md` (area J, the rows of which are run examples), `backend/README.md` (the "Customer import" paragraph).

## Scope

You may edit `docs/AUTOMATION_GUIDE.md` only (and `README.md` / `README.es.md` only if the guide's description there is now wrong). No code. No `tests/`. Write in English, tight, with short lists and tables, like the existing sections. Keep the existing section numbers stable: add the new material as new subsections placed where it reads naturally (the UI recipe with the other UI material, the API recipe with the other API material), and renumber nothing unless you fix every cross-reference (the documentation linter checks links and anchors).

## Requirements

1. **Uploading in the UI.** A subsection with: the ids of the page (a table: the link on the list, the heading, the help text, the file input, the submit button, the back link, the form, the result text, the list link, the alert, the errors table, the three cell kinds, the truncation note); the states of the form (`data-state` `idle` → `loading` → `success` or `error`, `aria-busy` while sending) and when each happens (after a success the form **stays** in `success` and returns to `idle` when another file is chosen; the input is emptied after a success; the submit button is disabled until a file is chosen and while sending; after a failure the focus is on the alert); and the traps (the file input is a native control: do not click the browser's "Choose file" button, set the files on the input; the table rows are in the API's order and the line is the line of the file, not the row number; a rejection creates nothing, so assert the list afterwards; the permission: Finance and Read-only see a permission notice and no form). Playwright sketches labelled "illustrative, not run in CI": `setInputFiles` with an in-memory buffer (`{ name: "clientes.csv", mimeType: "text/csv", buffer: Buffer.from(csv) }`, so no file on disk is needed) for a good file and for a bad one, waiting on `data-state`, and asserting the result text and the error rows by `customers-import-error-row-N` and its three cell ids. Say how to make a file too large (a buffer of 120 KB) and what the page answers.
2. **Uploading over the API.** A subsection with: `curl -F` for a good file and for a rejected one (run them: the output is in the guide), the multipart part name `file`, the Playwright `request` form (`request.post(url, { multipart: { file: { name, mimeType, buffer } } })`, labelled not run), the `Origin` rule of the writes (a browser sends it, `curl` and `request` must add it: say where the guide already explains it and link it), the answer shapes (201 `{created, items}`; 422 with `errors[]` whose `field` is `file`, `rows[N]` or `rows[N].<column>`; 403 before the file is read; 401; 413 at about 100 KB), the limits (UTF-8, `.csv`, the header rule, 1 to 200 rows, at most 100 error entries), all-or-nothing, and the line numbers (the header is line 1, blank lines count, a quoted line break counts).
3. **A worked round trip.** One short recipe that ties downloads and uploads together: export the customers, reshape the file (keep `name` and `email`), upload it and read the result (the rows are already taken: ten `CUSTOMER_EMAIL_TAKEN` entries on a fresh seed), and a second one that renames the emails so the import succeeds. Run it with `curl` and put the real output in.
4. **Cross-references.** Update the lists of what the guide covers, "what to read next" and any sentence that says the application has no file upload so that they are true now; link area J of `docs/PRACTICE.md` (it exists in `main`).
5. **Run it.** Every `curl` recipe must be run against a local API (start only the backend on a port of your own, for example 8020: another process may hold 8000; `DATABASE_URL= DATABASE_URL_UNPOOLED= TEST_MODE=1` and an `APP_ORIGIN`) and its output must match what you wrote; say in the report what you could not run. The Playwright sketches must be consistent with the ids and attributes in `docs/TESTIDS.md` and with how the page behaves (read `frontend/README.md` and the page's tests); they must only use Playwright APIs that exist (`page.getByTestId`, `locator.setInputFiles`, `expect(...).toHaveAttribute`, `expect(...).toHaveText`, `request.post` with `multipart`).

## Acceptance criteria

`node tools/audit/docs-lint.mjs` exits 0 (links, anchors and the test ids cited), and from `backend/` `uv run pytest -q tests/docs` passes (the documentation tests read the guide). The supervisor re-runs a sample of the `curl` recipes against a live server and drives the page once with real files.

## Rules for this task

- Commit as you go, in small real steps (about 4 to 6 commits, one per subsection). Conventional Commits, in English (`docs(guide): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, what you could not run, and any deviation or open question.
