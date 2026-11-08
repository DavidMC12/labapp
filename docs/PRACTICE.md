# Practice scenarios

LabApp exists so that a QA engineer can practice test automation against a clean, well-specified application. The automation guide ([AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md)) teaches the tools; this catalog is the other half: **what to test**. One section per area of the application, every scenario as a table row, and the exact expected result — status code, error `code`, Spanish message and the test id to assert on — taken from [SPEC.md](SPEC.md), [SEED.md](SEED.md), the generated catalog [TESTIDS.md](TESTIDS.md) and the code, so the reader can pick a row, automate it and know what "pass" means.

The scenarios assume the local start and the seed ([SEED.md](SEED.md)): `mise run dev`, log in as one of the four seeded users (password `Demo-LabApp-2026!`, shown on the login screen), and start each independent scenario with `POST /__test__/reset` (the API rows below that need a seed state say so). The seed is a contract: after a reset the first new customer is 11, the first new order `PED-0008`, the first new invoice `FAC-0004` and the next payment id is 5 — the rows name those exact records when they matter.

## How to read a row

| Column | Meaning |
|---|---|
| `ID` | Area letter and row number (`B-14`). A `✔` means the row was run against the local in-memory API with `curl` (from a script kept outside the repository) and behaved exactly as written; rows without a mark were read from the specification and the catalog but not executed. UI rows carry no mark. |
| `Level` | `UI` (only the browser), `API` (only HTTP against `/api`), or `Both` (the same behaviour observable on both sides, so it can be automated either way). |
| `Scenario` | One sentence describing what is put to the test. |
| `Steps` | At most three actions, naming the real test ids ([TESTIDS.md](TESTIDS.md)) or the endpoints. A test id shown as `module-{…}-kind` follows the grammar of [TESTABILITY.md](TESTABILITY.md) for a member of a family; `-N` is a record id or a list position. |
| `Expected` | The exact result copied from the specification: the status code, the error `code`, the Spanish message and the test id of the alert or element to assert on (errors appear in an element with `role="alert"`). |
| `Technique` | Equivalence class, boundary value, state transition, error guessing, decision table, concurrency or accessibility. |
| `Diff` | Level of difficulty: 1 easy, 2 medium, 3 hard. |

Techniques in this catalog:

- **Equivalence class** — one representative of a family the application treats the same way (all valid emails, all invalid card numbers).
- **Boundary value** — the edges the rule defends: 2–120 characters, 1–999, 100 KB, page 1 of 1.
- **State transition** — the order machine of an order (`draft`, `confirmed`, `paid`, `shipped`, `cancelled`), of an invoice (`issued`, `paid`, `void`) and of sessions: aim at each allowed transition and at the refusals between them.
- **Error guessing** — the recurring ways a real user (or a stranger) mistreats the system: a repeated submit, a modified amount, an old copy of a form.
- **Decision table** — combinations of role and action, or of payment method and its required data.
- **Concurrency** — two writers at once: versions, `ETag`/`If-Match`, idempotency keys, a reset against an open request.
- **Accessibility** — what the project guarantees per [TESTABILITY.md](TESTABILITY.md): test ids, `aria-busy`, skip link, titles, focus, no horizontal scroll.

## A. Customers (flow 1)

