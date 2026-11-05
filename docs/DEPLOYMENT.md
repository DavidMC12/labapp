# Deployment

The demo runs as one Vercel project made of two services (Vercel Services, a beta feature available on the free plan) plus a Neon PostgreSQL database. The configuration in [`vercel.json`](../vercel.json) follows the Vercel documentation and **has not been deployed yet**: the first deployment is also the test of this file.

| Service | Root | What it is | Receives |
|---|---|---|---|
| `backend` | `backend/` | FastAPI, entrypoint `app.main:app` | `/api/*` and `/__test__/*` |
| `frontend` | `frontend/` | Next.js | everything else |

Both services answer on one domain, so the session cookie is first party and the browser sends no cross-origin request. FastAPI receives the original path (`/api/customers`), which is how its routes are declared. The `/__test__/*` routes are guarded by the test token and answer 404 to anything else (see [ARCHITECTURE.md](ARCHITECTURE.md)).

## Create the project

1. In Vercel, add a project from the GitHub repository and set the **Root Directory** to the repository root and the framework preset to **Services**.
2. Add the environment variables below **before** the first deployment, for Production and Preview.
3. Enable "Automatically expose System Environment Variables": the API uses `VERCEL_URL` and its siblings to accept the origin of each preview deployment.
4. Deploy. The backend build applies the database migrations (`python -m app.cli migrate`, through `[tool.vercel.scripts]` in `backend/pyproject.toml`) over the direct connection before the new version goes live.

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

The Neon integration for Vercel can create `DATABASE_URL` and `DATABASE_URL_UNPOOLED` and a database branch per preview deployment. Without it, every preview shares one database.

## After the first deployment

- `GET /api/health` answers 200.
- Log in with a demo user from the login screen; reload the page and stay logged in.
- `POST /__test__/reset` answers 404 without a token and 200 with `X-Test-Token: <TEST_TOKEN>`.
- Rotate the database password and update the two connection strings if the string was ever pasted into a chat or a ticket.

## Known limits

- Vercel Services is in beta. Function limits of the free plan apply to each service: 300 seconds, 2 GB of memory, a 500 MB Python bundle and 4.5 MB request bodies.
- A function instance does not outlive a request, so nothing stateful lives in memory in production: sessions, rate-limit counters, the clock offset, fault rules and idempotency keys are stored in PostgreSQL. Until the tasks that move them there are merged, the in-memory rate limits are best effort (per instance).
- Every preview deployment shares the database unless the Neon integration creates a branch per preview.
