# Task 002: frontend skeleton

Assignee: Worker 2. Branch: `w2/frontend-skeleton`. Reviewer: Supervisor.

## Goal

Create the minimal Next.js project that every later screen builds on, together with the small set of UI components that make the test id contract hard to break. There is no API access, no login and no business screen yet.

## Read first

- `docs/TESTABILITY.md`: the whole file. The test id grammar, the pattern, the observable state attributes and the error conventions are the contract you implement.
- `docs/ARCHITECTURE.md`: section "Repository layout" and the description of the web app.
- `mise.toml`: the pinned Node and pnpm versions.

## Scope

You may create and edit files only under `frontend/`. Do not touch the repository root, `docs/`, `backend/` or any workflow.

## Requirements

1. **Project.** A pnpm project in `frontend/` using the latest stable Next.js (App Router), React, TypeScript in strict mode, Tailwind CSS and TanStack Query. Set the `packageManager` field to the pnpm version pinned in `mise.toml` and commit `pnpm-lock.yaml`. Scripts: `dev`, `build`, `start`, `lint`, `typecheck` (`tsc --noEmit`) and `test` (`vitest run`).
2. **Test id helpers** in `frontend/src/lib/testid.ts`:
   - `TEST_ID_PATTERN`: the exact regular expression from `docs/TESTABILITY.md`.
   - `isValidTestId(id: string): boolean`.
   - A `TestId` TypeScript type built from template literal types (the allowed modules and kinds, with optional numeric id suffix) so `tsc` rejects ids that cannot match.
   - `errorTestId(inputTestId)`: turns `customers-form-email-input` into `customers-form-email-error`; it throws for an id that does not end in `-input`.
3. **UI components** in `frontend/src/components/ui/`. Each takes a required `testId: TestId` prop and renders it as `data-testid`:
   - `Button`: a real `<button>`. A `loading` prop sets `aria-busy="true"`, `data-state="loading"` and disables the button; otherwise `data-state="idle"`. It defaults to `type="button"`.
   - `Input`: a label, an `<input>` linked with `htmlFor` and `id`, and an optional `error` message. When `error` is set, render `<p role="alert" data-testid={errorTestId(testId)}>`, set `aria-invalid="true"` and `aria-describedby` on the input.
   - `Link`: wraps `next/link` and renders `data-testid`.
4. **Hydration marker.** A client component sets `data-hydrated="true"` on `<body>` once hydrated (see `docs/TESTABILITY.md`). Mount it in the root layout.
5. **Pages.** `src/app/layout.tsx` (with the TanStack Query provider and the hydration marker; `lang="es"`) and `src/app/page.tsx` showing a heading "LabApp" with test id `app-home-heading`.
6. **Tooling.** ESLint with the Next.js and TypeScript presets, Vitest with Testing Library (jsdom). `pnpm lint` must pass with no warnings.
7. **Tests.** Cover: valid and invalid ids for `isValidTestId` (take the examples from `docs/TESTABILITY.md` and add your own), `errorTestId` including the throwing case, `Button` (test id, idle and loading states), `Input` (label association, error alert, derived error test id, aria attributes), `Link`, and the hydration marker.
8. **Docs.** `frontend/README.md` with the commands to install, run, lint, typecheck, test and build.

## Acceptance criteria

From `frontend/`, all of these pass:

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits): project init, Tailwind, providers, test id helpers, each component, hydration marker, tests, readme. Messages follow Conventional Commits, in English, for example `feat(frontend): add test id helpers`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the contract is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.

## Errata (added after the review)

- `pnpm lint` does not fail on warnings by default. The script must be `eslint . --max-warnings 0`; this is done in task 004.
- `Input` takes the props `id`, `testId`, `label` and `error`.
- `errorTestId` and `Input` only support `-input` ids without a numeric suffix; select and textarea fields and suffixed ids are added in task 004, together with the final pattern.
- TypeScript is pinned to 6.x because `typescript-eslint` does not support TypeScript 7 yet.