The ten seeded customers of [SEED.md](SEED.md) exist after every reset; after it, the first new customer is 11. Field rules and their messages: [SPEC section 4](SPEC.md#4-customers-flow-1). Where the seed matters the row names the record. The scenario "status of a customer" uses the two inactive ones: customer 5 (`Estudio Épsilon`) and customer 8 (`Hotel Horizonte`).

| ID | Level | Scenario | Steps | Expected | Technique | Diff |
|---|---|---|---|---|---|---|
| A-1 ✔ | Both | Create a customer with the minimum data. | Log in as Sales (`auth-login-email-input`, `auth-login-submit-button`), open `app-nav-customers-link` and then `customers-list-new-link`. | The detail screen answers: `customers-detail-heading` carries the new name and `customers-detail-state-status` is `Activo`. The API answer is 201 with `ETag: "1"` and `Location: /api/customers/11`. | Equivalence class | 1 |
| A-2 ✔ | API | The email is rejected when it has no `@` or no domain. | `POST /api/customers` with `{"name": "Prueba", "email": "no-good"}`. | 422 `VALIDATION_ERROR` with `errors: [{"field": "email", "code": "INVALID_FORMAT", "message": "El formato no es válido."}]`. | Equivalence class | 1 |
| A-3 ✔ | API | A name below the minimum is rejected with the documented message. | `POST /api/customers` with `{"name": "A", "email": "a3@example.test"}`. | 422 `VALIDATION_ERROR` with `errors: [{"field": "name", "code": "TOO_SHORT", "message": "Debe tener al menos 2 caracteres."}]`. | Boundary value | 1 |
| A-4 ✔ | API | A name of 121 characters exceeds the maximum; exactly 120 passes. | `POST /api/customers` with a 121-character `name`, then with a 120-character one. | 121 chars: 422 `TOO_LONG` "Debe tener como máximo 120 caracteres." — exactly 120: 201, the customer is created. | Boundary value | 2 |
| A-5 ✔ | API | A phone is checked for format before length, so `"abc"` is `INVALID_FORMAT`, not `TOO_SHORT`. | `POST /api/customers` with `{"name": "Prueba Tres", "email": "tres@example.test", "phone": "abc"}`. | 422 `VALIDATION_ERROR` with `{"field": "phone", "code": "INVALID_FORMAT", "message": "El formato no es válido."}`. | Decision table | 2 |
| A-6 ✔ | API | A phone of allowed characters but too short is `TOO_SHORT`. | `POST /api/customers` with `{"name": "…", "email": "…", "phone": "-"}` (one character of the allowed set). | 422 `VALIDATION_ERROR` with `{"field": "phone", "code": "TOO_SHORT", "message": "Debe tener al menos 7 caracteres."}`. | Boundary value | 2 |
| A-7 ✔ | API | An unknown field in the body names itself as the field. | `POST /api/customers` with `{"name": "…", "email": "…", "unknown": "v"}`. | 422 `VALIDATION_ERROR` with `{"field": "unknown", "code": "INVALID_FORMAT"}`. | Error guessing | 1 |
| A-8 ✔ | API | A repeated email is refused even in another case. | `POST /api/customers` with `{"name": "Acme Dos", "email": "ACME@example.test"}` (customer 1 uses `acme@example.test`). | 409 `CUSTOMER_EMAIL_TAKEN` with `detail: "Ya existe un cliente con ese email."`. | Error guessing | 1 |
| A-9 ✔ | API | The email is trimmed and lowercased, the name is trimmed and empty optionals are stored as `null`. | `POST /api/customers` with `{"name": "  Cliente Once  ", "email": "  UNO@Example.test  "}`. | 201: `email` `uno@example.test`, `name` `Cliente Once`, `status` `active`, `version` 1, `phone` and `address` `null`, `Location: /api/customers/11`, `ETag: "1"`. | Equivalence class | 2 |
| A-10 ✔ | API | Read-only may read the list but not create. | As `readonly@labapp.test`: `GET /api/customers`, then `POST /api/customers`. | `GET` 200 with the ten seeded customers; `POST` 403 `FORBIDDEN` "No tienes permiso para realizar esta acción.". | Decision table | 1 |
| A-11 ✔ | API | A stale `version` in the body is a conflict. | `POST /api/customers` to have customer 11, then `PATCH /api/customers/11` with `{"name": "Cliente Once B", "version": 5}`. | 409 `VERSION_CONFLICT` "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo." (in the UI the same answer offers the `Recargar datos` affordance). | Concurrency | 2 |
| A-12 ✔ | API | An update that changes nothing keeps `version` and `updated_at`; a real change bumps it. | `PATCH /api/customers/11` twice: first with the same values, then with a new name. | First: 200 with the same `ETag: "1"`. Second: 200 with `ETag: "2"` and a new `updated_at`. | Equivalence class | 2 |
| A-13 ✔ | API | A stale `If-Match` on deactivate is a conflict even if the state target is current. | After A-9: `POST /api/customers/11/deactivate` with `If-Match: "9"`. | 409 `VERSION_CONFLICT` "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.". | Concurrency | 2 |
| A-14 ✔ | API | Deactivate and reactivate a customer. | `POST /api/customers/11/deactivate` with `If-Match: "2"`, then `reactivate`. | First: 200, `status` `inactive`, `ETag: "3"`. Second: 200, `status` `active`, `ETag` + 1. Reset first if 11 does not exist. | State transition | 1 |
| A-15 ✔ | API | Asking for the state the customer already has answers 200 with no change. | Deactivate customer 11 again by `POST /api/customers/11/deactivate` (it is already inactive). | 200 with the same `version` and `updated_at`; no third event (the customer state badge `customers-detail-state-status` does not change on the screen either). | Boundary value | 2 |
| A-16 ✔ | Both | An inactive customer cannot receive new orders. | Deactivate customer 5 (`Estudio Épsilon`, already `inactive`; deactivate 11 instead with A-14 to go through the whole path) and `POST /api/orders` with `{"customer_id": 11}`. | 422 `CUSTOMER_INACTIVE` "El cliente está desactivado y no puede recibir pedidos." In the UI the picker `orders-form-customer-select` does not list inactive customers at all. | Error guessing | 2 |
| A-17 ✔ | API | Paging: a page beyond the last is empty; a bad `page` value is a 422. | `GET /api/customers?page=2` with 10 or 11 customers, then `?page=abc`, then `?page=0`. | Page 2: 200, `items` `[]`, `total` unchanged, `page_size` 20. `page=abc`: 422 `VALIDATION_ERROR` on `page` `INVALID_FORMAT`. `page=0`: 422 on `page` `OUT_OF_RANGE` "El valor debe estar entre 1 y 1000000.". | Boundary value | 2 |
| A-18 ✔ | API | The search is a literal "contains" that ignores case and accents. | `GET /api/customers?q=ferreteria`, then `?q=ACME`, then `?q=%`. | `ferreteria` finds customer 6 `Ferretería Fénix` (200, `total` 1); `ACME` finds `Acme Industrial S.A.`; `%` finds nothing (`total` 0): it is literal text, not a pattern. | Equivalence class | 2 |
| A-19 ✔ | API | A `q` with a control character is refused; a too long one would be `TOO_LONG`. | `GET /api/customers?q=a%0Ab` (a line feed inside `q`). | 422 `VALIDATION_ERROR` with `{"field": "q", "code": "INVALID_FORMAT", "message": "El formato no es válido."}`. | Error guessing | 2 |
| A-20 ✔ | API | An unknown id or a non-integer id on the detail route. | `GET /api/customers/9999`, then `GET /api/customers/abc`, in the UI `/customers/999`. | API: 404 `NOT_FOUND` "No se encontró el recurso solicitado."; `abc`: 422 `VALIDATION_ERROR` on `id`. UI: the section keeps its title and shows `customers-detail-error-alert` with the same 404 message. | Equivalence class | 1 |
