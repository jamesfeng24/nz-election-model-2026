# Stage30 — expanded normalized-residual persistence

## Findings and forecasting assessment

Prior residual information deserves retention for a later bounded joint test: carry-forward beats zero in **all five general development holdouts**, including the newly admitted2014/2020 environments. This does not identify uniquely personal retention or establish complete candidate-share improvement. Estimating an unrestricted intercept/slope provides no consistent gain over carry-forward: broad primary MAE is worse in2014/2017/2020 and only0.024pp better in2023. No automatic regularization or variant follows.

S remains preferred for complete-share development, with baseline mandatory. Persistence is a complementary research candidate to test jointly later, not a separately fitted adjustment to add onto S. Parity response remains paused. **All operational selections stay null; null is not an estimated zero effect.** Mathematical estimability, description, retrospective prediction, chronological prediction, development retention and operational selection are separate evidence levels (D060).

## Frozen scope and input roles

Pre-fit checkpoint `d30f646` preceded coefficients; construction `ba81f4e` preceded scoring. Stage26 broad accepted linkage is primary; strict exact-name sensitivity excludes nickname/middle concessions. All accepted links here are algorithmic, not newly documentary-confirmed, and no precision percentage is claimed. Stage26 reversible person groups/acceptance are unchanged. No source-winner or target/later anchor filter, biography selection, career gate, acquisition or new adjudication is used.

The inventory retains3,007 original occurrences,1,630 relationship proposals and356 target-geography records.482 broad residual-supported pairs comprise452 general/30 Māori;413 strict comprise386/27. Fourteen of496 broad accepted relationships and11 of424 strict accepted relationships lack usable residual support. Nonaccepted proposals remain exclusions, never inferred replacements. The whole geographic frame retains changed/ambiguous membership, cancellations and Māori evidence limitations. Stage25 two-sided certification establishes membership, not identical voters. Held status is independently joined from preserved Stage7 candidature, rather than assumed from the geographic layer's unadjudicated statuses.

Parties are pooled within scope, following Stage8; general and Māori are never pooled. Each occurrence retains its candidate-valid and party-valid denominators. Source residual is the frozen source-election candidate-share deviation from a leave-one-whole-contest-out party/election reference; target residual/reference is evaluation-only for its holdout. Stage7 reference populations are not rebuilt on linked records. Proportional/log-odds sensitivities change the expected candidate-share normalization, **not the units of the residual**: every residual remains a candidate-share difference reported in percentage points.

Equation: `r_target = alpha + beta*r_source + error`. Equal-record unrestricted OLS, intercept separately fitted; zero, carry-forward and independently estimated training mean are benchmarked on identical IDs. Numeric centering/RMS scaling only improves solver conditioning. Full rank/finite variation/independent solver agreement are required, without minimum election replication for displaying an identified development estimate. No pseudoinverse rank rescue, clipping, confidence weights, coefficient imports or slope restriction.

Expanding-window training target ≤ holdout source and < holdout target is primary. More-separated training target < source is sensitivity. Overlapping transitions are dependence, not automatically leakage: completed source residuals are permitted even when that election was a training response.2011 regression/mean abstain;2014 more-separated regression/mean also abstain. Zero/carry still score. Other chronological fits are numerically identifiable, including small Māori samples.

## Verified coverage

| Transition | General broad / strict | Māori broad / strict |
| --- | --- | --- |
| 2008→2011 | 120 / 112 | 8 / 8 |
| 2011→2014 | 47 / 42 | 4 / 4 |
| 2014→2017 | 116 / 104 | 9 / 8 |
| 2017→2020 | 61 / 50 | 2 / 2 |
| 2020→2023 | 108 / 78 | 7 / 5 |


## Primary general chronological results

Errors in pp, signed error=prediction−actual. MAE averages absolute pair errors; RMSE takes the root after mean squared errors. Pooled weighting is per record, so smaller partial-election samples do not receive equal election weight. Primary trained comparison excludes the120 earliest records for **all four methods**, while full-frame zero/carry remain reported separately. Macro transition MAE is only a labelled sensitivity.

| Target | Train / eval | α pp | β | Fit MAE / RMSE / bias | Carry MAE / RMSE | Zero MAE / RMSE | Mean MAE / RMSE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2011 | 0 / 120 | — | — | — / — / — | 2.485 / 3.642 | 4.424 / 6.976 | — / — |
| 2014 | 120 / 47 | 0.575 | 1.013 | 1.673 / 2.556 / 1.088 | 1.378 / 2.370 | 3.159 / 4.681 | 3.652 / 4.746 |
| 2017 | 167 / 116 | 0.263 | 1.019 | 2.329 / 4.230 / -0.195 | 2.267 / 4.167 | 4.216 / 6.892 | 4.274 / 6.763 |
| 2020 | 283 / 61 | 0.507 | 0.834 | 2.968 / 4.109 / 0.511 | 2.639 / 3.868 | 5.497 / 9.208 | 5.458 / 9.075 |
| 2023 | 344 / 108 | 0.374 | 0.874 | 2.638 / 4.521 / 0.017 | 2.662 / 4.638 | 4.724 / 7.533 | 4.536 / 7.304 |


