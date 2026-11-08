# Task 034: frontend test coverage report, gaps and a floor in CI

Assignee: Worker 2. Branch: `w2/coverage`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 032 is merged (the supervisor tells you, or tells you to branch from `w2/confirm-dialogs`).

## Goal

The frontend has about 700 tests but nobody knows what they leave uncovered. Measure it, close the real gaps, and put a floor in CI so that coverage cannot silently fall. Do not chase 100 percent: cover behavior that matters (branches of the data layer, error and edge paths of the screens), not trivial markup.

## Read first

`frontend/package.json`, `frontend/vitest.config.*`, `frontend/README.md` (the testing section), `.github/workflows/ci.yml` (the frontend job), a few existing tests (`src/features/orders/hooks.test.tsx`, `src/app/(app)/customers/page.test.tsx`) to follow their style.

## Scope

You may edit files under `frontend/` (the Vitest configuration, `package.json` and `pnpm-lock.yaml` for one new dev dependency, new and existing test files, the README) and `.github/workflows/ci.yml` (only the frontend job's test step). **You may add exactly one dependency: `@vitest/coverage-v8`**, at the same version as the installed `vitest` (the minor version must match), as a dev dependency. Do not change application code except to fix a bug that a new test proves (then keep the fix in its own commit and describe it in the report).

## Requirements

1. **Measure.** Configure coverage with the V8 provider: include `src/**/*.{ts,tsx}`, exclude tests, `src/test/`, type-only files, the generated Next.js files and `next-env.d.ts`; reporters `text-summary` and `lcov` (the output directory is git-ignored). Add `pnpm test:coverage` (`vitest run --coverage`). Record in your report the table by folder before and after.
2. **Close the gaps.** List the ten files with the lowest line coverage among those that contain logic (data layer, parsers, hooks, formatters, pages), and add tests for their uncovered branches: error answers, empty results, boundary values, the keyboard paths, the loading and the error states. Each new test asserts behavior, not that a line ran. Keep the tests deterministic (no timers left running, no real network).
3. **The floor.** Set thresholds in the Vitest configuration at the achieved percentages rounded down by two points (lines, statements, functions, branches). CI runs `pnpm test:coverage` instead of `pnpm test` in the frontend job, prints the summary, and fails below the floor.
4. **Docs.** A "Coverage" section in `frontend/README.md`: the command, where the report goes, the floor and the rule that a change must not lower it.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm test:coverage`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem. The lockfile changes only by the one dependency and its own dependencies.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 16 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the coverage table before and after, and any deviation or open question.
