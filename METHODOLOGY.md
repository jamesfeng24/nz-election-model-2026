# Methodology

## Current implementation

Historical design note: Stage 1 contained only the application shell, provenance contracts and documentation. Current state: all six 2008–2023 ingestions are merged; full historical-panel integration is complete for review (D022). The panel retains election-specific geography, unresolved candidate-person IDs, cancelled-contest missingness and known source discrepancies; it is not a harmonized or fitted dataset. Stage4 boundary reconstruction is merged and Stage5 parameter-free historical transformation backtesting is complete for review. No polling aggregation, fitted elasticity, candidate effects, simulation or MMP allocation is implemented. Empty states are not forecasts.

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
