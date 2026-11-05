# Task 010: backend customers module

Assignee: Worker 1. Branch: `w1/customers`. Reviewer: Supervisor.

## Goal

Implement the customers API of flow 1, exactly as the "Customers API" subsection of `docs/SPEC.md` describes it, on top of the authentication core. Storage goes through a port with an in-memory adapter (a test double and development aid): the production deployment is serverless with PostgreSQL, so the port must be written so that a PostgreSQL adapter can honor its atomicity rules later without changing the service or the routes.

## Read first

- `docs/SPEC.md`: section 4 (customers: fields, rules, errors and the "Customers API" subsection), section 5 "Concurrency" (`version`, `ETag`, `If-Match`), section 7 (error catalog, labels and the order of checks) and section 8 (formats and list rules).
- `docs/SEED.md`: the ten seeded customers.
- `backend/app/modules/auth/` (`routes.py`, `dependencies.py`, `container.py`, `adapters/memory.py`) and `backend/app/main.py`: the structure to copy.
- `backend/app/errors.py` (`ApiError`), `backend/app/domain/permissions.py` (`Action.MANAGE_CUSTOMERS`) and `backend/app/infra/clock.py`.

## Scope

You may create files under `backend/app/modules/customers/` and `backend/tests/customers/`; edit `backend/app/main.py` only to wire what this task adds; and add a short "Customers" section to `backend/README.md`. Every new folder needs an `__init__.py`. Do not change anything else (in particular not the auth module). No new dependencies.

## Requirements