Positive paired gain means the fitted model improves on its benchmark.

| Target | MAE gain vs zero | vs carry | vs mean | RMSE gain vs carry |
| --- | --- | --- | --- | --- |
| 2011 | — | — | — | — |
| 2014 | 1.486 | -0.295 | 1.979 | -0.185 |
| 2017 | 1.887 | -0.062 | 1.945 | -0.063 |
| 2020 | 2.529 | -0.329 | 2.490 | -0.241 |
| 2023 | 2.086 | 0.024 | 1.898 | 0.117 |


## Linkage, chronology and normalization sensitivities

Pooled errors below use the identical trained sample within each row, never compare own-population broad/strict as if population were fixed.

| View / scope / chronology / scale | Trained n | Fit MAE / RMSE | Carry MAE / RMSE | Zero MAE / RMSE |
| --- | --- | --- | --- | --- |
| broad / general / expanding_window / additive | 332 | 2.454 / 4.114 | 2.338 / 4.076 | 4.467 / 7.330 |
| broad / general / more_separated / additive | 285 | 2.536 / 4.265 | 2.497 / 4.292 | 4.683 / 7.680 |
| broad / general / expanding_window / proportional | 332 | 2.569 / 4.417 | 2.505 / 4.390 | 4.268 / 7.368 |
| broad / general / more_separated / proportional | 285 | 2.679 / 4.552 | 2.684 / 4.630 | 4.477 / 7.701 |
| broad / general / expanding_window / log_odds | 332 | 2.430 / 4.074 | 2.333 / 4.079 | 4.340 / 7.323 |
| broad / general / more_separated / log_odds | 285 | 2.507 / 4.214 | 2.486 / 4.293 | 4.575 / 7.688 |
| strict / general / expanding_window / additive | 274 | 2.562 / 4.349 | 2.427 / 4.310 | 4.491 / 7.234 |
| strict / general / more_separated / additive | 232 | 2.747 / 4.615 | 2.658 / 4.605 | 4.741 / 7.615 |
| strict / general / expanding_window / proportional | 274 | 2.718 / 4.682 | 2.629 / 4.655 | 4.314 / 7.275 |
| strict / general / more_separated / proportional | 232 | 2.915 / 4.935 | 2.885 / 4.972 | 4.542 / 7.615 |
| strict / general / expanding_window / log_odds | 274 | 2.543 / 4.307 | 2.427 / 4.314 | 4.361 / 7.223 |
| strict / general / more_separated / log_odds | 232 | 2.706 / 4.553 | 2.652 / 4.604 | 4.621 / 7.613 |


On the same strict evaluation IDs, changing only the training-linkage view has small effects:

| Target | Strict n | Broad-trained MAE | Strict-trained MAE |
| --- | --- | --- | --- |
| 2011 | 112 | — | — |
| 2014 | 42 | 1.442 | 1.522 |
| 2017 | 104 | 2.403 | 2.422 |
| 2020 | 50 | 3.010 | 3.052 |
| 2023 | 78 | 2.980 | 2.992 |


Broad-only additions are reported separately without refitting or excluding their outcomes:

| Target | Broad-only n | Fit MAE | Carry MAE | Zero MAE |
| --- | --- | --- | --- | --- |
| 2011 | 8 | — | 1.615 | 2.198 |
| 2014 | 5 | 3.614 | 3.268 | 3.569 |
| 2017 | 12 | 1.687 | 1.472 | 5.036 |
| 2020 | 11 | 2.780 | 1.889 | 7.566 |
| 2023 | 30 | 1.749 | 1.883 | 3.037 |


Original versus added transitions use saved expanding primary predictions; earliest fit abstention stays explicit:

| Composition | Eligible n | Fit n / MAE | Carry MAE | Zero MAE |
| --- | --- | --- | --- | --- |
| Original2011/2017/2023 | 344 | 224 / 2.478 | 2.467 | 4.448 |
| Added2014/2020 | 108 | 108 / 2.405 | 2.090 | 4.480 |


The comparison with historical Stage8 is not a clean sample-size experiment. Stage8's source-winner-selected, retrospectively anchored cohort differs in identity, population and chronology. Its original selection.json stays byte-identical. Applying only its labelled2017/2023 numerical performance convention to these new populations still fails the0.25pp each-fold / no RMSE loss screen. This is a historical diagnostic, not an estimation gate or a claim that prior residual contains no useful information.

