# Review: backend PostgreSQL order store (task 018, 2026-11-06)

- **Branch:** `w1/postgres-orders`, by Worker 1 (16 commits, all inside `backend/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge in round 1. No Critical or Important findings.
- **Verified by the supervisor:** the branch merged onto the current `main` without conflicts; lint clean and 1031 unit tests passing with warnings as errors; **the 127 integration tests run against a real PostgreSQL 18 database** (a random schema per run, an engine without the pinned search path), all passing on the first run in 11 minutes 49 seconds, including the order-store contract, every table constraint and unique index, the seed run twice, the sequence behavior, and the concurrency tests: the same order confirmed twice (one wins, the stock decremented once), two orders competing for the last units of a product (never below zero), two orders with the same two products in opposite order confirmed at the same time (no deadlock), a cancel racing a confirm, and a customer deactivated by another transaction between the lock and the check.

## What the work did well

One transaction per method; the lock order of the spec (order, then customer `FOR SHARE`, then products in ascending id) in every method that needs more than one; the checks after the locks and in the documented order, with the domain's own errors propagating; the order number from a database sequence (gaps allowed, repeats impossible); schema-qualified raw SQL for the sequences; the check constraint names wrapped in `op.f(...)` (the lesson of task 012 was applied without being asked twice).

## Findings

None. Noted: the worker's context was at 85% by the end of the task, so its session is restarted before the next one.
