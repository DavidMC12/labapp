# Task 068: practice rows for the hostile and malformed import files

Assignee: Worker 1. Branch: `w1/practice-hostile`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 066 (`w1/review-fixes`) is merged (the supervisor tells you). Until then branch from `w1/review-fixes`.

## Goal

Task 066 made the CSV import reject an unclosed or misplaced quote (before, a file with an unclosed quote swallowed the following rows and answered 201 with rows missing) and pinned how the import answers a set of hostile uploads. Those are exactly the cases a test engineer should practice. Add them to area **J** of `docs/PRACTICE.md`, run, at the standard of the other rows.

## Read first

`docs/PRACTICE.md` (the legend, the layout of area J and its introduction, which says how to upload with `curl -F`), `docs/SPEC.md` (the **Import** rule: the parsing sentence, the header rule, the order of checks), `backend/tests/domain/test_csv_import.py` and `backend/tests/customers/test_routes_import.py` (the cases task 066 added, with the exact answers they pin), `backend/tests/docs/test_practice_catalog.py` (the checks of the rows).

## Scope

`docs/PRACTICE.md` (new rows at the end of area J, ids continuing; one sentence in the introduction of the area if needed) and `backend/tests/docs/test_practice_catalog.py` only if a check needs a minimal adjustment (explain it). No code, no other document, no `tests/`.

## Requirements

1. **At least 10 new API rows** (level `API`, the same seven columns), covering, each with its exact answer taken from the SPEC and from what you observe:
   - **Quotes.** An unclosed quote in the last column, one in a middle column, and one at the start of a field at the end of the file: all 422 `VALIDATION_ERROR` with `{field: "file", code: "INVALID_FORMAT"}` and **nothing created** (read the list before and after); `"a"b` (a closing quote followed by text): the same; a bare double quote inside an unquoted field (`5" pipe`) is valid and stored as written; a quoted field with a doubled quote (`"say ""hi"""`) is stored as `say "hi"`.
   - **Line endings and BOM.** A file with only `\r` line endings (what the application answers: observe it and write it); CRLF and LF mixed in one file; a BOM at the start (ignored) against a BOM in the middle (accepted, it stays in the value: say what the stored value is).
   - **The upload itself.** A plain form field named `file` with no filename (`-F 'file=value'`): the answer; two `file` parts (the last one wins: show it with two different valid files and read which customers exist); an empty filename (`-F 'file=@x.csv;filename='`): the answer; a part named differently (`-F 'other=@x.csv'`): the answer.
   - **Control characters and size.** A NUL byte inside a value (the exact `rows[N].<column>` entry); a record with 20 000 cells (the exact answer, and that it comes back quickly); a file of 200 rows with the longest allowed values (above 100 KB: 413 `PAYLOAD_TOO_LARGE`).
2. **Run every row** with `curl -F` (or a script outside the repository) against a local in-memory API (`DATABASE_URL= DATABASE_URL_UNPOOLED=` with `TEST_MODE=1` and an `APP_ORIGIN`; start only the backend on a port of your own, for example 8020: another process may hold 8000), and mark the `ID` cell of each row you ran and found as written with `✔`. If a row behaves differently from the SPEC, **do not write the row as the code does: stop and report it** (the request, the answer, the SPEC text).
3. **Exactness and hygiene.** Messages, codes, field names and values come from the answer you saw; fixtures are made up on the fly outside the repository; seed-dependent rows say when a reset is needed. Every row has the same number of columns as the header. The catalog tests (`uv run pytest -q tests/docs/test_practice_catalog.py`) and `node tools/audit/docs-lint.mjs` pass.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -W error --cov=app --cov-report=term` pass; from the repository root `node tools/audit/docs-lint.mjs` exits 0. The supervisor re-runs a sample of the rows against a live server.

## Rules for this task

- Commit as you go, in small real steps (about 3 to 5 commits). Conventional Commits, in English (`docs(practice): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If the spec is ambiguous, or a row differs from the SPEC, do not guess: write it in your report.
- When done, reply with: the branch, the commit range, the number of rows added, how many you ran (and any that differ from the SPEC, with request, answer and SPEC text), the exact commands you ran with their exit codes, and any deviation or open question.
