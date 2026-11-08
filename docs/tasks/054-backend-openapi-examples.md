# Task 054: request and response examples in the OpenAPI contract

Assignee: Worker 1. Branch: `w1/openapi-examples`. Reviewer: Supervisor.

**Base.** Branch from `main` (task 050 is merged). If task 052 is still unmerged when you start, branch from `w1/csv-export`.

## Goal

The contract at `/api/openapi.json` and the Swagger page at `/api/docs` describe every route, but a person who opens "Try it out" sees an empty body or a generic placeholder. A test engineer who imports the contract into Postman, Bruno or Playwright's request fixture should get a body that works. Add named, realistic examples to the requests and the answers, taken from the specification, and prove with tests that they are true. No behavior changes.

## Read first

`backend/app/openapi.py` (the shared documentation helpers: how the responses are described today and how the money, id and rate schemas carry an `example`), the schemas of the modules (`schemas.py` of customers, orders and invoices) and how the routes take their bodies (several routes read a raw body and validate it in the service: read how the request body is described in the contract today), `docs/SPEC.md` sections 4, 5 and 6 (the JSON examples of the Orders API and of the payment, exact), section 7 (the error format and the stable codes), `docs/SEED.md`, `backend/README.md` (the contract section: how `docs/openapi.json` is generated and checked).

## Scope

You may edit under `backend/`: `app/openapi.py`, the route declarations and schemas of the modules (documentation only), the tests, `backend/README.md` (one sentence), and `docs/openapi.json` regenerated with the command the README gives. Do not edit `docs/SPEC.md`, the frontend, `tools/` or `tests/`. No new dependency. No change to a status code, a message, a validation rule or a header.

## Requirements

1. **Request examples**, as named OpenAPI examples (`examples` of the request body media type, a dictionary `name -> {summary, value}`), for: `POST /api/auth/login` (the admin demo user: the password is public, it is printed on the login screen), `POST /api/customers` (a minimal body and a full one), `PATCH /api/customers/{id}`, `POST /api/orders`, `PATCH /api/orders/{id}`, `POST /api/orders/{id}/lines`, `PATCH /api/orders/{id}/lines/{line_id}`, `PATCH /api/settings`, and `POST /api/invoices/{id}/payments` with four named examples: `card-approved` (the card body of the specification), `card-declined` (the number whose last four digits are `0002`), `transfer` (a reference) and `cash`. If the test-control routes (`/__test__/...`) are in the contract, give them one example each (`reset` needs none; `clock` advance, a fault rule, `seed` with `default` and `empty`).
2. **Response examples**: `201` of a customer, an order and an issued invoice; the approved payment result (`201`) exactly as the JSON example of SPEC section 6; the declined one (`402`); one example of the problem body for each of `401`, `403`, `404`, `409` (a version conflict) and `422` (a validation error with an `errors[]` entry) with the real codes and Spanish messages of section 7. Reuse one example per common problem, not one per route.
3. **Where the examples live.** Write each example once, as a Python value in one module (for example `app/openapi_examples.py`) and reference it from the routes, so that a test can import the same values. Keep the examples consistent with the seed (`docs/SEED.md`): ids, names, numbers and amounts that exist after a reset.
4. **Tests that make the examples true.**
   - Every request example is sent to the application (the in-memory test app with the seed) as the documented operation, with the right role, and answers the status the example is meant for (`2xx` for the working examples, 402 for `card-declined`). Where the operation needs state (an order in a given status), set it up first through the API.
   - Every response example validates against the response model of its route (use the Pydantic model or `TypeAdapter`, not a hand-written check).
   - The payment `card-approved` request and its `201` answer equal, field by field, the examples written in `docs/SPEC.md` section 6 (read the JSON blocks out of the SPEC in the test, with the helpers of `backend/tests/docs/support.py` if they fit).
   - The generated contract contains the examples (a test over `app.openapi()` for each route above).
5. **Regenerate `docs/openapi.json`**; the drift test passes. Open `/api/docs` with the app running and confirm the "Try it out" body is filled (say how you checked; a `curl` of `/api/openapi.json` and a look at the media type `examples` is enough if you cannot use a browser).
6. **README.** `backend/README.md`: one sentence in the contract section about the examples and where they live.

## Acceptance criteria

From `backend/`: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest -q -W error --cov=app --cov-report=term` pass (the coverage floor holds). The supervisor re-runs a sample of the request examples with `curl` against a live server.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the list of routes that now carry examples, and any deviation or open question.
