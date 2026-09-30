# Conditional Stage 6 NAT/LAB response review

## Pre-fit evidence checkpoint

PR #22 merged as `1374566`, containing reviewed head `333f634`. This Stage 16 branch starts from that merged state. This checkpoint audits preserved evidence only; no new fit or score has been calculated.

The original Stage 6 estimand is `C1 = C0 + beta * (P1-P0)`, separately for National and Labour. Candidate shares use valid candidate votes, party shares use valid party votes; changes are fractions and errors are reported in percentage points. Its zero-intercept, equal-party-seat-weight slope uses observed party movement. Stage 5 transforms substitute target local party inputs using observed target national support, without refitting the structural slope. This is conditional response, not an as-of forecast, causal resilience or a same-person effect. Carrying C0 forward carries a party-seat baseline even when the candidate changed.

The new inventory retains the original general frame: 384 party-seat pairs across 2008→2011, 2014→2017 and 2020→2023; 382 held eligible pairs, 191 per party. Two cancelled 2023 Port Waikato pairs remain explicit. Stage 6's 21 descriptive Labour Māori pairs and absent National pairs are coverage-only here. Within-election occurrence IDs are joined by validated boundary regime/seat number and affiliation, not name-based person inference. The inventory contains no target candidate results, target residuals or target winner flag. It pins and audits source files, candidate provenance, Stage 8 pair evidence, Stage 9 tenure, Stage 10 adjudication and the Stage 13 pilot separately.

No broad primary pre-result cross-election relation cohort is established. `primaryCrossElectionRelation=unresolved` is this review's conservative analysis gate, not a rewrite of retrospective adjudications. Stage 8/9 winner-profile coverage, Stage 10 outcome-related acquisition priority and Stage 13 limited relation coverage prevent turning inherited labels into balanced prospective status. Fact dates, publication/retrieval dates and original evidence routes remain nested in each inventory record; no new dates or alias links are inferred. The 48 NAT/LAB pairs inside the Stage 13 pilot do not establish primary relations. National's inherited Stage 10 classes include three supported replacements and Labour's two, but those selectively acquired cases do not justify a broad turnover adjustment. All identity evidence is audit-only; none admits, excludes or stratifies the primary regression.

One supported conditioning fact is available throughout: the party's source-election candidate won that seat. Source-win/source-loss counts are National 41/22, 41/23, 22/42 and Labour 19/44, 21/43, 40/24. This is a historical **party-seat victory indicator**, not proof that the target candidate is a returning incumbent or that continuous tenure occurred. Both groups remain in the full analysis. Its conditional association can be studied without linking people; its association also reflects baseline selection/regression-to-mean and cannot establish a causal incumbency effect.

Historical checkpoint next action was to freeze and commit the parsimonious source-victory response specification before fitting. Turnover/tenure conditioning remains unsupported; source-victory conditioning is the narrower supported question. No new acquisition or identity adjudication is authorized.

## Frozen pre-fit design

After inventory commit `20c9012`, the specification freezes one nested OLS family: `deltaC = alpha + beta deltaP + gamma W_source`. The primary comparison adds the supported source-victory indicator to a separately fitted common-intercept response on identical rows. Fixed-beta 0/1 variants re-estimate the same nuisance terms, so beta comparisons do not conflate an intercept or status adjustment. The original zero-intercept Stage 6 family and its beta0/beta1 benchmarks remain contextual comparisons. These are predefined restrictions of one family, not model search. Turnover and target personal incumbency remain unestimated.

Each party uses only completed earlier target elections to train its 2017/2023 predictions. In 2011, only parameter-free beta0/beta1 exist. A full-sample fit is labelled descriptive. The same fitted coefficients serve all four party-input modes. The original separate denominators and raw, unclipped candidate-share predictions are retained. Exact-rational small normal equations provide deterministic coefficients with explicit rank/group-size gates. Stage5 bounds propagate monotonically through the affine prediction, including negative beta; no arbitrary midpoint or independent joint sampling is introduced.

Primary tests compare source-victory vs common-intercept and source-victory vs its own fixed-beta0/1 restrictions. All other predeclared comparisons are context, not a route to select the best result. Materiality is a 0.25pp indicative aggregate MAE gain alongside fold/transform stability and RMSE/bias. Operational selections stay null regardless. Stage15 has no point predictions; comparison is limited to common-frame accounting, not an incompatible performance ranking.

## Findings after frozen chronological calculation

The specification was committed at `4fb3366` before new fitting/scoring. It allows only the narrower source-party-seat-victory association, not a replacement or personal-incumbency coefficient. Every eligible party has 63/64/64 observations in 2011/2017/2023. For 2017 the 63 completed 2011 records train the fit; for 2023 the 127 completed 2011/2017 records train it. All fitted 2011 predictions abstain. No fitted model fails the predeclared rank or source-status group-size gates in the supported folds. All retained Stage5 inputs on this unchanged-boundary frame are singleton intervals, so point errors are exact; the generic pipeline also preserves nondegenerate input bounds without midpoint substitution.

The main observed-local-party comparison is below. Errors are percentage points of valid candidate votes; each entry is MAE / RMSE. The common-intercept model omits only source victory and is fitted independently on identical training records.

