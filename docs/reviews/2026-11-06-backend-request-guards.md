# Review: backend stateless request guards (task 017, 2026-11-06)

- **Branch:** `w1/request-guards`, by Worker 1 (23 commits, all inside the folders the brief allowed).
- **Reviewer:** Supervisor. The brief was reviewed twice by a second agent (3 Critical and 11 Important findings, verified and fixed before the work started). This is security code and no second-agent pass of the code itself was run; the code is small, was read in full, and was checked by driving a real server (below). A pass over the whole request pipeline can still be asked for later.
- **Verdict:** Ready to merge in round 1, with one integration fix of the supervisor. No Critical or Important findings.
- **Verified by the supervisor:** the four acceptance commands with real exit codes on the branch merged onto the current `main` (1023 passed, 52 skipped without a database); the guards, the middleware changes, the settings and the container read in full; **a real server** driven with `curl`: malformed JSON gives 400 `MALFORMED_JSON`; a foreign origin gives 403 and the configured origin and a platform preview origin (`https://` plus `VERCEL_URL`) give 200, while the same host over `http` gives 403; a 200 KB body gives 413 both declared and chunked; every method, a trailing slash, a bad body and a big chunked body sent to `/__test__` without the token all give the same 404; ten logins pass and the eleventh gives 429 with `Retry-After` and a request id, the bucket follows the rightmost `X-Forwarded-For` entry (a different leftmost entry stays in the same bucket) and another address is unaffected; the test token exempts from the limits; the health check is never limited; the same checks on a clean clone before pushing.

## What the work did well

The middlewares are in the order of SPEC section 7 (request id, rate limit, controls guard, body size, application) and a test proves each pair of the order. The streaming size limit raises Starlette's `HTTPException(413)` from the wrapped `receive`, which FastAPI turns into the problem document; the controls guard is an ASGI middleware, so a probe cannot tell the routes exist by their method, a redirect or a body error. The origin check accepts the configured origin and the platform preview origins, validated to be exactly `scheme://host[:port]`. The rate limiter gained a bound on the number of tracked keys and a `clear()`; `X-Forwarded-For` lines are joined before the client address is taken.

## Findings

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The module-scoped orders tests (merged from task 015 after this task started) share one client address and would hit the 120-request and 10-login limits once the limits are enforced. The worker flagged it; it could not fix a file that did not exist in its base. | Fixed by the supervisor at the merge: the same autouse fixture that resets the limiters as in the customers tests. |

Deferred: the limiters are per process, so on the serverless deployment they are best effort (documented); a shared state in PostgreSQL comes with the stateful test controls task.
