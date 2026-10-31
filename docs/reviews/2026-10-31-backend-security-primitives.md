# Review: backend security primitives (task 006, 2026-10-31)

- **Branch:** `w1/security-primitives`, by Worker 1 (14 commits plus 3 fixes, all under `backend/app/security/`, `backend/tests/security/`, the README and one dependency).
- **Reviewer:** Supervisor.
- **Verdict:** With fixes in round 1, then ready to merge. No Critical findings.
- **Verified by the reviewer:** `uv sync`, `ruff check`, `ruff format --check` and `pytest -W error` re-run independently (361 tests); scope limited to the allowed files and the single dependency `argon2-cffi`; commit messages and authorship checked; each module read against SPEC sections 3, 6 and 7 and the guard table in `docs/ARCHITECTURE.md`; the limiter's memory behavior measured.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Important | The module and function named `test_*` were collected by pytest through imports, and the `__test__ = False` line at module level did not prevent it. The names came from the brief. | Fixed: renamed to `controls_guard.py` and `controls_allowed`; the hack was removed. |
| 2 | Important | The rate limiter kept the keys of clients that never came back. After 1000 keys and a long wait it still held 1001 of them: unbounded memory on a public demo. | Fixed: a sweep at most once per window; measured again, one key remains. |
| 3 | Minor | The constructor accepted invalid limits and the limiter was not safe for threads. | Fixed: argument validation and a lock, with tests. |

## Decisions on the points the worker asked about

Only the selected `X-Forwarded-For` entry is validated; default ports are normalized when comparing origins; `needs_rehash` may raise for a malformed hash (only `verify_password` must fail closed); rejected requests are not recorded as hits, so a client cannot extend its own lockout; the password hasher is a module-level object without secrets.

## Notes for later tasks

- The login must verify the password against a dummy hash for unknown emails, so timing does not reveal whether an account exists (task 007).
- The card number is normalized before fingerprinting only if the caller does it; the payment module should normalize first.
