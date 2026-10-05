# Stage45 residual-scale correction findings

2026-10-05. One post-Stage44 development correction, frozen at ed300e4 before revised scoring. Original Stage44 artifacts, mean coefficients, continuous transport, identities and operational nulls remain unchanged. No acquisition or MCMC.

## Verified cause and single correction

Nonmajor options account for97.05–98.43% of local squared CLR residual magnitude; coordinate count alone is not proof. Per-option heterogeneity and the direct N/L contrast verify the allocation issue: local N/L residual RMS0.1102–0.1928 versus Stage44 implied2023SD0.7650. Candidate N/L RMS0.2734–0.4036 versus old implied0.7616–0.8832. The old equations are correctly implemented. This is a statistical family limitation, not a numerical bug.

The arithmetic tree separates raw N/L log odds, combined-major/remainder log odds and projected within-remainder intensities. Scalar balances use their own earlier-election shared/seat moments; within remainder retains all minor/independent errors with two pooled exchangeable scales. Small-category splitting cannot inflate major covariance. One-major/no-major/absent remainder mappings are explicit. Fixed1e-6 resolution replacement and frozen-zero locks remain; the consumed candidate inventory has no zero actuals, correcting loose earlier wording about nine zero-vote source occurrences.

321party vectors and257candidate slates/1902candidates remain. Chronological uncertainty uses earlier residual years only:2011party/2014candidate are assumed priors; later estimates use1–4earlier environments. Three prior pseudo-environments strongly pool every direction. No independent coefficient/scale draws. Shared local/candidate effects are retained, national error shared once, cross-layer independence remains assumed. General coefficients/errors are not applied to Māori seats.

## Identical-case proper-score comparison

All values pp. Lower CRPS is better. Point is the identical frozen conditional mean, or the8000-national-draw transformed national-only mean, as a degenerate distribution. The Stage44 column is a separate unchanged-equation/scale8000-draw companion, not an overwrite of its original512-draw outputs. Contest-equal weighting and identical IDs apply.

| Case | Seats | Coordinates | Point CRPS | Stage44 CRPS | Revised CRPS | Revised energy128 | Revised MAE | Revised RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| local_party:2011 | 63 | 819 | 0.624 | 0.670 | 0.531 | 3.306 | 0.624 | 1.395 |
| local_party:2014 | 64 | 960 | 0.430 | 0.588 | 0.398 | 2.745 | 0.430 | 0.897 |
| local_party:2017 | 64 | 1024 | 0.518 | 0.627 | 0.413 | 3.373 | 0.518 | 1.281 |
| local_party:2020 | 65 | 1105 | 0.584 | 0.657 | 0.440 | 3.534 | 0.584 | 1.313 |
| local_party:2023 | 65 | 1105 | 0.551 | 0.706 | 0.486 | 3.548 | 0.551 | 1.094 |
| candidate:2014 | 64 | 451 | 2.717 | 2.211 | 2.003 | 7.830 | 2.717 | 4.846 |
| candidate:2017 | 64 | 431 | 2.369 | 2.284 | 1.835 | 6.761 | 2.370 | 4.295 |
| candidate:2020 | 65 | 561 | 2.132 | 1.766 | 1.473 | 6.669 | 2.133 | 3.622 |
| candidate:2023 | 64 | 459 | 2.247 | 2.294 | 1.832 | 6.366 | 2.247 | 4.573 |
| composed:2017 | 64 | 431 | 3.540 | 2.886 | 2.512 | 9.064 | 3.544 | 5.673 |
| composed:2020 | 65 | 561 | 1.952 | 2.113 | 1.595 | 6.981 | 1.952 | 3.668 |
| composed:2023 | 64 | 459 | 3.044 | 2.889 | 2.302 | 7.992 | 3.043 | 4.959 |

Revised CRPS improves over both old uncertainty and point references in all12cases. This is useful development evidence, not calibrated deployment. Local and candidate expected-share MAE remains essentially unchanged; the correction improves uncertainty allocation rather than fitting a better mean.

