# Stage44 local-party and candidate uncertainty findings

2026-10-05. One frozen pooled log-ratio family, no mean refitting, source acquisition or MCMC. External gauss provisional; continuous S+R mean preferred, S active and baseline mandatory. No operational selection.

## Evidence and chronology

321 general local-party vectors (2011/14/17/20/23:63/64/64/65/65);257 candidate residual vectors (2014/17/20/23:64/64/65/64),1902 candidates. Wider356 records retain35 Māori coverage-only cases and cancellation. Valid2023 Port Waikato party votes remain; its cancelled candidate ballot is absent.2011 has no fitted candidate residual.

Party residuals condition on observed national support; candidate residuals condition on observed local party support. Thus polling misses do not estimate local scales and ordinary party-input errors do not estimate candidate scales.2014/2020 candidate means consistently use continuous transport,2017/2023 exact means reproduce Stage33 fixed-to-observed predictions. Original vote denominators, slate/category IDs, source features, supported mass, broad evidence tiers, training IDs and means are pinned in the inventory.

2011 party and2014 candidate use fixed assumption-based priors; later folds use only completed earlier target years. One to four election environments and three prior pseudo-environments imply strong pooling, not calibrated variance. Full-panel moments are separately descriptive and never enter earlier forecasts. No current2026 partial slate is normalized. Geography band `fallback` means below90/uncertain dominance in the old classification; the candidate mean still uses continuous weighting.

## Representation and dependence

CLR residuals use fixed1e-6 share resolution replacement for observations/predictions only. Noise is projected shared coarse-class plus isotropic seat noise, followed by softmax. Zero frozen means stay on the zero face. Shared Gaussian effects are common across seats within an election; national cached draw IDs remain shared once. No unrestricted covariance, coefficient jitter, scale-parameter draws or probability over flow vertices/Other scenarios.

Class scales are pooled equally by earlier election; seat replication is not election replication. Cross-layer independence is an explicit approximation, not established by conditional residual definitions. National/Labour within-election-centered CLR correlations are 0.0727/0.0634 on257 matching seats/four environments. Fine minor parties share the other class. Parameter/scale-estimation uncertainty is omitted; past predictive residuals contain some earlier fixed-fit estimation error.

### Earlier-only fitted/assumed log-unit scales

| Year | Seats | Exact seats | Candidates | S supported | R supported | Mean R mass | R evidence tiers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2014 | 64 | 20 | 451 | 330 | 146 | 0.2883 | accepted_algorithmic_same_person |
| 2017 | 64 | 64 | 431 | 285 | 116 | 0.2691 | accepted_algorithmic_same_person |
| 2020 | 65 | 34 | 561 | 318 | 113 | 0.1848 | accepted_algorithmic_same_person |
| 2023 | 64 | 64 | 459 | 271 | 108 | 0.2353 | accepted_algorithmic_same_person |

Supported mass is source coverage, not identity confidence or known strength. Missing contributions stay neutral; every standing candidate remains. Candidate historical means/identity tiers are not re-estimated by this uncertainty layer. All general simulation cases construct successfully; Māori and2011 no-candidate-fit remain explicit scope exclusions.

| Layer | Target | Earlier targets | Environments | Shared SD | Seat SD | Status |
| --- | --- | --- | --- | --- | --- | --- |
| candidate | 2014 | none | 0 | 0.20000 | 0.50000 | assumed_prior_no_earlier_residuals |
| candidate | 2017 | 2014 | 1 | 0.31150 | 0.50174 | strongly_pooled_earlier_moments |
| candidate | 2020 | 2014,2017 | 2 | 0.33126 | 0.51185 | strongly_pooled_earlier_moments |
| candidate | 2023 | 2014,2017,2020 | 3 | 0.36348 | 0.50783 | strongly_pooled_earlier_moments |
| local_party | 2011 | none | 0 | 0.15000 | 0.35000 | assumed_prior_no_earlier_residuals |
| local_party | 2014 | 2011 | 1 | 0.13279 | 0.40891 | strongly_pooled_earlier_moments |
| local_party | 2017 | 2011,2014 | 2 | 0.12903 | 0.47232 | strongly_pooled_earlier_moments |
| local_party | 2020 | 2011,2014,2017 | 3 | 0.12478 | 0.49766 | strongly_pooled_earlier_moments |
| local_party | 2023 | 2011,2014,2017,2020 | 4 | 0.13076 | 0.52487 | strongly_pooled_earlier_moments |

## Component and bounded composed scores

