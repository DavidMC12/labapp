# Review: tests that keep the practice catalog true (task 056, 2026-11-08)

- **Branch:** `w1/practice-tests`, by Worker 1 (8 commits, tests only: `backend/tests/docs/`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it does:** a parser of the 121 scenario rows of `docs/PRACTICE.md` and four checks that run on every test run: every error code quoted in backticks exists in SPEC section 7 or in the application; every Spanish message quoted in an `Expected` cell exists in the application (the error tables, the field messages, the source of the backend and the frontend); every `METHOD /path` of a `Steps` cell exists in the OpenAPI document (a literal id matches an `{id}` template and nothing else does, so `/api/customers/export` does not fall into `{id}`) or is a test-control route; and the status that starts an `Expected` cell is declared for the operation. Failures name the row (`PRACTICE B-12: the code 'ORDER_EMPTYY' is not defined`). Coverage of each check: 77 rows with codes, 63 with messages, 108 endpoint references in 83 rows, 36 rows with a status.
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and the unit suite with the coverage floor exit 0 (1817 passed); the new file runs in about half a second. Then a mutation test on the real catalog: a wrong code (`ORDER_EMPTYY`), a wrong Spanish message, a wrong endpoint (`/api/customers/11/disable`) and a wrong status (`418`) were each reported with the right row; the file was restored.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | The seven `/__test__` routes are read from the table of the automation guide, because the SPEC does not list them. | Accepted: the guide is where they are documented; moving them to the SPEC is a later cleanup. |
| 2 | Note | The message check also scans `frontend/src`, because several rows quote screen messages. | Accepted. |
| 3 | Note | A few tokens are excluded on purpose (`ACME`, `CARD_DECLINED`, `GATEWAY_UNAVAILABLE`, the HTTP verbs); each has a comment. | Accepted. |
