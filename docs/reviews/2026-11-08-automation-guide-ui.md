# Review: automation guide, part 1 (task 040, 2026-11-08)

- **Branch:** `w2/automation-guide`, by Worker 2 (10 commits, documentation only: `docs/AUTOMATION_GUIDE.md` and one link line in each README).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge, with one fix by the supervisor. No Critical or Important findings.
- **Verified by the supervisor, mechanically against the repository:**
  - all 103 test ids quoted in the guide exist in `docs/TESTIDS.md` or in the frontend source, and the four templates are documented placeholders;
  - every URL path quoted in the guide is a real route;
  - every Spanish message quoted in the guide exists verbatim in the code or the SPEC (the one that does not is a template string, `¿Cancelar el pedido {number}?`);
  - the commit rules.
- **Read in full:** the five sections of the flows, the seed cheat sheet and the surprises list; the worker described the not yet deployed parts (rate limits online, nightly reset, test controls) as configured but not active, which is true.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Minor | Two Playwright sketches called `toHaveText` on a locator without `expect(...)`, which does not run. | Fixed by the supervisor. |
| 2 | Minor | The sketches are not run in CI. | Accepted: they are labelled "illustrative"; the documentation linter of task 042 checks the ids they use. |
