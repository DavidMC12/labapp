# Task 030: the OpenAPI contract as a committed, checked file

Assignee: Worker 1. Branch: `w1/openapi-contract`. Reviewer: Supervisor.

**Base.** Branch from `main` after tasks 021, 022 and 024 are merged (the supervisor tells you), so that the API is complete. Until then you may build it on top of your current branch and rebase later.

## Goal

`docs/ARCHITECTURE.md` says that the OpenAPI document is the contract of the API and that CI fails when it drifts, but no copy of it is committed and nothing checks it. The owner writes API automation against this contract, so it must be a file they can open, import into any tool and trust. Export it, commit it, and make a test fail whenever the code and the file disagree.

## Read first

`docs/ARCHITECTURE.md` (the first section and "Test-only controls"), `backend/app/main.py` (`create_app`), `backend/app/cli.py`, `backend/tests/invoices/test_openapi.py` and any other test that reads `app.openapi()`, `backend/README.md`.

## Scope

You may create and edit files under `backend/app/cli.py`, `backend/tests/` (a new `test_openapi_contract.py`), `backend/README.md` and `docs/openapi.json` (new); and change **one sentence** of `docs/ARCHITECTURE.md` (the one about the contract, to say what is true: the committed file is checked in CI; the typed frontend client is not generated yet). If the schema shows a defect (a missing `response_model`, a missing description of an error answer, a duplicated component name), do not change the routes: list it in your report. No new dependencies.

## Requirements

1. **CLI.** `python -m app.cli openapi` prints the OpenAPI document of the application to standard output; `--output <file>` writes it to a file instead. The application is built with the default settings and no database (`create_app(Settings(session_secret="openapi-export"))` or the equivalent the other CLI commands and tests use), so the command opens no connection and needs no environment. The JSON is `json.dumps(document, indent=2, ensure_ascii=False)` followed by a newline, with the keys in the order FastAPI produces them (do not sort them).
2. **The committed file.** Generate `docs/openapi.json` with that command and commit it. It contains no `/__test__` route (they are `include_in_schema=False`).
3. **The check.** `backend/tests/test_openapi_contract.py` builds the document the same way, compares it with the committed file (read relative to the repository root, found from the test file) and fails with a message that names the command that regenerates the file (`cd backend && uv run python -m app.cli openapi --output ../docs/openapi.json`). One more test asserts that every path under `/api` appears in the file with at least one answer code, that every money field of the invoices and orders schemas is of type `string` and that no operation is missing an `operationId`.
4. **Docs.** A short "OpenAPI contract" section in `backend/README.md`: the file, the command, the rule that a change of the API commits the regenerated file in the same change.
5. **The sentence** in `docs/ARCHITECTURE.md`.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
uv run python -m app.cli openapi --output ../docs/openapi.json && git diff --exit-code ../docs/openapi.json
```

## Rules for this task

- Commit as you go, in small real steps (about 6 to 8 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the schema defects you found, and any deviation or open question.
