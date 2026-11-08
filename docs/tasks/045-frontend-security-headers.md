# Task 045: security headers of the web app, and a spacing fix on the login

Assignee: Worker 2. Branch: `w2/security-headers`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

The web app sends no security headers. A public demo should at least refuse to be framed, refuse content sniffing, send a minimal referrer and, in production, restrict what the page may load. Add them through `next.config.ts`, carefully: the API paths are served by the API service online (and proxied locally) and must not receive the web app's Content-Security-Policy (the Swagger page at `/api/docs` loads its assets from a CDN). Also fix a visual defect found in screenshots: on the login the theme selector sits almost on top of the heading "Iniciar sesión".

## Read first

`frontend/next.config.ts` and its test, `frontend/src/app/layout.tsx` (the inline no-flash theme script, the fonts through `next/font`), `frontend/src/app/login/page.tsx` (the top of the form column, the theme selector), the Next.js documentation of `headers()` in `node_modules/next/dist/docs/` for the installed version (read it, do not rely on memory), `docs/DEPLOYMENT.md`, `frontend/README.md`.

## Scope

You may edit `frontend/next.config.ts`, its test, `frontend/src/app/login/page.tsx` and its tests (spacing classes only), `frontend/README.md` and `docs/DEPLOYMENT.md` (one short section: what headers the web app sends and why the API paths are excluded). No new dependencies. Do not change any `data-testid` or text.

## Requirements

1. **Headers for every page of the web app** (a `headers()` entry whose `source` excludes `/api` and `/__test__`, for example `/((?!api|__test__).*)`; write a test that the regular expression does not match `/api/docs`, `/api/openapi.json` and `/__test__/reset` and matches `/`, `/login`, `/orders/3`):
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()`
   - `Cross-Origin-Opener-Policy: same-origin`
2. **Content-Security-Policy in production only** (`process.env.NODE_ENV === "production"`; in development Next needs `eval` and inline styles for its overlay, so none is sent): `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'`. `'unsafe-inline'` for scripts is needed by the framework's own inline bootstrap and by the no-flash theme script; say so in a comment and in the README, and note that a nonce-based policy is the next step. The headers are built by an exported pure function (like `apiRewrites`) so that it can be unit tested with and without `NODE_ENV`.
3. **Check it for real.** Build and start the production server (`pnpm build` then `next start`) and fetch `/login`, `/` and a static asset with `curl -I`; the report lists the headers you saw. Then open the login page in a real browser if you can (you cannot: say so) and state what only a browser run can confirm: that no CSP violation appears in the console. The supervisor will run that check.
4. **Login spacing.** On the login, give the theme selector row enough room above the heading (at least 1.5rem of space between the bottom of the selector and the top of the heading on a wide screen, and 1rem on a phone), without moving the heading or the form on a phone more than that.
5. **Tests.** The pure function with and without `NODE_ENV=production`; the `source` pattern as described; the exact header names and values; the login classes. Keep all tests passing.
6. **Docs.** The README sentence and the `docs/DEPLOYMENT.md` section.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` and `node tools/audit/docs-lint.mjs` report no problem; and the `curl -I` check of requirement 3.

## Rules for this task

- Commit as you go, in small real steps (about 6 to 8 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the headers you saw with `curl -I`, and any deviation or open question.
