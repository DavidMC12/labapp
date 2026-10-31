# Review: frontend test id contract (task 004, 2026-10-31)

- **Branch:** `w2/testid-contract`, by Worker 2 (10 commits, all under `frontend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the reviewer:** `pnpm install --frozen-lockfile`, `pnpm lint` (now failing on warnings), `pnpm typecheck`, `pnpm test` (37 tests) and `pnpm build` re-run independently; scope limited to `frontend/`; commit messages and authorship checked; the regular expression in `src/lib/testid.ts` compared character by character with the one in `docs/TESTABILITY.md` (identical).

## What the work did well

- `errorTestId` keeps a numeric suffix (`orders-line-quantity-input-7` becomes `orders-line-quantity-error-7`) and rejects other kinds.
- `Input`, `Select` and `Textarea` share one `Field` wrapper, so label, alert and ARIA wiring cannot drift apart. `Input`'s public props did not change.
- The tests cover valid and invalid ids from the grammar, including the old cases that became invalid.

## Minor notes (no change required now)

- The `TestId` type still accepts any string between module and kind (casing and word structure are checked at runtime by `isValidTestId`, later by the lint rule and the audit).
- `errorTestId` accepts the kinds `input`, `select` and `textarea` only; a checkbox with an error would need its own rule when the first screen requires one.