## Māori evidence, separate and small

Estimates are displayed when numerically identifiable. Tiny held-out counts and few shared election environments limit forecasting conclusions; no general/Māori pooling or operational coefficient.

| View | Target | Train / eval | α pp | β | Fit MAE / RMSE | Carry MAE | Zero MAE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| broad | 2011 | 0 / 8 | — | — | — / — | 7.614 | 9.420 |
| broad | 2014 | 8 / 4 | 7.386 | 0.858 | 5.239 / 5.510 | 2.483 | 2.958 |
| broad | 2017 | 12 / 9 | 5.637 | 0.865 | 7.673 / 8.944 | 5.295 | 12.714 |
| broad | 2020 | 21 / 2 | 3.412 | 1.040 | 6.598 / 8.626 | 6.418 | 13.328 |
| broad | 2023 | 23 / 7 | 2.927 | 1.073 | 10.580 / 11.817 | 11.656 | 12.393 |
| strict | 2011 | 0 / 8 | — | — | — / — | 7.614 | 9.420 |
| strict | 2014 | 8 / 4 | 7.386 | 0.858 | 5.239 / 5.510 | 2.483 | 2.958 |
| strict | 2017 | 12 / 8 | 5.637 | 0.865 | 7.207 / 8.587 | 5.232 | 13.610 |
| strict | 2020 | 20 / 2 | 3.880 | 1.035 | 6.574 / 8.955 | 6.418 | 13.328 |
| strict | 2023 | 22 / 5 | 3.324 | 1.074 | 8.403 / 9.718 | 9.974 | 8.683 |


## Full-panel description and transition-deletion influence

These fits describe the retained panel. No deleted transition is scored as a forecast; adjacent retained transitions preserve election information. Deletion ranges are not confidence intervals.

| View / scope | Deleted transition | Pairs / environments | α pp | β | Retained fit MAE / RMSE |
| --- | --- | --- | --- | --- | --- |
| broad / general | none | 452 / 5 | 0.379 | 0.867 | 2.401 / 3.853 |
| broad / general | 2008→2011 | 332 / 4 | 0.306 | 0.835 | 2.372 / 3.896 |
| broad / general | 2011→2014 | 405 / 4 | 0.474 | 0.860 | 2.501 / 3.976 |
| broad / general | 2014→2017 | 336 / 4 | 0.194 | 0.948 | 2.433 / 3.877 |
| broad / general | 2017→2020 | 391 / 4 | 0.482 | 0.837 | 2.348 / 3.820 |
| broad / general | 2020→2023 | 344 / 4 | 0.374 | 0.874 | 2.323 / 3.618 |
| broad / maori | none | 30 / 5 | 3.508 | 1.060 | 6.613 / 8.046 |
| broad / maori | 2008→2011 | 22 / 4 | 2.195 | 1.106 | 6.875 / 8.523 |
| broad / maori | 2011→2014 | 26 / 4 | 3.696 | 1.073 | 7.271 / 8.577 |
| broad / maori | 2014→2017 | 21 / 4 | 4.753 | 1.019 | 6.438 / 8.158 |
| broad / maori | 2017→2020 | 28 / 4 | 3.909 | 1.032 | 6.580 / 7.990 |
| broad / maori | 2020→2023 | 23 / 4 | 2.927 | 1.073 | 5.430 / 6.513 |
| strict / general | none | 386 / 5 | 0.418 | 0.849 | 2.482 / 4.009 |
| strict / general | 2008→2011 | 274 / 4 | 0.319 | 0.805 | 2.462 / 4.079 |
| strict / general | 2011→2014 | 344 / 4 | 0.534 | 0.840 | 2.620 / 4.172 |
| strict / general | 2014→2017 | 282 / 4 | 0.144 | 0.942 | 2.514 / 4.045 |
| strict / general | 2017→2020 | 336 / 4 | 0.525 | 0.834 | 2.431 / 3.985 |
| strict / general | 2020→2023 | 308 / 4 | 0.489 | 0.842 | 2.370 / 3.676 |
| strict / maori | none | 27 / 5 | 3.604 | 0.979 | 5.712 / 7.053 |
| strict / maori | 2008→2011 | 19 / 4 | 2.068 | 0.989 | 5.589 / 7.312 |
| strict / maori | 2011→2014 | 23 / 4 | 3.848 | 0.991 | 6.317 / 7.567 |
| strict / maori | 2014→2017 | 19 / 4 | 4.329 | 0.885 | 5.449 / 6.762 |
| strict / maori | 2017→2020 | 25 / 4 | 4.124 | 0.940 | 5.633 / 6.845 |
| strict / maori | 2020→2023 | 22 / 4 | 3.324 | 1.074 | 5.313 / 6.381 |


