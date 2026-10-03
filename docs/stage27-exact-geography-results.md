# Stage27 — expanded exact-geography conditional retests

Stage27 tests the registered identity-free formulations on canonical Stage25 two-sided exact geography. [Pre-fit contract](stage27-exact-geography-plan.md) and input/sample checkpoint `3b03120` were pushed before fitting. Construction `ae826f4` was pushed before new scoring. Original Stage16/22 artifacts, Stage25 contracts, Stage26 linkage and all operational null/unresolved selections remain unchanged. No new source, identity effect, V, S+V, transform tuning or Stage23 substitution.

## What changed, and what did not

Expanding-window training is primary: completed training targets may equal the holdout source election, always preceding the holdout target. More-separated training retains target < holdout source. Both use precisely Stage25’s IDs; no competing geography definition. Earlier outcome/source-feature election reuse is legitimate conditional information but induces dependence. Publication by a historical cutoff remains unverified.

All inputs are observed target **local** party shares and retrospective complete slates. This is conditional development research, not an as-of forecast, changed-boundary validation, calibrated probability model or operational selection. Five transitions provide four primary fitted environments, not five independent replications. All elections have informed prior design.

## Coverage and fixed samples

| Target | Full geographic frame | Complete exact general slates | Candidates | Supported S / fallback | NAT/LAB records | Primary / separated training slates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2011 | 70 | 63 | 423 | 280 / 143 | 126 | 0 / 0 |
| 2014 | 71 | 20 | 143 | 99 / 44 | 40 | 63 / 0 |
| 2017 | 71 | 64 | 431 | 285 / 146 | 128 | 83 / 63 |
| 2020 | 72 | 34 | 286 | 159 / 127 | 68 | 147 / 83 |
| 2023 | 72 | 64 | 459 | 271 / 188 | 128 | 181 / 147 |

The full frame retains 356 targets: 245 admitted general slates / 1,742 candidates / 490 response records, 35 Māori coverage-only targets, 75 nonexact general targets and cancelled Port Waikato (nine nominations). Added exact coverage is **20 seats / 143 candidates in 2014** and **34 / 286 in 2020**. No approximate transport. These are selected unchanged seats, not representative electorate samples. Candidate publication/slate and geographic certification timing are retrospective.

All permitted trained floor/S coverage and within-slate rank gates pass in printed/lower/upper scenarios. All 20 distinct candidate numerical training problems succeed; all parameters are interior and independent-profile checks agree. Response nuisance/status count and rational rank gates pass in every permitted trained fold. There are no numerical abstentions. 2011 has no transition-trained model; separated 2014 also abstains. Uniform shares remain applicable across all 245 slates. Restricted zero-floor coverage is 43/15/31/14/31 contests, respectively, independent of fit availability.

## Complete-share results

Each contest has equal weight; MAE averages the within-slate mean absolute pp error, RMSE is the square root after averaging within-slate MSE across contests. Each slate includes every standing candidate. S uses the earlier source group-row destination, not personal strength; unsupported features receive the frozen neutral adjustment. Shared-group local support is used once. No outgoing premium or other effect is stacked.

| Protocol | Target | Baseline MAE / RMSE pp | S MAE / RMSE pp | MAE gain pp | Correct unique winners, baseline / S |
| --- | --- | ---: | ---: | ---: | ---: |
| expanding_window | 2011 | no earlier fit | no earlier fit | — | — |
| expanding_window | 2014 | 2.999 / 4.901 | 2.978 / 4.936 | 0.020 | 15 / 16 of 20 |
| expanding_window | 2017 | 2.433 / 4.709 | 2.182 / 4.207 | 0.251 | 56 / 61 of 64 |
| expanding_window | 2020 | 3.293 / 5.783 | 2.257 / 4.051 | 1.036 | 21 / 25 of 34 |
| expanding_window | 2023 | 3.162 / 5.343 | 2.355 / 4.840 | 0.807 | 54 / 52 of 64 |
| more_separated | 2011 | no earlier fit | no earlier fit | — | — |
| more_separated | 2014 | no earlier fit | no earlier fit | — | — |
| more_separated | 2017 | 2.433 / 4.709 | 2.220 / 4.235 | 0.213 | 56 / 61 of 64 |
| more_separated | 2020 | 3.261 / 5.759 | 2.144 / 3.923 | 1.118 | 21 / 25 of 34 |
| more_separated | 2023 | 3.169 / 5.352 | 2.289 / 4.731 | 0.880 | 54 / 52 of 64 |

