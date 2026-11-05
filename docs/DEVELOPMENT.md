# Local development

## Start everything

```bash
mise install          # once: Node, pnpm and uv at the pinned versions
mise run dev          # or: scripts/dev.sh
```

The script installs the dependencies if needed and starts the API on <http://127.0.0.1:8000> and the web app on <http://localhost:3000>. Open the web address and log in with one of the demo users shown on the login screen. The web dev server forwards `/api/*` and `/__test__/*` to the API, so the browser sees a single origin, as it does online. Press Ctrl+C to stop both.

By default the data lives in memory and is lost on restart. The script turns `TEST_MODE` on, which switches the rate limits off and enables the test-only controls (see [ARCHITECTURE.md](ARCHITECTURE.md)).

| Variable | Default | Meaning |
|---|---|---|
| `API_PORT`, `WEB_PORT` | `8000`, `3000` | Ports of the two processes. |
| `TEST_MODE` | `1` | Test-only controls on, rate limits off. |
| `SESSION_SECRET` | a development value | Application secret; never reuse it online. |
| `DATABASE_URL` | unset | Use a PostgreSQL database instead of memory (see below). |

## Use a database

Put the connection strings in `backend/.env` (it is ignored by git; see `.env.example`), apply the migrations and load the seed data:

```bash
cd backend
uv run python -m app.cli migrate
uv run python -m app.cli seed
```

Then run `scripts/dev.sh` as usual. Never commit a connection string.

## Run the checks

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest -q -W error
cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

The backend integration tests need a direct (unpooled) database URL in `TEST_DATABASE_URL`; without it they are skipped. They create a random schema, run the migrations in it and drop it at the end, never touching `public`:

```bash
cd backend && TEST_DATABASE_URL=... uv run pytest tests/integration
```
