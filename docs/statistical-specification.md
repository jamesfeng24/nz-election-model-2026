# Statistical specification — intended design, not an implemented model

Historical Stage 1 design note / 2026-09-07: at that checkpoint no data had been collected, coefficients estimated or electoral rules verified. Current ingestion progress is recorded in PROJECT_STATE.md; no model has been fitted. This document records the requested research design; it is not a set of empirical findings. Consult it for modelling, integration or relevant methodological questions under AGENTS.md.

## Intended final pipeline

1. Reconstruct 2023 election results on official 2026 electorate boundaries and quantify reconstruction uncertainty.
2. Estimate current national party support using multiple major pollsters, documenting fieldwork, pollster effects and uncertainty.
3. Project national party movement into individual electorates using validated local baselines.
4. Independently estimate candidate outcomes using several empirically testable models.
5. Normalize historical local over/underperformance against national election conditions wherever possible.
6. Estimate candidate-status effects historically, including personal-vote persistence, first re-election and replacement effects.
7. Combine overlapping models through out-of-sample historical backtesting, rather than stacking correlated bonuses.
8. Propagate input, parameter, reconstruction and model uncertainty, including correlations.
9. Simulate all electorate winners. The requested coverage target is all 71 electorates; verify the official boundary inventory before treating that count as data.
10. Determine electorate qualification for sub-5% parties under verified rules. The threshold is a requested design requirement, not yet an implemented or independently verified rule.
11. Perform exact Sainte-Laguë allocation with independently checked examples and edge cases.
12. Calculate list MPs, overhangs and Parliament size, handling list availability and eligibility under verified rules.
13. Calculate outcomes for configurable government combinations. User-selected combinations are scenarios, not predictions of political agreements.

## Three independent candidate-vote estimators

| Estimator | Proposed estimand | Evidence and validation needed |
| --- | --- | --- |
| Split-ticket model | Candidate vote conditional on local party votes and joint party/candidate voting patterns | Source denominators, coverage, identifiability and temporal transferability |
| Party/electorate elasticity model | Response of candidate/electorate vote to party-vote movement, including different National and Labour resilience | Historical panel, boundary comparability, national conditions and out-of-sample stability |
| Normalized candidate-premium model | Candidate over/underperformance after accounting for party and national election conditions | Explicit national normalization, candidate histories, persistence and status effects |

Keep these estimators independent initially: separate predictions, configurations, diagnostics and historical validation outputs. Final combination weights must be learned from historical out-of-sample backtesting, not subjective judgement. Define election holdouts before fitting and avoid leakage from later candidacies, revised boundaries or outcomes. Weight fitting itself needs held-out evaluation. Do not choose coefficients, blend weights or a normalization formula in this stage.

## Explicit modelling constraints

- Historical split-ticket behaviour for National, Labour, Green, ACT, NZ First and Te Pāti Māori may be used when source quality and coverage support it. This permission is not evidence that a dataset exists.
- Do not extrapolate 2023 TOP electorate splitting directly into 2026 Opportunity. Opportunity gets a separate model; party identities and any relationships require explicit evidence and do not authorize behaviour transfer.
- Regional swing is outside the central model without adequate regional polling.
- Generic ministerial bonuses, MRP, turnout effects and tactical-voting feedback are not central assumptions unless later evidence supports them.
- Chris Bishop must not receive a generic freshman-incumbency bonus: the project instruction identifies him as having previously represented Hutt South. Verify candidate history from sources before creating a data record. Do not encode this as a name-based exception in model code.
- Normalize relevant historical overperformance metrics against national-level over/underperformance wherever possible; document exceptions and sensitivity.
- Do not count overlapping manifestations of personal vote multiple times. Persistence, incumbency, resilience, split voting, normalized premium and replacement effects may overlap.
- Distinguish established continuing, first-term, returning/former incumbents, replacement candidates, returning challengers, completely new and list-only candidates. Party leadership is an orthogonal flag; uncertain classification remains explicitly unknown. Prior tenure excludes automatic first-term status merely because the current spell is new.

## Required design record before implementing each component

Record the estimand, units, denominator, input source IDs, boundary vintage, missingness, equations, conditioning variables, uncertainty, validation plan, outputs and limitations. Maintain an effect-overlap table showing baseline, residual contribution and where each effect enters. Document whether a decision is permanent infrastructure or subject to backtesting. Reject fake precision and fabricated missing observations.

