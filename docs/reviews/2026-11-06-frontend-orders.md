# Review: frontend orders screens (task 016, 2026-11-06)

- **Branch:** `w2/orders-ui`, by Worker 2 (28 commits, all inside `frontend/` plus the merged documentation).
- **Reviewer:** Supervisor. The brief was reviewed by a second agent before and during the work; its corrections reached the implementer by message and were applied.
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the supervisor:** the five frontend commands re-run with real exit codes on the branch merged onto the current `main` (385 tests, zero lint warnings, typecheck, production build); the static test id audit; **the frontend's own API layer run against the real backend** (the orders of task 015) through the local single-origin proxy with a temporary test: list and filters, create, add a line, change a quantity, move the customer, remove a line, `ORDER_EMPTY`, `INSUFFICIENT_STOCK` with its shortages, cancel with the frozen rate, `INVALID_TRANSITION` and the `quantity` field name of a 422, all matching the types and the mocks; **real screenshots** of the list, the new-order page, a draft with lines and a confirmed order, on desktop and on a 390px phone, before and after the fixes; the same checks on a clean clone before pushing.

## What the work did well

The data layer follows the customers pattern (numeric ids parsed once, URL list state with fallbacks, `setQueryData` before navigating, a refetch after every failed mutation) and the corrections of the review: every mutating control of the detail page is disabled while any mutation is pending, a quantity is sent as a number, as the typed text when it is not digits-only, and as an empty-field error when empty; the customer picker never holds an id the select does not show; the products and the picker have loading, empty and error states. Every id of the table of the brief exists, and the money and date formats follow the spec.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The static audit (added to main after the task started) reported three elements without a test id: the per-row quantity form and two `h2`. | Fixed with `orders-detail-line-form-{line}`, `orders-detail-lines-heading` and `orders-detail-addline-heading`. |
| 2 | Minor | The orders list table and the lines table did not fill their container. | Fixed with `w-full` inside the scroll wrapper. |
| 3 | Minor | The per-row quantity label repeated visibly in every row. | Fixed: `hideLabel` on `Field` and `Input` keeps the linked label and hides it visually (`sr-only`), with tests. |
| 4 | Minor | The orders list footer had no id while the customers list footer has one. | Fixed: `orders-list-footer-item`. |

Deferred: the customer picker shows at most 20 active customers (stated on screen, with a search); the per-row editors make the lines table wide on a phone, where it scrolls inside its wrapper.
