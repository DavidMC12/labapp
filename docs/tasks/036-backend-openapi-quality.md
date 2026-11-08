# Task 036: make the OpenAPI contract complete and usable

Assignee: Worker 1. Branch: `w1/openapi-quality`. Reviewer: Supervisor.

**Base.** Branch from the branch of task 030 (`w1/openapi-contract`), which commits `docs/openapi.json` and a test that fails when it drifts. After the supervisor merges 030 into `main`, branch from `main`.

## Goal

Task 030 exported the contract and found its defects. The owner will import this file into their API tools and write automation from it, so it must describe what the API really answers. Fix what you listed, without changing any behavior of the API: the same requests get the same answers; only the documentation of them changes (plus a security scheme, which documents the existing cookie).

## Read first

`docs/tasks/030-backend-openapi-contract.md` and your own report of it, `docs/SPEC.md` sections 2, 3, 7 and 8 (the problem document, the error tables, which errors every route can answer), `backend/app/errors.py` (`problem_response`, the problem members `errors`, `payment_id`, `reason`), `backend/app/main.py`, every module's `routes.py` and `schemas.py`, `backend/app/guards/` (which answers come from middleware: 400 `MALFORMED_JSON`, 403 `CSRF_ORIGIN_MISMATCH`, 413 `PAYLOAD_TOO_LARGE`, 429 `RATE_LIMITED`, 503 `SERVICE_BUSY` and `LOCK_TIMEOUT`, 500 `INTERNAL_ERROR`), `backend/tests/test_openapi_contract.py`.

## Scope

You may create `backend/app/openapi.py` (shared documentation helpers) and edit `backend/app/main.py`, every module's `routes.py` and `schemas.py` (documentation only: `responses=`, `openapi_extra`, `summary`, `description`, `tags`, `response_model` declarations that already match the real answer), `backend/tests/` (the contract tests), `docs/openapi.json` (regenerated), `backend/README.md`. **You may not change the status code, the headers, the body or the validation of any answer**: the whole unit suite must pass unchanged. No new dependencies. If a documentation fix would require a behavior change, do not make it; list it in your report.

## Requirements

1. **A `Problem` component.** One named schema `Problem` (`type`, `title`, `status`, `code`, `detail`, optional `errors` as a list of `FieldError` `{field, code, message}`, and the optional `payment_id` and `reason`), served as `application/problem+json`, referenced by every error answer instead of the 121 inlined copies. The module-level `_PROBLEM_SCHEMA` dictionaries go away.
2. **Answers that apply to every route.** Every operation documents the answers that any route can give: 400 `MALFORMED_JSON` (only for operations with a body), 401 `UNAUTHENTICATED` (for protected operations), 403 `CSRF_ORIGIN_MISMATCH` (for POST, PATCH, PUT and DELETE), 413 (with a body), 429, 500 and 503. The answers specific to an operation (404, 409, 422 and the business codes) are documented only where the SPEC says the operation can give them: no 409 on a plain read. Each answer's description names the stable codes it can carry (from the SPEC tables).
3. **Security.** A `cookieAuth` security scheme (`apiKey` in `cookie`, name `labapp_session`) applied to every protected operation; the public ones (`POST /api/auth/login`, `GET /api/health`) carry no security. `POST /api/auth/logout` is public in the SPEC (idempotent): keep it as the SPEC says.
4. **Payment body.** `PaymentCreate` is a component (method, amount, card, reference) with the amount pattern `^[0-9]{1,10}(\.[0-9]{1,2})?$`, the card object with its three fields, and a description of which fields each method needs. The pay route still receives the raw body (the service validates, as in task 019); the component only documents the shape (through `openapi_extra`).
5. **Money and ids.** Money fields keep `type: string` and gain the pattern `^[0-9]+\.[0-9]{2}$` and an `example`; the tax rate likewise; ids and versions keep their integer bounds where the SPEC gives them.
6. **Servers and metadata.** `info.title`, `info.version` (read from the package version), a short `info.description` pointing to the SPEC, tags per module with a description, and `servers` with one relative entry `{"url": "/"}` (the web app and the API share one origin online and locally).
7. **Tests.** Extend `test_openapi_contract.py`: no inline problem objects (every error response references `#/components/schemas/Problem`), the `Problem` and `FieldError` shapes, the common answers by method and protection, the security scheme and which operations carry it, the `PaymentCreate` component, the money pattern on every money field, and that every `$ref` resolves. Regenerate `docs/openapi.json` with the command of task 030; the drift test must pass.
8. **Docs.** Update the "OpenAPI contract" section of `backend/README.md` (what a reader can rely on in the file).

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
uv run python -m app.cli openapi --output ../docs/openapi.json && git diff --exit-code ../docs/openapi.json
```

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, anything you could not document without a behavior change, and any deviation or open question.