Units pp. MAE and RMSE give each complete contest equal total weight; CRPS, widths and interval scores average categories/candidates within contest then contests. Energy uses complete-vector Euclidean pp norm/first128 joint draws. Coverage below reports raw covered/coordinate counts; categories within seats and seats within elections are correlated. The mean point vector itself is a degenerate CRPS reference, not another fitted model.

| Case | Seats | Coordinates | MAE | RMSE | CRPS | Energy | 50% covered | 90% covered | 90% width | 90% score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local_party:2011 | 63 | 819 | 0.6242 | 1.3947 | 0.6644 | 4.4384 | 519/819 | 729/819 | 7.030 | 7.456 |
| local_party:2014 | 64 | 960 | 0.4304 | 0.8971 | 0.5868 | 4.5321 | 640/960 | 833/960 | 6.965 | 7.177 |
| local_party:2017 | 64 | 1024 | 0.5182 | 1.2808 | 0.6284 | 5.6495 | 695/1024 | 921/1024 | 7.003 | 7.109 |
| local_party:2020 | 65 | 1105 | 0.5840 | 1.3132 | 0.6539 | 5.7456 | 719/1105 | 960/1105 | 7.204 | 7.386 |
| local_party:2023 | 65 | 1105 | 0.5511 | 1.0943 | 0.7060 | 5.8410 | 787/1105 | 1034/1105 | 8.107 | 8.272 |
| candidate:2014 | 64 | 451 | 2.7173 | 4.8469 | 2.2173 | 8.6842 | 269/451 | 406/451 | 16.633 | 19.581 |
| candidate:2017 | 64 | 431 | 2.3695 | 4.2944 | 2.3033 | 8.4978 | 261/431 | 389/431 | 19.336 | 22.581 |
| candidate:2020 | 65 | 561 | 2.1324 | 3.6215 | 1.7756 | 8.3150 | 372/561 | 528/561 | 16.346 | 17.232 |
| candidate:2023 | 64 | 459 | 2.2466 | 4.5736 | 2.2990 | 8.1282 | 336/459 | 431/459 | 20.397 | 24.957 |
| composed:2017 | 64 | 431 | 3.5121 | 5.5792 | 2.8918 | 10.6467 | 254/431 | 387/431 | 23.732 | 25.089 |
| composed:2020 | 65 | 561 | 2.0007 | 3.7235 | 2.1402 | 9.8122 | 338/561 | 526/561 | 19.179 | 20.642 |
| composed:2023 | 64 | 459 | 3.0385 | 4.8972 | 2.9105 | 10.4110 | 289/459 | 411/459 | 26.664 | 29.840 |

Local all-category point MAE0.43–0.62pp conceals National/Labour point errors about1.4–2.8pp and unusually wide90% intervals27–44pp. Both majors are covered in every party case. All local CRPS values exceed their degenerate-mean MAE reference: the proper score penalizes dispersion despite superficially near90% pooled coverage. The isotropic log-ratio residual family, heavily influenced by sparse minor-category errors, is too diffuse for these major-party shares. This is substantive evidence against claiming calibrated sharpness, not a numerical failure. Do not automatically search a new covariance family.

Candidate intervals are also broad: major-party90% widths38–56pp. Candidate CRPS improves on the degenerate mean in2014/2017/2020 but not2023. Minor-party misses remain, including unusually strong candidate overperformance. Pooled coverage alone does not establish calibrated winner probabilities.

Composition uses three preserved external56-day national forecasts and recent_report_prior fine allocation, with64/65/64 complete slates.2020 includes continuous changed-boundary seats beyond Stage39 exact34; these results are not a matching Stage39 replay. Its90% major-party intervals cover all193 National and193 Labour observations, with widths51–64pp. This suggests poor sharpness even when marginal coverage looks acceptable.2020 CRPS is worse than its mean point reference. No national uncertainty was inflated or recalibrated.

### Major-party diagnostics (candidate/category equal)

