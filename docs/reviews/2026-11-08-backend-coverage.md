# Review: backend coverage floor (task 035, 2026-11-08)

- **Branch:** `w1/coverage`, by Worker 1 (15 commits, tests, `pyproject.toml`, CI step and README only: `git diff` of `backend/app` is empty).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and `pytest -q -W error --cov=app --cov-report=term` in a detached checkout, all exit 0: 1594 passed, 211 skipped (integration), coverage 87.71 % against the floor of 85 %. A script found no new test without an assertion (202 tests). The reset tests check the restored state module by module, not only that the code runs.
- **Also in this task:** the strict `xfail` in `tests/docs/test_field_errors.py` is replaced by a real test that every message of the SPEC section 7 table appears in the application source.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The floor gates only the unit-only total; the CI run (with PostgreSQL) prints a higher number that is not gated. | Accepted by design; the number is printed in the log. |
| 2 | Minor | The field-message test matches a SPEC placeholder (`{min}`) against any f-string expression, not the exact variable name. | Accepted: the names differ in the code (`minimum`, `MAX_ID`) and the message text is what matters. |
