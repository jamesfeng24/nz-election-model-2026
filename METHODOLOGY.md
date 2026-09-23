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

## Stage7 — occurrence-level normalized candidate overperformance

The specification was frozen at21dfed7 before diagnostics. Each of the six observed elections is processed on its published geography; there is no cross-election or person matching. A held candidate contest is eligible only when the candidate affiliation has an exact normalized within-election party-vote counterpart. Existing source-header expansions remain source-local; report alliances do not create counterpart identities. Independents, unmatched affiliations and cancelled nominations remain in the occurrence inventory with reasons. General occurrence IDs/source labels are unchanged. The42 previously preserved supporting Māori candidate files supply174 additional observed occurrences, with IDs derived from election, official electorate number and source candidate order. These are not person IDs.

Candidate share c uses valid candidate votes; party share p uses valid party votes. Raw premium is c−p. For each party/election, aggregate candidate and party shares over **exactly the same eligible contested seats**, using their respective summed denominators. The primary reference includes both general and Māori eligible contests. For each focal occurrence subtract its entire contest's candidate numerator/denominator and party numerator/denominator. Expected raw additive share is p+C_ref,−i−P_ref,−i; normalized residual is c−expected. A party with fewer than two matched contests retains raw premium but has no normalized residual. A candidate cannot contribute to its own reference.

The additive residual is an interpretable percentage-point deviation after removing the election-wide matched-contest offset. It is not necessarily exactly zero-mean across seats: references are vote-weighted, denominators differ and each reference leaves out a different seat. This is not a defect to remove by additional centering. It is not identified candidate quality, persistent personal vote, a causal effect or a forecast bonus.

Proportional expected share p×C_ref,−i/P_ref,−i and the corresponding log-odds shift are sensitivity fields in the same pipeline. Undefined domains stay null with reasons; no pseudocounts. Raw expected values, explicit out-of-range flags and bounded alternatives are separate. Primary residuals use raw additive values, never silent clipping.

| Election | All occurrences | Eligible exact counterparts | Normalized |
|---|---:|---:|---:|
|2008|522|486|486|
|2011|453|423|423|
|2014|483|412|412|
|2017|453|407|407|
|2020|601|543|542|
|2023|495|403|403|
|Total|3,007|2,674|2,673|

Exclusions:163 independents,161 unmatched affiliations,nine cancelled Port Waikato nominations. The only eligible singleton is Heartland NZ2020.90 party-election reference cells retain full slate coverage and denominator metadata (one to72 contests).2014 MANA Movement/Internet Party,2020 NZ Public Party and2023 Freedoms constituent affiliations are not globally joined to alliance party votes. Historical TOP is unchanged.

Additive is retained as `additive_national_centered`. Only3/2,673 (0.112%) raw references fall outside[0,1], all slightly negative: NZ First/Wellington Central2011, ACT/Rongotai2020, ACT/Māngere2023. The largest bounded adjustment is0.6583pp. Proportional/log-odds have zero out-of-range or undefined cases among normalized occurrences (the singleton is unavailable for every method). Across all occurrences, additive residual correlation with local party share is0.0395 and with leave-one-out party reference strength−0.0210. Correlation with candidate share0.3071 is descriptive and partly mechanically induced by the residual definition, not a fitting target.

General normalized residuals: n2,528, mean−0.0369pp, SD5.1974pp. Māori: n145, mean1.0026pp, SD10.5500pp. General National/Labour each have383 normalized occurrences, means−0.0410/+0.7037pp and SD7.4440/6.8453pp. Māori Labour has42, mean−9.4688pp; Māori National has only2 (both2023), mean−5.5078pp, insufficient for generalization. These scope differences are substantive descriptive findings, not candidate-quality comparisons.

