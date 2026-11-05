# Review: backend customers (task 010, 2026-11-04)

- **Branch:** `w1/customers`, by Worker 1 (19 commits plus 2 fixes, all inside `backend/`).
- **Reviewer:** Supervisor. The brief itself went through the background Reviewer before the work started (9 Important findings fixed).
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the supervisor:** the acceptance commands re-run with real exit codes (624 tests with warnings as errors, lint and format clean); the customer tests run three times in a row to look for flakiness in the two-thread version race; a live probe script against the real application (all four roles, check order, list edge cases, `If-Match` forms, ETag and Location); the same checks on a clean clone before pushing.

## What the work did well

The port is written for PostgreSQL (atomic add with a unique lowercase email, row lock on update, literal `q`, normalized search columns written at write time, id reset in `replace_all`) and the same contract tests can run against the SQL adapter. Permission, then existence, then body validation, then version holds, including for an unknown id with an invalid body. The seed matches `docs/SEED.md`. A stale `If-Match` is a conflict even when the status already matches.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | An `If-Match` of more than 4300 digits made `int()` raise and the API answered 500. | Fixed: the length is checked before converting, and the 5000-digit, 11-digit and valid maximum cases are tested for both status routes. |
| 2 | Important | The address rejected line breaks, though it is entered in a multi-line field. The cause was a rule in the spec, not the worker. | The spec now allows `\n` and `\r\n` (stored as `\n`) in `address` only; fixed and tested, other fields keep rejecting every control character. |

Deferred: a malformed JSON body answers 422 with the field `[1]` instead of 400 `MALFORMED_JSON` (task 008a); a `q` made of a tab is rejected as a control character, as the spec says; the in-memory adapter and the app clock are per process, so the PostgreSQL adapter is the next task.