1. **Model** (`models.py`). A frozen dataclass `Customer` (`id: int`, `name`, `email`, `phone: str | None`, `tax_id: str | None`, `address: str | None`, `status: CustomerStatus`, `version: int`, `created_at: datetime`, `updated_at: datetime`) and a `CustomerStatus` string enum (`active`, `inactive`).
2. **Port** (`ports.py`), as a `Protocol` plus three exceptions (`CustomerNotFound`, `VersionConflict`, `EmailTaken`):
   - `list(*, query: str | None, status: CustomerStatus | None, page: int, page_size: int) -> tuple[list[Customer], int]` returns the page and the total number of matches, ordered by `created_at` descending then `id` descending.
   - `get(id) -> Customer | None`.
   - `add(data, now) -> Customer`: assigns the next id and `version` 1, `created_at` and `updated_at` equal to `now`, status `active`; raises `EmailTaken` if the (already normalized) email exists.
   - `update(id, changes, expected_version, now) -> Customer`: **one atomic operation** (under the adapter's lock; a future PostgreSQL adapter will use one transaction with a conditional `UPDATE`). It raises `CustomerNotFound` for an unknown id; `VersionConflict` when `expected_version` is not `None` and differs from the stored version; `EmailTaken` when the new email belongs to another customer. If the changes leave every field as it already is, it returns the stored customer untouched (no new version, no new `updated_at`); otherwise it applies them, increases `version` by 1 and sets `updated_at = now`.
   - `set_status(id, status, expected_version, now) -> Customer`: the same rules (not found, version conflict, no change when the status is already the requested one).
3. **Search helper** (`search.py`): `normalize_for_search(text: str) -> str`, which applies Unicode NFKD, removes the combining marks and case-folds, so that "Cafetería" matches "cafeteria" and "ÉPSILON" matches "epsilon". The adapter matches `query` as a "contains" on the normalized name or normalized email.
4. **Validation** (`validation.py`), plain functions that raise `ApiError(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", errors=[...])` listing every problem at once, with the codes and Spanish messages of SPEC section 7 (`REQUIRED`, `TOO_SHORT`, `TOO_LONG`, `INVALID_FORMAT`): `validate_new(...)` for creation and `validate_changes(...)` for updates. Fields and limits are those of the field table in SPEC section 4; text is trimmed, an empty optional field becomes `None`, the email is lowercased, the email format and the 254-character limit are as in the "Create" rule. For updates, only the fields that were sent are validated; `null` clears `phone`, `tax_id` and `address` and is `REQUIRED` for `name` and `email`.
5. **Service** (`service.py`): `CustomerService(repository, clock)` with `list_customers(page, query, status)`, `get(id)`, `create(data)`, `update(id, data, version)`, `deactivate(id, expected_version)` and `reactivate(id, expected_version)`. It validates, calls the port with `clock.now()`, and translates the port exceptions into `ApiError`: `CustomerNotFound` to 404 `NOT_FOUND` ("No se encontró el recurso solicitado."), `VersionConflict` to 409 `VERSION_CONFLICT`, `EmailTaken` to 409 `CUSTOMER_EMAIL_TAKEN`, with the messages of the catalog. Page size is the constant 20; `page` below 1 is `ApiError(422, "VALIDATION_ERROR", ..., errors=[{"field": "page", "code": "OUT_OF_RANGE", "message": "El valor debe ser 1 o mayor."}])`.
6. **In-memory adapter** (`adapters/memory.py`), protected by a `threading.Lock`, implementing the port, with `replace_all(customers)` for the future reset. **Seed** (`seed.py`): the ten customers of `docs/SEED.md` (ids 1 to 10, names, emails, tax ids, statuses, phone and address of customer 1, `created_at` equal to `2026-01-01T09:00:00Z` plus `n` minutes for customer `n`, `updated_at` equal to `created_at`, `version` 1); the next new id is 11.
7. **Schemas and routes** (`schemas.py`, `routes.py`), all **plain `def`**:
   - Pydantic models: `CustomerOut` (the `Customer` shape of the spec, status as the enum), `CustomerListOut` (`items`, `page`, `page_size`, `total`), `CustomerCreate` and `CustomerPatch` (both with `extra="forbid"`, so an unknown field becomes a 422 `INVALID_FORMAT` through the existing handler; values are typed as `str | None` so that length and format problems reach the validation of point 4 and get their own codes; `CustomerPatch` also has a required integer `version`, and the fields that were sent are told apart from the absent ones with `model_fields_set`).
   - The six routes of the spec under `/api/customers`. Reading routes depend on `get_current_user`; creating, updating, deactivating and reactivating depend on `require_action(Action.MANAGE_CUSTOMERS)`. `POST` answers 201 with a `Location` header; every response with one customer carries `ETag: "<version>"`; `deactivate` and `reactivate` read an optional `If-Match` header (`"3"` or `3`); a malformed value is a 422 with `INVALID_FORMAT` on the field `If-Match`. Declare `responses` for 401, 403, 404, 409 and 422 with the problem shape, as the auth routes do.
   - Query parameters of the list: `page` (default 1), `q`, `status`; a `status` other than `active` or `inactive` is a 422 with `INVALID_FORMAT` on `status`.
8. **Wiring** (`main.py`): build the service once with the in-memory adapter seeded as above and the application clock, store it as `app.state.customers`, and include the router. Add a dependency `get_customer_service` that reads it from `request.app.state`.
9. **Tests** (`backend/tests/customers/`), deterministic (injected clock, no sleeps; log in through the real login route and cache one login per role in a fixture, because each real login costs a password hash). Cover:
   - `normalize_for_search`, and the validation of every field at and around its limits (1, 2, 120, 121 characters for the name; email without `@`, without a domain dot, with spaces, of 254 and 255 characters; phone and tax id character sets and lengths; address 200 and 201), several problems reported together, trimming, empty optional fields becoming `null`, email lowercasing;
   - the adapter: ordering, pagination, `total`, search by name and by email with accents, status filter, unique email (case-insensitive), the atomic `update` rules (not found, conflict, email taken, no-op keeps `version` and `updated_at`, a real change bumps both), `set_status` no-op, two threads updating the same customer with the same `expected_version` (exactly one succeeds);
   - the routes for each of the four roles (admin and sales write; finance and read-only get 403 on every write and 200 on reads; no cookie gives 401): create (201, `Location`, `ETag`, `version` 1, 409 on a duplicate email, 422 listings), read (200, 404, a non-integer id as 422), patch (partial change, `null` clearing, `null` on `name` as `REQUIRED`, missing `version` as `REQUIRED`, stale `version` as 409, an unknown field as 422, the no-op case, new `ETag`), deactivate and reactivate (state change, idempotent repeat, `If-Match` stale as 409, malformed `If-Match` as 422), list (default page, page 2 after creating enough customers, an empty page beyond the last, `q` with and without accents, `status`, invalid `page` and `status`, ordering, `total`);
   - the order of checks of SPEC section 7 for one write route (wrong role beats validation errors; unknown id beats a stale version);
   - the OpenAPI document contains `CustomerOut` and `CustomerListOut`.
10. **Docs.** A short "Customers" section in `backend/README.md`: the layers, the atomicity contract of the port (what a PostgreSQL adapter must guarantee), and example `curl` calls.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

and, manually, with the server started as in the backend README (`SESSION_SECRET=dev-secret uv run uvicorn app.main:app --port 8000`, stopped afterwards with Ctrl+C), log in as the sales user and list, create and patch a customer with `curl`, showing the status line and the `ETag`.

## Rules for this task

- Commit as you go, in small real steps (about 14 to 20 commits): for example the model, the port, the search helper, the validation, the adapter, the seed, the service, the schemas, the routes, the wiring, then tests next to each piece and the README. Messages follow Conventional Commits, in English, for example `feat(backend): add the customer repository port`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory; never ask for access outside it.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
