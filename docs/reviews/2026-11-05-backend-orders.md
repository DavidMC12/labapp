# Review: backend orders, products and settings (task 015, 2026-11-05)

- **Branch:** `w1/orders`, by Worker 1 (22 commits, all inside `backend/app/modules/orders/`, `backend/tests/orders/`, `backend/app/main.py` and the README).
- **Reviewer:** Supervisor. The brief and the "Orders API" subsection of the spec were reviewed twice by a second agent before and during the work (3 Critical and 11 Important findings, all verified against the code and fixed in the brief and the spec).
- **Verdict:** Ready to merge in round 1. No Critical or Important findings.
- **Verified by the supervisor:** the four acceptance commands re-run with real exit codes on the branch merged onto the current `main` (936 passed, 52 skipped without a database, lint and format clean); the in-memory store read in full and the service and schemas read in part; **the API driven end to end through HTTP** against the contract of the spec: the literal example of an order after adding a line matched byte for byte (ids, totals, `ETag`, version), a 422 with the `quantity` field (never a `lines[0]` path), strict integers (`"5"`, `5.0` and `true` rejected), a huge `product_id` as `REFERENCE_NOT_FOUND`, the tax rate patterns including `"10\n"`, a stale version, a no-op, the permission of every role, a 5000-digit `If-Match` answering 422 and not 500, the seed totals (the `5.03` rounding tie of the seventh order), a cancelled draft keeping its frozen rate and totals after the rate changed, a confirm with two short products listing both in `shortages`, the inactive-customer and invalid-transition errors, the list filters and the id and paging edge cases.

## What the work did well

It followed the layering of the customers module and the deliberate rules of the brief literally: the store raises its own exceptions only for what the domain does not already express, and the domain's `ApiError` for duplicates, the line cap, invalid transitions, empty orders and stock propagate unchanged. The order of the checks inside each store method is the one of the spec (existence, line, references, version, editability, customer active, then the business rules and the no-op case). Both cancels freeze the tax rate, so a cancelled order never has an undefined rate. The examples of the spec are reproduced as literal expected bodies in a test, so the screens built in parallel from the same spec cannot drift from the backend.

## Findings

None that block. Deferred by design: the PostgreSQL adapter of the order store (the port documents the locking order and the atomic confirm; it is a later task), the cancel of a confirmed order voiding its invoice (the invoices task), and the `paid` transition (the payments task).
