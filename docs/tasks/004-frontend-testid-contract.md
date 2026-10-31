# Task 004: frontend test id contract update

Assignee: Worker 2. Branch: `w2/testid-contract`. Reviewer: Supervisor.

## Goal

Bring the frontend skeleton in line with the final test id grammar in `docs/TESTABILITY.md`, and make the field components cover every field kind. The first skeleton only supported `-input` fields and an older, looser pattern.

## Read first

- `docs/TESTABILITY.md`: the whole file, especially the pattern, the "Which kind to use" table and the rules about numeric suffixes.
- `frontend/src/lib/testid.ts` and `frontend/src/components/ui/`: what exists today.
- `docs/tasks/002-frontend-skeleton.md`: the previous task, including its errata.

## Scope

You may create and edit files only under `frontend/`.

## Requirements

1. **Pattern.** Replace `TEST_ID_PATTERN` with the exact expression in `docs/TESTABILITY.md`, and update the doc comment that repeats it. Every word of the name now starts with a letter, so a numeric record id can only be the final suffix after the kind.
2. **Tests for the pattern.** Update the existing tests: `invoices-3-alert` is no longer valid. Add valid cases (`orders-line-quantity-input-7`, `customers-list-row-42`) and invalid cases (`orders-line-7-quantity-input`, `customers-list-row-42-view-button`, an id ending in `-input-x`, a trailing dash).
3. **`errorTestId`.** Accept ids whose kind is `input`, `select` or `textarea`, with or without the numeric suffix, and return the id with the kind replaced by `error`, keeping the suffix: `customers-form-email-input` becomes `customers-form-email-error` and `orders-line-quantity-input-7` becomes `orders-line-quantity-error-7`. It throws for any other kind. Update its tests.
4. **Field components.** Add `Select` and `Textarea` in `src/components/ui/`, with the same behavior as `Input`: a label linked with `htmlFor` and `id`, a required `testId`, an optional `error` rendered in a `role="alert"` paragraph with the derived error test id, and `aria-invalid` and `aria-describedby` on the control. `Select` renders a native `<select>` and takes its options as children. Write tests for both. Keep `Input`'s public props unchanged.
5. **Lint.** The `lint` script must fail on any warning: `eslint . --max-warnings 0`.
6. **README.** Update `frontend/README.md` so its "test id" section points to the table in `docs/TESTABILITY.md` instead of repeating it, and lists the available components.

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

- Commit as you go, in small real steps (about 8 to 10 commits). Messages follow Conventional Commits, in English, for example `feat(frontend): add Select component`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the contract is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