## Coverage and proper interval scores

Coordinate counts are correlated, not independent calibration observations. Full comparison records, both coverage levels, group signed bias/MAE/RMSE, proper scores, energy and substantive misses are in evaluation.json. Width/score summaries average within complete contest then contests.

| Case | 50% covered | 50% width | 50% score | 90% covered | 90% width | 90% score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| local_party:2011 | 544/819 | 1.741 | 2.468 | 756/819 | 4.318 | 5.189 |
| local_party:2014 | 654/960 | 1.622 | 1.899 | 887/960 | 4.000 | 4.235 |
| local_party:2017 | 654/1024 | 1.226 | 1.921 | 936/1024 | 3.017 | 3.593 |
| local_party:2020 | 697/1105 | 1.420 | 2.000 | 989/1105 | 3.528 | 3.834 |
| local_party:2023 | 754/1105 | 1.738 | 2.244 | 1052/1105 | 4.308 | 4.512 |
| candidate:2014 | 257/451 | 4.528 | 8.967 | 418/451 | 11.264 | 16.052 |
| candidate:2017 | 255/431 | 4.647 | 8.173 | 404/431 | 11.467 | 16.365 |
| candidate:2020 | 358/561 | 4.127 | 6.552 | 532/561 | 10.349 | 12.045 |
| candidate:2023 | 322/459 | 5.036 | 8.166 | 438/459 | 12.543 | 19.127 |
| composed:2017 | 233/431 | 5.681 | 11.373 | 396/431 | 14.053 | 17.859 |
| composed:2020 | 345/561 | 4.890 | 7.187 | 531/561 | 12.161 | 14.012 |
| composed:2023 | 272/459 | 6.638 | 10.146 | 426/459 | 16.518 | 21.738 |

### Major and remainder diagnostics

Group errors give each selected coordinate equal weight; their averages do not sum to the whole-slate score. Major widths shrink substantially: local about9.5–12.5pp instead of28–44; candidate21–25pp instead of38–51; composed26–35pp instead of51–64. Narrowness alone is not success; CRPS and interval scores improve materially too. Some major misses now appear, including composed2017Labour53/64 andNational56/64 at90%. Pooled50% coverage remains high in many cases; calibration is not established.

