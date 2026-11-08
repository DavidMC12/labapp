# Review: frontend coverage report and floor (task 034, 2026-11-08)

- **Branch:** `w2/coverage`, by Worker 2 (14 commits, inside `frontend/` plus the frontend test step of `ci.yml`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:**
  - the commands re-run with real exit codes in a detached checkout: install, lint, typecheck, `pnpm test:coverage` (statements 97.6 %, branches 93.19 %, functions 99.5 %, lines 97.56 %; the floor of 95, 95, 97 and 90 holds), build, and the test id audit (0 problems);
  - the commit rules; the lockfile and `package.json` gain only `@vitest/coverage-v8` (pinned to the version of Vitest);
  - the CI diff: the frontend job runs `pnpm test:coverage` instead of `pnpm test`.
- **Result:** the frontend was already well covered; the worker added tests for the lowest files (the customer form, formatting helpers, the invoice detail, the theme module) and left unreachable defensive branches uncovered on purpose, as the brief asked.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The floor was computed as the achieved value minus two points, floored. | Accepted: it is what the brief said; the floor holds with margin. |
| 2 | Minor | `ConfirmDialog.tsx` keeps two uncovered lines (a forwarded ref object nobody passes, a null guard). | Accepted. |
