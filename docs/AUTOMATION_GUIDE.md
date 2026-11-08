# Automation guide

LabApp is a small order-to-cash ERP (customers, orders, invoices, payments) built to be automated: it is the application a QA engineer drives with Playwright when learning the suite. This is **part 1: the web UI** — how to start it, how to locate everything, what the screens contain, and how the three core flows behave. Part 2 (the test controls — reset, seed, clock, faults — and the HTTP API contract) follows after those parts exist.

Every id, URL, label and message here was read from the code and the documents ([TESTABILITY](TESTABILITY.md), [TESTIDS](TESTIDS.md), [SEED](SEED.md), [SPEC section 2–6 and 8](SPEC.md)). The generated catalog [TESTIDS.md](TESTIDS.md) is the source for ids; this guide links it instead of copying it.

## 1. Start in five minutes

```bash
mise install    # once: Node, pnpm and uv at the pinned versions
mise run dev    # API on 127.0.0.1:8000, web on http://localhost:3000
```

The script ([docs/DEVELOPMENT.md](DEVELOPMENT.md)) installs dependencies if needed and starts both processes. For UI tests point Playwright at **`http://localhost:3000`**: the web dev server forwards `/api/*` and `/__test__/*` to the API, so the browser sees one origin, as it does online. By default the data lives in memory: it is the seed below, and it is lost when the processes restart.

Log in at `/login` with one of the four seeded users. The login screen lists them with the shared password (demo list `auth-login-demo-list`, items `auth-login-demo-item-1` to `auth-login-demo-item-4`, password line `auth-login-demo-password-text`).

| Email | Role |
|---|---|
| `admin@labapp.test` | Admin |
| `sales@labapp.test` | Sales |
| `finance@labapp.test` | Finance |
| `readonly@labapp.test` | Read-only |

Password for all four: `Demo-LabApp-2026!`. What each role can do ([SPEC section 2](SPEC.md); the server enforces every rule, the UI only hides controls):

| Action | Admin | Sales | Finance | Read-only |
|---|---|---|---|---|
| View customers, products, orders, invoices, payments | yes | yes | yes | yes |
| Create, edit, deactivate and reactivate customers | yes | yes | no | no |
| Create and edit Draft orders; confirm, cancel, ship | yes | yes | no | no |
| Create invoices and register payments | yes | no | yes | no |
| Change the tax rate | yes | no | no | no |

**Online demo vs local.** There is no deployed demo yet (see [docs/DEPLOYMENT.md](DEPLOYMENT.md) — configured, not deployed); when it exists it lives on the project's Vercel URL. Tell them apart by the hostname, `localhost:3000` versus the `https://` deployment URL, and by the data:

- **Local:** in-memory data, restored from the seed on every start; `TEST_MODE=1`, so the request rate limits are off.
- **Online:** one shared dataset (strangers may move it between your runs), rate limits active — 120 requests per minute and 10 login attempts per minute per client IP; exceeding one answers HTTP 429 with code `RATE_LIMITED` and the message `Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.` ([SPEC section 3](SPEC.md)). A nightly reset workflow at 03:17 UTC restores the seed, but it only works once the test controls are deployed (task 022, part 2 of this guide).
