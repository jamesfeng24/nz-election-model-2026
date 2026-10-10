<!-- fold: changelog -->
## Final checks: rehearsal and readout corrections, refreshed outputs, production run, 2026-10-10

- `scripts/release_rehearsal/run.py` (audit C4): the report no longer says the Stage64 baseline is used or that the classification and roster do not exist. It reads the national input from the config's `national.source` (its refresh's `estimate.json`) and the as-of date from `national.dataCutoff`, so it follows each adoption instead of stopping with `SystemExit`. The stand-in list names the synthetic candidate list and classification the rehearsal still uses on purpose.
- `scripts/seat_polls/readout.py` (audit C7): `simulate_with_poll` now gets the D121 within and mass multipliers as well as the D107 balance multiplier, so the readout's ordinary-seat probabilities match the live assembly.
- Regenerated: `data/processed/seat-polls/readout-2026.json` (2,048 draws) and `data/processed/release-rehearsal/report.json` (bank digest `b918afe0…`, config 2026-10-10.4; Python gate fails only `provenanceLive`, as a synthetic rehearsal should). Development gate and synthetic fixture reproduce unchanged. No model, configuration, data or frozen-pipeline change.

<!-- fold: state -->
# Final checks: rehearsal and readout refresh, production run — review-ready, 2026-10-10

Branch `claude/parallel-full-replay-qikw5y` restarted from main `a8cec13` (after #120 and #121 merged). Authorized by the coordinator's brief (James's final-check plan, 2026-10-10).

**Production run (local, not published).** `python3 -m scripts.nowcast_assembly.run --require-complete --bank .release-build/production/bank.json` at 4,096 national draws x 16 layer replicates (65,536 rows, 71 of 71 seats) on config 2026-10-10.4: the config validates complete, the Python gate passes (bank digest `2d3e1744…`, about 34 minutes on 4 cores), and a dry-run snapshot built with `release:publish --rehearsal` into the gitignored `.release-build/production/archive/` passes the TypeScript release gate (every probability's MCSE at most 0.01). Nothing under `public/` or any archive path was written. Basis: national refresh of 2026-10-07 (week of 2026-09-27); the 2026-10-10 refresh (#114) is not adopted.
- Seats, median (80% range): National 35 (32 to 42), Labour 35 (32 to 41), Green 17 (15 to 18), NZ First 13 (11 to 15), ACT 12 (10 to 13), TOP 8 (6 to 10), Te Pāti Māori 4 (2 to 6). Mean Parliament 124.82 (mean overhang 4.82).
- Bloc P(majority): NAT+ACT+NZF 0.278, LAB+GRN+TPM 0.053, LAB+GRN 0.009, NAT+ACT 0.0001. Hung 0.669; TOP kingmaker either side 0.597.
- Polled Māori seats, leader's chance C to P: Hauraki-Waikato 0.88 to 0.74, Te Tai Hauāuru 0.74 to 0.64, Te Tai Tonga 0.84 to 0.61, Waiariki 0.97 to 0.82; fallback seats single numbers (Ikaroa-Rāwhiti 0.64, Tāmaki Makaurau 0.50, Te Tai Tokerau 0.66). Full tables: project file `final-checks/production-run-2026-10-10.md`.

**Finding.** The weekly Poll refresh workflow does not run `weekly_refresh.adopt`, by design (spec row 1; the routine never edits the config). With the electorate-poll run now pinned (D128), new national and electorate polls reach the forecast only when someone adopts a merged refresh and regenerates the development gate, fixture and readout. Four Mondays remain before election day; left manual.

**Not done here.** `pyproject.toml` description text (audit C5): editing it forces every frozen pipeline to replay (about 170 of 180 minutes), so it goes in its own PR. Audit C6 was already completed by Stage88.

**Checks.** See the PR body.

**Exact next action.** The coordinator reviews and merges on James's go. Then the `pyproject.toml` PR, then one manual dispatch of the Full replay workflow on main to record per-group durations and tighten its timeouts. Adoption of the 2026-10-10 refresh waits on James.
