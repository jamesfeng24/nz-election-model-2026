# Stage6 architecture challenge audit — 2026-09-23

## Executive conclusion

**Sound with minor architectural-contract changes, not a numerical model rewrite.** Keep the frozen Stage6 results and unresolved operational coefficients. Do not describe the fitted slopes as identified causal resilience or the elasticity view as independently deployable on2026 geography. Explicitly make it a provisional response component requiring a target-boundary candidate baseline. No Stage7 implementation, source acquisition, person linking or new model selection occurred.

This is a bounded exploratory audit, not a replacement preregistration. Diagnostics are reproducible with `.venv/bin/python -m scripts.audits.stage6`; `stage6-exploratory.json` records inputs/results. Intercept alternatives were not selected using in-sample improvement. PR13 is ready to merge as a historical baseline/diagnostic stage with these contract clarifications, not as a production elasticity estimator.

## Material findings

Each finding has exactly one category. “Later stage” names below refer to the planned sequence, not authorization to start it.

| Finding | Category | Expected impact / why it matters | Cost | Action |
|---|---|---|---|---|
| “Structural elasticity/resilience” overstates identification | CHANGE NOW | β mixes party movement, national candidate divergence, replacement/personal/tactical effects and denominator behaviour. Correlated omitted changes can bias slopes either way, not merely inflate noise. No magnitude is identified here. | Low, documentation | Call Stage6 a descriptive unconditional party-seat response; coefficients provisional, operational values still null. |
| Missing target-boundary candidate baseline blocks literal2026 deployment | CHANGE NOW | C0 on2020 boundaries is not C0 on2026 boundaries. Substituting it can materially bias changed-seat predictions. | Low now, later baseline work | Define an explicit baseline/applicability dependency; do not fabricate candidate reconstruction or use a dominance cutoff chosen after seeing results. |
| “Three independent estimators” must mean separately validated predictive views, not independent evidence | CHANGE NOW | All views reuse party/candidate/split evidence. Summing them or treating their errors as independent would double-count loyalty/personal vote. | Low contract change | Common inputs and explicit baseline; each view predicts the full same outcome, never additive bonuses. Ensembling requires joint out-of-fold predictions and residual-correlation diagnostics. |
| Zero-intercept primary comparison | KEEP | Common intercept α is−0.529pp National/−1.012pp Labour pooled, but chronological transfer does not improve consistently (below). Fixed transition intercepts change slopes but cannot supply an unseen election intercept. | None | Keep frozen zero-intercept comparison; it is a restriction of a provisional predictor, not a proven behavioural law. |
| Turnover conditioning and source-level residual dependence | DEFER | Residual correlation with source candidate share is−0.267 National/−0.233 Labour, versus−0.039/+0.018 with source party share. This could reflect regression-to-mean, arithmetic differencing, candidate changes or bounded outcomes; not proof of a new effect. | Moderate shared infrastructure | Define occurrence-level normalization at Stage7; build reusable history/status at start of persistence; reconsider joint/conditional β after replacement-effects work, before three-view integration. Do not infer people now. |
| Equal-seat weighting | KEEP | Vote-weighted β is0.73602/0.62098 versus0.73687/0.61475. Transition balancing changes slopes by<0.00046. Seat accuracy is the estimand, not voter-total loss. | None | Preserve equal eligible electorate-transition weights. No substantial weighting search. |
| Distinct valid candidate/party denominators | KEEP | They define the requested outcomes correctly. Replacing candidate denominator with party denominator changes delta by median≈0.22pp; p90≈0.72/0.59pp and maxima1.57/2.51pp. Not universally negligible, but denominator substitution changes the estimand rather than fixing it. | None | Preserve both denominator concepts; future ballot-count simulation must handle them explicitly. No ingestion rewrite. |
| Bounded/logit candidate model now | NOT WORTH PURSUING | Only three out-of-range predictions across repeated evaluation configurations; no evidence this drives current conclusions. | Moderate extra specification | Keep raw linear diagnostics. At later deployable-model validation specify a bounded output policy and test it if actual failures become material. |
| Same-boundary-only fitting, missingness and separate Māori scope | KEEP | Prevents fabricated candidate changes. National has no Māori pairs; Labour has21 pairs in three clusters. Pooling or manufacturing data would change identification. | None | Retain exclusions and descriptive Māori status; no extra acquisition. |
| Stage4 feasible bounds / Stage5 retained transforms / occurrence IDs | KEEP | Existing contracts preserve global coupling, source precision, unresolved transform choice and election-local identities. They support later work without overwriting observations. | Low future adapter reuse | Consume versioned inputs; parameterize one pipeline. Never independently sample marginal endpoints or rerun name matching in each effect module. |
| Extra precision, broad source archaeology, formal cluster inference | NOT WORTH PURSUING | Tiny numerical improvements cannot resolve three-cluster instability or omitted candidate structure. | Potentially high | Preserve existing bounds/discrepancies. No extra web/data/solver work. |

## Intercept challenge: quantitative evidence

Exploratory pooled common-intercept slopes are0.7690 National and0.5900 Labour. Transition-intercept slopes are0.6971 and0.5313. Associated transition intercepts (pp) are National−0.968/−0.417/+0.710 and Labour+3.257/−2.567/−4.719. Thus election-wide offsets are potentially material, especially Labour; they are not shown to be portable to an unseen election.

Chronological candidate-share MAE(pp), training only earlier transitions:

| Party / holdout | Frozen zero-intercept fit | Common-intercept diagnostic | β=1 |
|---|---:|---:|---:|
| National2014→2017 | 3.857 | 3.582 | 3.478 |
| National2020→2023 | 4.434 | 5.009 | 4.202 |
| Labour2014→2017 | 4.023 | 8.744 | 7.873 |
| Labour2020→2023 | 10.609 | 12.395 | 7.388 |