| Case | Group | Count | MAE | Bias pred−actual | CRPS | 90% covered | 90% width |
| --- | --- | --- | --- | --- | --- | --- | --- |
| local_party:2011 | national | 63 | 2.267 | -0.200 | 2.829 | 63/63 | 33.24 |
| local_party:2011 | labour | 63 | 2.371 | -0.181 | 2.413 | 63/63 | 27.49 |
| local_party:2014 | national | 64 | 1.655 | -0.628 | 2.868 | 64/64 | 37.09 |
| local_party:2014 | labour | 64 | 1.396 | +0.138 | 2.263 | 64/64 | 28.63 |
| local_party:2017 | national | 64 | 2.819 | +0.557 | 3.638 | 64/64 | 42.34 |
| local_party:2017 | labour | 64 | 2.816 | -0.657 | 3.533 | 64/64 | 39.02 |
| local_party:2020 | national | 65 | 1.538 | +0.655 | 2.816 | 65/65 | 36.41 |
| local_party:2020 | labour | 65 | 2.288 | -1.229 | 3.569 | 65/65 | 43.93 |
| local_party:2023 | national | 65 | 2.184 | -0.322 | 3.482 | 65/65 | 42.98 |
| local_party:2023 | labour | 65 | 2.211 | +1.109 | 2.890 | 65/65 | 37.30 |
| candidate:2014 | national | 64 | 6.497 | +6.081 | 5.387 | 63/64 | 44.29 |
| candidate:2014 | labour | 64 | 5.709 | -4.852 | 4.677 | 64/64 | 38.18 |
| candidate:2017 | national | 64 | 5.051 | +1.629 | 5.155 | 63/64 | 49.33 |
| candidate:2017 | labour | 64 | 4.097 | +1.622 | 4.569 | 64/64 | 48.59 |
| candidate:2020 | national | 65 | 6.384 | -6.068 | 5.327 | 65/65 | 44.13 |
| candidate:2020 | labour | 65 | 4.073 | +2.858 | 4.644 | 65/65 | 50.86 |
| candidate:2023 | national | 64 | 4.011 | +2.759 | 4.959 | 63/64 | 52.37 |
| candidate:2023 | labour | 64 | 3.539 | -1.618 | 4.266 | 64/64 | 44.57 |
| composed:2017 | national | 64 | 7.140 | +5.744 | 6.468 | 64/64 | 58.19 |
| composed:2017 | labour | 64 | 7.946 | -7.595 | 6.778 | 64/64 | 50.97 |
| composed:2020 | national | 65 | 4.411 | -3.179 | 5.808 | 65/65 | 58.68 |
| composed:2020 | labour | 65 | 5.995 | +5.686 | 6.480 | 65/65 | 63.94 |
| composed:2023 | national | 64 | 4.622 | -2.776 | 6.066 | 64/64 | 64.08 |
| composed:2023 | labour | 64 | 4.615 | +3.309 | 5.362 | 64/64 | 60.92 |

Other mapped/no-party-group counts, biases and scores, coordinate-equal sensitivities, exact/transport provenance, full-slate accounting bias and the five largest interval misses in every case are preserved in evaluation.json. Group averages do not sum to complete-slate contest metrics.

### Pooled summaries

| Layer | Seats | Contest MAE | Contest CRPS | Equal-election MAE | Equal-election CRPS |
| --- | --- | --- | --- | --- | --- |
| candidate | 257 | 2.3655 | 2.1474 | 2.3664 | 2.1488 |
| composed | 193 | 2.8460 | 2.6448 | 2.8504 | 2.6475 |
| local_party | 321 | 0.5415 | 0.6481 | 0.5416 | 0.6479 |

## Expected shares, stress and precision

Conditional component mean preservation agrees within1e-10 shares (1e-8pp); the offset is outcome-independent finite-bank marginal adjustment. For varying national draws it does not guarantee per-national-draw conditional means. After local uncertainty the candidate map is nonlinear; preserving candidate mean around that new conditional ensemble cannot erase its Jensen shift relative to national-only propagation.

| Election | Mean absolute nonlinear shift pp | Maximum shift pp | Candidate adjustment gap pp |
| --- | --- | --- | --- |
| 2017 | 0.1860 | 1.6487 | 9.96e-09 |
| 2020 | 0.1010 | 1.3323 | 9.29e-09 |
| 2023 | 0.1964 | 2.2549 | 9.85e-09 |

There is one zero-mean/positive-outcome lock:2014 electorate23 Democrats for Social Credit,7/27338 valid party votes. Its interval cannot cover that observation while preserving frozen mean0. Nine2023 zero-vote standing candidates use the frozen finite-resolution residual policy. Neither changes mean coefficients.

The sole transport stress adds50% candidate seat variance on nonexact seats, on identical random banks; exact predictions stay unchanged. It is assumed excess variance, possibly duplicating transport variation already in ordinary pooled residuals, not an overlap-calibrated distribution.

