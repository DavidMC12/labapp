# Task 023: frontend dark theme

Assignee: Worker 2. Branch: `w2/dark-theme`. Reviewer: Supervisor.

**Base.** Branch from `main` after tasks 016 and 020 are merged, so that every screen exists and is covered by the guards. This task changes only how things look and adds a theme selector; every `data-testid` outside the selector, every text and every behavior stays as it is.

## Goal

Add the dark theme that the owner asked for after the "Libro mayor" light theme: the same design in a dark ground, chosen by the system preference by default and overridable by the user with a selector that is remembered. Because all colors already live in tokens (`globals.css`) and the two guard tests keep literal colors out of the components, this is a change of `globals.css` plus the selector and its no-flash script.

## Read first

`frontend/src/app/globals.css`, `frontend/src/app/tokens.test.ts`, `frontend/src/app/colors-guard.test.ts`, `frontend/src/app/layout.tsx`, `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/login/page.tsx`, `frontend/src/components/ui/`, `frontend/README.md` (the "Design" section), `docs/tasks/013-frontend-libro-mayor-theme.md` and `docs/TESTABILITY.md`.

## Scope

You may edit files only under `frontend/`. No new dependencies. Do not change any existing `data-testid`, any text, any hook or API call.

## Requirements

1. **Dark tokens.** In `globals.css` keep the light values on `:root` with `color-scheme: light`, and redefine **every** color token for the dark theme in exactly these two places, with the same values and `color-scheme: dark`: `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { ... } }` (the system default) and `:root[data-theme="dark"] { ... }` (the explicit choice, which also wins over a light system). The shape, so that nothing is defined only inside a media query or an attribute selector, is the one of the "Theme-aware" rule: every token has its first definition on bare `:root`. The dark values (their contrast ratios were computed and checked by the Supervisor; use them exactly):

| Token | Dark value |
|---|---|
| `paper` | `#111513` |
| `surface` | `#1A1F1C` |
| `ink` | `#E8EEEA` |
| `muted` | `#9FB0A7` |
| `line` | `#2C3631` |
| `control-border` | `#7C8C84` |
| `rail` | `#0B2019` |
| `rail-ink` | `#E8F0EA` |
| `rail-muted` | `#A9C2B6` |
| `rail-hover` | `#143528` |
| `accent` | `#4FBF9A` |
| `accent-hover` | `#6FD3B2` |
| `accent-ink` | `#07231A` |
| `ok-bg` | `#12362B` |
| `off-bg` | `#262C29` |
| `danger` | `#FF8F85` |
| `danger-bg` | `#3A1D1B` |
| `focus` | `#7AD9BC` |

   In the dark theme `accent` is a light green: primary buttons are a light-green block with dark text (`accent-ink`), links are light green on the dark paper. If a component hardcodes the assumption that `accent` is dark or `accent-ink` is white, fix the component to use the tokens only.
2. **Selector.** A "Tema" control with the options "Sistema", "Claro" and "Oscuro", built with the existing `Select` component: in the shell (`app-theme-select`, in the user block of the rail, and in the same place under the links on the phone layout) and on the login page (`auth-login-theme-select`, at the top right of the form column, above the heading). Choosing "Claro" or "Oscuro" sets `data-theme="light"` or `data-theme="dark"` on `<html>`; choosing "Sistema" removes the attribute. The choice is stored in `localStorage` under the key `labapp-theme` (the values `light` and `dark`; no key means system). Every read and write of `localStorage` is inside `try/catch` and the page works when it throws or is empty (private windows, blocked storage). One small module (`src/lib/theme.ts`) owns the key, the read, the write and the application of the attribute, with tests.
3. **No flash.** The stored choice must be applied before the first paint: an inline script in the `<head>` of the root layout that reads `labapp-theme` inside `try/catch` and sets the attribute, written so that it also works with the cookies and storage blocked, and `suppressHydrationWarning` on `<html>`. A test asserts that the script text contains the key and sets `data-theme` only for `light` and `dark`. The selector reads the real state after hydration (not during render) so that server and client markup match.
4. **Guards.** Extend `tokens.test.ts`: parse the three places (`:root`, the media block, the attribute block); every token defined on `:root` is defined in both dark places with the same value; the dark values equal the table above; the WCAG contrast pairs of the light theme are checked again with the dark values, with the same minimums (`ink`/`paper`, `ink`/`surface`, `muted`/`paper`, `muted`/`surface`, `rail-ink`/`rail`, `rail-muted`/`rail`, `rail-muted`/`rail-hover`, `accent-ink`/`accent`, `accent-ink`/`accent-hover`, `accent`/`ok-bg`, `muted`/`off-bg`, `danger`/`danger-bg`, `accent`/`paper`, `accent`/`surface`, `danger`/`paper`, `danger`/`surface` at least 4.5; `control-border`/`surface`, `control-border`/`paper`, `focus`/`paper`, `focus`/`rail` at least 3). The literal-color guard keeps scanning everything outside `globals.css`; it must still pass.
5. **Screens.** Review every screen for an assumption that breaks in the dark theme (a hardcoded `white` or `black`, an `opacity` over a token that was tuned for light, a border that disappears, the focus ring, the badges, the disabled buttons at 55% opacity, the ledger footer double rule, the table row hover tint, the inline SVG mark). Fix them with tokens. You cannot see the result in a browser; list in your report every choice that only a visual check can confirm.
6. **Docs.** Extend the "Design" section of `frontend/README.md`: the three places of the tokens, the selector, the storage key and how to add another theme.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem (the two new ids follow the grammar and are unique).

## Rules for this task

- Commit as you go, in small real steps (about 12 to 18 commits). Conventional Commits, in English, for example `style(frontend): add the dark theme tokens`.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the brief is ambiguous or two requirements collide, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.

## Corrections after the review

The brief was reviewed by a second agent before the work started. Its findings were sent to the worker as corrections and are part of the delivered work:

- Two more tokens, `rail-active` and `rail-active-ink` (light: `#FBFAF6` and `#18241F`, the old look; dark: `#24573F` and `#E8F0EA`), because the current link of the rail used `paper`, which is 1.08 to 1 against the dark rail.
- `Field` and `Select` take an optional `labelClassName`, so the "Tema" label can use `text-rail-ink` on the rail (`ink` on the light rail is 1.2 to 1).
- The shell holds one single `app-theme-select` (responsive CSS), never a second copy.
- `tokens.test.ts` parses the file block by block with a brace counter, pins the light values, asserts that no token exists in a dark block that is not on `:root`, and runs every pair in both themes, with `focus`/`surface` at least 3 and `rail-ink`/`rail-hover` at least 4.5.
- The no-flash script is a static string built in the server `layout.tsx` from the exported storage key, with the whole `window.localStorage` access inside the `try`.
- The browser audit got a `--theme` option and CI runs it in both themes (a supervisor task, outside `frontend/`).
