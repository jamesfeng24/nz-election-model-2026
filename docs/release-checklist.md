# Release checklist: remaining work and publication gate (2026 nowcast)

The only active remaining-work list. Design and definitions live in [nowcast-specification.md](nowcast-specification.md). Update an item here when it changes rather than restating it elsewhere. Status as of 6 October 2026.

## Must happen before the first public nowcast

| # | Item | Depends on | Status |
|---|---|---|---|
| 1 | Decisions recorded: nowcast estimand (D106), 0.60/1.00 policy (D107) | — | done (this reconciliation) |
| 2 | 2026 candidate and local-party scales computed with the frozen Stage45 rule over 2014–2023 (the folds stop at 2023 today) | — | open |
| 3 | `config/nowcast-2026.json` as the single live configuration (spec §8) | 2 | open |
| 4 | 2026 ordinary/exceptional classification for all 64 general seats, dated and sourced; a missing seat fails the build | James | open |
| 5 | Canonical final roster after nominations close; rebuild S/R destinations, Māori poll-to-candidate matching, export directory and MMP expected electorates from it | Stage50 (after 8 Oct, 12:00 NZDT) | waiting |
| 6 | Cut over to the Stage69 notional baseline through one pointer; mark the Stage64 and Stage41 2026 artifacts as not live; test that only the configured baseline is read | Stage69 | waiting |
| 7 | National adapter on `lastDataSupport` from the latest Stage70 refit, as-of week recorded | Stage70 | waiting |
| 8 | Decide the four unpolled Māori seats (labelled fallback, or withhold MMP outputs) | James | open |
| 9 | Assembly: Python draw bank → Stage65 seat layer → snapshot v2 exporter, one draw id end to end | 2–8 | open |
| 10 | Production draw count and precision policy, with effective-sample Monte Carlo errors for national-driven quantities | Stage63 | waiting |
| 11 | Bloc definitions for any coalition output | James | open |
| 12 | Probability-release policy approved (proposal below) | James | open |
| 13 | Export v2 completion: candidate-share intervals, Monte Carlo SE, thresholds/overhang/size/blocs, per-seat uncertainty class; 80% quantiles in Stage65 summaries | 9, 10 | open (schema core done) |

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

- **Universe:** 71 electorates (64 general + 7 Māori), unique ids; every seat predicted or explicitly `unavailable`, never zero.
- **Roster and slates:** the roster snapshot hash equals the configured one; complete slates; no unknown party or candidate.
- **Shares:** candidate and party shares close; no NaN; probabilities in [0, 1].
- **Classification:** ordinary/exceptional is exhaustive and exclusive over the 64 general seats; no 1.00 seat carries `extraSdPp` without an opt-in; the multiplier changes standard deviation only.
- **National source:** `lastDataSupport`; any `electionDay` draw in a `nowcast` snapshot fails.
- **Draws:** one national draw id per simulated election across all seats and MMP; all 71 winners present once per draw; Stage65 accounting identities hold.
- **Precision:** Monte Carlo SE and effective sample size reported, and precision thresholds met, or the quantity is withheld.
- **Determinism:** the same snapshot and seed give identical bytes.
- **Schema:** snapshot v2 validates (`targetType: nowcast`, `modelStateAsOf` ≤ `dataCutoff` ≤ `createdAt`, nested 50/80/90 intervals); archive hash and supersession are consistent; `npm run check:dist` passes (no synthetic data).
- **Reconciliation diagnostic:** turnout-weighted local party means agree with the national mean within tolerance.
- **Staleness:** polls, roster and Māori inputs are within configured staleness windows, or are labelled stale.

## Proposed probability-release policy (for James to approve; not operational)

| Output | Proposal |
|---|---|
| National vote shares | Show 80% (50/90 on demand), labelled "latent support, week of …" |
| General-seat candidate shares and win probabilities | Show, labelled "uncalibrated nowcast", when the Monte Carlo SE is ≤ 0.01 |
| Māori seats | Show only as a Stage66–Stage71 labelled range, or withhold until all seven have a defined estimate |
| Party seats, threshold/lifeboat, overhang, Parliament size | Only when all 71 seats are defined and the effective-sample Monte Carlo SE is ≤ 0.01 |
| Coalition/bloc probabilities | Only for blocs James defines, worded as scenarios, not predictions of agreements |
| Unavailable or under-precise components | Withheld with a reason, never zero |
| Calibration label | Every probability is labelled `uncalibrated` until a validation exists |
| Wording | "If an election were held under current conditions (latent state week of …)"; intervals are central ranges across simulated elections, not margins of error or election-day ranges |
