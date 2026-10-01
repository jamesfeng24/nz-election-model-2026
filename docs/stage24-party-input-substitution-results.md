# Stage 24 — fixed candidate-model party-input substitution

The [frozen contract](stage24-frozen-input-substitution.md) and exact input inventory were committed as `6ee5cb0` before any Stage24 prediction. The construction was committed separately as `519b587` before held-out candidate outcomes were read. This report evaluates that committed construction without refitting Stage22. Full candidate-level errors, paired contest records, group errors, ranking transitions and fixed party-error-bin summaries are in [diagnostics.json](../data/processed/checkpoints/stage24-party-input-substitution/diagnostics.json). The adjacent evaluation manifest pins its inputs and output bytes.

## Population and information set

The common four-cell sample is 64 unchanged-boundary held general contests/431 candidates in 2017 and 64/459 in 2023, with no within-sample abstention. The fixed 213-contest frame also has 63 held general 2011 contests without an eligible earlier Stage22 S fit, 21 Māori coverage-only contests and cancelled Port Waikato. All six observed-input A/B constructions reproduce Stage22's saved candidate shares **exactly** across both folds and printed/lower/upper source-rounding scenarios. The printed working approximation is primary. An affirmative no-party-group candidate has zero *party input*, not zero predicted candidate share. The 2023 sample includes 26 official single-destination shared-group candidates without duplicating party mass.

Stage23's target local party vectors are conditional on **observed target national party support**. A/B additionally use observed target local party support. Every cell uses a retrospective complete candidate slate. None is an as-of forecast; neither national reconciliation nor 2026 target-boundary transport is established. The 2017/2023 elections have repeatedly informed model design and are development evidence.

## Four-cell results

A = baseline with observed local party input; B = S-only with observed input; C = baseline with Stage23 predicted input; D = S-only with predicted input. Errors are percentage points of **valid candidate share**. Each contest is weighted equally, with RMSE computed as the square root of the mean of contest candidate MSEs. The S difference is S-only minus baseline, so a negative value favours S. `I = (D−C)−(B−A)` uses identical contests and candidate IDs in all four cells.

| Holdout | Contests / candidates | A MAE / RMSE | B MAE / RMSE | C MAE / RMSE | D MAE / RMSE | B−A MAE | D−C MAE | C−A / D−B damage | I |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2017 | 64 / 431 | 2.433 / 4.709 | 2.220 / 4.235 | 2.533 / 4.922 | 2.634 / 4.808 | −0.213 | +0.101 | +0.100 / +0.414 | **+0.314** |
| 2023 | 64 / 459 | 3.173 / 5.357 | 2.303 / 4.750 | 3.324 / 5.437 | 2.355 / 4.751 | −0.871 | −0.969 | +0.151 / +0.052 | **−0.099** |
| Pooled, 128 equal contests | 128 / 890 | 2.803 / 5.043 | 2.261 / 4.500 | 2.928 / 5.186 | 2.495 / 4.780 | −0.542 | −0.434 | +0.125 / +0.233 | **+0.108** |

The 2017 S advantage in observed-input MAE reverses under predicted inputs; 2023's advantage increases slightly. The pooled positive I is an equal-contest arithmetic average of opposite fold interactions, **not** an independent-election estimate or a selection statistic. Candidate-equal MAEs are 2.403/2.151/2.509/2.559 for A/B/C/D in 2017 and 2.997/2.134/3.130/2.187 in 2023. Neither the pooled average nor the large 2023 improvement licenses an operational coefficient. Stage22's existing 2017 0.25pp developmental materiality screen was not met on observed inputs; Stage24 introduced no new threshold.

The 2017 contest-level I distribution has min/25th/median/75th/max −1.152/−0.103/+0.117/+0.516/+2.702pp; its leave-one-contest-out mean range is +0.276 to +0.337pp. In 2023 these values are −2.449/−0.359/+0.002/+0.346/+1.374pp and −0.122 to −0.061pp. The largest absolute I observations are 2017 electorate IDs 48, 07 and 45 (+2.702/+2.487/+2.295pp) and 2023 IDs 10, 04 and 35 (−2.449/−2.278/−2.068pp). All remain in the primary scores. The saved diagnostic gives five influential contests and leave-one-out ranges for each fold and the pooled sample.

## Candidate categories and local-party errors

The table reports **candidate-equal** MAE by fixed group. Each National and Labour group covers one candidate in each of 64 contests per fold. `Other` means mapped party/group candidates; `No group` is an affirmative classification and remains separate. The full artifact also records candidate-equal RMSE, signed bias, and a contest-equal group sensitivity averaged only over contests containing that group. These subgroup averages are not additive components of whole-slate MAE.

