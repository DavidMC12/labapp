# Task 031: document titles, a skip link and the landmarks

Assignee: Worker 2. Branch: `w2/titles`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 029 is merged (the supervisor tells you, or tells you to branch from `w2/products`).

## Goal

Every screen of the app has the same browser tab title, "LabApp", there is no way to jump over the navigation with the keyboard, and the login page has no `main` landmark. These are accessibility basics (WCAG 2.4.1 bypass blocks, 2.4.2 page titled) and they are also what a test asserts first after a navigation: "am I on the page I expect?". The title must say so.

## Read first

`docs/TESTABILITY.md`, `frontend/src/app/layout.tsx`, `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/login/page.tsx`, every `page.tsx` under `frontend/src/app/`, `frontend/src/app/not-found.tsx`, `frontend/src/app/error.tsx`, `frontend/src/lib/`, `frontend/src/components/ui/`.

## Scope

You may create and edit files only under `frontend/`: a small hook in `src/lib/`, the page components (only to call the hook), the shell and login layouts (the skip link and the landmark), the root layout (the title template), their tests, and the README. No new dependencies. Do not change any existing `data-testid`, text or behavior.

## Requirements

1. **Title hook** (`src/lib/useDocumentTitle.ts`): `useDocumentTitle(title)` sets `document.title` to `"{title} · LabApp"` in an effect (and to `"LabApp"` when the title is empty or undefined). It restores nothing on unmount (the next page sets its own). The root layout metadata keeps `"LabApp"` as the default for the server render.
2. **Where it is used** (titles in Spanish; while data loads use the section title, and when the record arrives the specific one): login "Iniciar sesión"; home "Resumen"; customers list "Clientes", new "Nuevo cliente", detail "Cliente {name}" (section title while loading), edit "Editar cliente"; orders list "Pedidos", new "Nuevo pedido", detail "Pedido {number}"; invoices list "Facturas", detail "Factura {number}"; settings "Configuración"; products "Productos" if that screen exists on your branch; not found "Página no encontrada"; error "Algo salió mal". The not found page is a server component: give it the title through the `metadata` export instead of the hook.
3. **Skip link.** The first focusable element of the shell and of the login page is a link "Saltar al contenido" to `#main-content`, visually hidden until it receives focus (the `sr-only focus:not-sr-only` pattern, with a visible focus style using the existing tokens, readable in both themes). Its id is `app-skip-link` in the shell and `auth-login-skip-link` on the login page. The `main` element of the shell gets `id="main-content"` and `tabIndex={-1}` so the jump moves focus there.
4. **Landmarks.** The login page content is inside a `main` element (with `id="main-content"`). The shell keeps its `nav` (with its `aria-label`) and its `main`. Nothing else is restructured.
5. **Tests.** Mock `fetch` and `next/navigation`. Cover: the hook (set, empty, undefined, change on re-render), the title of every page listed above in its loading and loaded states, the skip link (first in the tab order, its `href`, the target exists with `tabIndex` -1, on both the shell and the login), the landmarks, the not found `metadata`. Keep every existing test passing; the static audit must pass (the new links need ids that follow the grammar).
6. **Docs.** A short "Titles, skip link and landmarks" section in `frontend/README.md`, and one line in `docs/TESTABILITY.md` ("the document title names the page: `{page} · LabApp`").

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
