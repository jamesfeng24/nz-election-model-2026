# Stage39 — bounded national-to-candidate integration

2026-10-05. Frozen contract a8cf66a and prediction seal5b864f2 precede scoring. No new national/candidate fits, owned replay, R-only replay, acquisition, calibrated electorate probabilities or live forecast. External gauss is provisional national engine; S+R preferred development candidate, S active alternative/baseline control. Historical numerical findings/screens/operational nulls remain unchanged (D073).

## Coverage and construction

Three cached 56-day cases: 2017/2020/2023; 64/34/64 held exact-general contests, 431/286/459 candidates (162/1176). All six election/policy cases construct on identical complete slates with zero abstentions. Māori coverage-only, nonexact, cancelled and outside-scope cases remain in the linked wider 356-record ledger; no 2014/14-day forecast is manufactured. Source S coverage 285/159/271 and source R 116/61/108; unsupported candidates remain with neutral missing-feature exponents. All R-supported candidates also have S, without implying interchangeable information. The wider ledger retains35 Māori coverage-only and75 nonexact records plus84 outside-case exclusions (including cancelled Port Waikato); its original contestStatus remains explicit.

Raw joint election-target draws and chain IDs are shared across every seat/model/policy. The Sunday-start election-week approximation is preserved; last-data support is distinct and never scored as election-day forecast. No per-seat redraw, second national error, outgoing residual transfer or candidate-only party renormalization. Complete local vectors use original affinity/entrant rules. Every matching Stage33 conditional vector reproduces, maximum gap 2.22e−16 (gate 1e−12). Decimal 50 fixed exponent factors implement the same intensity equation efficiently and portably; no tolerance/statistical change. Joint log-intensity coefficients are not personal-vote retention percentages or causal decompositions.

## Expected-share accuracy

MAE is contest-equal valid-candidate-share absolute error in pp. RMSE is the square root after pooling within-contest candidate squared errors. All 162 contests receive equal pooled weight (64/34/64 by election); this does not give a 20- or 34-seat sample the weight of a 64-seat election. Candidate-equal sensitivities and every paired contest error are saved in evaluation.json. Full-slate signed bias cancels as an accounting check.

| Policy / election | Contests | Baseline MAE / RMSE | S MAE / RMSE | S+R MAE / RMSE | Joint improvement over S |
|---|---:|---:|---:|---:|---:|
| recent_report_prior / 2017 | 64 | 4.1683 / 7.0684 | 3.6451 / 6.1786 | 3.5405 / 5.6681 | 0.1046 |
| prior_only / 2017 | 64 | 4.2116 / 7.0819 | 3.6826 / 6.1946 | 3.5801 / 5.6884 | 0.1025 |
| recent_report_prior / 2020 | 34 | 2.5144 / 4.6885 | 1.9648 / 3.7075 | 2.0728 / 3.8632 | -0.1080 |
| prior_only / 2020 | 34 | 2.5867 / 4.7117 | 1.9974 / 3.7275 | 2.1166 / 3.8845 | -0.1191 |
| recent_report_prior / 2023 | 64 | 4.4352 / 6.7168 | 2.9988 / 4.9547 | 3.0445 / 4.9617 | -0.0456 |
| prior_only / 2023 | 64 | 4.4562 / 6.7209 | 3.0104 / 4.9597 | 3.0605 / 4.9676 | -0.0501 |
| recent_report_prior / pooled | 162 | 3.9266 / 6.4942 | 3.0371 / 5.2597 | 3.0365 / 5.0548 | 0.0006 |
| prior_only / pooled | 162 | 3.9672 / 6.5052 | 3.0634 / 5.2720 | 3.0677 / 5.0694 | -0.0043 |

Positive improvement means comparator error minus model error. Under recent-report allocation, S and joint improve pooled MAE by 0.8895/0.8902pp over baseline; joint versus S is only 0.0006pp. Prior-only reverses this tiny ordering (joint 0.0043pp worse). Joint shareMAE wins 2017, S wins 2020/2023; joint RMSE improves 2017/pooled, worsens 2020 and is nearly tied 2023. Preserve the user’s provisional S+R development preference, S active alternative and baseline control; small scores do not trigger another tuning/model-selection cycle.

## Matching conditional context — combined input and averaging change

Saved Stage33 primary predictions used complete local affinity vectors conditional on observed national support. The same coefficients, source features, slates and exact IDs are used here. This context does not substitute observed-local retrained predictions, create a four-cell experiment or causally separate national/geographic/candidate error. Negative change means replay error is lower; a lower error can include cancellation and is not isolated evidence for the candidate feature.

