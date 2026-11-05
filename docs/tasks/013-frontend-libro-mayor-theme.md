# Task 013: frontend "Libro mayor" light theme

Assignee: Worker 2. Branch: `w2/libro-mayor`. Reviewer: Supervisor.

## Goal

Give the whole web app (login, application shell, customers screens) the visual design the owner chose, "Libro mayor": a warm paper background, dark green ink, a fixed side rail for navigation, and tables in the style of an accounting ledger. This task changes how things look, not what they do: every `data-testid`, every text, every behavior and every existing test stays as it is, except for the few additions listed below. The dark theme comes in a later task, so everything you write must be ready for it: colors live only in design tokens.

## Read first

`docs/TESTABILITY.md` (test ids and the rules for markup), `frontend/README.md`, and the current files you will restyle: `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx`, `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/login/page.tsx`, `frontend/src/components/ui/`, `frontend/src/app/(app)/customers/` and `frontend/src/features/customers/CustomerForm.tsx`.

## Scope

You may edit files only under `frontend/`. No new dependencies. Fonts come from `next/font/google` (IBM Plex Sans and IBM Plex Serif), which needs no package. Do not change any `data-testid`, any visible text (except the additions below), any hook, API call or route, and do not delete or weaken a test. Existing tests must keep passing unchanged; if one fails because of a class name or a DOM nesting you introduced, change your markup, not the test, unless the test asserts something that is purely visual.

## Design tokens

Define every color once, in `globals.css`, as CSS custom properties on `:root` and expose them to Tailwind with `@theme inline` so utilities such as `bg-paper` and `text-ink` exist. Components use only these utilities. A hex color, `rgb()`, or a Tailwind palette class (`gray-200`, `green-700`, `bg-white`, `text-black`) outside `globals.css` is forbidden.

| Token | Value | Use |
|---|---|---|
| `paper` | `#FBFAF6` | page background |
| `surface` | `#FFFFFF` | inputs, cards, table body |
| `ink` | `#18241F` | main text, table header rule |
| `muted` | `#5B6B63` | secondary text, labels |
| `line` | `#D9D4C5` | decorative separators, row rules |
| `control-border` | `#8A8470` | borders of inputs and selects |
| `rail` | `#14342B` | side rail background |
| `rail-ink` | `#E8F0EA` | text on the rail |
| `rail-muted` | `#A9C2B6` | links on the rail |
| `rail-hover` | `#1D4A3D` | hovered link on the rail |
| `accent` | `#0F5B46` | primary buttons, links, active badge text |
| `accent-ink` | `#FFFFFF` | text on `accent` |
| `ok-bg` | `#DCEBE3` | active badge background |
| `off-bg` | `#ECE9DF` | inactive badge background |
| `danger` | `#A3261B` | error text |
| `danger-bg` | `#F9E1DE` | error background |
| `focus` | `#1F8A6C` | focus ring |

Add a test that parses the tokens from `globals.css` and checks these WCAG contrast ratios (write the small contrast function in the test): `ink`/`paper` and `muted`/`paper` at least 4.5; `muted`/`surface` at least 4.5; `rail-ink`/`rail`, `rail-muted`/`rail` and `rail-muted`/`rail-hover` at least 4.5; `accent-ink`/`accent` at least 4.5; `accent`/`ok-bg`, `muted`/`off-bg` and `danger`/`danger-bg` at least 4.5; `accent`/`paper` at least 4.5; `control-border`/`surface` and `focus`/`paper` at least 3. Add a second test that scans every `.ts`, `.tsx` and `.css` file under `src/` except `globals.css` and the tests themselves and fails on a hex color, `rgb(`, `hsl(` or a Tailwind palette color class, so the dark theme can be added by changing `globals.css` alone.

## Typography and rhythm

- Body: IBM Plex Sans 400, 15px, line height 1.5, color `ink`. Headings `h1` and the brand: IBM Plex Serif 600, `h1` 28px with line height 1.1. Table numbers and counts use `tabular-nums`. Loaded with `next/font/google` and `display: "swap"`, exposed as CSS variables, with `system-ui` and `Georgia` fallbacks.
- Spacing on a 4px scale; page content padded 24px on the sides from 768px up and 16px below. Text blocks wider than about 70 characters are not needed here.
- No animation except a 120ms color transition on buttons and links, disabled under `prefers-reduced-motion: reduce`.

