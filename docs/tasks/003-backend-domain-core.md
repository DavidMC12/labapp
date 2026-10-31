# Task 003: backend domain core

Assignee: Worker 1. Branch: `w1/domain-core`. Reviewer: Supervisor.

## Goal

Implement, as pure Python, the business rules that every later backend module will call: money and totals, order states and line validation, permissions, number formatting, card validation and the fake payment gateway, and the Spanish labels. There is no database, no HTTP route and no I/O in this task, so every rule can be tested exhaustively and quickly.

## Read first

- `docs/SPEC.md`: section 2 (permissions), section 5 (orders), section 6 (invoices and payments), section 7 (errors, labels) and section 8 (formats).
- `docs/SEED.md`: the seeded orders, whose totals your tests must reproduce.
- `backend/app/errors.py`: `ApiError`, which you raise for every rule violation. Its signature is `ApiError(status, code, detail, *, title=None, errors=None, **extra)`.
- `backend/README.md` and `backend/pyproject.toml`: how the project is run and linted.

## Scope

You may create files only under `backend/app/domain/` and `backend/tests/domain/`, and add a short "Domain" section to `backend/README.md`. Do not change other existing files. Both new folders need an `__init__.py`.

## Requirements

1. **Money** (`app/domain/money.py`).
   - `quantize_money(value: Decimal) -> Decimal`: two decimals, rounding half-up.
   - `LineInput(unit_price: Decimal, quantity: int)` and `Totals(subtotal, tax, total)` as frozen dataclasses.
   - `compute_totals(lines, tax_rate: Decimal) -> Totals`: `subtotal` = sum of unit price times quantity; `tax` = `subtotal` × `tax_rate` ÷ 100, rounded half-up to 2 decimals; `total` = `subtotal` + `tax`. Raise `ValueError` if `tax_rate` is outside 0.00 to 100.00 or has more than 2 decimals.
2. **Numbering** (`app/domain/numbering.py`): `format_number(prefix, value)` for the prefixes `PED` and `FAC`: zero-padded to at least 4 digits and longer when needed (`PED-0001`, `FAC-0042`, `PED-10000`). Raise `ValueError` for `value < 1` or another prefix.
3. **Labels** (`app/domain/labels.py`): dictionaries with the Spanish labels of order states, invoice states, payment states, payment methods and roles, exactly as listed in SPEC section 7.
4. **Permissions** (`app/domain/permissions.py`): `Role` and `Action` enums covering every row of the permission table in SPEC section 2, `is_allowed(role, action) -> bool`, and `require(role, action)` that raises `ApiError(403, "FORBIDDEN", "No tienes permiso para realizar esta acción.")`.
5. **Orders** (`app/domain/orders.py`).
   - `OrderStatus` (`draft`, `confirmed`, `paid`, `shipped`, `cancelled`) and `OrderAction` (`confirm`, `pay`, `ship`, `cancel`).
   - `next_status(current, action)` returns the new status or raises `ApiError(409, "INVALID_TRANSITION", ...)` with the message from SPEC section 7 using the Spanish state labels (for example "No se puede pasar el pedido de enviado a cancelado."). The target in the message is the status the action would produce.
   - `validate_draft_lines(lines)`, where each entry has `product_id: int` and `quantity: object` (raw input). In this order: field-level problems first, as one `ApiError(422, "VALIDATION_ERROR", "Revisa los datos ingresados.", errors=[...])` listing every bad line with `field` like `lines[0].quantity`; a quantity that is not an integer (including booleans and floats) is `INVALID_FORMAT`, an integer outside 1 to 999 is `OUT_OF_RANGE`. Then a repeated product raises `ORDER_DUPLICATE_PRODUCT` (422), then more than 10 lines raises `ORDER_TOO_MANY_LINES` (422). An empty list is valid for a draft.
   - `ensure_confirmable(lines)`: raises `ORDER_EMPTY` (422) when there are no lines.
   - `check_stock(lines, stock_by_product)`: raises `ApiError(409, "INSUFFICIENT_STOCK", ...)` when any line lacks stock. The extra member `shortages` lists every short line (`product_id`, `sku`, `name`, `available`, `requested`) ordered by product id, and the message names the first one: "No hay stock suficiente de {name}: disponible {available}, solicitado {requested}."
6. **Payments** (`app/domain/payments.py`).
   - `luhn_valid(number: str) -> bool`.
   - `parse_card(number, expiry, cvc, today: date)`: spaces and hyphens in the number are ignored; the number must be 16 digits and pass Luhn (`CARD_NUMBER_INVALID`); `expiry` is `MM/YY` (anything else is `INVALID_FORMAT` on `card.expiry`) and valid through the last day of its month (`CARD_EXPIRED` when that day is before `today`); `cvc` is exactly 3 digits (`CARD_CVC_INVALID`). All problems are reported together as one `ApiError(422, "VALIDATION_ERROR", ...)` with `field` values `card.number`, `card.expiry` and `card.cvc`. On success return a `Card` that holds only `last4`.
   - `validate_transfer_reference(reference)`: 4 to 40 characters (`TOO_SHORT`, `TOO_LONG` on `reference`).
   - `gateway_decision(method, card_last4=None)` returning a `GatewayDecision(outcome, reason)`: for `card`, last four digits `0002` are `declined` with reason `CARD_DECLINED`, `0003` is `unavailable` with reason `GATEWAY_UNAVAILABLE`, any other card is `approved`; `transfer` and `cash` are always `approved`. The reason is `None` when approved.
7. **Messages.** Every message is Spanish and comes from SPEC section 7 or the tables of sections 4 to 6. Do not invent wording; if a message you need is missing, write the question in your report.
8. **Tests** (`backend/tests/domain/`), one file per module, exhaustive:
   - Totals: reproduce the totals of the seven seeded orders in `docs/SEED.md` from their lines and prices (type the inputs and expected values into the test); the 5.025 tie becomes 5.03; rate boundaries 0, 100, 100.01 and three decimals.
   - Quantity boundaries 0, 1, 999 and 1000, a float, a string and a boolean; 10 versus 11 lines; duplicates; several bad lines reported together.
   - The full transition matrix, 5 statuses × 4 actions, with the expected result for each.
   - The full permission matrix, every role against every action, checked against the table in SPEC section 2.
   - Luhn with `4242 4242 4242 4242`, `4000 0000 0000 0002`, `4000 0000 0009 0003` and invalid numbers; spaces and hyphens; expiry in the current month (valid), the previous month (expired), malformed values; CVC lengths 2, 3 and 4; transfer references of 3, 4, 40 and 41 characters.
   - Gateway decisions for every method and the two magic endings.
   - Number formatting for 1, 9999, 10000 and invalid values.
   - Stock checks with one and several shortages, including the order of `shortages`.
9. **Style.** Type hints everywhere, short docstrings, no I/O and no global state. `ruff check` and `ruff format --check` must pass.

## Acceptance criteria

From `backend/`, all of these pass:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -W error
```

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits): for example one per module plus its tests, then the README section. Messages follow Conventional Commits, in English, for example `feat(backend): add order state machine`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