| Election (recent policy) | Baseline conditional→replay MAE | S conditional→replay MAE | Joint conditional→replay MAE |
|---|---:|---:|---:|
| 2017 | 2.5402→4.1683 | 2.6297→3.6451 | 2.6560→3.5405 |
| 2020 | 3.1131→2.5144 | 2.0007→1.9648 | 2.2484→2.0728 |
| 2023 | 3.3231→4.4352 | 2.3840→2.9988 | 2.3139→3.0445 |

2017/2023 replay MAE deteriorates versus conditional context; 2020 can improve. These are three reused development environments and selected unchanged general seats, with overlapping training transitions and retrospective slates. No as-of or representative-national-candidate validation claim.

## Category diagnostics

Recent-report policy, pooled. Each error/bias averages candidates in that group on the original valid-candidate denominator. Groups do not sum to the contest-equal primary score. National/Labour combined is an overlapping diagnostic, not extra observations. No-party-group candidates remain distinct from smaller mapped parties.

| Group | Candidates / present contests | Baseline MAE / bias | S MAE / bias | Joint MAE / bias |
|---|---:|---:|---:|---:|
| affirmative_no_party_group | 126 / 86 | 0.6273 / -0.3280 | 0.8982 / 0.0802 | 0.8104 / -0.0334 |
| labour | 162 / 162 | 7.5854 / -2.2971 | 6.4369 / -0.6573 | 6.3343 / -0.2615 |
| national | 162 / 162 | 7.0290 / -2.3032 | 5.6447 / 2.1501 | 5.6611 / 0.4876 |
| national_labour | 324 / 162 | 7.3072 / -2.3001 | 6.0408 / 0.7464 | 5.9977 / 0.1130 |
| other_mapped | 726 / 162 | 2.6634 / 1.0834 | 1.7687 / -0.3470 | 1.7641 / -0.0447 |

Joint improves Labour/other mapped shareMAE slightly versus S but National is nearly tied/slightly worse. Neither feature model beats baseline on no-group MAE; joint improves no-group MAE/bias versus S. Their support still changes through complete-slate normalization. This bounded diagnostic does not authorize a new fallback fit.

## Rankings and margins — descriptive, not calibrated probabilities

| Election (recent policy) | Baseline correct / margin MAE | S correct / margin MAE | Joint correct / margin MAE |
|---|---:|---:|---:|
| 2017 | 46/64 / 16.4829 | 54/64 / 17.5819 | 61/64 / 15.6276 |
| 2020 | 25/34 / 14.0307 | 28/34 / 10.3645 | 29/34 / 11.4935 |
| 2023 | 56/64 / 12.7887 | 55/64 / 9.5292 | 56/64 / 9.4105 |
| pooled | 127/162 / 14.5088 | 137/162 / 12.8858 | 146/162 / 12.3038 |

All predictions have unique winners (existing 1e−12 tie tolerance; no outcome-based tie breaking). Joint correct counts 61/29/56 versus S54/28/55; pooled 146 versus 137, baseline 127. These rank counts are not a veto on better shares and not draw winner probabilities. Margin MAE uses predicted share difference between observed winner/runner-up minus their observed difference; actual ties retain every runner as in Stage33. Predicted top-two-gap error is separately saved.

### Fixed-fit contest influence

| Election (recent policy) | Joint−S gain | Leave-one-contest-out gain range | Most influential retained contests |
|---|---:|---:|---|
| 2017 | 0.1046 | 0.0141 to 0.1692 | nz-general-2017-electorate-12:5.8030; nz-general-2017-electorate-41:4.4485; nz-general-2017-electorate-36:-3.9640; nz-general-2017-electorate-39:2.4582; nz-general-2017-electorate-03:-2.3383 |
| 2020 | -0.1080 | -0.2180 to -0.0214 | nz-general-2020-electorate-11:3.5229; nz-general-2020-electorate-24:-2.9650; nz-general-2020-electorate-26:-1.9845; nz-general-2020-electorate-50:-1.0881; nz-general-2020-electorate-60:-0.9109 |
| 2023 | -0.0456 | -0.0769 to -0.0115 | nz-general-2023-electorate-48:-2.1998; nz-general-2023-electorate-11:1.9212; nz-general-2023-electorate-05:-1.5176; nz-general-2023-electorate-57:1.4254; nz-general-2023-electorate-25:-1.2230 |

All contests remain in primary scores. These are fixed-prediction score influences, not leave-one-election-out forecasts or refitted ablations.

## Allocation sensitivity and nonlinear expectations

Raw gauss schemas are preserved: 2017 explicit Conservative/United Future, 2020 MRI/TOP inside Other, 2023 explicit MRI/TOP. Existing category continuity maps 2017“New Conservative” to conservative; 2023 MRI to ballot key tepatimaori. Explicit shares are unchanged; only Other is allocated. Whole alliances and parties without candidates remain represented. For 2020 MRI, recent reports use the same Stage37 cutoff/weight arithmetic on already-preserved MRI observations; prior-only retains earlier support. Unknown support is not zero and target final shares do not select weights.

