# Release checklist: remaining work and publication gate (2026 nowcast)

The only active remaining-work list. Design and definitions live in [nowcast-specification.md](nowcast-specification.md). Update an item here when it changes rather than restating it elsewhere. Status as of 7 October 2026.

## Must happen before the first public nowcast

| # | Item | Depends on | Status |
|---|---|---|---|
| 1 | Decisions recorded: nowcast estimand (D106), 0.60/1.00 policy (D107) | — | done (this reconciliation) |
| 2 | 2026 candidate and local-party scales computed with the frozen Stage45 rule over 2014–2023 | — | done (Stage72) |
| 2a | Candidate-mean (S+R) fit trained on every completed election, 2026 features recentred | — | done (Stage75) |
| 3 | `config/nowcast-2026.json` as the single live configuration (spec §8) | 2 | done (Stage72); pending fields listed in the file |
| 4 | 2026 ordinary/exceptional classification for all 64 general seats, dated and sourced; a missing seat fails the build | James | **done** (Config, 2026-10-10): `config/general-seat-classification-2026.json`, 64 seats (12 exceptional), recorded by James with reasons in [general-seat-classification-2026.md](general-seat-classification-2026.md); the live development gate now simulates all 64 general seats |
| 5 | Canonical final roster after nominations close; rebuild S/R destinations, Māori poll-to-candidate matching, export directory and MMP expected electorates from it | Stage50 (after 8 Oct, 12:00 NZDT) | refresh pipeline ready and tested (Stage50 part 1, [stage50-nominations.md](stage50-nominations.md)); acquisition after publication; Māori official-candidate mapping open |
| 6 | Cut over to the Stage69 notional baseline through one pointer; mark the Stage64 and Stage41 2026 artifacts as not live; test that only the configured baseline is read | Stage69 | waiting |
| 7 | National adapter on `lastDataSupport` from the latest Stage70 refit, as-of week recorded | Stage70 | waiting |
| 8 | Decide the four unpolled Māori seats (labelled fallback, or withhold MMP outputs) | James | decided (James, 2026-10-07, D114): labelled fallback from the Māori layer without a poll. The fallback model is not defined yet: see item 15 |
| 9 | Assembly: Python draw bank → Stage65 seat layer → snapshot v2 exporter, one draw id end to end | 2–8 | Python draw bank and gate (Stage73) and bank → snapshot v2 (Stage74) done; live run blocked on 4, 5, 8, 10, 11 |
| 10 | Production draw count and precision policy, with effective-sample Monte Carlo errors for national-driven quantities | Stage63 | set (Stage77): 4,096 national draws × 16 layer replicates (Stage63, James M = 16); batch-means MCSE within chains with replicates kept together |
| 11 | Bloc definitions for any coalition output | James | done (James, 2026-10-07): NAT+ACT, NAT+ACT+NZF, LAB+GRN, LAB+GRN+TPM; hung parliament over NAT+ACT+NZF and LAB+GRN+TPM with TOP as kingmaker (`mmp.blocs`, `mmp.hungParliament`) |
| 12 | Probability-release policy approved | James | done (James, 2026-10-07, D114): no calibration label, no staleness windows, MCSE ≤ 0.01 precision gate, an internal-only reconciliation check, one release after each accepted weekly poll refresh; recorded as `release.policyApprovedBy` |
| 12a | MMP rules version pinned | James | done (James, 2026-10-07, D114): Electoral Act 1993 version 238.0 as at 1 January 2026 (`mmp.rulesVersion`). No later amendment affecting 2026 seat allocation found on 7 October |
| 14 | Production runner and rehearsal | — | done (Stage77): `npm run release:build` / `release:publish`; full-size rehearsal with labelled stand-ins ([stage77-release-steps.md](stage77-release-steps.md)) |
| 15 | Labelled no-poll fallback for Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau and Te Tai Tokerau: define, calibrate and register it (the Māori layer has none; Stage66/71 left them `unpolled`) | James authorizes a bounded stage | open; until then those seats are `unavailable` and `maori.unpolledFallbackModel` keeps the config incomplete |
| 13 | Export v2 completion: candidate-share intervals, Monte Carlo SE, thresholds/overhang/size/blocs, per-seat uncertainty class; 80% quantiles in Stage65 summaries | 9, 10 | done (Stage74); precision thresholds set (MCSE ≤ 0.01); the calibration label was dropped (D114) |

