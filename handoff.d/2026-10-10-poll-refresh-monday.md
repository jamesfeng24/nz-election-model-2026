<!-- fold: changelog -->
## Poll refresh moved to Monday 00:00 NZ time, 2026-10-10

- `.github/workflows/poll-refresh.yml` now fires weekly at Monday 00:00 NZDT (`0 11 * * 0` UTC) instead of Thursday 06:55, at James's request; refresh dates are 12, 19 and 26 October and 2 November (the last before election day). Wording is date-only: the PR text gives the Wikipedia last-modified as a date, and the site wording ("Most recently refreshed <date>") is the site build's.
- A same-date rerun of a published electorate run (second manual dispatch) now exits 0 as `ELECTORATE_NO_CHANGE` and edits nothing; a blocked date still fails. Refresh PRs get the `poll-refresh` label; review-flag lines in the PR body read plainly. Selector, registry and statistical code untouched.
