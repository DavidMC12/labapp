# Review: a truth audit of the deployment, development and architecture documents (task 071, 2026-11-08)

- **Branch:** `w2/docs-truth-audit`, by Worker 2 (4 commits; documents and `.env.example` only).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **What it did:** read `docs/DEPLOYMENT.md`, `docs/DEVELOPMENT.md` and `docs/ARCHITECTURE.md` like a person following them with no other help, ran every safe local command (the start script, the CLI `--help` of the five commands, the contract export and its diff, the lint, the tests, the frontend gates and both dependency audits) and read the rest against the code, the workflows and `vercel.json`. Four corrections: ARCHITECTURE named `products`, `payments` and `settings` as backend modules (the real ones are `auth`, `customers`, `orders`, `invoices` and `testcontrols`); the Neon claims that cannot be verified from the repository now say "not verified in a real deployment"; `.env.example` documents `DATABASE_SCHEMA`, which the code reads; the first paragraph of `backend/README.md` still said there was no database, authentication or business logic. One short new section, "If something goes wrong" in `docs/DEPLOYMENT.md`, built only from behavior seen in the code.
- **Verified by the supervisor:** the documentation linter and the documentation tests exit 0. The new section was checked line by line against the code: `CSRF_ORIGIN_MISMATCH` and the `APP_ORIGIN` rule; the lock timeout (`LOCK_TIMEOUT_MS`, default 5000, range 100 to 60000, and the log line `Lock wait timed out on <method> <path>`); `SERVICE_BUSY` on login (a semaphore of two concurrent hashes, Argon2 with its default 64 MiB); `RATE_LIMITED` with `Retry-After` (120 requests and 10 login attempts a minute per client IP; the health check is excluded; `TRUSTED_PROXY_COUNT` defaults to 0); the schema rules of `DATABASE_SCHEMA` (lowercase, digits, underscores, `public` and `pg_*` refused): all true.

## Problems reported and not changed (the brief forbids touching code and configuration)

| # | Item | Disposition |
|---|---|---|
| 1 | The moderate advisory in a development-only dependency (`minimatch`). | Already recorded in `2026-11-08-dependency-audit.md`; production is clean. |
| 2 | Claims about the platforms (Vercel Services beta, Hobby limits, cold starts, the Neon integration) cannot be verified from the repository. | They stay as caveats; the first real deployment will settle them. |
| 3 | `backend/.env.example` does not exist; the documents point to the root `.env.example`, which is correct. | Nothing to do. |
