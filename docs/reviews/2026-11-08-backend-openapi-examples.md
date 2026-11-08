# Review: request and response examples in the OpenAPI contract (task 054, 2026-11-08)

- **Branch:** `w1/openapi-examples`, by Worker 1 (11 commits, plus 4 for the review feedback).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge after the fixes below. No Critical findings.
- **What it does:** named request examples for login, customers, orders, lines, settings and the four payment bodies (`card-approved`, `card-declined`, `transfer`, `cash`), response examples for the created customer, order and invoice and the approved and declined payment (the JSON of SPEC section 6, field by field), and one shared problem example per status (401, 403, 404, 409, 422). The values live once in `app/openapi_examples.py`; the routes declare them and the tests import the same objects; `install_openapi` re-applies the canonical examples after FastAPI generates the document so that `null` members survive.
- **Verified by the supervisor:** `ruff check`, `ruff format --check` and the unit suite with the coverage floor exit 0 (1785 passed). A live check against a server started from the branch: the examples of login, customer creation (minimal and full), order creation, line addition and the tax rate were sent as written and answered as documented; the contract served at `/api/openapi.json` equals the committed `docs/openapi.json`.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The one shared 409 example was `VERSION_CONFLICT` on every operation, including `POST /api/customers`, whose real 409 is `CUSTOMER_EMAIL_TAKEN` (there is no version when creating). | Fixed by Worker 1: a `CUSTOMER_EMAIL_TAKEN` example for that route only. |
| 2 | Important | Found by the new test that Worker 1 added for finding 1: the 403 example of login and logout was a permission error, while the real 403 there is `CSRF_ORIGIN_MISMATCH`. | Fixed by Worker 1. The test now checks every problem example against the codes the description of its response names, so this class of error cannot return. |
| 3 | Note | The `/__test__/...` routes are not in the contract, so they carry no examples. | Accepted: the brief made them conditional; they are documented in the automation guide. |

## Lesson

My first live check went to the wrong server: a worker's development server held the port, mine failed to start, and the request answered from the worker's branch. Check that the process that answers is the one just started (use a free port of your own).