| Holdout / group | Candidates / containing contests | A | B | C | D | Group I |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2017 National | 64 / 64 | 4.053 | 4.352 | 4.869 | 5.990 | +0.822 |
| 2017 Labour | 64 / 64 | 5.565 | 3.449 | 5.330 | 4.349 | +1.134 |
| 2017 National + Labour | 128 / 64 | 4.809 | 3.901 | 5.099 | 5.169 | +0.978 |
| 2017 other mapped | 258 / 64 | 1.508 | 1.494 | 1.542 | 1.548 | +0.020 |
| 2017 no group | 45 / 33 | 0.685 | 0.938 | 0.685 | 0.936 | −0.002 |
| 2023 National | 64 / 64 | 5.210 | 4.316 | 5.504 | 4.088 | −0.522 |
| 2023 Labour | 64 / 64 | 4.161 | 3.328 | 4.659 | 3.417 | −0.409 |
| 2023 National + Labour | 128 / 64 | 4.686 | 3.822 | 5.081 | 3.752 | −0.465 |
| 2023 other mapped | 281 / 64 | 2.623 | 1.569 | 2.659 | 1.689 | +0.084 |
| 2023 no group | 50 / 33 | 0.779 | 0.981 | 0.779 | 0.982 | +0.002 |

National/Labour local party input MAE is 2.819/2.816pp in 2017 and 2.200/2.215pp in 2023. The Stage23 all-category average is much smaller because many minor categories are near zero; it is not the accuracy of the major-party inputs used here. The fixed signed party-error bins and paired candidate-error changes are saved separately for each party. For example, 2017 National has 26 of 64 party-input errors in `(2,5]`pp, while Labour has 21 in `(−5,−2]`pp. These are retrospective evaluations against actual local party results, not construction features. The category bias records show that whole-slate signed bias cancels through conservation even while party-specific biases remain material. For 2023 National, S-only signed candidate bias is +3.797pp with observed and +3.230pp with predicted party input; for Labour it is −1.418 and −0.182pp. Unknown person-specific strength remains unmodelled.

## Rankings, rounding and limitations

Unique predicted winners correct out of 64 are A/B/C/D **56/61/56/59** in 2017 and **54/52/54/53** in 2023. No predicted ties occur under the frozen `1e−12` tolerance. Substitution changes four baseline and two S-only predicted winner sets in 2017; the latter loses two correct winners. In 2023 it changes one winner set for each model, and S-only gains one correct winner. Thus the 2023 S-only share gain does not imply better winner accuracy than baseline (53 versus 54 under predicted inputs). Mean absolute actual-winner margin errors A/B/C/D are 9.386/6.392/9.829/9.999pp in 2017 and 7.662/8.496/8.611/7.927pp in 2023. Margin and transition details are evaluation-only records; no calibrated winner probabilities exist.

Printed, selected-lower and selected-upper saved source-rounding fits produce the same conclusions. Maximum change from printed in a fold's four-cell MAE is below `4e−8`pp in 2017 and `7e−10`pp in 2023. These coherent rounding witnesses are measurement sensitivities, not predictive uncertainty ranges. Stage23's maximum oracle-weighted national category gaps are 0.295/0.872/0.313pp for 2011/2017/2023; no national reconciliation is imposed. A positive pooled I does not identify why errors overlap, and the unchanged-boundary general comparison does not validate Māori seats, boundary changes, a 2026 slate, national support forecast, correlated uncertainty or live operation.

**Decision:** retain the saved baseline and S-only models as research comparators and all operational selections as null. The next separately authorized decision should be a bounded design for dated as-of national support, nominations and joint candidate uncertainty on a clearly supported historical sample; it must not choose S-only, refit it to Stage23 inputs or combine it operationally from these reused development folds. A national-reconciliation change is separate and should be justified by its own input contract rather than these candidate scores.

## Reproduction and preservation

Run `python3 -m scripts.checkpoints.stage24_inventory --check`, `stage24_construction --check`, and `stage24_evaluation --check` with the same module prefix. The Stage24 input contract pins Stage22 fit/feature/actual and Stage23 construction bytes and verifies their inherited consumed-source records and raw checksums. Construction and evaluation have separate manifests. The tests independently recalculate all four MAE/RMSE values and I from saved predictions and actuals, exercise the complete-slate formula, winner ties, group arithmetic, outcome mutation, and deterministic regeneration. No raw resource, identity adjudication, previous numerical artifact or operational selection is rewritten.