Do not estimate a holdout transition intercept from its outcomes and call that a forecast. With three clusters, neither significance claims nor elaborate random-intercept inference is warranted. Future national candidate-vs-party normalization belongs to the normalized-performance design and must not then be added again as a separate intercept. Retaining the present specification means retaining its diagnostic comparison, not endorsing a universal zero-intercept behavioural assumption.

## Viable2026 dependency and effect map

The operational contract requires: source/target boundary IDs, source local party baseline, **target-geography reference candidate baseline or explicit unavailable**, baseline provenance/coverage, retained transform scenario, provisional/frozen coefficient status, and uncertainty dependencies. Stage6 alone cannot populate that candidate-baseline field. Port Waikato remains unavailable; a later by-election would require separate authorization/evidence.

Preferred later route: define normalized candidate-performance evidence at Stage7, then construct a target-boundary reference baseline only where its transport and candidate-status assumptions are defensible. Applicability/coverage gates may withhold an elasticity view for weak predecessor mappings. A transported seat-level premium is an assumption, not automatically a person's persistent effect. Do not adopt a dominance threshold or transport equation during this audit.

For clarity, if a *later validated* reference baseline is C0*=P0*+u0*, the response view can be written C1=P1*+u0*+(β−1)(P1*−P0*). This identity exposes the overlap: attenuated response is a change in candidate-minus-party advantage. Adding a second persistent-premium term to this complete prediction would count the same baseline twice. This is a dependency illustration, not a Stage7 implementation or chosen normalization formula.

| Component | Baseline → outcome | Conditioning | Residual contribution / overlap guard |
|---|---|---|---|
| Stage5 party transform | Historical local party → target local party | Source/target national support; historical boundary input | Party baseline only; retained method is a shared scenario, not independent per-seat noise. |
| Stage6 response component | Available C0*,P0* → target candidate share | Local party movement; provisional β | Complete response-view prediction; β is reconsidered conditional on later candidate-status structure. Do not add separate unchanged u0 again. |
| Stage7 normalized performance | Defined party/national reference → occurrence-level candidate deviation | Same denominators, election environment, geography | Choose/reference the residual scale first; do not identify it as permanent personal quality. Preserve alternative baseline sensitivity. |
| Persistence | Source normalized deviation → target deviation | Verified person/history, contest context, training folds | Predict retention of the same residual; not a bonus added atop an already retained premium. |
| First-term incumbency | Persistence/reference prediction → residual change | Prior tenure/status, normalized source performance | Incremental conditional effect, not raw incumbent advantage; exclude prior-tenure misclassification. |
| Replacement | Reference for continuing candidate → replacement outcome | Same normalized scale and history/status | Account for removal/change of retained premium; do not both erase it and subtract a full unconditioned replacement penalty. |
| Split-ticket view | Local party distribution → candidate allocation | Candidate slate and identifiable split evidence | Alternative complete candidate prediction, overlapping premium/loyalty evidence; never an additive personal-vote bonus. |

**Strongest architecture:** common target-geography data/normalization contracts, separately trained response/premium/split predictive views where inputs are supported, and held-out combination of complete predictions. Do not force all three to exist or have positive ensemble weight. Stage6 is a component of the response view, not a standalone deployable estimator. Out-of-sample weights help with correlation but cannot repair shared leakage, weak identification or missing candidate baselines; with few transitions they may themselves be unstable. Compare simpler individual views as ensemble benchmarks.

## Stage order and reusable identity plan

Keep Stage7 next: define occurrence-level normalization and leakage-safe evaluation **before** learning persistence. It does not require person IDs. At the start of the persistence stage, first build one shared occurrence→person evidence table and election-dated status/history layer, reused by persistence, first-term and replacement work.

Repository-only linkage may resolve uniquely corroborated full-name/party/seat/history chains, with explicit rule/evidence and collision checks. Equal names alone, surname/initial similarity, party switch or seat switch are not proof. Source-local aliases already recorded are not cross-election identity evidence. Preserve unresolved alternatives and abstain on collisions; do not default to biography browsing. Store links separately from immutable occurrence records. Tenure/status needs actual prior history, not just first appearance in2008–2023; left-censored prior service stays unknown. “Same person” and “same candidacy/party/seat” are different keys.

After replacement effects are available, and before three-view integration, re-estimate/review response β jointly or using leakage-safe residualization against the common normalized candidate/status structure. Do not condition on future outcome-derived effects or classify status using future information. Compare against current unconditional fits andβ1. Freeze operational coefficients only through the later historical model/ensemble validation. This adds a prerequisite and a review gate, not a reorder of the whole project.

## Uncertainty contract and review gates

- Boundary feasible sets remain coupled constraints, not independent uniforms on published marginal intervals. No probability distribution is implied by bounds.
- Transform choice is a shared model scenario; preserve correlated electorate/cross-party impacts rather than adding independent transform noise to each prediction.
- Candidate normalization, persistence and response coefficients are dependent estimates. Refit/evaluate together by historical fold; do not add their marginal uncertainty variances as independent.
- Polling uncertainty later induces shared national movement. Candidate effects and residual seat shocks need a separate joint structure conditional on the components already included. Do not add full historical residual error again on top of uncertainty already calibrated from those same errors.
- Calibrate total held-out predictive error and correlation after component integration, including baseline availability. Stage4 bounds and Stage5/6 model ambiguity need scenario/sensitivity treatment until defensible probabilities exist.

Retain larger reviews: **after historical split-ticket work/before three-view integration; after full historical ensemble backtesting/before2026 inputs; after Monte Carlo/MMP/before final website integration**. No subsequent stage is started here.
