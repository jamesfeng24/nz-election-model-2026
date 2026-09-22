# Methodology

## Current implementation

Historical design note: Stage 1 contained only the application shell, provenance contracts and documentation. Current state: all six 2008–2023 ingestions are merged; full historical-panel integration is complete for review (D022). The panel retains election-specific geography, unresolved candidate-person IDs, cancelled-contest missingness and known source discrepancies; it is not a harmonized or fitted dataset. Stage4 boundary reconstruction is merged and Stage5 parameter-free historical transformation backtesting is complete for review. Stage6 descriptive party-seat elasticity fits and temporal validation are complete for review, with both operational elasticities unresolved. No polling aggregation, person/candidate effects, simulation or MMP allocation is implemented. Empty states are not forecasts.

## Intended scope (not yet methods)

Estimate current national party support from multiple pollsters; reconstruct 2023 results on 2026 electorate boundaries; model every 2026 electorate using party vote, candidate vote and split-ticket evidence; distinguish National and Labour electorate-vote resilience; normalize candidate overperformance for national conditions; estimate first-term incumbency and candidate replacement effects; model Opportunity separately from 2023 TOP; simulate joint outcomes, qualification, Sainte-Laguë, list MPs and overhangs; explain individual electorate forecasts.

## Requirements for each future component

Before implementation record: research question and estimand; source IDs and coverage; units and missingness; assumptions; mathematical specification; uncertainty treatment; interactions with other components; validation and sensitivity tests; outputs and limitations. Cite verified electoral rules before implementing MMP. Do not hard-code unverified thresholds, seat counts or boundaries.

## Prevent overlapping effects

Resilience, split voting, national-environment normalization, incumbency and replacement can explain overlapping variation. Maintain an effect-dependency table when specifying models. State baseline, conditioning variables, residual effect and integration order; do not sum separately fitted effects without justification and validation. No integration order is chosen yet.

## Validation principles

Future work should document suitable historical holdouts, calibration and sensitivity checks without leaking outcome information. Distinguish evidence gaps, sampling uncertainty, parameter uncertainty and model uncertainty. Record seeds for stochastic runs, intervals and their interpretation. Never substitute fabricated data to produce a complete-looking forecast.

## Detailed intended specification

Read [docs/statistical-specification.md](docs/statistical-specification.md) for the full pipeline, independent estimators, historical normalization, candidate personal-vote persistence, exclusion rules and configurable government scenarios. These are design constraints, not implemented methods or sourced observations. The source registry was empty after the Stage 1 correction; current acquired coverage is recorded in DATA_SOURCES.md and PROJECT_STATE.md.

## Revised sequencing constraint — 2026-09-08

The authoritative implementation order is recorded in [docs/future-work.md](docs/future-work.md). It supersedes earlier proposed ordering without changing estimands. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Freeze the historical backtesting design and ensemble weights before Opportunity-specific modelling or current 2026 polling ingestion. Each later task requires explicit authorization.

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

## Stage6 architecture audit clarification

The [challenge audit](docs/audits/stage6-architecture.md) retains numerical results but clarifies identification and deployment. β is a provisional unconditional party-seat association; candidate/status effects correlated with party movement need not be mere noise. A response view requires a validated target-boundary candidate reference baseline, which Stage4 did not supply. Later premium construction must make that dependency/availability explicit. Three views are separate complete predictions with overlapping evidence, not independent bonuses. Review conditional β after replacement effects and before integration. Build reusable person/history/status evidence once at the start of persistence, after occurrence-level normalization is defined. No Stage7 work was performed by this audit.