S improves MAE in every trained fold under both protocols. The predeclared all-fold development screen **fails under both**: expanding 2014 gains only 0.020 pp, increases RMSE 0.036 pp, and has a negative leave-one-contest-out lower gain. Separated 2017 gains 0.213 pp, below 0.25 pp. Expanding 2017 gains 0.250758 pp, only just above the unchanged screen; the original 2017/2023 subset passes under expanding but not separated training. Do not promote that threshold crossing to independent confirmation.

Pooling only fitted folds gives baseline/S MAE **2.912 / 2.345 pp** and RMSE **5.169 / 4.495 pp** under primary training (182 contests / 1,319 candidates). Candidate-equal MAE is 2.826 / 2.236 pp. Separated pooled MAE is **2.897 / 2.231 pp**, RMSE **5.200 / 4.377 pp** (162 / 1,176); these different pools are not an identical-sample chronology comparison. Partial-election samples receive their actual contest weights, not full-election weights.

The common floor retains party-input ordering; S can change rankings, but lower share error is not synonymous with better winners. Primary winner counts improve 15→16/20, 56→61/64, 21→25/34, then worsen 54→52/64. Baseline/S have no predicted ties; uniform ties every complete slate and contains the observed winner in its tied set, never a unique success. Absolute actual-winner margin errors are 11.101→14.693 pp (2014), 9.389→6.393 (2017), 15.558→11.500 (2020), 7.640→8.839 (2023). No winner probabilities.

| Primary target | Restricted no-independent/positive-support contests | Zero-floor MAE pp | Baseline / S MAE pp on that same subset |
| --- | ---: | ---: | ---: |
| 2011 | 43 | 3.178 | no fitted model |
| 2014 | 15 | 2.825 | 2.805 / 2.988 |
| 2017 | 31 | 2.669 | 2.646 / 2.402 |
| 2020 | 14 | 3.744 | 3.769 / 2.389 |
| 2023 | 31 | 3.742 | 3.741 / 2.678 |

Uniform’s large errors chiefly show the value of supplying observed party support; they are not evidence for fitted S or κ. Fallback is missing-feature neutrality, not an empirical finding of zero incoming strength. Party/mapping/S-support/slate-size bias and candidate-equal errors are saved for all fixed groups. Full-slate signed bias cancels by conservation and is only an accounting check.

### Training changes versus added evaluation

The original 2017/2023 slates remain identical (64 each). The following uses the same amended-model evaluation IDs, refitting original-only versus expanded training; positive gain means expanded training lowers MAE.

| Protocol | Original target | Baseline expanded-training gain pp | S expanded-training gain pp |
| --- | --- | ---: | ---: |
| expanding_window | 2017 | -0.000382 | 0.037591 |
| expanding_window | 2023 | 0.011779 | -0.052188 |
| more_separated | 2017 | -0.000000 | -0.000000 |
| more_separated | 2023 | 0.004423 | 0.013641 |

These changes are small (<0.06 pp for S). The 2014/2020 gains evaluate **new election environments**, not a training improvement on the original targets. Every case also saves expanded/original-common/newly-admitted summaries; newly admitted is empty in the original target years and comprises the full exact subset in the added years. No separately tuned subset fit.

### Coefficients, rounding and influence

| Primary target | Baseline κ | S κ | S θ | Earlier training contests |
| --- | ---: | ---: | ---: | ---: |
| 2014 | 0.002510703 | 0.009387611 | 1.366428 | 63 |
| 2017 | 0.002550797 | 0.008265885 | 1.242950 | 83 |
| 2020 | 0.004083888 | 0.009438014 | 1.110573 | 147 |
| 2023 | 0.003607766 | 0.008430881 | 1.204804 | 181 |

Each included parameter is refitted jointly from scratch on the declared earlier IDs; reduced baseline fits do not zero an S-model coefficient. Means are training-only and equal-contest / within-slate 1/n weighted. No V requirement is imposed; unused legacy V slots are explicitly null/zero-mean and never a V measurement or term.

Printed S is a rounded working approximation. Complete exact source-row witnesses preserve the coupled 100% constraints for selected-lower/upper scenarios; each sensitivity recomputes means/refits. They are measurement scenarios, not future uncertainty intervals. Gain differences across these scenarios are under 0.000001 pp here; this does not bound all possible rounded-table combinations. Each fold’s exact rounding gains and all five largest paired changes are retained.

