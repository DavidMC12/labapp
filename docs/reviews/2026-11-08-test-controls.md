# Review: test controls, OpenAPI contract and hardening (tasks 022, 024, 030, 036, 037, 2026-11-08)

- **Branches:** the stack `w1/request-controls` (022), `w1/test-controls-api` (024), `w1/openapi-contract` (030), `w1/openapi-quality` (036) and `w1/controls-hardening` (037), by Worker 1 (about 80 commits, inside `backend/` and the documents named in the briefs), plus three small test fixes by the supervisor. Merged together as `w1/controls-hardening`.
- **Reviewers:** the supervisor, and for 022 and 024 a **second agent** (a Claude process in the background, read-only, security focus) because this code can erase a database.
- **Verdict:** With fixes (round 1), all fixed in task 037, then ready to merge. No Critical findings.

## What the second agent found, and what happened

No way for a request without the token to reach a control or erase data (two guard layers that fail closed, constant-time token comparison, the path variants checked, the right middleware order, one transaction with an advisory lock for the reset, Core statements only, the decoy schema test). Findings, each checked against the code by the supervisor:

| # | Severity | Finding | Disposition |
|---|---|---|---|
| I1 | Important | A failed reset left the sequences restarted while the data rolled back (`setval` is not undone by a rollback), so the next insert collided until another reset succeeded. | Fixed in 037: every `replace_all` takes `defer_sequences`; the resetter runs all restarts as the last statements of the transaction. The failing-step tests assert the sequence values do not change. |
| I2 | Important | The atomicity test could not tell one transaction from five and no test injected a failing step. | Fixed in 037: it starts from a non-empty state and polls one statement with several counts; failing data step and failing deferred step tests added. |
| I3 | Important | Database errors raised inside the request controls middleware bypassed the error handlers (a lock timeout became a 500 and the driver message was logged). | Fixed in 037: the middleware answers 503 `LOCK_TIMEOUT` or a generic 500 and logs only class, SQLSTATE and request id. |
| M1 to M7 | Minor | Guard path vs routing path, the reset 409 mapping and logging, rule path validation, cost of the middleware on non-API paths, the CLI host check and abbreviations, `TEST_MODE` refusal on Lambda, small points. | All fixed in 037 (10 numbered fixes, each with tests). |

## Verified by the supervisor

- The four backend commands re-run with real exit codes on the tip merged with `main` (ruff, format, `pytest -q -W error`: 1465 passed, 211 integration tests skipped without a database) and the contract command (`app.cli openapi` writes `docs/openapi.json` with no difference).
- **The whole integration suite (211 tests) against a real PostgreSQL 18 on Neon**, twice during the work: the 022 stack (201 passed) and the full stack after 037. The second run showed 4 failures, all **defects of the new tests, not of the application**: the snapshot listed a sequence that does not exist (`products_id_seq`, products have explicit ids), a test read the stored response body with a wrong key, and one slice of the order links was wrong. Fixed by the supervisor; the 10 reset tests then pass, including the failing-step rollback tests with unchanged sequences.
- The controls driven over real HTTP (a real server with `TEST_MODE=0` and a token): reset without a token and with a wrong one is 404, `HEAD` is 404, with the token 200; the clock advances one hour; a boolean or a 20 year advance is 422; a fault of status 500 with `times` 2 gives 500, 500, then 200; a rule path under `/__test__` is 422; `seed` `empty` leaves 0 customers, `reset` restores 10, keeps the session (the login cookie still works) and puts the clock back to 0.
- The commit rules over the 82 commits of the stack.

## Not verified

- Behavior on Vercel (nothing is deployed yet); the notes on `VERCEL_ENV` and `AWS_LAMBDA_FUNCTION_NAME` are from the documentation.
