# Review: local start script, test id audit, Vercel configuration and docs (2026-11-05)

- **Branches merged:** `feat/dev-script`, `feat/testid-audit`, `feat/vercel-config`, `docs/all-on-vercel` and `docs/orders-api` (the Orders API of the spec and the briefs of tasks 015 to 017), plus the fixes below.
- **Reviewer:** a second agent, in the background, over the whole combination.
- **Verdict:** With fixes, no Critical findings; the Important findings were fixed before the merge.
- **Verified by the supervisor:** the local start script run for real (login through the single-origin proxy, both ports freed on stop, and the web server confirmed unreachable on the machine's LAN address after the fix); the audit run against the frontend (0 problems over 33 files) and its 13 node tests; the five frontend commands and the backend suite re-run with real exit codes; the 52 PostgreSQL integration tests re-run against a real database, including a new test that runs two migrations at the same time; the same checks on a clean clone before pushing.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | `next dev` listens on all interfaces by default, so the dev server (test mode, a public development secret, the proxy to the test controls) was reachable from the local network. | Fixed: `--hostname 127.0.0.1`, checked from the LAN address; the script also warns when `backend/.env` sets a database and refuses bash older than 4.3. |
| 2 | Important | The audit accepted any identifier ending in `testId` without checking its value, and never scanned `.ts` files, so a malformed id in a constant or a data file passed. | Fixed: every `...TestId` constant and `testId:` property is checked wherever it is written, `.ts` files are scanned, hidden inputs are exempt; negative tests added, including a failing tree. |
| 3 | Important | The docs stated future behavior as fact (the `/__test__` routes, the origin check using the platform variables, the guard answering 404, `TEST_MODE` effects) and gave a wrong reason for the no-memory rule. | Fixed: each is marked as planned, the post-deploy checklist moves them to "once the test controls exist". |
| 4 | Important | The build hook migrated on every build, previews included, against a shared database: an unmerged migration would change the production schema, and two builds could race. | Fixed: a `deploy --production-only` command skips preview deployments (opt in with `RUN_MIGRATIONS_ON_PREVIEW=1`), and migrations take an advisory lock; tested with two concurrent processes. |
| 5 | Important | The spec's rule for the `field` of body errors contradicted its own unknown-field rule. | Fixed: the two exceptions are stated (the unknown field's own name, and `body`). |
| 6 | Minor | The default tax rate was never validated or quantized (`150` would break the first read; `10` serialized as `"10"`). | Fixed in `Settings` with tests. |
| 7 | Minor | Several small contradictions and gaps in the spec and the briefs (the no-op ordering, the frozen rate on cancel, the allowed origins of the platform, a number input that cannot show a server message, test id and audit rules for the new screens, a guard path match, a middleware order that is the reverse of the call order, an unnecessary auth fixture), and the README and the env example disagreeing with the development guide. | Fixed. |

Deferred: the audit does not yet follow `createElement`, aliased components or interactive `div` elements (the browser audit of the contract will); `vercel.json` has never been deployed, so the first deployment is also its test; the process-group handling of the start script is verified for the normal stop and not for every failure mode.