Primary leave-one-contest-out score-gain ranges are −0.082…0.134 (2014), 0.207…0.289 (2017), 0.961…1.093 (2020), 0.769…0.898 (2023), in pp. These omit one evaluation score, not one training observation/refit. No influential seat is removed from primary scores.

## Separate NAT/LAB response comparison

Outcome C uses valid-candidate votes; P uses valid-party votes. Registered models predict C1=C0+α+β(P1−P0)+γW, where W is observed **source** party-seat victory, not target incumbency, verified same person, turnover or causal effect. Separate party OLS and every fixed-β nuisance model are refitted on identical training records. Predictions are never clipped or normalized into a whole slate.

Primary equal-party-seat-record MAE, pp:

| Target | Party | β=0 | β=1 | Stage6 zero intercept | Common intercept | Source victory |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2011 | labourparty | 4.564 | 6.663 | — | — | — |
| 2011 | nationalparty | 3.565 | 3.713 | — | — | — |
| 2014 | labourparty | 2.814 | 3.131 | 2.706 | 3.595 | 3.848 |
| 2014 | nationalparty | 3.343 | 3.126 | 3.255 | 3.054 | 3.053 |
| 2017 | labourparty | 4.924 | 7.873 | 3.994 | 6.404 | 6.089 |
| 2017 | nationalparty | 4.591 | 3.478 | 3.843 | 3.459 | 3.400 |
| 2020 | labourparty | 10.228 | 4.637 | 6.816 | 6.303 | 6.357 |
| 2020 | nationalparty | 10.301 | 9.391 | 2.866 | 3.062 | 3.233 |
| 2023 | labourparty | 17.144 | 7.388 | 7.180 | 9.763 | 9.952 |
| 2023 | nationalparty | 10.691 | 4.202 | 4.863 | 5.885 | 5.656 |

Large 2020/2023 movements expose instability: a single fitted response does not consistently beat both fixed-β controls, and adding source victory does not repair it. Labour’s common-intercept/source-victory models have substantial positive 2017/2023 bias and negative 2020 bias. National’s bias also reverses. These are conditional errors, not evidence of personal-vote absence.

| Primary target | Party | Source-victory α pp / β / γ pp | Gain vs common-intercept pp | Gain vs independently fitted W+β0 / W+β1 pp |
| --- | --- | ---: | ---: | ---: |
| 2014 | labourparty | 2.822 / 0.637347 / 3.585 | -0.253 | -0.108 / 0.528 |
| 2014 | nationalparty | -0.453 / 0.471919 / -0.002 | 0.000 | 0.527 / -0.254 |
| 2017 | labourparty | 2.079 / 0.567697 / 2.549 | 0.316 | -0.974 / 6.971 |
| 2017 | nationalparty | -0.732 / 0.574839 / -0.483 | 0.059 | 1.061 / 0.449 |
| 2020 | labourparty | 0.503 / 0.258124 / 1.345 | -0.054 | 2.585 / -2.044 |
| 2020 | nationalparty | 0.203 / 0.546617 / -1.743 | -0.172 | 6.070 / 6.929 |
| 2023 | labourparty | 1.193 / 0.377679 / 0.692 | -0.189 | 10.373 / -1.772 |
| 2023 | nationalparty | -0.067 / 0.482303 / -1.322 | 0.229 | 7.131 / -0.639 |

Primary source-victory versus common-intercept pooled MAE gains are **0.069 pp National / 0.007 pp Labour**, below 0.25 pp and with fold reversals. Separated gains are 0.090 / 0.160 pp; Labour still reverses. Both source-victory screens fail. Worst primary RMSE deterioration is 0.061 / 0.354 pp; separated worst is −0.0003 / 0.489 pp. The nine registered restrictions, their RMSE/bias, source-victory strata, out-of-range counts, paired controls and original-only/expanded training differences are all saved. No response prediction leaves [0,1] in these results, but the implementation/test preserves that possibility without clipping.

## Preservation, reproducibility and independent checks

New companions are in `data/processed/models/exact-geography-retests/`: frozen inventory/folds/coverage, original-byte pre-fit manifest, required input/source contracts, prior-data snapshot, separate construction/cache, evaluation-only actuals/results, and independent verification/manifests. The metadata pin added later names unchanged bytes from pre-fit commit `3b03120`; it is not a post-result sample/design change. A reporting correction keeps the parameter-free zero-floor benchmark visible in 2011 even though fitted models abstain. It changes no fit/prediction/sample.