| Case | Group | Count | Revised CRPS | Stage44 CRPS | Point CRPS | Revised90% covered | Revised90% width |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| local_party:2011 | labour | 63 | 1.746 | 2.443 | 2.371 | 59/63 | 10.379 |
| local_party:2011 | national | 63 | 1.777 | 2.860 | 2.267 | 58/63 | 12.543 |
| local_party:2011 | other | 693 | 0.307 | 0.310 | 0.316 | 639/693 | 3.019 |
| local_party:2014 | labour | 64 | 1.107 | 2.247 | 1.396 | 62/64 | 9.504 |
| local_party:2014 | national | 64 | 1.317 | 2.881 | 1.655 | 63/64 | 12.279 |
| local_party:2014 | other | 832 | 0.272 | 0.284 | 0.262 | 762/832 | 2.940 |
| local_party:2017 | labour | 64 | 2.066 | 3.539 | 2.816 | 56/64 | 10.621 |
| local_party:2017 | national | 64 | 1.997 | 3.629 | 2.819 | 59/64 | 11.227 |
| local_party:2017 | other | 896 | 0.181 | 0.205 | 0.190 | 821/896 | 1.887 |
| local_party:2020 | labour | 65 | 1.649 | 3.592 | 2.288 | 62/65 | 11.435 |
| local_party:2020 | national | 65 | 1.176 | 2.847 | 1.538 | 64/65 | 10.116 |
| local_party:2020 | other | 975 | 0.310 | 0.315 | 0.407 | 863/975 | 2.562 |
| local_party:2023 | labour | 65 | 1.513 | 2.899 | 2.211 | 59/65 | 9.700 |
| local_party:2023 | national | 65 | 1.521 | 3.501 | 2.184 | 65/65 | 10.927 |
| local_party:2023 | other | 975 | 0.348 | 0.373 | 0.332 | 928/975 | 3.508 |
| candidate:2014 | labour | 64 | 3.995 | 4.663 | 5.709 | 59/64 | 21.341 |
| candidate:2014 | national | 64 | 4.774 | 5.360 | 6.497 | 55/64 | 23.973 |
| candidate:2014 | no_group | 34 | 0.317 | 0.381 | 0.643 | 29/34 | 2.275 |
| candidate:2014 | other | 289 | 1.066 | 1.090 | 1.366 | 275/289 | 6.895 |
| candidate:2017 | labour | 64 | 3.192 | 4.493 | 4.097 | 61/64 | 24.612 |
| candidate:2017 | national | 64 | 3.810 | 5.106 | 5.051 | 62/64 | 24.738 |
| candidate:2017 | no_group | 45 | 0.715 | 0.738 | 0.948 | 38/45 | 1.796 |
| candidate:2017 | other | 258 | 1.129 | 1.173 | 1.440 | 243/258 | 5.924 |
| candidate:2020 | labour | 65 | 3.098 | 4.619 | 4.073 | 62/65 | 24.859 |
| candidate:2020 | national | 65 | 4.365 | 5.303 | 6.384 | 59/65 | 22.181 |
| candidate:2020 | no_group | 55 | 0.260 | 0.275 | 0.477 | 44/55 | 1.911 |
| candidate:2020 | other | 376 | 0.798 | 0.782 | 1.198 | 367/376 | 6.456 |
| candidate:2023 | labour | 64 | 2.807 | 4.272 | 3.539 | 61/64 | 21.496 |
| candidate:2023 | national | 64 | 3.244 | 4.892 | 4.011 | 63/64 | 23.987 |
| candidate:2023 | no_group | 50 | 0.685 | 0.702 | 0.904 | 40/50 | 1.985 |
| candidate:2023 | other | 281 | 1.194 | 1.183 | 1.461 | 274/281 | 9.256 |
| composed:2017 | labour | 64 | 5.645 | 6.772 | 7.891 | 53/64 | 25.559 |
| composed:2017 | national | 64 | 5.306 | 6.444 | 7.444 | 56/64 | 27.889 |
| composed:2017 | no_group | 45 | 0.726 | 0.756 | 0.982 | 38/45 | 1.930 |
| composed:2017 | other | 258 | 1.175 | 1.207 | 1.710 | 249/258 | 9.130 |
| composed:2020 | labour | 65 | 4.478 | 6.361 | 5.742 | 61/65 | 35.293 |
| composed:2020 | national | 65 | 3.660 | 5.747 | 4.301 | 63/65 | 31.798 |
| composed:2020 | no_group | 55 | 0.253 | 0.265 | 0.459 | 43/55 | 1.825 |
| composed:2020 | other | 376 | 0.863 | 0.892 | 1.025 | 364/376 | 5.481 |
| composed:2023 | labour | 64 | 3.533 | 5.288 | 4.831 | 63/64 | 31.752 |
| composed:2023 | national | 64 | 3.707 | 6.020 | 4.591 | 63/64 | 31.750 |
| composed:2023 | no_group | 50 | 0.685 | 0.701 | 0.905 | 42/50 | 2.029 |
| composed:2023 | other | 281 | 1.684 | 1.668 | 2.269 | 258/281 | 11.126 |

Small-option misses are retained. Other mapped candidates have slightly worse CRPS than Stage44 in candidate2020/2023 and composed2023; some minor local groups also remain worse than the point reference. No-group CRPS/coverage generally improves. All largest individual90% misses remain saved, without exclusions or adaptive scales.

### Margins and winner diagnostics