## Runtime boundary

Offline Python may perform ingestion, geographic transformation, regression and backtesting. Export versioned JSON/GeoJSON with provenance, coefficients and uncertainty metadata for the website; Python must not be required on Cloudflare Pages. Pure TypeScript simulation modules must accept serializable inputs and seeded configuration so they can run in a module Web Worker. No model, worker execution or simulation is implemented in stage 1.

## Revised sequencing constraint — 2026-09-08

The authoritative implementation order is recorded in [future-work.md](future-work.md). It supersedes earlier proposed ordering without changing estimands. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Freeze the historical backtesting design and ensemble weights before Opportunity-specific modelling or current 2026 polling ingestion. Each later task requires explicit authorization.

## Stage 5 — local party-vote transformation backtesting (2026-09-23)

Estimand: target electorate party share among valid party votes, conditional only on source local share p and nationwide source/target shares P0/P1. The frozen parameter-free rules are clipped additive p+P1−P0, clipped proportional p×P1/P0, and odds shift p×OR/(1−p+p×OR), OR=P1(1−P0)/(P0(1−P1)). No epsilon, coefficients, candidate effects or cross-party renormalization.

Existing panel canonical identities only:53 eligible party-transition identities,27 exits,25 entrants; entrants never receive invented zero baselines. No new alias/report-group continuity. All nationwide denominators include Māori and general electorates. Historical TOP remains historical TOP.

3,773 records cover2008→2011,2011→2014,2014→2017,2017→2020,2020→2023. The three observed same-boundary transitions supply2,271 primary records; the two reconstructed transitions provide robustness evidence. Both scopes remain separate, with seven Māori electorates per transition. No2026 outcome or political input is scored.

Primary macro-party MAE (pp): general additive0.60869, proportional0.59569, log-odds0.49588; Māori1.75441,1.05099,0.99474 respectively. General RMSE1.48388/2.01505/1.42977; Māori4.62851/2.86743/2.42959. General National MAE2.0547/2.2709/2.0151; general Labour2.1529/3.5760/2.4882. Māori National favours proportional (0.5326 versus log-odds0.6709); Māori Labour favours log-odds (4.4960 versus additive4.9334).

All-five general macro-MAE conservative ranges: additive[0.55462,0.56260], proportional[0.55817,0.56614], log-odds[0.47474,0.48276]. Māori ranges[1.45023,1.45106], [1.03896,1.03994], [0.87784,0.87872]. These are marginal conservative loss bounds, not jointly attainable election-wide extrema. Source-share bounds propagate monotonically; original numerical extremum brackets remain separate. No midpoint or extra optimizer refinement.

Frozen0.5%/1% national-support threshold diagnostics and leave-one-transition-out results are retained. Log-odds remains the general macro-MAE leader under both thresholds and all primary leave-one-out runs. Māori leave-out2020 favours proportional, as do its first two observed transitions. Primary additive clipping occurs in8.74% of general and23.66% of Māori records; proportional/log-odds have no clipping here. Vector sums and clipping magnitudes are recorded without renormalization.

Selection remains `unresolved_between_methods`, default null, retained set additive/proportional/log-odds. Log-odds is the strongest generic aggregate performer and robust to the bounded geographic evidence, but the material general-Labour advantage for additive and mixed Māori transition results prevent a universal default under the frozen rule. No statistical significance claim from only three primary clusters. Later authorized elasticity must use one parameterized pipeline and evaluate retained-transform sensitivity; stop precision exploration if conclusions are materially unchanged.

Output family: `data/processed/models/party-vote-transform/` specification, pinned input contract, continuity, records, scores, vector diagnostics, selection and manifest. Exact next stage: **NAT/LAB electorate elasticity only**, not begun.

## Stage6 — National/Labour party-seat elasticity (2026-09-23)

Estimand: Δcandidate share = β_party × Δlocal party share, each share using its own valid-vote denominator. Fit separate unrestricted, zero-intercept, equal-observation OLS slopes on general seats. The positive prediction C1=C0+β(P1−P0) follows the explicit delta estimand; inconsistent minus signs in the request's displayed prose were interpreted as formatting slips before fitting. No candidate premium/person effect is estimated.