## Components (`src/components/ui/`)

1. `Button` gets an optional `variant`: `"primary"` (default, `accent` background, `accent-ink` text, 6px radius, padding 9px 14px, weight 600), `"secondary"` (transparent, `accent` text and a 1px `accent` border) and `"rail"` (transparent, `rail-ink` text, no border, for the logout button). Disabled and loading buttons keep a visible shape at 55% opacity and `cursor-not-allowed`. Minimum height 38px (44px under 768px).
2. `Link` gets an optional `variant`: `"text"` (default: `accent` text, underlined, thicker underline on hover), `"primary"` and `"secondary"` (look like the matching buttons, for links that act as buttons such as "Nuevo cliente"), and `"rail"` (for the rail navigation). The `href`, `testId` and every existing prop keep working.
3. `Input`, `Select`, `Textarea` (through `Field`): label above the control, weight 500, 13px, `ink`; control 38px high (textarea min 96px), `surface` background, 1px `control-border`, 6px radius, 10px horizontal padding; the error paragraph (`role="alert"`) in `danger`, 13px, with 4px top margin, and the control gets a `danger` border when it has an error. Do not remove `aria-invalid` or `aria-describedby`.
4. A global focus style for `a`, `button`, `input`, `select`, `textarea`: `outline: 3px solid var(--color-focus)` with a 2px offset on `:focus-visible`. Never remove an outline without replacing it.
5. A small `Alert` component (`role` stays on the element the screens already use; do not move test ids) is allowed if it reduces repetition: `danger-bg` background, `danger` text, 6px radius, padding 10px 12px, weight 500. The existing `role="alert"` paragraphs of the login, shell, list, detail and form pages use it or the same classes.

## Screens

1. **Application shell** (`src/app/(app)/layout.tsx`). From 768px up: a fixed-width rail (212px) on the left, full height, `rail` background, containing the brand "LabApp" (serif, 18px, with a small inline SVG mark you draw yourself, `aria-hidden`), the main navigation (Clientes, Pedidos, Facturas; each link 38px high, 6px radius, `rail-muted` text; the current section has `paper` background and `ink` text with weight 600 and `aria-current="page"`; hover uses `rail-hover`), and at the bottom, separated by a 1px rule, the user's name, the role in `rail-muted`, and the "Salir" button (`rail` variant). The content area is `paper`. Below 768px the rail becomes a top bar: brand and "Salir" on one row, the three links in a horizontally scrollable row underneath (no hamburger, no JavaScript), user name and role under the brand. Use real icons drawn as inline SVG (16px, `currentColor`, `aria-hidden`), never emoji. Keep the `nav` with `aria-label="Principal"`, the order of the focusable elements and all test ids. The current section is derived with `usePathname`.
2. **Login** (`src/app/login/page.tsx`). From 768px up, two columns: on the left a `rail` panel with the brand and the sentence "Del pedido al cobro, sin perder el hilo." in serif 32px (this text is new and has the test id `auth-login-tagline-text`), and a second smaller line "Demostración pública. Los datos se reinician cada noche." (`auth-login-notice-text`); on the right the form column with the heading, the error alert, the form and the demo users box (a bordered `surface` card, the list as definition-like rows with the email on the left and the role in `muted` on the right). Below 768px the left panel is hidden and the form takes the whole width. The existing heading, fields, button and demo users keep their test ids.
3. **Customers list.** Page heading row: `h1` and, on the right, "Nuevo cliente" as a `primary` link (wraps below the heading on narrow screens). The search form on one row (field, select, "Buscar" as `secondary`), wrapping on narrow screens, with 12px gaps and bottom alignment. The table lives in a wrapper with `overflow-x-auto`; `th` 12px uppercase, letter spacing 0.07em, `muted`, a 2px `ink` rule under the header row; cells padded 9px 10px with a 1px `line` rule under each row; the customer name link in weight 500; hovered rows slightly darker (a tint made from `ink` at low opacity, via `color-mix`); empty values "—" in `muted`. The state cell shows a badge (`ok-bg`/`accent` for "Activo", `off-bg`/`muted` for "Inactivo", 12px, weight 600, 4px radius) inside the existing `td`, with the same text as today. Under the table, the ledger footer: a row with a 4px double `ink` rule above it holding the total text ("10 clientes") on the left in weight 600 and the pagination (Anterior, "Página X de Y", Siguiente as `secondary` buttons) on the right, wrapping on narrow screens; keep `customers-list-total-text`, `customers-list-page-text` and the buttons' test ids where they are. Loading, empty and error states: plain `muted` text for loading and empty, the `Alert` for errors with its "Reintentar" button.
4. **Customer form (create and edit).** A single column of at most 520px; heading `h1`; fields stacked with 16px gaps; the form-level alert above the fields; "Guardar" as `primary` and "Cancelar" as a `text` link on one row (stacked and full width below 768px).
5. **Customer detail.** `h1`; a card (`surface`, 1px `line` border, 8px radius, 20px padding) with the values as a two-column grid from 640px up (label in `muted` 13px, value in `ink`; long names wrap, never overflow); the status as the same badge; the actions row below: "Editar" as `secondary` link, "Desactivar" or "Reactivar" as `secondary` button, and "Volver a clientes" as a `text` link.
6. **Home** (`src/app/(app)/page.tsx`) and the Orders and Invoices placeholders: only the heading style and spacing.

