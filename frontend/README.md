# LabApp frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS + TanStack Query.
The test id contract implemented here is defined in `docs/TESTABILITY.md`.

## Requirements

- Node `24.22.2` and pnpm `12.16.1` (pinned in the repository's `mise.toml`).

## Commands

Run from this `frontend/` directory:

```bash
# install (exact versions from pnpm-lock.yaml)
pnpm install --frozen-lockfile

# dev server
pnpm dev

# production build, then server
pnpm build
pnpm start

# lint (ESLint, Next.js + TypeScript presets, zero warnings)
pnpm lint

# type check
pnpm typecheck

# unit tests (Vitest + Testing Library, jsdom)
pnpm test
```

## Layout

```
src/
  app/        layout ( providers + hydration marker) and pages
  components/
    ui/       Button, Input, Select, Textarea, Link — interactive elements
              take a required testId; fields also share Field
  lib/        testid.ts — the test id grammar: pattern, type and helpers
  test/       Vitest setup
```

## Test id contract

- The grammar (`<module>-<name>-<kind>` with the numeric record id as the
  final suffix), the kind table and the observable state attributes are
  defined in [docs/TESTABILITY.md](../docs/TESTABILITY.md); the enforced
  pattern lives in `src/lib/testid.ts` as `TEST_ID_PATTERN`.
- Every interactive element renders `data-testid` built from `TestId`.
- `Button` exposes `data-state` (`idle`/`loading`) and `aria-busy`.
- `Input`, `Select` and `Textarea` render field errors as
  `<p role="alert">` with the test id derived by `errorTestId()` and
  linked from the control via `aria-describedby`; `Select` takes its
  options as children.
- `Link` wraps `next/link` and always renders `data-testid`.
- The hydration marker sets `data-hydrated="true"` on `<body>` once the
  client has hydrated.
