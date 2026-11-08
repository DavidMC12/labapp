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
