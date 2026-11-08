# Review: automation guide, part 2 (task 043, 2026-11-08)

- **Branch:** `w2/automation-guide-api`, by Worker 2 (11 commits, documentation only: part 2 of `docs/AUTOMATION_GUIDE.md`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge, with one fix by the supervisor. No Critical or Important findings.
- **Verified by the supervisor, by running what the guide says against a real server:**
  - the three flows through the API (login, create a customer, create a draft order, add a line, confirm with `If-Match`, issue the invoice, pay with the approved card): every status code, `Location`, `ETag`, number (`PED-0008`, `FAC-0004`), total (`43.78`), version and payment id (5) is exactly as documented, and the order ends `paid`;
  - the clock recipes: advancing 28,801 seconds makes the next request answer 401 `SESSION_EXPIRED`, and putting the offset back makes the same cookie work again; the card expiry recipe (`12/30`, then a cumulative advance) is accepted at first and then answers 422 `CARD_EXPIRED` on `card.expiry`;
  - earlier in the day, the controls guard, the faults (`times`, exhaustion, list, clear), `seed`, `reset` and the validation limits over real HTTP;
  - the documentation linter on the guide (links and ids) and the commit rules.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The guide said the running API serves the contract at `/openapi.json`; after task 041 it is `/api/openapi.json`, with the Swagger UI at `/api/docs`. | Fixed by the supervisor. |