| Case | Mean winners | Brier | Zero actual-winner frequency | Forecast-pair CRPS | Pair90% coverage | Observed-top-two MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| candidate:2014 | 56/64 | 0.184 | 0 | 8.404 | 0.906 | 12.724 |
| candidate:2017 | 61/64 | 0.085 | 0 | 6.087 | 0.969 | 8.422 |
| candidate:2020 | 55/65 | 0.226 | 0 | 6.581 | 0.954 | 9.912 |
| candidate:2023 | 57/64 | 0.166 | 1 | 5.573 | 0.969 | 8.171 |
| composed:2017 | 61/64 | 0.092 | 0 | 10.390 | 0.875 | 15.645 |
| composed:2020 | 57/65 | 0.205 | 0 | 7.738 | 0.954 | 10.044 |
| composed:2023 | 57/64 | 0.194 | 0 | 6.464 | 1.000 | 9.400 |

Material probability failure: candidate:2023/Tāmaki has zero observed-winner frequency in the finite bank, hence infinite empirical winner log loss. No probability floor is inserted. This is not a claim of mathematically zero probability under the Gaussian law.

Competitive pairs are chosen from prediction-time point means; observed-top-two is retrospective evaluation only. Probabilities remain diagnostics. Two or four reused environments cannot establish calibration.

## Conditional means and common dependence

Independent GH81 checks verify aggregate conditional arithmetic expectations versus GH41 locations within6.1e-14 shares. This preserves major mass and N/L response for each national/local input in the theoretical integration. Finite simulation means can still drift; no target outcomes adjust locations. Within remainder retains an explicitly limited weighted marginal adjustment, not conditional preservation for every national draw.

| Case | Method | Mean absolute simulated shift pp | Maximum shift pp |
| --- | --- | ---: | ---: |
| local_party:2011 | revised | 0.001 | 0.010 |
| local_party:2011 | unchanged_stage44 | 0.000 | 0.000 |
| local_party:2014 | revised | 0.001 | 0.010 |
| local_party:2014 | unchanged_stage44 | 0.000 | 0.000 |
| local_party:2017 | revised | 0.000 | 0.007 |
| local_party:2017 | unchanged_stage44 | 0.000 | 0.000 |
| local_party:2020 | revised | 0.000 | 0.008 |
| local_party:2020 | unchanged_stage44 | 0.000 | 0.000 |
| local_party:2023 | revised | 0.000 | 0.008 |
| local_party:2023 | unchanged_stage44 | 0.000 | 0.000 |
| candidate:2014 | revised | 0.005 | 0.053 |
| candidate:2014 | unchanged_stage44 | 0.000 | 0.000 |
| candidate:2017 | revised | 0.004 | 0.051 |
| candidate:2017 | unchanged_stage44 | 0.000 | 0.000 |
| candidate:2020 | revised | 0.004 | 0.046 |
| candidate:2020 | unchanged_stage44 | 0.000 | 0.000 |
| candidate:2023 | revised | 0.005 | 0.041 |
| candidate:2023 | unchanged_stage44 | 0.000 | 0.000 |
| composed:2017 | revised | 0.020 | 0.777 |
| composed:2017 | unchanged_stage44 | 0.189 | 1.751 |
| composed:2020 | revised | 0.012 | 0.613 |
| composed:2020 | unchanged_stage44 | 0.104 | 1.594 |
| composed:2023 | revised | 0.022 | 1.513 |
| composed:2023 | unchanged_stage44 | 0.199 | 2.683 |

Composition shifts include nonlinear local-to-candidate propagation and finite integration. They are not a fitted bias correction. New average composed shifts are about0.012–0.022pp versus0.10–0.20pp for the old companion, but individual deviations remain.

Representative historical conditional-input audit, revised: maximum major conditional shift0.000pp; remainder1.060pp. New major expectations use independently verified quadrature; old full/revised remainder audit uses fixed scrambledSobol2048, a numerical approximation.
Representative historical conditional-input audit, unchanged_stage44: maximum major conditional shift3.076pp; remainder0.754pp. New major expectations use independently verified quadrature; old full/revised remainder audit uses fixed scrambledSobol2048, a numerical approximation.
Frozen synthetic conditional-input audit, revised: maximum major conditional shift0.000pp; remainder0.026pp. New major expectations use independently verified quadrature; old full/revised remainder audit uses fixed scrambledSobol2048, a numerical approximation.
Frozen synthetic conditional-input audit, unchanged_stage44: maximum major conditional shift2.574pp; remainder0.269pp. New major expectations use independently verified quadrature; old full/revised remainder audit uses fixed scrambledSobol2048, a numerical approximation.

