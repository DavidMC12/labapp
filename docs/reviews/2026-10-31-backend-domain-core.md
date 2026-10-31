# Review: backend domain core (task 003, 2026-10-31)

- **Branch:** `w1/domain-core`, by Worker 1 (11 commits, all under `backend/app/domain/`, `backend/tests/domain/` and the README).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the reviewer:** `uv sync`, `ruff check`, `ruff format --check` and `pytest -W error` re-run independently (201 tests); scope limited to the allowed folders; commit messages and authorship checked; the rules read against SPEC sections 2, 5, 6, 7 and 8 and `docs/SEED.md`.

## What the work did well

- The permission matrix, the state machine, the rounding, the card validation and the gateway decisions match the spec; the tests reproduce the totals of the seven seeded orders, including the 5.025 tie.
- Card parsing reports every problem together, keeps only the last four digits and rejects non-ASCII digits.
- Field-level errors are checked before duplicates and the line cap, matching the order of checks.

## Minor notes (to settle in a later task)

- `compute_totals` does not quantize the subtotal or the total; this is exact while unit prices have two decimals, which the database guarantees.
- `check_stock` raises `KeyError` for an unknown product; callers must report `REFERENCE_NOT_FOUND` first.
- `GatewayDecision.outcome` is a plain string; an enum would stop callers from mistyping it.
- A transfer reference made only of spaces passed the length check; the spec now says the reference is trimmed, and the code should follow.
