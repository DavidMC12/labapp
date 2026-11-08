# Review: security headers of the web app (task 045, 2026-11-08)

- **Branch:** `w2/security-headers`, by Worker 2 (6 commits, inside `frontend/` and `docs/DEPLOYMENT.md`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Verified by the supervisor:** a production build (`next build`, then `next start`) served over a real API in a detached checkout. `curl -I /login` shows the five headers and the Content-Security-Policy; `/api/docs` and `/api/openapi.json` answer 200 **without** any of them (the exclusion works). A headless Chromium opened `/login`, signed in through the real form and visited `/`, `/customers`, `/orders`, `/invoices`, `/products`, `/settings` and a 404 page: no CSP violation, no console error, no blocked request, the page titles are right and the theme script still sets `data-theme` under the policy. The commands of the task (install, lint, typecheck, coverage, build, test id audit, documentation lint) and the browser audit in both themes were re-run with real exit codes.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | The site has no favicon: `GET /favicon.ico` answers 404 and Chromium logs it on every page. | Next task (icon). |
| 2 | Note | `next start` reads the rewrites from the build, so `API_URL` must be set when running `pnpm build`, not only when serving. Worker 2 found it while testing. | Not an issue online (the platform does the routing); noted here for anyone who runs the production server locally. |

## Declined to judge

- The Content-Security-Policy keeps `'unsafe-inline'` for scripts and styles because of the framework bootstrap and the no-flash theme script. A nonce-based policy is the stated next step; it needs a request-time nonce and so dynamic rendering of every page.