Use only2008→2011,2014→2017,2020→2023 on their validated2007/2014/2020 boundary regimes. Changed-boundary candidate baselines were not reconstructed. Each party has191 general observations (63/64/64). Port Waikato cancellation excludes one2020→2023 pair per party. Candidate names remain source labels; person identity is neither inferred nor required. Māori evidence has21 Labour pairs and zero National pairs; it is descriptive only, never pooled or assigned a separate operational coefficient.

| Party | Full OLS β | 2008→2011 | 2014→2017 | 2020→2023 |
|---|---:|---:|---:|---:|
| National | 0.736872 | 0.387667 | 0.759028 | 0.758046 |
| Labour | 0.614747 | 0.212515 | 0.305435 | 0.729720 |

Chronological training uses2008 only for the2014 transition, then2008+2014 for2020. National training slopes0.387667/0.576726; Labour0.212515/0.279460. Leave-one-transition-out estimates are stability diagnostics, explicitly not chronological forecasts when future data train an earlier holdout.

Observed-local-party chronological MAE(pp), pooled over the two equal-sized holdouts: National β0=7.6412, β1=3.8401, fitted=4.1457; Labour β0=11.0337, β1=7.6308, fitted=7.3160. National fitted loses toβ1 in both holdouts (3.8575vs3.4778 and4.4340vs4.2024). Labour improves strongly in2014→2017 (4.0231vs7.8733) but worsens in2020→2023 (10.6089vs7.3883). RMSE/bias/median/p90 and predictions are preserved per party/transition/baseline.

One pipeline uses the same structural training slope with Stage5 additive/proportional/log-odds predictions. Chronological fitted MAE: National4.5880/4.6019/4.6428 versusβ1 4.2202/4.6241/4.2277; Labour7.3911/7.5308/7.5207 versusβ1 7.5891/7.9081/6.9946. Transform sensitivity does not establish stable bespoke elasticity. No transform-specific refitting or change to Stage5's unresolved default.

Both parties remain `unresolved_no_stable_material_gain`, selectedBeta null; full OLS estimates are descriptive, β1 retained as benchmark rather than claimed optimal truth. The pre-fit0.25pp indicative material-gain screen and consistent chronological holdout/transform improvement requirement fail. This is not a significance test. Raw linear predictions are not silently clipped; out-of-range diagnostics are stored (three across all repeated evaluation configurations).

Limitations: only three transition clusters, residual candidate changes, no same-person effects, no changed-boundary candidate pairs, seven Māori seats per election, conditional realized-party validation distinguished from forecast-pipeline sensitivity. No new sources/web use or2026 predictions. Exact next stage: **Normalized candidate overperformance only**, on separate authorization.

## Stage7 frozen descriptive normalization

Stage7 specification: `data/processed/models/candidate-overperformance/specification.json` (frozen21dfed7). For eligible occurrence i, c_i=v_i/D_candidate,e and p_i=w_p,e/D_party,e. Over the same party/election matched contest set E excluding e, C_−i=Σv/ΣD_candidate and P_−i=Σw/ΣD_party. Raw premium=c_i−p_i; primary normalized residual=c_i−[p_i+C_−i−P_−i]. This uses all eligible general/Māori contests together, with scope diagnostics separate. Require |E|≥2 before removing the focal contest. No smoothing, missingness imputation, fitted slope or extra coverage threshold.

Proportional p_i C_−i/P_−i requires P_−i>0. Odds shift requires both reference shares strictly inside(0,1). Preserve raw expected values, bounded alternatives, domain failures and residuals separately. Primary additive residual uses the raw reference. Nationally centred does not imply an exactly zero unweighted seat mean. The identity join is exact within election, not cross-election organizational/person inference.

Outputs cover3,007 occurrences,2,674 eligible and2,673 normalized in six observed elections. Retain additive primary;3 raw references are negative by at most0.6583pp. Alternative scales have material individual and Māori differences; they remain sensitivities for later validation, not independently selected models. Full diagnostics and quantitative reference coverage are persisted. See METHODOLOGY for results and the updated dependency map.

Same-election normalization describes an outcome. A target election's observed reference or residual cannot be a predictor of that target. Stage6 is still a provisional response component. No candidate baseline transport, persistence or additive stacking of overlapping candidate effects is authorized by this layer.
