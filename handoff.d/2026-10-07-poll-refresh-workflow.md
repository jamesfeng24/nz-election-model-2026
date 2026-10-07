<!-- fold: changelog -->
## CI — weekly poll refresh on a GitHub Actions schedule, 2026-10-07

- New workflow `.github/workflows/poll-refresh.yml` ("Poll refresh") runs the Stage70 refresh every Thursday 06:55 NZDT (`55 17 * * 3` UTC; also `workflow_dispatch` with an optional date) with `requirements-external.lock`, and opens one pull request per refresh: published run (with the runbook checks), blocked run (capture, `blocked.json`, `review.json`), nothing for `NO_NEW_POLLS`. It never merges, never pushes to `main`, never edits earlier runs, and does not run on `pull_request` or `push`. It stops cleanly from election day (the existing 7 November guard in `run.py` is unchanged).
- Uses the repository secret `POLL_REFRESH_TOKEN` (fine-grained token, Contents and Pull requests read/write) so Verify starts on the pull request; falls back to `GITHUB_TOKEN` and says in the PR body that CI must be started manually. Setup steps are in `docs/stage70-weekly-poll-refresh.md`.
- New `scripts/polling/refresh_workflow/helper.py` (PR body, allowed-path guard, election-day check) and `scripts/tests/test_weekly_refresh_workflow.py`. Not touched: Verify, the frozen-pipeline selector and registry, every statistical module, `scripts/polling/weekly_refresh/`, `config/nowcast-2026.json`. The Claude routine is disabled by the coordinator after this merges.

<!-- fold: state -->
# CI weekly poll refresh workflow — review-ready, 7 October 2026

Branch `ci/scheduled-poll-refresh-kf6s0c` from main `3db0b63` (#93 merged). Decision D113 (number taken from main's highest, D112; the coordinator may renumber).

**What was done.** `.github/workflows/poll-refresh.yml` reproduces the Stage70 routine runbook as a scheduled workflow (Thursday 06:55 NZDT, UTC cron `55 17 * * 3`, plus dispatch) so the refresh no longer depends on a Claude session or usage limits. Behaviour, outcome table, token setup and limits: `docs/stage70-weekly-poll-refresh.md`, section "Scheduled GitHub Actions workflow". Helper `scripts/polling/refresh_workflow/helper.py`, tests `scripts/tests/test_weekly_refresh_workflow.py`.

**Not done.** No change to Verify, the selector, the registry, any statistical code or the 7 November stop. Not exercised on GitHub: a workflow can only be dispatched once it is on `main`, and the token secret does not exist yet.

**Exact next action.** James adds the `POLL_REFRESH_TOKEN` secret (steps in the stage doc). The coordinator merges this PR when green, runs the workflow once by dispatch, and then disables the Claude routine `trig_01LB91p9NumjAUQjJB6QKdVs`. Merge each weekly refresh PR before the next Thursday (an open refresh PR makes the next run fail on purpose).

<!-- fold: decisions -->
## D113 — 2026-10-07 — the weekly poll refresh runs as a scheduled GitHub Actions workflow, not a Claude routine

The refresh is one deterministic command, so it runs on a GitHub schedule (Thursday 06:55 NZDT) independent of Claude, accounts and usage limits, and opens a pull request per refresh exactly as the Stage70 runbook specified; it never merges, never pushes to `main`, never edits earlier runs and never adopts into the nowcast configuration. A fine-grained token in the repository secret `POLL_REFRESH_TOKEN` is used so Verify starts on the pull request; without it the workflow falls back to `GITHUB_TOKEN` and states that CI must be started manually. A run fails on purpose, rather than duplicating polls, while an earlier refresh pull request is still open. The refresh's 7 November stop is unchanged. D104 stands.
