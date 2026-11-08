# Task 039: a new order from a customer

Assignee: Worker 2. Branch: `w2/order-from-customer`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

From the detail of a customer there is a link to the customer's orders, but no way to start an order for that customer: the user has to go to "Nuevo pedido" and search for them again. Add the shortcut: a link on the customer detail that opens the new-order form with the customer already chosen. It also gives the automation suite a faster path to set up data and a second way into the same form.

## Read first

`docs/SPEC.md` section 4 (an inactive customer cannot receive an order), section 5 ("Orders API": create needs an active customer); `docs/TESTABILITY.md`; `frontend/src/app/(app)/orders/new/page.tsx` (the picker: the search box, the customers select with up to 20 active customers, the submit), `frontend/src/app/(app)/customers/[id]/page.tsx`, `frontend/src/features/customers/` (the `useCustomer` hook and the list hook), `frontend/src/features/orders/params.ts` (how a strict positive id is parsed from a URL).

## Scope

You may edit files only under `frontend/`: the new-order page, the customer detail page, a small parser in `src/features/orders/` if you need one, their tests, and the README. No new dependencies. Do not change any existing `data-testid` or text, or the behavior of the form when the URL has no `customer_id`.

## Requirements

1. **The link.** On the customer detail, for a customer that is `active` and a user who can edit draft orders (the same permission the new-order page checks), a link "Nuevo pedido" to `/orders/new?customer_id={id}`, id `customers-detail-neworder-link`, placed with the other actions of the page. Not shown for an inactive customer or for a user who cannot create orders.
2. **The preselection.** `/orders/new` reads `customer_id` from the URL with a strict parser (a positive integer up to 2147483647; anything else is ignored as if absent). When it is valid: load that customer (`useCustomer`); while it loads the select is disabled with the option "Cargando cliente…"; when it arrives and is `active`, it is added to the options of the select (without duplicating it when it is already in the first 20) and selected, and the "Crear pedido" button works at once; when it is `inactive` or not found (404), nothing is selected, and a notice (`role="status"`, id `orders-form-presetcustomer-status`) says "El cliente indicado no está disponible para nuevos pedidos." The user can still change the selection or search as usual. The preselection is applied once: a later change of the select by the user is never overwritten by a re-render or a refetch.
3. **Nothing else changes.** Without the parameter the page behaves exactly as today; the search keeps working with a preselected customer.
4. **Test ids.** The two new ids above; all valid and unique; the static audit passes.
5. **Tests.** Mock `fetch` and `next/navigation`. Cover: the link for an active customer with a user who can edit orders, its absence for an inactive customer and for Finance and Read-only, the parser (valid, zero, negative, decimal, letters, above the limit), the preselection of a customer inside and outside the first 20, an inactive customer, a 404, the loading state, the user changing the selection afterwards, the request sent on submit with the preselected id, and the form without the parameter. Keep every existing test passing.
6. **Docs.** One sentence in the orders and customers sections of `frontend/README.md`.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` all pass (the coverage floor must hold); from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
