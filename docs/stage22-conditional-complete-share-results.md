# Stage 22: shared-group repair and conditional complete-share experiment

The [implementation plan](stage22-implementation-plan.md), [amended pre-fit checkpoint](stage22-prefit-amendment.md) and [machine fit contract](../data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json) were committed before Stage22 fitting. The [saved fits and predictions](../data/processed/checkpoints/stage22-shared-group-experiment/predictions.json) were then committed before the [evaluation-only actuals and diagnostics](../data/processed/checkpoints/stage22-shared-group-experiment/diagnostics.json) were generated. Original Stage18/20 and Stage5–21 artifacts remain historical and unchanged.

## Amended sample and evidence

The official 2014 Internet MANA and 2023 Freedoms NZ party-ballot groups each have one documented standing constituent candidate in the affected held seats. The baseline assigns that group share once to its one local candidate while retaining original affiliation separately. This is an explicit candidate-share allocation assumption, not a constituent-specific observed party vote. In all, 26 previously excluded 2014 **election-local training** seats become complete, 20 held 2023 evaluation contests (147 candidates) become constructed, and six already constructed 2023 candidates have erroneous no-group support corrected to positive Freedoms-group support. The cancelled contest remains excluded. These corrections do not assert cross-election alliance–constituent continuity. The 2014 alliance exits; later constituent categories enter and receive neutral S/V fallback.

The fixed 213-contest frame has 191 constructed held general contests/1,313 target candidate occurrences, 21 Māori coverage-only contests (79 candidate occurrences), and one cancelled contest (nine nominations outside the 1,313 held-general denominator). The 2011/2017/2023 constructed general folds have 63/423, 64/431 and **64/459** contests/candidates. Supported S/V features cover 280/285/271 candidates, leaving 143/146/188 neutral feature fallbacks. All four methods share exact contest/candidate IDs. The 2017 fit trains on 2011's 63/423; the 2023 fit trains on 2011+2017's 127/854. The earliest 2011 fold has no eligible earlier feature transition and is not fitted. Rank 2 for S/V, rank 3 with the floor and scaled training condition ratios below 2.80 pass all frozen pre-fit gates. Exact IDs, source contracts, fallback reasons and old/new deltas are in the machine checkpoint.

## Fitted printed-percentage scenario

Each restriction was refitted jointly from scratch with equal-contest cross entropy. κ is in share units; θ acts on one-unit fractional S/V covariates after training-only centering. All printed-scenario solutions satisfy the fixed numerical checks and lie inside their parameter boxes.

| Holdout | Restriction | κ | θS | θV | Contest-equal MAE | RMSE | Unique winners correct |
|---|---|---:|---:|---:|---:|---:|---:|
| 2017 | baseline | 0.002511 | — | — | 2.433 pp | 4.709 pp | 56/64 |
| 2017 | +S | 0.009388 | 1.366 | — | 2.220 | 4.235 | 61/64 |
| 2017 | +V | 0.002873 | — | 3.772 | 3.022 | 5.652 | 55/64 |
| 2017 | +S+V | 0.005184 | 0.644 | 2.837 | 2.819 | 5.196 | 59/64 |
| 2023 | baseline | 0.004317 | — | — | 3.173 | 5.357 | 54/64 |
| 2023 | +S | 0.010161 | 1.153 | — | 2.303 | 4.750 | 52/64 |
| 2023 | +V | 0.005032 | — | 2.518 | 3.109 | 5.386 | 53/64 |
| 2023 | +S+V | 0.007417 | 0.582 | 1.820 | 2.849 | 5.314 | 53/64 |

Negative **model-minus-control** error differences mean improvement; gains below are control MAE minus model MAE on identical slates. In 2017, S gains **0.213 pp**, V loses **0.590 pp**, and S+V loses **0.386 pp** versus baseline. S+V also loses **0.599 pp** against refitted S. In 2023, S gains **0.871 pp**, V gains **0.065 pp**, and S+V gains **0.324 pp** versus baseline, but loses **0.546 pp** against refitted S. The reduced restrictions were independently refitted, never obtained by zeroing a combined coefficient. Uniform is much worse (16.433/14.773 pp MAE) but that mainly measures the value of supplied observed party shares, not the fitted feature adjustments. On the restricted positive-mapped/no-independent 31-contest subset in each holdout, the zero-floor comparator has 2.669/3.742 pp MAE; it is contextual, not an all-slate alternative. Uniform predicts a tied winner in all 128 trained-fold contests; none of the four fitted restrictions has a winner tie.

