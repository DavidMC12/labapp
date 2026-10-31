# Review: frontend skeleton (task 002, 2026-10-31)

- **Branch:** `w2/frontend-skeleton`, by Worker 2 (15 commits, all under `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the reviewer:** `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test` (22 tests) and `pnpm build` re-run independently; scope limited to `frontend/`; commit messages and authorship checked; the regular expression compared with the one in `docs/TESTABILITY.md`.

## Deviation accepted

TypeScript is pinned to `^6.0.3` instead of 7.0. The ESLint stack required by the task (`typescript-eslint` 8.72 through the Next.js preset) rejects TypeScript 7 and declares a peer range below 6. The pin stays until `typescript-eslint` supports TypeScript 7. Recorded in `docs/ARCHITECTURE.md`.

## Minor notes (no change required now)

- `TestIdName` is `${string}`, so the type rejects unknown modules and kinds but not casing or structure; those are enforced at runtime by `isValidTestId` and later by the lint rule and the audit.
- `Input` derives the error id with `errorTestId`, which throws for ids that do not end in `-input`. Select and textarea fields will need their own components with the same error behavior.
- `aria-busy` is rendered only while loading (`data-state` always carries the state), and the error paragraph also gets an `id` so `aria-describedby` has a target. Both match the contract.
- The Link tests mock `next/link`, which is standard for jsdom; the wrapper and `data-testid` propagation are what they cover.
