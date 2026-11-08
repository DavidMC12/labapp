# Deployment

The demo runs as one Vercel project made of two services (Vercel Services, a beta feature available on the free plan) plus a Neon PostgreSQL database. The configuration in [`vercel.json`](../vercel.json) follows the Vercel documentation and **has not been deployed yet**: the first deployment is also the test of this file.

| Service | Root | What it is | Receives |
|---|---|---|---|
| `backend` | `backend/` | FastAPI, entrypoint `app.main:app` | `/api/*` and `/__test__/*` |
| `frontend` | `frontend/` | Next.js | everything else |

Both services answer on one domain, so the session cookie is first party and the browser sends no cross-origin request. FastAPI receives the original path (`/api/customers`), which is how its routes are declared. The `/__test__/*` routes (the test controls) are guarded by the test token and answer 404 to anything else (see [ARCHITECTURE.md](ARCHITECTURE.md)).

## Create the project

1. In Vercel, add a project from the GitHub repository and set the **Root Directory** to the repository root. If the dashboard offers a Services framework preset, choose it; otherwise the `services` key of `vercel.json` is what selects the mode (check this in the dashboard: it is the first thing the first deployment tests).
2. Add the environment variables below **before** the first deployment, for Production and Preview.
3. Enable "Automatically expose System Environment Variables": the origin check uses `VERCEL_URL` and its siblings to accept the origin of each preview deployment.
4. Deploy. The backend build runs `python -m app.cli deploy --production-only` (through `[tool.vercel.scripts]` in `backend/pyproject.toml`): it applies the database migrations over the direct connection and loads the demo data into an empty database, **only on a Production deployment**. Preview deployments skip it, because they share the database unless the Neon integration gives each one its own branch, and a migration of an unmerged branch must not change the schema that production uses. Set `RUN_MIGRATIONS_ON_PREVIEW=1` once every preview has its own database. Concurrent builds wait for each other (an advisory lock).

## Environment variables

| Variable | Value |
|---|---|
| `DATABASE_URL` | The pooled Neon connection string (host with `-pooler`). Runtime queries. |
| `DATABASE_URL_UNPOOLED` | The direct Neon connection string. Migrations only. |
| `SESSION_SECRET` | A long random value. The API refuses to start with a placeholder. |
| `TEST_MODE` | `0`. Never `1` in a public deployment. |
| `TEST_TOKEN` | A long random value; sent as `X-Test-Token` by the test suites that use `/__test__/*`. Leave empty to disable the controls. |
| `APP_ORIGIN` | The production URL, for example `https://labapp.vercel.app`. Preview origins are added from the platform variables. |
| `TRUSTED_PROXY_COUNT` | `1`, so the client IP is the entry the platform appends to `X-Forwarded-For`. Check it on the first deployment. |
| `DEFAULT_TAX_RATE` | `10` |
| `LOCK_TIMEOUT_MS` | `5000` (the default). The longest wait for a row lock before a request answers 503 `LOCK_TIMEOUT`. |

The Neon integration for Vercel can create `DATABASE_URL` and `DATABASE_URL_UNPOOLED` and a database branch per preview deployment. Without it, every preview shares one database.

## After the first deployment

- `GET /api/health` answers 200. The contract is at `GET /api/openapi.json` and the Swagger UI at `GET /api/docs`; log in on the web app first so "Try it out" sends the session cookie.
- Log in with a demo user from the login screen; reload the page and stay logged in.
- `POST /__test__/reset` answers 404 without a token and 200 with `X-Test-Token: <TEST_TOKEN>`; then `GET /api/customers` (after logging in) lists the 10 seeded customers. The nightly workflow does the same call.
- Rotate the database password and update the two connection strings if the string was ever pasted into a chat or a ticket.

## Security headers

The web app sends five headers on every page (`next.config.ts`):
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`, a
`Permissions-Policy` that switches off camera, microphone, geolocation,
payment and usb, and `Cross-Origin-Opener-Policy: same-origin`. A strict
`Content-Security-Policy` (`default-src 'self'` with `frame-ancestors
'none'`, `object-src 'none'` and no remote origins) is added **in
production only**: in development Next.js needs `eval` and inline styles
for its error overlay, so no CSP is sent there.

The `source` of the entry excludes the API: `/((?!api|__test__).*)`
never matches `/api/*` or `/__test__/*`. Those paths are served by the
API service (the local rewrite forwards them), and their responses must
not carry the web app's policy — the Swagger page that `/api/docs`
serves loads its assets from a CDN, which `default-src 'self'`
forbids. `'unsafe-inline'` for scripts is what the framework's own
inline bootstrap and the no-flash theme script need; a nonce-based
policy is the next step after the first real deployment.

## Nightly reset

The workflow [`nightly-reset.yml`](../.github/workflows/nightly-reset.yml) calls `POST /__test__/reset` every day at 03:17 UTC and can be started by hand from the Actions tab. It needs two settings in the GitHub repository (Settings, Secrets and variables, Actions):

| Name | Kind | Value |
|---|---|---|
| `DEMO_URL` | Variable | The production URL, for example `https://labapp.vercel.app` |
| `TEST_TOKEN` | Secret | The same value as `TEST_TOKEN` in Vercel |

Without `DEMO_URL` the job shows as skipped; with it but without the secret the job fails. Only an exact HTTP 200 counts as a reset (a redirect fails, and redirects are never followed, so the token cannot leave the configured host). It cannot work before the test controls (task 022) are deployed.

## Known limits

- GitHub disables scheduled workflows of a repository with no activity for 60 days. The nightly reset then stops without any error: a push or a re-enable from the Actions tab starts it again.
- Vercel Services is in beta. Function limits of the free plan apply to each service: 300 seconds, 2 GB of memory, a 500 MB Python bundle and 4.5 MB request bodies.
- A function instance may be frozen or replaced between requests and several run in parallel, so nothing stateful lives in memory in production: sessions, the clock offset, fault rules, idempotency keys and every record are stored in PostgreSQL. The one exception is the rate-limit counters, which are per instance and best effort.
- Every preview deployment shares the database unless the Neon integration creates a branch per preview.
