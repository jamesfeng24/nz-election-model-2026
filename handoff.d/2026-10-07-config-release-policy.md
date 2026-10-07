<!-- fold: changelog -->
## Config: release policy, Māori seats and MMP rules version, 2026-10-07

- `config/nowcast-2026.json` (version 2026-10-07.8) records James's decisions of 2026-10-07 (D114): `release.policyApprovedBy`; `mmp.rulesVersion` = `electoral-act-1993-2026-01-01` with source `mmp-electoral-act-1993-v238-2026-01-01`; `maori.unpolledSeats` = `labelled-fallback`; `maori.presentation` = `labelled-range`; release cadence and the after-election freeze.
- Removed the `uncalibrated` label end to end: the `calibrationStatus` field in the v2 export schema, the release-gate check, the site banner and the exporter. No fixture or archived snapshot carried the field.
- Site copy now says "Forecast if the election were held today, as of <refresh date>" instead of "nowcast" (page label, banner, notices); the estimand and field names are unchanged.
- Removed the staleness windows (`release.staleDays`), `assemble.staleness`, the publisher's "Stale input" limitations and the `--as-of` argument of the production runner.
- Kept the seat-versus-national reconciliation (1.0pp) as an internal build gate only; it is never exported or shown.
- Regenerated `data/processed/nowcast-assembly/development-gate.json` and `data/processed/release-rehearsal/report.json` (config version and pending fields changed, staleness key removed). No model input, draw or statistic changed.

<!-- fold: decisions -->
## D114 — 2026-10-07 — release policy, Māori seat presentation and the MMP rules version (James)

- **Calibration label.** None. The "uncalibrated" and "experimental" labels are dropped entirely (James).
- **Staleness.** No staleness windows. After each refresh every output states "Forecast if the election were held today, as of <date of that refresh>" (the snapshot's `dataCutoff`; the site banner shows it, with the latent-state week). After election day (7 November 2026) outputs are frozen and labelled "as of" the last release.
- **Site wording.** User-facing copy says "Forecast if the election were held today" with the as-of date, not "nowcast" (James: "nowcast" feels clunky). The estimand is still the D106 nowcast, so specs, docs, field names (`targetType: nowcast`) and internal strings keep "nowcast". Only the site's page label, headings, banners and notices changed.
- **Precision gate.** Every published probability needs a Monte Carlo SE of at most 0.01 (unchanged).
- **Reconciliation.** The 1.0pp check that the 64 general seats' party-vote means agree with the national mean stays as an internal build gate. The pipeline computes a party-vote mean per general seat only as an intermediate (the candidate shares are derived from it); no per-seat party vote is exported or shown. The check guards against a broken affinity table. Latest development run: maximum gap 0.38pp.
- **Cadence.** One release after each accepted weekly poll refresh.
- **Māori seats.** Shown as a labelled range (the Stage66/71 layer). The four unpolled seats (Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau, Te Tai Tokerau) use a labelled fallback from the Māori layer without a poll. The Māori layer has no no-poll estimate (Stage66 and Stage71 left those seats `unpolled`), so this decision sets the policy only: the fallback model must be defined, calibrated and registered in a separately authorized bounded stage. Until then those seats are `unavailable` and `maori.unpolledFallbackModel` keeps the config pending.
- **MMP rules.** Electoral Act 1993 version 238.0 as at 1 January 2026 (D084): 5% or one electorate, Sainte-Laguë over 120, s 192 overhang added on top. A search on 2026-10-07 found no later amendment affecting 2026 seat allocation: the Electoral Amendment Act 2025 (Royal Assent December 2025) covers enrolment, prisoner voting and donations, and the Electoral (District Boundaries) Amendment Bill 2026 only moves boundary-review timing to 2030 onward. The legislation site blocked direct fetches, so this rests on the Stage49 verification and secondary pages.

<!-- fold: state -->
# Config: release policy decisions — ready for review, 2026-10-07

Branch `claude/config-release-policy-1evrj1`, from main `767d491`. Records D114 (James's release policy, Māori presentation and MMP rules version) in `config/nowcast-2026.json` and removes the code that read the dropped settings (calibration label, staleness windows). Not changed: any model, draw, scale or statistic; the roster and classification; `data/sources.json`.

- **Config pending list now:** `roster.snapshotId` (Stage50 part 2, after nominations close 12:00 NZDT 8 October) and `maori.unpolledFallbackModel` (new). `release.policyApprovedBy`, `mmp.rulesVersion` and `maori.unpolledSeats` are set.
- **Important:** James's labelled fallback for the four unpolled Māori seats cannot be switched on by config alone: no no-poll Māori estimate exists. Seat counts and Parliament outputs stay blocked until a fallback model is defined and calibrated in a separately authorized stage (release checklist item 15).
- **Checks run:** see the PR body for exact counts.
- **Exact next action:** James reviews the PR (the coordinator merges). Then, when authorized, a bounded stage defines the labelled no-poll fallback for the four Māori seats. Stage50 part 2 still follows the official nominations list. The classification of the 64 general seats still waits for official candidates.
