# Task 038: a compact header on the phone

Assignee: Worker 2. Branch: `w2/phone-header`. Reviewer: Supervisor.

**Base.** Branch from `main` (it has everything up to task 034).

## Goal

On a phone (390 pixels wide) the shell header takes about 340 pixels of an 844 pixel screen, a third of the page, before any content: the brand row, two rows of navigation links (seven links wrap), the user block, the theme selector on its own full-width row and "Salir" on its own row. Make it compact without removing anything and without changing the desktop rail. This was found by looking at real screenshots; you cannot see them, so the requirements below are stated in terms you can assert in tests.

## Read first

`frontend/src/app/(app)/layout.tsx` (the shell: the markup around the `aside`, the navigation and the user block), `frontend/src/app/(app)/layout.test.tsx` and `layout.current-section.test.tsx`, `frontend/src/components/ui/ThemeSelect.tsx`, `Select.tsx`, `Field.tsx`, `Button.tsx`, `frontend/README.md` (the layout notes).

## Scope

You may edit files only under `frontend/`: the shell layout, the three small components above (only to add an optional `compact` or class prop that changes classes, never markup order or ids), their tests and the README. No new dependencies. Do not change any existing `data-testid`, text, DOM order (it is the tab order) or the desktop (768 pixels and up) appearance.

## Requirements

1. **Navigation in one scrollable row, not two wrapped rows.** Below 768 pixels the navigation links sit in a single row that scrolls horizontally inside its own container, with the current link kept visible (`scrollIntoView({ inline: "nearest", block: "nearest" })` when the pathname changes, in an effect), smaller horizontal padding, and a visible scroll affordance (a fade on the right edge made with the existing tokens, or the partially cut next link: do not rely on a scrollbar). Keep the semantic `nav` with its `aria-label`; the links keep their order and ids. Note: an earlier version scrolled sideways and hid "Configuración" without any cue, which is why it was changed to wrap; the scroll-into-view and the cue are what make the single row acceptable. If you judge the single row not good enough, keep the wrap and say so in your report with your reason.
2. **One row for the user block.** On a phone the user name, the role, the theme select and "Salir" share one row that may wrap only when the name is long: the name and the role stacked in a small block on the left, then the theme select (`w-auto`, its label visually hidden on the phone but still in the DOM as `sr-only`, so its accessible name stays "Tema"), then "Salir" at the right. On 768 pixels and up nothing changes (the label stays visible in the rail).
3. **Spacing.** The brand row loses the vertical padding it does not need on a phone (`py-2`). The target, which a test can approximate with class assertions and the README must state: the header on a phone needs at most three rows (brand, navigation, user) instead of five.
4. **Tests.** Mock `fetch` and `next/navigation`. Cover: the classes of the navigation container below and above the breakpoint (the assertions the existing layout tests already use for classes), the scroll-into-view call on a pathname change (stub `Element.prototype.scrollIntoView`), the theme select label (`sr-only` class on the phone, visible on `md`), the DOM order of the shell unchanged (a test that lists the `data-testid` of the focusable elements in order), the desktop classes unchanged. Keep every existing test passing; the static audit and the browser audit must still pass.
5. **Docs.** Update the layout notes of `frontend/README.md`.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` all pass (the coverage floor must hold); from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, what only a visual check can confirm, and any deviation or open question.