All 1,362 earlier tracked data artifacts are byte-identical to merged Stage26; global sources/older adjudications/operational selections remain protected. 854 consumed official records/raw bytes are verified through the Stage25 source contract; unrelated registry additions remain allowed, altered/deleted/ambiguous required records and changed raw bytes fail. Frozen Stage25 IDs/geography are protected; Stage26 links are audit-only and never model inputs.

Original-only refits reproduce saved Stage16/22 under matching contracts: 104 checks, direct saved-parameter candidate reproduction≤1e−12, refit predictions within the pre-fit declared tolerance. 20 distinct candidate training problems were also fully refitted again; outputs were unchanged. Normal deterministic construction checks reuse only SHA-keyed identical training tensors after objective/gradient checks, with a pinned output checksum. `--refit` independently regenerates every numerical fit. 314 further independent checks use direct slate arithmetic, direct joint optimization and NumPy least squares, verifying fitted means/parameters and all saved fold errors.

### Numerical serialization amendment

After construction/evaluation, the established Stage24 50-digit Decimal evaluator was adopted for platform-stable serialization of the **same** intensity equation. `portability-contract.json` pins that helper and the original `ae826f4` prediction hash. Maximum candidate-share change is `2.22e−16`; fits, IDs, means, response predictions, weighting and conclusions are unchanged. Direct saved-parameter and refit reproduction remain within their original tolerances. Independent checks retain enforced objective/parameter/share tolerance decisions and six-decimal displayed pp metrics rather than platform-dependent optimizer tail digits. Raw historical scores and parameters are not rounded. The first CI runs (`37105489219`, `37105527611`) passed construction and the full suite, then failed exact evaluation reproduction. Local verification finds 39 errors with differing `pow(x,2)` versus multiplication tails. A second computational amendment evaluates the identical squared-error equations by `x*x`, as Stage24 does, without editing inherited Stage22 code or changing tolerances. Only 66 saved numeric fields change (maximum 1.14e−13); IDs, fits, predictions and development screens are unchanged. Exact reproduction remains mandatory; structural-difference diagnostics make any further failure inspectable. This is an explicit computational amendment, not the original pre-fit numerical implementation or a statistical redesign.

Commands (repository `.venv` / pinned requirements):

```sh
python -m scripts.models.exact_geography_retests.inventory --check
python -m scripts.models.exact_geography_retests.construction --check
python -m scripts.models.exact_geography_retests.construction --check --refit
python -m scripts.models.exact_geography_retests.evaluation --check
python -m scripts.validate.stage27_independent --check
python -m unittest scripts.tests.test_stage27_retests -v
python -m unittest discover -s scripts/tests -v
python scripts/validate/source_files.py
```

Focused tests exercise real adapters/runners with held-out outcomes/winner/identity mutations, legitimate source-victory and earlier training outcomes, chronology, preprocessing, mapping, conservation, missing inputs, rank/failure, rounding, ties/metrics, provenance and earliest parameter-free controls. No Python formatter/linter is configured; compilation and whitespace checks are used. Final local/CI counts and PR are recorded in PROJECT_STATE.md. No frontend changes; GitHub also runs its frontend checks.

## Decision and exact next action

Keep baseline/S as frozen conditional research comparators. Expanded evidence supports a consistent directional S share association, but weak 2014 materiality, chronology-sensitive 2017 threshold and worse 2023 winners prevent a stronger claim. Source-victory conditioning still offers no stable material response improvement; do not automatically investigate new variants. **All operational selections remain null/unresolved; null is not an estimated zero effect.**

After independent PR review, the recommended next separately authorized task is the Stage25 roadmap’s bounded **earlier-election preserved-input feasibility inventory** for the existing response/baseline/S questions: identify exact geography, complete ballot-group/candidature/denominator and source-split support before expanding experiments. No new fitting or open-ended search. A later one-horizon dated-input replay and complete-party/reconciliation/uncertainty designs are distinct. Stage23 input substitution was not run here.

Persistence may subsequently use Stage26 broad/strict views only under a separately frozen estimand/selection/chronology contract. Freshman still requires career completeness; replacement requires independently supported distinct-person claims. The interior-middle-name recall limitation and 1,064 exception queue remain deferred. Stop before acquisition, identity-dependent fitting, new response forms, integration or forecasts.