## Should do soon

- **Stage70:** save joint national draws at the as-of week.
- **Māori:** a structure-specific minor-candidate scale; optionally couple the shared factor with national Te Pāti Māori support, with a stated correlation.
- **General-seat electorate polls:** use the Stage56 route for now; a measurement interface can follow.

## Optional or post-launch

- carry the national state forward to the publication week;
- a labelled election-day scenario;
- the Stage57 blind replay to retest the 0.60 ordinary scale;
- 2026 scoring of outputs A, B and A-on-untouched-seats.

## Stop: do not reopen

- the national model or poll windows, and historical national MCMC reruns;
- Student-t, mixtures, regimes and variance predictors;
- replacement transfer (Stage55);
- a swing term for the shared split (Stage68);
- a fitted multiplier above 1 for exceptional seats (Stage67);
- a turnout reconciliation stage;
- candidate-quality scores.

## Publication gate (a snapshot is publishable only if all hold)

Implemented (Stage77): the Python gate (`scripts/nowcast_assembly/assemble.py` `gate`) and the TypeScript release gate (`src/release/releaseGate.ts`) cover config completeness, provenance, universe, winners, classification multipliers, national reconciliation, schema, seat layer and MMP availability, and the probability MCSE threshold. Archive hash and supersession are enforced by `addToArchive` and the index schema; determinism by the bank digest.

- **Universe:** 71 electorates (64 general + 7 Māori), unique ids; every seat predicted or explicitly `unavailable`, never zero.
- **Roster and slates:** the roster snapshot hash equals the configured one; complete slates; no unknown party or candidate.
- **Shares:** candidate and party shares close; no NaN; probabilities in [0, 1].
- **Classification:** ordinary/exceptional is exhaustive and exclusive over the 64 general seats; no 1.00 seat carries `extraSdPp` without an opt-in; the multiplier changes standard deviation only.
- **National source:** `lastDataSupport`; any `electionDay` draw in a `nowcast` snapshot fails.
- **Draws:** one national draw id per simulated election across all seats and MMP; all 71 winners present once per draw; Stage65 accounting identities hold.
- **Precision:** Monte Carlo SE and effective sample size reported, and precision thresholds met, or the quantity is withheld.
- **Determinism:** the same snapshot and seed give identical bytes.
- **Schema:** snapshot v2 validates (`targetType: nowcast`, `modelStateAsOf` ≤ `dataCutoff` ≤ `createdAt`, nested 50/80/90 intervals); archive hash and supersession are consistent; `npm run check:dist` passes (no synthetic data).
- **Reconciliation (internal build check, never shown to users):** turnout-weighted local party means agree with the national mean within tolerance.
- **Staleness:** no windows (D114). Every output states "Forecast if the election were held today, as of <refresh date>"; after election day (7 November) outputs are frozen and labelled "as of" the last release.

## Probability-release policy (approved by James, 2026-10-07, D114)

| Output | Policy |
|---|---|
| National vote shares | Show 80% (50/90 on demand), labelled "latent support, week of …" |
| General-seat candidate shares and win probabilities | Show when the Monte Carlo SE is ≤ 0.01 |
| Māori seats | Shown as a labelled range (Stage66–Stage71 layer). The four unpolled seats use a labelled fallback from the Māori layer without a poll, once it is defined (item 15) |
| Party seats, threshold/lifeboat, overhang, Parliament size | Only when all 71 seats are defined and the effective-sample Monte Carlo SE is ≤ 0.01 |
| Coalition/bloc probabilities | Only for blocs James defines, worded as scenarios, not predictions of agreements |
| Unavailable or under-precise components | Withheld with a reason, never zero |
| Calibration label | None: no "uncalibrated" or "experimental" label (James) |
| Staleness | No windows. Every output states "Forecast if the election were held today, as of <refresh date>" (the snapshot `dataCutoff`); frozen and marked "as of" after election day |
| Cadence | One release after each accepted weekly poll refresh |
| Reconciliation check | Internal build gate only (1.0pp); never shown to users |
| Wording | "If an election were held under current conditions (latent state week of …)"; intervals are central ranges across simulated elections, not margins of error or election-day ranges |