| Case | Stress−primary CRPS pp | Stress90% coverage | Stress90% width |
| --- | --- | --- | --- |
| candidate:2014 | +0.1087 | 0.931 | 18.541 |
| candidate:2017 | +0.0000 | 0.903 | 19.336 |
| candidate:2020 | +0.0641 | 0.947 | 17.397 |
| candidate:2023 | +0.0000 | 0.939 | 20.397 |
| composed:2017 | +0.0000 | 0.898 | 23.732 |
| composed:2020 | +0.0573 | 0.943 | 19.798 |
| composed:2023 | +0.0000 | 0.895 | 26.664 |

Stress worsens proper CRPS in the affected2014/2020 cases; wider intervals are not a success criterion. No scale was selected from this comparison.

Frozen1024draw first/last-seat precision audit:24 records; maximum mean CRPS change 0.1076pp, maximum90% width change 3.261pp; 2 coverage classifications change. Composed expected-share differences reach 0.3969pp from finite national/noise integration; component means remain locked. These are numerical-resolution warnings, not calibrated error bounds; do not publish high-precision probability claims from512 draws.

## Margins and diagnostic probabilities

| Case | Mean winners | Winner Brier | Finite log loss | Infinite count | Forecast pair CRPS | Pair90% coverage | Observed-top-two MAE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| candidate:2014 | 56/64 | 0.1910 | 0.4234 | 0 | 9.571 | 1.000 | 12.726 |
| candidate:2017 | 61/64 | 0.1356 | 0.2723 | 0 | 9.135 | 0.984 | 8.419 |
| candidate:2020 | 55/65 | 0.2510 | 0.4190 | 0 | 9.000 | 1.000 | 9.914 |
| candidate:2023 | 57/64 | 0.2126 | 0.4306 | 0 | 8.581 | 1.000 | 8.166 |
| composed:2017 | 61/64 | 0.1576 | 0.3037 | 0 | 12.150 | 1.000 | 15.470 |
| composed:2020 | 56/65 | 0.2589 | 0.4490 | 0 | 11.922 | 1.000 | 10.464 |
| composed:2023 | 57/64 | 0.2787 | 0.5075 | 0 | 10.434 | 1.000 | 9.094 |

Competitive pairs are chosen from deterministic prediction-time means (national-only mean in composition); actual-top-two reporting is separately retrospective. Draw ties share probability equally, with frozen1e-12 tolerance. Probabilities, Brier and log loss are diagnostics, not calibrated electorate win odds. No general coefficients or uncertainty are applied to Māori seats.

## Readiness, limits and next decision

**Retain the coherent simulation interface for development; do not claim production-calibrated local probabilities.** The single family is numerically sound but major-party intervals are excessively broad, point means can move through nonlinear composition, and sparse minor-category residuals affect scale pooling. No new uncertainty tournament or mean search follows automatically. A separately scoped residual-scale adequacy decision is needed before presenting probabilities; this stage records the defect rather than concealing it with national variance.

Remaining deployment blockers: complete dated official nominations; separate Māori-seat baseline and candidate/local-party electorate polls with question/denominator/dates/sample/dependence and unpolled/stale fallback; justified all-population turnout/valid-party reconciliation; fine-party allocation remains scenarios; unidentified fragment political composition; omitted explicit parameter/scale uncertainty and independent-layer approximation; finite simulation precision. National reconciliation is not imposed by this layer. A later weighted all-seat reconciliation operator must preserve shared dependence before candidate mapping and requires its own contract.

Concrete next bounded forecast-building task: official nomination refresh after bulk publication plus the separately authorized Māori baseline/poll interface. This uncertainty implementation remains a versioned development scenario pending an explicit calibration/sharpness decision; do not fit alternatives now. External gauss/S+R mean preferences, S alternative/baseline control and all historical operational nulls remain unchanged.

## Reproduction and validation

Run `.venv/bin/python -m scripts.uncertainty.NAME --check` for inventory, estimation, construction, evaluation, precision, verification, report and manifest, in that order. Case caches under `.cache/stage44/<exact-signature>/` resume construction; check mode reconstructs and verifies. No MCMC. Score generation consumes sealed draws only. Dependencies reuse pinned numpy2.2.6/scipy1.16.0; no new environment/backend.

Independent scalar CLR/QR moment calculations, manual draw expectations and all-pair proper-score arithmetic are recorded in independent-verification.json. Focused tests exercise actual adapter counterfactuals, chronology, source-only R, no outgoing transfer, streams/conservation/mean treatment, cache signatures/checksums and scores. Full configured/local and final-head CI results are recorded in PROJECT_STATE and the PR handoff. Consumed-source hashes are separate from all-prior preservation checks; unrelated registry additions do not change model signatures. No political acquisition, old-artifact changes or operational selections.