## Rules of markup that must survive

Semantic HTML stays: real `table`, `th scope="col"`, `label` linked to its control, `nav`, `main`, `h1`. Headings do not skip levels. Do not use `div` buttons. Color is never the only carrier of meaning (the badge keeps its text). Nothing may cause horizontal scrolling of the page at 360px width (wide content scrolls inside its own wrapper). Touch targets are at least 38px high (44px below 768px).

## Tests and docs

- New tests: the two token tests above; `Button` and `Link` variants (class presence, `disabled`/`loading` unchanged); the shell marks the current section with `aria-current="page"` (for `/customers`, `/orders`, `/invoices` and a nested `/customers/7`); the login shows the two new texts with their test ids; the list renders the badge text and the ledger footer with the total text inside it; every new test id passes `isValidTestId`.
- `frontend/README.md`: a short "Design" section: the token table by name (not the values), how to add a theme by changing `globals.css` only, and the two guard tests.

## Acceptance criteria

From `frontend/`, all of these pass:

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

## Rules for this task

- Commit as you go, in small real steps (about 14 to 20 commits): the tokens and their tests, the fonts, each component, the shell, the login, the list, the form, the detail, the README. Conventional Commits, in English, for example `style(frontend): add the Libro mayor design tokens`.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory.
- If the brief is ambiguous or two requirements collide, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question. You cannot see the result in a browser; say so, and list the choices you made that only a visual check can confirm.

## Corrections after the review

A second agent reviewed this brief while the work was under way. These corrections were sent to the implementer and are part of the task as delivered:

- **Existing tests.** `src/app/(app)/layout.test.tsx` and `src/app/auth-flow.test.tsx` gained `usePathname` in their `next/navigation` mocks, and one assertion of `src/app/login/page.test.tsx` (the `"· "` separator of the demo-user rows) was relaxed to the email and the role label. No other test was changed.
- **Tailwind and fonts.** Element rules live in `@layer base`; the font variables have their own names (`--font-plex-sans`, `--font-plex-serif`); IBM Plex Sans at weights 400, 500 and 600, IBM Plex Serif at 600, Latin subset; the font calls are only in the root layout.
- **Tokens.** A new `accent-hover` token (`#0B4A38`); more contrast pairs are tested (`focus`/`rail`, `danger`/`paper`, `danger`/`surface`, `accent-ink`/`accent-hover`); the literal-color guard also rejects `rgba(`, `hsla(`, `oklch(`, `oklab(`, `lab(`, `lch(`, `hwb(`, `color(` and Tailwind palette classes.
- **Layout.** The DOM order of the shell is brand, navigation, user block; below 768px the user block is a row under the links. Scrolling containers have 6px of padding so the focus ring is not clipped. The rail is 212px wide and sticky. Inputs use 16px text below 768px. The ledger footer is a wrapper with the test id `customers-list-footer-item`, holding the total text and the pagination `nav`.
- **After the first visual check** (screenshots of the running app): the ID fiscal and Estado cells do not wrap, the list table has a minimum width so the wrapper scrolls on a phone, and the customer form column is left aligned.