Alternative scales are not interchangeable. Proportional/log-odds residual differences from additive have overall SD2.0908/1.4308pp; individual absolute differences reach35.48/26.42pp. Māori mean differences are−3.3697/−1.9691pp. Their Māori local-share correlations (−0.562/−0.493) do not consistently remove the additive pattern (−0.439). Sparse references and heterogeneous contest environments warrant sensitivity in later validation, not a new tuned normalization or forced Māori-only model. No broadly systematic failure requires changing the frozen additive descriptive estimand; no operational predictive superiority is claimed.

### Updated effect dependency contract

| Component | Stage7 dependency / overlap guard |
|---|---|
|Stage6 response|Remains provisional; requires a later defensible target-geography candidate reference. Stage7 supplies observed residual evidence, not that transported baseline.|
|Persistence (next, separately authorized)|First build one reusable person/history/status evidence layer; then test whether prior same-person normalized residual predicts a later residual. Do not add retained premium twice.|
|First-term incumbency / replacement|Estimate conditional residual change using the same normalized scale and shared history; do not stack unconditioned bonuses or remove a prior premium twice.|
|Split-ticket / later integration|Alternative complete predictive views with overlapping evidence. Combine validated complete predictions, not independent premium/elasticity/split bonuses.|

**Forecast restriction:** same-election observed references and residuals validly describe that election's outcomes. Neither the target election's observed reference offset nor its observed residual may be an input to forecasting that election. Later temporal validation must construct predictors from information available before the holdout. No residual has been transported across boundaries/candidates, no person linking performed and no2026 candidate baseline created.

## Stage8 — evidenced candidate persistence

Stage8 starts from all Stage7 occurrences and links person identity separately with evidence and explicit unresolved states. A bounded official Parliament index pass corroborates 215 MP-linked occurrences; 747 exact-record chains remain probable and 2,045 occurrences unresolved. Election-dated status is separate from identity/party, with unknown and left-censored history preserved. No candidate names, affiliations or occurrence IDs are changed. The full design, counts and results are in [the Stage8 audit](docs/candidate-persistence.md).

The primary estimand is conditional predictive association between a confirmed person's previous additive normalized residual and their later residual in the same electorate, under an unchanged published boundary regime. Only2008→2011,2014→2017 and2020→2023 supply observed same-boundary candidate pairs; changed-boundary names do not establish comparability. There are69 confirmed general primary pairs (23/26/20); zero confirmed Māori pairs. Retrospective validation conditions on known target candidacy and corroborated identity. The target residual/reference is outcome-only and never enters its own predictor or training sample.

The descriptive full-sample intercept+slope is +1.423pp and0.850. An intercept is appropriate because returnee residuals need not average zero. Chronological fits train only on earlier target elections;2011 has benchmarks only,2017 trains on2011 and2023 trains on2011+2017. The fitted model's MAE is3.479pp versus2.521pp for the unchanged-prior benchmark in2017, and4.999pp versus4.998pp in2023. RMSE also worsens in both. Proportional/log-odds sensitivities do not reverse that operational conclusion;281 confirmed-or-probable general pairs improve slightly only in2017 and worsen in2023.15 probable Māori pairs are too sparse for a separate coefficient. Full-sample slopes describe selected same-seat continuity, not isolated personal retention.

Selected operational persistence coefficient is null. Stable seat/party conditions, incumbency, MP-focused identity confirmation, shared party/election references and only three dependent transition clusters prohibit causal attribution or candidate-pair iid uncertainty claims. Stage6 remains provisional and no independent candidate bonus is added. Freshman-incumbency and replacement effects remain separate later stages.

### Stage6/7 source-provenance correction

The old Stage6/7 whole-file `data/sources.json` pin was too broad: an unrelated source registration invalidated deterministic checks. An audited immutable snapshot now pins the 42 official supporting Māori candidate source records actually consumed by those stages. Live required records must exactly match the snapshot, and their raw file bytes remain checksum-verified; unrelated additions are allowed. Only provenance contracts/manifests and Stage6 record hash metadata changed. Historical numerical outputs remain byte-identical. See `docs/audits/stage8-source-provenance.md`.