The 2023 original Stage20 intersection has 44 contests/312 candidates **using corrected group inputs and the same amended fits**. There S+V gains 0.391 pp against baseline. The newly admitted 20 contests/147 candidates have a smaller 0.179 pp S+V gain. S alone gains 0.988 and 0.611 pp respectively. There was no subset-specific refit. Stage20 had no scores; Stage18's earlier historical scores used six wrong zero-group inputs and must not be treated as corrected common-sample scores.

As in Stage18, the κ-only model adds the same floor to each candidate and cannot change the party-support ordering of a fixed slate. S/V adjustments can change rankings but provide no winner-probability distribution. The S model's lower 2023 share MAE accompanies **52/64** correct unique winners versus **54/64** for baseline; share improvement and ranking improvement are different outcomes.

## Rounding, influence and decision

Coherent all-row selected-lower/upper witness refits use the same IDs and fresh training-only means. The combined-versus-baseline MAE gain ranges **−0.386333 to −0.386333 pp** in 2017 and **0.324296 to 0.324296 pp** in 2023 at shown precision. These scenarios only perturb published source rounding; they are not uncertainty bounds on future candidate behavior. Combined-versus-baseline leave-one-contest-out gain ranges **−0.455 to −0.321 pp** in 2017 and **0.238 to 0.431 pp** in 2023. The largest paired 2017 losses are electorates 36 and 57 (4.520 and 4.294 pp contest MAE difference); the largest 2023 loss is electorate 49 (6.403 pp), while electorate 11 gains 5.743 pp. All contests remain in the primary estimates.

The frozen combined-model development screen **fails**: 2017 MAE worsens 0.386 pp and RMSE worsens 0.488 pp, exceeding the 0.25 pp regression screen. The 2023 0.324 pp MAE gain and no RMSE regression cannot erase the earlier reversal. No operational Stage22 coefficient is selected. The positive S-only diagnostic does not automatically authorize a separate operational model: its 2017 gain is below the 0.25 pp screen and both elections were already used in model development. Inherited operational nulls remain null, not estimated real-world zero effects.

Complete-slate signed bias cancels mechanically. The supported-S/V candidates instead show combined-model mean signed bias **+0.273/+0.149 pp** in 2017/2023, while fallback candidates show **−0.533/−0.215 pp**; the exact category and party breakdowns, including small-cell counts, remain in the machine report. These are descriptive allocation errors, not evidence of causal candidate strength.

## Limits and next decision

S is a rounded earlier party-ballot destination proportion; V is an earlier candidate-share minus party-share gap with distinct denominators. Neither is a uniquely personal or causal effect. The baseline and features use observed target local party support and retrospective candidacy. Earlier source publication by target nomination close remains unverified. Neutral fallback preserves unknown strength, rather than observing it as zero. Shared group assignment is election-local, and only unchanged-boundary general contests are evaluated. Māori local split support remains unavailable. Three already inspected transitions are development evidence, not independent untouched confirmation. Category-level and feature-support signed biases, candidate-equal sensitivities, tie handling and complete paired contest errors are saved in the diagnostic JSON. Full-slate signed bias is zero by accounting, not calibration. No calibrated winner probabilities, changed-boundary 2026 baseline or complete-pipeline score follows.

**Recommended next decision:** retain the joint S/V operational null and stop fitting Family B variants on these reused elections. A separately authorized, narrowly scoped **complete coherent party-category input design** is the next prerequisite for level-3 complete-pipeline diagnostics; Stage5 marginal outputs cannot be zero-filled or combined into a joint vector. Dated as-of inputs, target-boundary candidate evidence and joint uncertainty remain separate later requirements. No integration or ensemble choice follows from this stage.

## Reproduction

Install pinned Python dependencies from `requirements-boundaries.txt`, then run `python3 -m scripts.checkpoints.stage22_prefit --check`, `python3 -m scripts.checkpoints.stage22_construction --check`, and `python3 -m scripts.checkpoints.stage22_evaluation --check` in that order. The first checks the outcome-free mapping, exact IDs, rank audit and consumed raw-source snapshot. The second independently refits and compares the committed construction bytes. The third reads the committed construction and evaluates target outcomes separately. Each manifest pins its inputs, generators and output hashes. Historical Stage18/20, Stage5–21 numerical files and raw sources are not regenerated by these checks. The source registry may add unrelated records without breaking Stage22; consumed registry records, ambiguous IDs and altered raw bytes fail.
