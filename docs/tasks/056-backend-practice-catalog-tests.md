# Task 056: tests that keep the practice catalog true

Assignee: Worker 1. Branch: `w1/practice-tests`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

`docs/PRACTICE.md` is a catalog of about 120 scenarios with exact status codes, error codes, Spanish messages and endpoints, written by hand and checked once by running a sample. When the application changes, a row can silently become false, and a test engineer who trusts it loses an afternoon. The backend already has tests that compare the SPEC and the seed with the code (`backend/tests/docs/`). Add the same kind of tests for the catalog, so a change to the API that makes a row false fails the build, and the author of the change is told which row to fix.

## Read first

`docs/PRACTICE.md` (the legend, and a few rows of each area: the cells hold backticked codes, quoted Spanish messages and `METHOD /path` requests), `backend/tests/docs/support.py`, `markdown.py` and two of the existing tests (`test_error_codes.py`, `test_error_status_and_message.py`) for the style, `backend/app/errors.py` (the code constants, `ERROR_MESSAGES` and `FIELD_MESSAGES`), `docs/openapi.json` (or `app.openapi()`), `docs/SPEC.md` section 7 (the codes tables).

## Scope

You may add and edit files under `backend/tests/docs/` only (a new `test_practice_catalog.py`, and helpers in `support.py` / `markdown.py` if needed; the existing tests must keep passing). Do not edit `docs/PRACTICE.md` or any other document: when a test finds a row that is wrong, **do not fix the row and do not weaken the test**: mark that single case with `pytest.mark.xfail(strict=True, reason="PRACTICE <row id>: <what is wrong>")` and list it in the report, so the supervisor decides which side is right. No new dependency.

## Requirements

1. **Parse the catalog.** A helper that reads every scenario row of `docs/PRACTICE.md` into a record (`id`, `level`, `scenario`, `steps`, `expected`, `technique`, `difficulty`, the `✔` mark) from the nine tables, skipping the legend table; a test that the number of rows is at least 100, that every row has the seven cells, that every `ID` is unique and has the form `<A-H>-<number>` and that the numbers of an area are consecutive from 1.
2. **Error codes.** Every upper-case snake-case code in backticks in a row (`VALIDATION_ERROR`, `CUSTOMER_EMAIL_TAKEN`, ...; take the pattern `` `[A-Z][A-Z0-9_]{2,}` ``, and skip the known non-code tokens you meet, with a short comment each, such as `ETag`-like words or HTTP verbs) exists in the stable codes of SPEC section 7 or among the error codes the application defines (the constants of `app/errors.py`, the field codes of `FIELD_MESSAGES`, and the codes in the field-error table). A code that exists nowhere fails the test and names the row.
3. **Spanish messages.** Every message the catalog quotes in a row's `Expected` cell (text between double quotes that contains a space and ends with a period, or the text between double quotes after the word `message`/`detail`; read the rows to find the real convention and say what you chose) equals a message of the application: `ERROR_MESSAGES`, `FIELD_MESSAGES`, the field messages of the SPEC table, or a message string that appears in the application source (as the existing field-message test does). A quoted message found nowhere fails and names the row.
4. **Endpoints.** Every `METHOD /path` that appears in a `Steps` cell (methods `GET`, `POST`, `PATCH`, `PUT`, `DELETE`; the path with its query string cut off) exists in the OpenAPI document, comparing templates (`/api/customers/11` matches `/api/customers/{id}`, `/api/orders/8/lines/8` matches `/api/orders/{id}/lines/{line_id}`) with that method, or is a test-control route `/__test__/...` that the SPEC lists, or `/api/health`. Write the path matching so that a literal id matches an `{id}` template and nothing else does.
5. **Status codes.** For each row whose `Steps` has exactly one `METHOD /path` that resolves to an operation and whose `Expected` cell starts with a three-digit status (for example `422 ...`, `409 ...`, `201 ...`, `403 ...`), the status is one the OpenAPI document declares for that operation (the `responses` keys; `422`, `401` and `403` count as declared when the operation is behind a session, as the contract lists them). Rows with several requests, or whose expectation starts with something else, are skipped by this test; say how many rows it covers.
6. **The test ids.** The documentation linter already checks the ids of the catalog; do not repeat that.
7. **Failure messages** name the row (`PRACTICE B-14: the code 'ORDER_EMPTYY' is not defined`) so a human can go straight to it.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass (the coverage floor holds); the new tests are fast (under 2 seconds in total). Prove that the tests can fail: for each of the checks 2 to 5, change one cell of a **copy** of the catalog in a temporary file (the tests take the path from a helper you can point to a temporary file in a unit test of the helper, or you run the check function directly on altered text) and show that it is reported; those unit tests of the checks stay in the suite.

## Rules for this task

- Commit as you go, in small real steps (about 6 to 9 commits: the parser, then one check each, then the proofs). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the number of rows each check covers, every `xfail` you added with its row and reason, and any deviation or open question.
