# Online smoke test

One command answers the question "is the online demo working?" after a
deployment, on a preview or against the local stack. It needs no dependencies
(Node's built-in `fetch`) and no running test framework: the command runs the
checks in order, prints one line per check and exits non-zero when one fails.

```bash
node tools/smoke/online-smoke.mjs --base https://example.vercel.app
```

The base is the web origin (the Vercel deployment, a preview URL or the local
web app): the API lives behind the same origin under `/api/*` and `/__test__/*`,
exactly as a browser sees it.

## Flags

| Flag | Meaning |
|---|---|
| `--base <url>` | Required. A deployment, a preview or `http://localhost:<port>` (the local stack). |
| `--token <token>` | The `TEST_TOKEN` of the deployment, sent as `X-Test-Token` to `/__test__/*`. Falls back to the environment variable `TEST_TOKEN`. It is never printed. |
| `--allow-reset` | Calls `POST /__test__/reset` and creates one customer, then deactivates it. Without this flag the shared data is never reset or written. |
| `--json` | Prints the report as one JSON document (`base`, `local`, `checks`, `summary`) instead of lines. |
| `-h`, `--help` | The usage text. |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Every check passed (warnings, skipped checks and info lines do not fail the run). |
| `1` | At least one check failed. |
| `2` | The command line is invalid, or `docs/SEED.md` cannot be read. |

## What the checks prove

**Web.** `/` and `/login` answer `200 text/html`; `/login` has the title
`Iniciar sesión · LabApp` and the security headers of
[DEPLOYMENT.md](../../docs/DEPLOYMENT.md) (`nosniff`, `X-Frame-Options: DENY`);
`/no-such-page` is a `404` with the title `Página no encontrada · LabApp`;
`/icon.svg` answers `200` with an image type. The `Content-Security-Policy`
check is skipped on `localhost` and `127.0.0.1`, because Next.js sends the
policy in production only.

**API basics.** `/api/health` answers `200` (a cold start can take seconds, so
the check retries up to five times, five seconds apart). `/api/openapi.json` is
JSON with the paths `/api/customers`, `/api/orders`, `/api/invoices` and
`/api/customers/import`; `/api/docs` is HTML. Both documents carry `nosniff`
and no `Cache-Control`. A read without a session is a `401
UNAUTHENTICATED` problem document with `nosniff` and `no-store`, and an unknown
API path is a `404 NOT_FOUND` with the same two headers.

**The four users.** Every demo user of [SEED.md](../../docs/SEED.md) logs in
with the password of that document, gets a `labapp_session` cookie (`HttpOnly`,
`SameSite=Lax`, `Secure` on https) and reads its own role from
`/api/auth/me`. A wrong password is `401 INVALID_CREDENTIALS`; a logout ends
the session, so the same cookie answers `401` afterwards.

**Reads through the web origin, as Sales.** The customers list has `items` and
`total`, the products list has 15 items (a different number is a `warning`, not
a failure: the shared demo changes during the day), the customers export is
`text/csv` with the SPEC header line and `Content-Disposition`, the sorted list
answers `200`, and `?sort=bogus` is a `422`.

**The origin rule.** A write with a wrong `Origin` is `403
CSRF_ORIGIN_MISMATCH`; a write without `Origin` (a logout) is accepted.

**The test controls.** `POST /__test__/reset` without a token and with a wrong
token is a `404` (with `nosniff`): the controls stay closed on a deployment
that runs with `TEST_MODE=0`. With `--token`, `GET /__test__/clock` answers
`200`.

**A write and its cleanup** (only with `--allow-reset`). After the reset the
customers list has `total` 10; a new customer can be created, read back and
deactivated (the demo has no delete), and the list grows by one.

## The local stack

The local start script runs with `TEST_MODE=1`, so the controls answer without
a token. When the no-token probe gets a `200` from a base on `localhost` or
`127.0.0.1`, the run reports it as `info`, not as a failure: that is the
documented local behavior, and the probe has just restored the seed data. On
any other host a `200` there is a failure (`TEST_MODE` must be `0` online).

```bash
WEB_PORT=3400 API_PORT=8400 DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh
node tools/smoke/online-smoke.mjs --base http://localhost:3400
node tools/smoke/online-smoke.mjs --base http://localhost:3400 --allow-reset
```

## Why `reset` needs `--allow-reset`

A deployment owns one shared set of demo data, and `POST /__test__/reset`
replaces it with the seed. The command therefore calls it only when
`--allow-reset` is passed (the one exception is the closed-controls probe
above, which changes nothing on a deployment whose controls answer `404`).
The reset also removes the records of every visitor who is working on the demo
at that moment; run it by hand, not on a schedule, and never on a demo in use.

## From GitHub Actions

The workflow [`smoke-online.yml`](../../.github/workflows/smoke-online.yml) is
manual only (`workflow_dispatch`). It asks for the base URL and the
`allow_reset` boolean, reads the token from the `TEST_TOKEN` repository secret
and runs the same command. Use it from the Actions tab after a deployment, and
leave `allow_reset` off unless you mean to reset the shared demo.

## Tests of the helpers

```bash
node --test tools/smoke/checks.test.mjs
```

The tests need no network: they call the pure helpers of
[`checks.mjs`](checks.mjs) (header assertions, the session-cookie attributes,
the problem-body check and the retry policy with an injected clock, sleep and
fetch) with a good answer and with a bad one.