| Party | Holdout | Source-victory model | Common-intercept model | Original zero-intercept Stage6 | Simple beta1 |
| --- | --- | --- | --- | --- | --- |
| National | 2017 | 3.5820 / 5.6170 | 3.5823 / 5.6173 | 3.8575 / 5.7429 | 3.4778 / 5.6549 |
| National | 2023 | 4.7868 / 6.1558 | 5.0089 / 6.3863 | 4.4340 / 5.9730 | 4.2024 / 6.3612 |
| Labour | 2017 | 7.7661 / 9.2901 | 8.7440 / 9.9797 | 4.0231 / 4.8133 | 7.8733 / 9.3633 |
| Labour | 2023 | 13.0213 / 14.1746 | 12.3955 / 13.5021 | 10.6089 / 11.8828 | 7.3883 / 8.3508 |

These columns are not a model-selection contest: the first two isolate source-victory conditioning; original Stage6 and simple beta1 have different intercept restrictions and are context. Nuisance-matched beta0/1 restrictions of both intercept families are also saved, each re-estimating its intercept/status terms on the same training sample. Bias and source-win/source-loss breakdowns are in `analysis.json`.

National's source-victory term improves both folds relative to the common-intercept model, but 2017 improves by only 0.00025pp. Aggregate MAE gains over observed/additive/proportional/log-odds inputs are **0.1111 / 0.0994 / 0.1414 / 0.1143pp**, all below the indicative 0.25pp materiality threshold. No extra precision work is justified for that distinction.

Labour's gains are **0.1760 / 0.1901 / −0.0422 / 0.0226pp**. Each input mode improves 2017 and worsens 2023; the aggregate sign reverses for proportional inputs. The disagreement is retained rather than used to choose a favourable transform. In the source-victory family, a freely estimated beta also fails stable two-holdout improvement over the nuisance-matched beta1 restriction for either party. National's aggregate gain against that restriction ranges from −0.4467 to +0.0681pp, Labour's from −0.2762 to +0.6014pp. Fold reversal persists. This is not an invariant numerical result across transforms, but no retained mode establishes stable operational readiness.

Full-sample source-victory coefficients `(alpha pp, beta, gamma pp)` are National **(+0.5924, 0.7397, −1.8298)** and Labour **(−0.6281, 0.5819, −1.0346)**. They are descriptive only. Gamma is a conditional source-party-seat-victory association, potentially reflecting baseline strength, selection and regression-to-mean, not a personal incumbency penalty or causal effect. It does not resolve turnover confounding. None is added to Stage7–10 terms.

The original Stage6 zero-intercept full slopes and all 16 original chronological fitted mode/party/fold errors are reproduced within floating-point tolerance by an independent rational implementation. The response pipeline does not silently clip out-of-range predictions; all five occurrences across repeated model/mode/fold configurations are saved with raw bounds. Operational beta and source-victory selections remain null irrespective of the diagnostic comparisons.

## What remains unsupported

Candidate turnover and returning-incumbent conditioning remain unsupported on a broad balanced prospective frame. Retrospectively supported relations stay visible but are not fitted or used to admit cases. Source victory is complete and available from the previous election, yet it cannot distinguish a returning incumbent from a replacement, intervening by-election or former member. There is no missing-status indicator pretending to fix that problem.

Observed local party movement is a conditional input. Stage5 transformed movement is conditional on observed target national support. Neither supplies a national forecast, dated target nomination information, or a candidate baseline on 2026 boundaries. A heldout candidate result is only an evaluation outcome; earlier completed results train later folds. Changing source victory legitimately changes W, whereas changing target/later winner flags with evidence fixed does not.

Stage15 shares 63/64/64 general contests with this review, but has no candidate-vote point forecasts. `stage15-overlap.json` reports overlap only; it does not manufacture an interval-versus-point performance ranking. Neither the failed pooled-equality ledger nor this conditional response constitutes a complete, mass-conserving as-of candidate forecast. No independent NAT/LAB normalization, outgoing-premium subtraction or effect stacking was performed.

The useful next design question is how to establish a defensible target-boundary party-seat candidate baseline and joint predictive uncertainty, while retaining explicit unknown candidate changes. This review supplies chronological residual diagnostics and a negative result for the tested conditional adjustment; it does not authorize that later design, further acquisition, integration or ensemble weights.

## Reproduction and validation

Run `.venv/bin/python -m scripts.models.conditional_nat_lab_response.inventory --check` and `.venv/bin/python -m scripts.models.conditional_nat_lab_response.run --check`. The inventory, specification, consumed input hashes and analysis manifest are separate checkpoints. Source records and raw bytes from the shared election snapshot and existing identity plans are verified without pinning unrelated registry additions. Prior stages are read only.

Focused tests cover full inventory/adapter/fold outcome mutation, source-status missingness, deficient rank, earliest-holdout abstention, nuisance-matched restrictions, signed interval propagation, unclipped predictions, original Stage6 replication and independent NumPy coefficients. Full configured checks and final CI status are recorded in PROJECT_STATE.md. No new sources or person adjudications were acquired.

Local configured validation passed: 30 frontend tests, typecheck/build, 306 Python tests (including 13 focused Stage16 tests), and 924 registered source checks. The input contract also verifies 763 consumed raw resources across preserved plans. Inventory/analysis regeneration and Python compilation pass. Independent NumPy chronological MAE/RMSE/bias calculations agree in all four input modes. Registry tests reject changed/deleted required records and duplicate IDs while accepting unrelated additions; changed input hashes fail. Git comparison against merged main finds no prior data artifact changes.
