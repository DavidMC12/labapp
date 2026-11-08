# Task 035: backend test coverage report, gaps and a floor in CI

Assignee: Worker 1. Branch: `w1/coverage`. Reviewer: Supervisor.

**Base.** Branch from `main` after tasks 024, 030 and 033 are merged (the supervisor tells you), or on top of your current branch until then.

## Goal

The backend has more than 1300 unit tests and 200 integration tests, but nobody knows what they leave uncovered. Measure it, close the real gaps, and put a floor in CI so that coverage cannot silently fall. Do not chase 100 percent: cover behavior that matters (error paths, boundaries, concurrency branches that can be exercised without a database, the guards, the rules), not trivial lines.

## Read first

`backend/pyproject.toml`, `backend/README.md` (the Test section), `.github/workflows/ci.yml` (the backend job: it runs unit and PostgreSQL integration tests together), a few existing tests (`backend/tests/orders/`, `backend/tests/guards/`) for the style.

## Scope

You may edit files under `backend/` (configuration, `pyproject.toml` and `uv.lock` for one new dev dependency, new and existing test files, the README) and `.github/workflows/ci.yml` (only the backend job's test step). **You may add exactly one dependency, `pytest-cov`**, as a dev dependency. Do not change application code except to fix a bug that a new test proves (then keep the fix in its own commit and describe it in the report).

## Requirements

1. **Measure.** Configure coverage (`[tool.coverage.run]` with `source = ["app"]`, branch coverage on, `omit` for `__main__` style files only; `[tool.coverage.report]` with `show_missing`). Add the way to run it to the README: `uv run pytest --cov=app --cov-report=term-missing:skip-covered`. Record in your report the per-package table (`app/modules/*`, `app/domain`, `app/guards`, `app/security`, `app/infra`) before and after. Without `TEST_DATABASE_URL` the PostgreSQL adapters are mostly uncovered: measure both ways, with and without the integration tests (you cannot run the latter; the Supervisor will run them and send the numbers back), and base the floor on the **unit-only** number so that it holds anywhere.
2. **Close the gaps.** List the ten files with the lowest branch coverage among those that contain logic, excluding the PostgreSQL adapters, and add tests for their uncovered branches. Each new test asserts behavior, not that a line ran. Keep them deterministic.
3. **The floor.** Set `fail_under` at the achieved unit-only total rounded down by two points. CI runs the backend tests with `--cov=app --cov-report=term` and fails below the floor. In CI the integration tests run too, so the CI number is higher than the floor: print it, do not gate on it.
4. **Docs.** A "Coverage" section in `backend/README.md`: the command, the floor, how to read the report, the rule that a change must not lower it.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
uv run pytest -q -W error --cov=app --cov-report=term
```

## Rules for this task

- Commit as you go, in small real steps (about 10 to 16 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the coverage tables before and after, and any deviation or open question.