The old marginal location can materially alter response at a particular national scenario; the new aggregate treatment resolves that part. Remainder conditional distortion still reaches about1.06pp on representative inputs. Shared/seat covariance contributions and cross-seat log-ratio correlations are saved in mean-audit.json; common effects have not been deleted. No additional national error, transport variance or cross-layer covariance is fitted.

## Frozen numerical cap and precision limitations

| Draws | Maximum mean change pp | Maximum CRPS change pp | Maximum90% width change pp | Gate |
| --- | ---: | ---: | ---: | --- |
| 1024 | initial | initial | initial | unmet |
| 2048 | 0.343 | 0.283 | 3.064 | unmet |
| 4096 | 0.065 | 0.190 | 1.664 | unmet |
| 8000 | 0.168 | 0.189 | 1.195 | unmet |

**8000 cap reached; frozen convergence gates remain unmet.** Do not relabel this as convergence or weaken thresholds. The largest final changes0.168pp expected shares,0.189pp coordinateCRPS and1.195pp90width constrain fine differences. These are maximum representative-coordinate differences, not pooled score error bars. Both policies use the same cap/cases. Independent energy128→256 sensitivity reaches0.656pp; complete-vector energy is materially approximate. Do not use these finite checks as confidence intervals or publish excessive probability precision.

## Decision, preservation and deployment boundary

**Carry the revised aggregate/within implementation forward for development simulations, preserving Stage44 as a control.** Its cause-based correction yields materially sharper proper scores while retaining minor errors and cross-seat dependence. No mean-model or national-engine preference changes. This is not an operational uncertainty/calibration approval: earliest priors, few repeatedly inspected elections, conditional minor distortions, numerical cap failure, zero-frequency winner miss and omitted parameter/scale uncertainty remain consequential.

Complete dated nominations, separately designed Māori baseline/electorate polls, all-population reconciliation/turnout, fine Other allocation and fragment composition, then MMP/live assembly remain separately bounded. No new family search, acquisition, nomination refresh or inference starts automatically.

## Reproduction and validation

Run diagnosis, priors, estimation, construction, evaluation, mean_audit, verification, report, manifest as `.venv/bin/python -m scripts.uncertainty_revision.NAME --check`. Construction caches exact-signature NPZ files under `.cache/stage45/`; local commits preserve resumable state. No MCMC. Cache bytes match their runtime SHA; cross-platform metadata/draw comparisons retain1e-10 tolerance. Finite dot products use explicit sum/einsum to avoid platform floating-status warnings without changing equations.

Independent scalar/QR scales, GH81 expectations, simplex vectors, CDF-integralCRPS, quantiles/interval scores, energy, winner and all paired/group/pooled arithmetic are separately recorded. Full local/configured checks and final-head Ubuntu status are recorded in PROJECT_STATE and the PR handoff. Prior1774datafiles and consumed code/coefficients/identities remain unchanged.

## Bounded CI cost control

Hosted CI previously ran on all pushes plus PR events. It now runs on PR events and main pushes, with workflow/event/PR-or-ref concurrency. Local resumable commits replace routine checkpoint pushes; unskipped remote PR updates still trigger runs. Optional non-review backups may use skip markers, leaving required checks pending; final review and merge heads must be unskipped. No marker in PR title/default merge message, no protection/check removal.

The first restructured review head and main retain complete Ubuntu verification. Conservative dependency-aware reuse and semantic archival-test details are in docs/ci-validation.md; hash integrity is not independent Linux reproduction. No extra hosted benchmarking, generated-output caching or scheduled workflow. Savings are duplicate and routine archival-work avoidance, not a guaranteed minute allowance.