| Election / policy | Other allocated pp | Recent-report mass pp | Prior mass pp | Neutral-seed mass pp |
|---|---:|---:|---:|---:|
| 2017 / recent_report_prior | 2.2636 | 1.3541 | 0.6472 | 0.2623 |
| 2017 / prior_only | 2.2636 | 0.0000 | 1.3509 | 0.9126 |
| 2020 / recent_report_prior | 3.5012 | 2.4704 | 0.4155 | 0.6153 |
| 2020 / prior_only | 3.5012 | 0.0000 | 3.0695 | 0.4316 |
| 2023 / recent_report_prior | 2.9935 | 0.9693 | 1.0423 | 0.9818 |
| 2023 / prior_only | 2.9935 | 0.0000 | 2.2758 | 0.7178 |

Prior/reported weights inform a conditional scenario, not observed true support or a fine-party posterior. Both scenarios conserve all Other; no unresolved mass is dropped. Some minor polling evidence also informed national inference and is not independent corroboration.

| Election | Primary→prior national fine-vector TV pp | Māori-party national share, primary / prior pp | Maximum expected-candidate allocation difference pp |
|---|---:|---:|---:|
| 2017 | 0.9890 | 1.1995 / 1.1995 | 2.3403 |
| 2020 | 1.1020 | 0.7784 / 0.8487 | 2.1706 |
| 2023 | 0.5444 | 3.3840 / 3.3840 | 0.8716 |

MRI column is a scenario allocation, including 2020 conditional Other support, not an observed Māori electorate quantity. No national reconciliation is imposed over selected exact seats.

Expected shares average all 8,000 transformed candidate vectors. The shortcut using only mean national inputs differs by up to4.3906pp for a candidate in 2020 joint (1.5385pp in 2023 joint,0.2718pp in 2017 joint). This is why the nonlinear draw propagation is required; it does not identify an additional causal effect.

## What uncertainty is represented

Saved per-candidate 50%/90% quantiles are **national-input-only conditional intervals**. They propagate national common polling error/future movement through deterministic local affinity, conditionalOther policy and fixed candidate fits. They omit local-party forecast error, candidate residual error, fitted parameter uncertainty, changed-boundary transport and stochastic fine-category allocation. The two policies are not a probability distribution. No calibrated electorate win probability or interval-calibration claim follows, and misses do not authorize inflating national uncertainty.

Inferred publication dates, retrospective rosters/source-feature availability, retrospective gauss error-scale development and only three dependent election environments remain. Full share conservation establishes correctness, not completeness of uncertainty. Fixed-fit replay does not select political mechanisms or erase component evidence.

## Validation and practical next step

Independent checks are recorded in independent-verification.json: {'contestMetricChecks': 1944, 'expectedCandidateShares': 324, 'foldAndPooledMetricChecks': 120, 'nationalVectors': 48000, 'pairedComparisonChecks': 42, 'representativeDrawCandidateVectors': 288000}. Actual-path outcome/cutoff mutations, synthetic entrant/zeroOther/sharedgroup/no-group/extreme-vector stress, fixed fits/means, batching and cache/provenance checks pass. All 1,671 prior datafiles are byte-identical; no earlier identity/geography/model/operational output is rewritten. Deterministic regeneration uses cached external forecasts and never MCMC. Candidate draw transforms are saved in a local 458 MiB runtime cache with committed checksums; CI recreates them from committed fine national archives, fixed fits and features. Source checks/configured tests/finalCI are reported separately at handoff; no Python formatter/linter is configured.

**Next separately authorized bounded implementation:** build 2026 target-boundary/candidate-slate readiness records, using the preserved 2023→2026 geography contracts and a finite dated nomination/source plan. Deliver every target seat with explicit known/unknown slate status, original affiliation/ballot-group mapping, source-feature eligibility and neutral-history fallbacks. Population/party reconstruction does not reconstruct candidate votes, so unsupported residual transport must remain unavailable. Do not produce a live forecast in that readiness task. Then implement the coherent joint local/candidate uncertainty design and separately planned Māori polls/unpolled baseline, before reconciliation/denominators and MMP/publication. See stage39-forecast-roadmap.md.

National TPM party support is not Māori electorate candidate support. Future candidate/localparty/both poll routes must preserve question, denominator, fieldwork/publication,n, poll age/noise and dependence. Use an explicit Māori-seat baseline and wider documented unpolled fallback without double-counting national/local information. No such acquisition or implementation occurred here.

Stop after the bounded replay/review. Small score differences are not authorization for new national comparison, candidate tuning, learned blend, fallback estimation, live output or operational adoption.
