# Review: backend PostgreSQL adapters (task 014, 2026-11-05)

- **Branch:** `w1/postgres-adapters`, by Worker 1 (19 commits, all inside `backend/`).
- **Reviewer:** Supervisor. The brief carried every finding of the earlier second-agent review of the PostgreSQL work (raw SQL ignoring the schema, values leaking through database error messages, contract tests that cannot run on PostgreSQL as written).
- **Verdict:** Ready to merge in round 1. No Critical or Important findings.
- **Verified by the supervisor:** the four acceptance commands re-run with real exit codes (680 passed, 51 skipped without a database, lint and format clean); the adapters, the helpers, the error logging change and the wiring read in full; **the 51 integration tests run against a real PostgreSQL 18 database** (a random schema per run, an engine without the pinned search path for the adapters, so any unqualified raw SQL would have failed against the empty `public` schema), all passing on the first run, with the three contract classes, the concurrency tests (two threads racing an update, two racing creates with the same email, 20 concurrent session creates with a cap of 5) and the seed run twice; the same checks on a clean clone before pushing.

## What the work did well

Each port method is one transaction; the customer update locks the row first and checks in the documented order; the unique violation is mapped by the name of the violated index, in `add` and also in `update`, so a concurrent create of the same email gives `EmailTaken` instead of an unhandled error. The session cap serializes through a transaction-level advisory lock, which survives a transaction-mode pooler, and replaces an existing token like the in-memory store. `touch` is monotonic in SQL. Raw SQL names its schema through one helper. Unhandled database errors are logged with their class, SQLSTATE and request id only, never with the message that carries the offending values, and a test proves it. Creating the application and the health check open no connection, and the seed command is idempotent.

## Findings

None that block. Noted and deferred: the unit suite relies on the integration run for the real behavior of the SQL (run in CI later with a service database), and the database `lower()` of non-ASCII emails depends on the server locale (the application already lowercases emails before storing them, so the index compares already-lowercase text).