Largest fixed-fit leave-one-pair changes in regression-versus-carry MAE gain (all pairs remain in primary scores):

| Target | Omitted pair ID | Model absolute error pp | Change in carry gain pp |
| --- | --- | --- | --- |
| 2014 | nz-general-2011-electorate-60-candidate-06->nz-general-2014-electorate-61-candidate-04 | 1.416 | -0.023 |
| 2014 | nz-general-2011-electorate-45-candidate-02->nz-general-2014-electorate-46-candidate-04 | 0.934 | -0.021 |
| 2017 | nz-general-2014-electorate-12-candidate-10->nz-general-2017-electorate-12-candidate-06 | 0.252 | -0.005 |
| 2017 | nz-general-2014-electorate-60-candidate-07->nz-general-2017-electorate-60-candidate-03 | 9.968 | 0.005 |
| 2020 | nz-general-2017-electorate-12-candidate-06->nz-general-2020-electorate-11-candidate-09 | 6.947 | 0.100 |
| 2020 | nz-general-2017-electorate-12-candidate-03->nz-general-2020-electorate-11-candidate-04 | 6.876 | 0.087 |
| 2023 | nz-general-2020-electorate-11-candidate-09->nz-general-2023-electorate-11-candidate-04 | 1.271 | -0.046 |
| 2023 | nz-general-2020-electorate-11-candidate-04->nz-general-2023-electorate-11-candidate-02 | 6.608 | 0.041 |


Party and rule-level bias/counts, complete influence lists, all three normalization scales and both chronology views are in evaluation.json. Sparse groups (<10 pairs) are visibly flagged; no subgroup-specific coefficient is fitted. The full-panel broad general slope0.867 and deletion range0.835–0.948 describe association; they do not justify importing that slope into a historical fold or candidate forecast. Māori slopes and deletions are more identity-sensitive.

## Dependence, evidence limitations and readiness

The sample is conditional on repeated candidacy, accepted practical names/context and exact geography with matched party references. It includes losers without a victory gate but is not a representative sample of all candidates, replacements or changed seats. Retrospective algorithmic linkage is not proof of identity or as-of source availability. The strict subset is a sensitivity, not documentary ground truth. Profile acquisition/history completeness never enters this sample; source availability and cross-election name changes can still affect accepted-link coverage. No linkage queue is reopened.

Shared party/election LOO references, repeated people, repeated seat membership chains and overlapping transitions induce dependence. Counts of records and transition environments are separate in construction.json. Even target records share reference information. Many candidate rows do not create independent elections. No iid significance, causal personal-vote claim, calibrated intervals or winner probability follows. Stable party-seat conditions, tactical voting and joint references can generate retention without uniquely personal effects.

**Graded assessment:** useful predictive information relative to zero is consistent on the general panel; carry-forward is a stronger mandatory comparator than zero/mean. Flexible retention does not yet establish a forecasting improvement over carry-forward. Reasonable linkage/chronology choices preserve that qualitative result, while normalizations affect absolute scales/errors. Keep prior residual for a specifically incremental future development test; do not deploy the fitted coefficient, reject complementary information merely because the historical screen fails, or translate residual error into complete-share gains.

**Exact next decision:** after independent review, separately authorize expanded Stage23 coherent party vectors and fixed-parameter baseline/S input substitution on the Stage25 exact panel. Then specify one small joint/regularized candidate-share comparison using defensible same-person evidence, coherent complete-slate shares and refitted ablations; no separately fitted coefficient stacking. No acquisition, tenure/replacement expansion, parity salvage or new variant is started here.

## Reproducibility and validation

Run the five Stage30 modules `inventory`, `construction`, `evaluation`, `verification`, `report` with `--check`, under `scripts.models.expanded_candidate_persistence`. Initial inventory generation pins consumed records/contracts and all1,402 prior data bytes; provenance accepts unrelated additions but rejects altered required records/raw bytes. Existing raw files, Stage7–29 numerical artifacts, Stage25 geography/folds, Stage26 adjudications/linkage and every prior selection remain unchanged.

Independent covariance arithmetic verifies156 OLS fits; direct vectors verify17,922 predictions,1,224 fold metric values and252 paired gains at1e−8 tolerance. Synthetic and real-adapter tests cover selection/units/rank failures, chronology, strict subsets, missingness, benchmarks, target-result mutation and legitimate earlier-response fitting. Full configured Python/source checks and final-head CI status are recorded in PROJECT_STATE.md/PR. No formatter/linter is configured; compilation/whitespace checks apply. Raw fits/errors are unrounded; three-decimal tables are display only.
