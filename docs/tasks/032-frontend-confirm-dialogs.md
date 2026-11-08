# Task 032: confirmation dialogs for destructive actions

Assignee: Worker 2. Branch: `w2/confirm-dialogs`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 031 is merged (the supervisor tells you, or tells you to branch from `w2/titles`).

## Goal

"Cancelar pedido" (which returns the stock and voids the invoice) and "Desactivar" a customer act at the first click. A confirmation step is the standard guard for those two actions, and it gives the owner's automation suite a real modal to handle (focus, Escape, the backdrop, the accessible name), which the app does not have yet. Build one reusable confirmation dialog on the native `<dialog>` element and use it in those two places. Reactivating a customer, confirming or shipping an order are not destructive and stay immediate.

## Read first

`docs/SPEC.md` section 4 (deactivate and reactivate a customer), section 5 (cancel and its consequences: stock returns, the invoice is voided) and section 6; `docs/TESTABILITY.md` (the `dialog` kind of the grammar); `frontend/src/components/ui/` (Button, Alert and the other components, their tests and `index.ts`), `frontend/src/app/(app)/orders/[id]/page.tsx` (the transition handler, the pending state, the alert), `frontend/src/app/(app)/customers/[id]/page.tsx` (the status toggle), their tests, `frontend/src/lib/testid.ts`, `frontend/src/app/globals.css` (tokens only).

## Scope

You may create and edit files only under `frontend/`: the new component and its tests in `src/components/ui/`, the two pages and their tests (existing tests that click those two buttons must now go through the dialog), `src/app/globals.css` only for the dialog backdrop (with tokens, readable in both themes), and the README. No new dependencies. Do not change any existing `data-testid` or text outside the two actions.

## Requirements

1. **Component** `ConfirmDialog` (`src/components/ui/ConfirmDialog.tsx`, exported from `index.ts`): a controlled component built on `<dialog>` and `showModal()`. Props: `open`, `title`, `children` (the message), `confirmLabel`, `cancelLabel` (default "Volver"), `pending` (disables both buttons and shows the confirm button as loading), `onConfirm`, `onCancel`, and the test ids of its parts (typed `TestId`s). Behavior: when `open` becomes true it calls `showModal()`, when it becomes false it closes; the native `cancel` event (the Escape key) calls `onCancel` and is not allowed to close the dialog by itself while `pending`; a click on the backdrop does the same as Escape; the first focus goes to the cancel ("Volver") button, never to the destructive one; closing returns focus to the element that opened it (the native behavior; assert it in a test). The dialog has `aria-labelledby` (the title) and `aria-describedby` (the message). The confirm button uses the existing danger-like styling that the design has (use tokens; if the existing `Button` has no danger variant, add one with the tokens `danger` and `danger-bg`, readable in both themes, and keep the contrast guard tests passing).
2. **Order detail.** "Cancelar pedido" opens the dialog; title "¿Cancelar el pedido {number}?"; message for a `draft`: "El borrador quedará cancelado."; for a `confirmed` order: "El stock reservado vuelve al inventario y la factura emitida, si existe, se anula."; confirm label "Sí, cancelar pedido". Confirm runs the same transition as today (same request, same `If-Match`, same pending guard against a second click); the dialog closes when the request ends; a failure shows the existing alert as today; success behaves as today. Ids: `orders-cancel-confirm-dialog`, `orders-cancel-title-heading`, `orders-cancel-message-text`, `orders-cancel-confirm-button`, `orders-cancel-back-button`.
3. **Customer detail.** "Desactivar" opens the dialog; title "¿Desactivar a {name}?"; message "No podrá recibir pedidos nuevos. Sus pedidos y facturas existentes no cambian."; confirm label "Sí, desactivar". "Reactivar" stays immediate. Same request and error handling as today. Ids: `customers-deactivate-confirm-dialog`, `customers-deactivate-title-heading`, `customers-deactivate-message-text`, `customers-deactivate-confirm-button`, `customers-deactivate-back-button`.
4. **Tests.** jsdom may not implement `showModal` and `close`: stub them on `HTMLDialogElement.prototype` in the test setup of these files (a small shared helper). Cover: the component (opens, closes, Escape and backdrop call `onCancel`, pending blocks both, first focus on "Volver", focus returns to the opener, the accessible name and description, the ids), the order cancel flow for a draft and for a confirmed order (the request is sent only after the confirmation; "Volver" sends nothing; a failure shows the alert; the double-click guard), the customer deactivate flow (same), and that "Reactivar", "Confirmar" and "Enviar" still act at once. All the new ids are valid and unique; the static audit passes.
5. **Docs.** A "Confirmation dialogs" section in `frontend/README.md`, and one line in `docs/TESTABILITY.md` listing the two dialogs.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
