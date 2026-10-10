<!-- fold: changelog -->
## Stage82 — weekly poll refresh on a GitHub Actions schedule, with electorate polls, 2026-10-10

- New workflow `.github/workflows/poll-refresh.yml` ("Poll refresh") runs every Thursday 06:55 NZDT (`55 17 * * 3` UTC; also `workflow_dispatch` with an optional date): it captures the Wikipedia opinion-polling page once, reads the electorate polls (new `scripts/polling/electorate_refresh/`), then runs the unchanged Stage70 national refresh on the same capture, and opens one pull request per refresh (published, updated or blocked; nothing when neither changed). It never merges, never pushes to `main`, never edits earlier runs, does not run on `pull_request` or `push`, and stops cleanly from election day (the existing 7 November guard is unchanged).
- Electorate polls (docs `docs/stage82-electorate-poll-refresh.md`): a header-driven reader that expands merged cells before reading, so each number sits under its own party; only electorate-vote shares are used (party-vote rows stored unused, Lead ignored); `~30` becomes 30 flagged approximate, dashes and blanks are missing, never zero; seat names matched to the official list ("Mount Albert" is "Mt Albert"); revised or removed published rows, unknown seats and any unrecognised layout stop the run. Output is a dated append-only live-inputs file (`data/processed/polling/electorate-live/`), `aggregator_only`, **read by no model layer yet**. First run 2026-10-10: 12 polls (8 general, 4 Māori).
- Uses the repository secret `POLL_REFRESH_TOKEN` (fine-grained token) so Verify starts on the pull request; falls back to `GITHUB_TOKEN` and says in the PR body that CI must be started manually. Setup steps: `docs/stage70-weekly-poll-refresh.md`. The Claude routine `trig_01LB91p9NumjAUQjJB6QKdVs` keeps running until the workflow has merged and done one good run.
- Frozen-pipeline selector (`scripts/validate/ci_frozen.py`, James approved 2026-10-10): `.github/workflows/poll-refresh.yml` is exempt from the "CI configuration changed" full replay (`NON_VERIFY_WORKFLOWS`), because without it a new workflow file forced the 3-hour full replay, which exceeded the job limit on this PR's first Verify run. The exemption lapses if `ci.yml` names the file; any other `.github/` path still forces full. One test added in `scripts/tests/test_ci_frozen.py`.
- Not touched: Verify, the frozen-pipeline registry, every statistical module, `scripts/polling/weekly_refresh/`, `config/nowcast-2026.json`, `data/sources.json`, Stage66/71/78.

<!-- fold: state -->
# Stage82 weekly poll refresh workflow and electorate polls — review-ready, 2026-10-10

Branch `ci/scheduled-poll-refresh-kf6s0c` (PR #95, reworked from the national-only workflow), main `9d2c8f1` merged in. Decision D120 (D113 was taken by Stage77 while the PR was on hold).

**What was done.** The Stage70 weekly refresh runs as a scheduled GitHub Actions workflow independent of Claude. Stage82 adds electorate polls (general and Māori) from the same Wikipedia capture into an append-only dated live-inputs file, with a strict header-driven reader (merged cells expanded first), approximate and missing-value handling, seat-name matching to the official list, and blockers for revised, removed or unrecognised rows. First live run committed (2026-10-10, 12 polls, 3 review flags). Details, outputs and limits: `docs/stage82-electorate-poll-refresh.md`, `docs/stage70-weekly-poll-refresh.md` (workflow section).

**Not done.** Nothing consumes the electorate file (Stage79 general-seat update and the Māori layer wiring are separate stages); no refit or estimate changed; the public-repository push is a commented stub; the workflow has not run on GitHub (it can only be dispatched once on `main`, and the secret does not exist yet).

**Exact next action.** James adds the `POLL_REFRESH_TOKEN` secret (steps in the Stage70 doc). The coordinator merges this PR when green and dispatches the workflow once; after one good run the Claude routine `trig_01LB91p9NumjAUQjJB6QKdVs` is disabled. Merge each weekly refresh PR before the next Thursday (an open refresh PR makes the next run fail on purpose).

<!-- fold: decisions -->
## D120 — 2026-10-10 — the weekly poll refresh runs as a scheduled GitHub Actions workflow and keeps electorate polls in a dated live-inputs file (Stage82)

The refresh is deterministic, so it runs on a GitHub schedule (Thursday 06:55 NZDT) independent of Claude, accounts and usage limits, and opens a reviewed pull request per refresh; it never merges, never pushes to `main`, never edits earlier runs and never adopts into the nowcast configuration. Electorate polls (general and Māori) are read from the same Wikipedia capture into an append-only dated file, `aggregator_only`, never into pinned stage files, so a new electorate poll is a data change applied at run time with fitted parameters fixed, with no refit; consumers (Stage79, the Māori layer) are separate authorised stages. Only electorate-vote shares are used; the reader expands merged cells before reading and stops for a human on any layout, value or row change it does not understand. A fine-grained token in the repository secret `POLL_REFRESH_TOKEN` starts Verify on the pull request; without it the workflow falls back to `GITHUB_TOKEN` and says CI must be started manually. A run fails on purpose while an earlier refresh pull request is open. The Claude routine keeps running until the workflow has merged and done one good run. D104 stands; the 7 November stop is unchanged.

<!-- fold: sources -->
## Wikipedia electorate polling tables (Stage82)

Byte copies of the Wikipedia REST page (Opinion polling for the 2026 New Zealand general election, Electorate polling section) are preserved per change under `data/raw/polling/electorate-live/<date>/` with headers and fetch log, each registered with its SHA-256 in `data/processed/polling/electorate-live/<date>/source-registry.json` (Wikipedia text is CC BY-SA; aggregator evidence only, primary releases not verified). `data/sources.json` is not edited.

<!-- fold: roadmap -->
| Stage82 | Weekly poll refresh on a GitHub Actions schedule, with electorate polls in a dated live-inputs file | review-ready (D120): workflow reworked in #95, 12 electorate polls from the first live run, nothing consumes them yet |
