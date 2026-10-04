# Stage36 national poll-of-polls backtest

National-only chronological research under Stage35/D068. Election-day forecasts are scored; current latent support is reported separately and is not directly validated against the later result. Candidate components and operational selections are unchanged.

See the [development decision](stage36-national-polling-decision.md) for interpretation and the precise next dependency. `output-manifest.json` is the branch-specific national interface companion; original fit archives remain unchanged.

## Primary findings

All share/error/width/CRPS/energy quantities below are percentage points. Positive MAE gain means the model beats the average. Seven common categories include TOP within Other; eight-category fine results retain TOP separately from 2017 onward. Complete per-party errors, intervals, uncertainty covariances and diagnostics are in `evaluation.json`.

| Case | Model status | Model MAE | Average MAE | Model RMSE | Average RMSE | MAE gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2014 / 14d | accepted | 0.7034 | 1.5147 | 0.8901 | 1.8976 | 0.8113 |
| 2014 / 56d | accepted | 1.0588 | 2.1618 | 1.6717 | 2.6907 | 1.1029 |
| 2017 / 14d | accepted | 1.8986 | 1.6585 | 2.4254 | 2.3242 | -0.2402 |
| 2017 / 56d | accepted | 2.9339 | 2.9685 | 4.5098 | 4.4066 | 0.0346 |
| 2020 / 14d | accepted | 1.2734 | 1.3701 | 1.8004 | 1.9139 | 0.0967 |
| 2020 / 56d | accepted | 2.6483 | 2.4646 | 3.4616 | 2.9611 | -0.1837 |
| 2023 / 14d | accepted | 0.9676 | 1.1060 | 1.2388 | 1.4543 | 0.1384 |
| 2023 / 56d | accepted | 2.1984 | 2.4117 | 2.5923 | 2.8221 | 0.2133 |

### Uncertainty

| Case | CRPS | Energy | 50% coverage | 90% coverage | 50% width | 90% width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2014 / 14d | 0.5202 | 1.7364 | 0.5714 | 0.8571 | 1.4429 | 3.5683 |
| 2014 / 56d | 0.8312 | 3.1348 | 0.2857 | 0.8571 | 1.3910 | 3.4826 |
| 2017 / 14d | 1.3033 | 4.7434 | 0.2857 | 0.7143 | 1.7463 | 4.2580 |
| 2017 / 56d | 2.5108 | 9.7327 | 0.1429 | 0.4286 | 1.8231 | 4.4616 |
| 2020 / 14d | 0.9434 | 3.3382 | 0.2857 | 0.8571 | 2.1101 | 5.1364 |
| 2020 / 56d | 1.9615 | 6.7427 | 0.2857 | 0.5714 | 2.5798 | 6.3161 |
| 2023 / 14d | 0.6797 | 2.2856 | 0.7143 | 1.0000 | 2.2325 | 5.5075 |
| 2023 / 56d | 1.3838 | 4.5770 | 0.2857 | 1.0000 | 2.9276 | 7.0921 |

Major-party uncertainty is displayed separately. Election-day SD includes future movement; current SD is not an election-day interval. Error is prediction minus actual.

| Case | Party | Current SD | Election-day SD | 90% width | 90% covered | Error |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| 2014 / 14d | NAT | 2.2027 | 2.3562 | 7.6702 | True | 0.7004 |
| 2014 / 14d | LAB | 1.7105 | 1.8317 | 6.0143 | True | -0.3748 |
| 2014 / 56d | NAT | 2.0065 | 2.4295 | 8.0021 | True | 3.5531 |
| 2014 / 56d | LAB | 1.5867 | 1.9217 | 6.3530 | True | -0.1657 |
| 2017 / 14d | NAT | 2.4542 | 2.6745 | 8.7695 | True | -3.8565 |
| 2017 / 14d | LAB | 2.5012 | 2.7011 | 8.8904 | True | -2.7888 |
| 2017 / 56d | NAT | 2.3022 | 2.8738 | 9.4568 | True | 0.0002 |
| 2017 / 56d | LAB | 1.9861 | 2.4517 | 7.9930 | False | -10.2685 |
| 2020 / 14d | NAT | 2.6391 | 3.1410 | 10.2147 | True | 4.0094 |
| 2020 / 14d | LAB | 3.0883 | 3.6496 | 11.9158 | True | 0.3633 |
| 2020 / 56d | NAT | 3.0496 | 4.3886 | 14.4213 | True | 1.9140 |
| 2020 / 56d | LAB | 3.6171 | 5.0952 | 16.6186 | True | 7.2210 |
| 2023 / 14d | NAT | 2.7517 | 3.1973 | 10.5234 | True | -2.1521 |
| 2023 / 14d | LAB | 2.3825 | 2.7669 | 9.1020 | True | 0.5376 |
| 2023 / 56d | NAT | 2.8204 | 4.2540 | 13.8010 | True | -3.9319 |
| 2023 / 56d | LAB | 2.6609 | 4.0230 | 13.1801 | True | 3.7708 |

Scale parameters are in orthonormal log-contrast units; the fixed HalfNormal prior scales are 0.035 weekly,0.12 house and0.08 common bias. With few completed polling cycles, hyperparameter learning and common error remain prior-sensitive; this is not a calibrated covariance estimate.

| Case | Weekly σ mean [5%,95%] | House scale mean [5%,95%] | Common-bias scale mean [5%,95%] |
| --- | ---: | ---: | ---: |
| 2014 / 14d | 0.0206 [0.0152,0.0271] | 0.0704 [0.0454,0.1037] | 0.2065 [0.1342,0.2841] |
| 2014 / 56d | 0.0166 [0.0114,0.0227] | 0.0729 [0.0461,0.1079] | 0.2171 [0.1490,0.2916] |
| 2017 / 14d | 0.0276 [0.0224,0.0334] | 0.0823 [0.0527,0.1188] | 0.1958 [0.1396,0.2595] |
| 2017 / 56d | 0.0213 [0.0172,0.0260] | 0.0753 [0.0471,0.1114] | 0.2031 [0.1481,0.2660] |
| 2020 / 14d | 0.0461 [0.0413,0.0512] | 0.1231 [0.0842,0.1699] | 0.1777 [0.1184,0.2438] |
| 2020 / 56d | 0.0439 [0.0391,0.0490] | 0.1323 [0.0909,0.1818] | 0.1811 [0.1212,0.2486] |
| 2023 / 14d | 0.0439 [0.0402,0.0479] | 0.1196 [0.0935,0.1500] | 0.1398 [0.0864,0.1971] |
| 2023 / 56d | 0.0438 [0.0401,0.0478] | 0.1278 [0.0992,0.1611] | 0.1416 [0.0905,0.1986] |

### Historical availability

These counts describe admitted current-cycle waves, not verified historical archives. Earlier endpoints obey the frozen next-January availability assumption. The overlap selector can retain a later inferred wave in primary while verified-only retains an earlier verified wave: Roy Morgan August2023 is excluded from primary by conservative latest-overlap selection. Verified-only is therefore not simply a nested deletion of primary observations.

| Case | Current waves | Verified | Inferred | Missing n | Earlier anchored cycles |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2014 / 14d | 123 | 0 | 123 | 123 | 0 |
| 2014 / 56d | 110 | 0 | 110 | 110 | 0 |
| 2017 / 14d | 70 | 0 | 70 | 70 | 1 |
| 2017 / 56d | 62 | 0 | 62 | 62 | 1 |
| 2020 / 14d | 41 | 1 | 40 | 4 | 2 |
| 2020 / 56d | 37 | 0 | 37 | 4 | 2 |
| 2023 / 14d | 107 | 0 | 107 | 14 | 3 |
| 2023 / 56d | 98 | 0 | 98 | 11 | 3 |

### Major-party and small-party accounting

Each category below receives equal case weight (four elections, two horizons each). Overall signed bias cancels on the complete simplex; party bias is informative. Many small categories must not conceal National/Labour errors.

| Category | Cases | Model MAE | Average MAE | Model bias | Average bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| NAT | 8 | 2.5147 | 2.7247 | 0.0296 | 1.1421 |
| LAB | 8 | 3.1863 | 3.5816 | -0.2131 | 0.1313 |
| GRN | 8 | 1.7752 | 2.1758 | -0.1646 | 0.9646 |
| ACT | 8 | 1.3249 | 1.4914 | 0.1250 | 0.2112 |
| NZF | 8 | 1.7833 | 2.1373 | 0.2527 | -1.0212 |
| MRI | 8 | 0.1987 | 0.2662 | -0.0763 | -0.1063 |
| OTH | 8 | 1.1891 | 1.3218 | 0.0468 | -1.3218 |

Fine TOP output is separate from the coarse benchmark comparison. It supplies no allocation of the remaining Other category.

| Case | TOP expected share (%) | TOP actual (%) | TOP bias | TOP CRPS |
| --- | ---: | ---: | ---: | ---: |
| 2017 / 14d | 1.2352 | 2.4407 | -1.2055 | 1.0194 |
| 2017 / 56d | 0.7014 | 2.4407 | -1.7394 | 1.5892 |
| 2020 / 14d | 1.1326 | 1.5053 | -0.3727 | 0.2493 |
| 2020 / 56d | 0.9512 | 1.5053 | -0.5541 | 0.4032 |
| 2023 / 14d | 1.9945 | 2.2217 | -0.2272 | 0.1630 |
| 2023 / 56d | 1.8951 | 2.2217 | -0.3266 | 0.2195 |

## Finite sensitivities and coverage

Primary uses verified publication plus the declared five-day inference. Timing sensitivity substitutes ten days; missing-n sensitivity substitutes 1,000 for 750 in the model only. Verified-only never silently promotes inferred dates. No sensitivity Cartesian product or score-guided adjustment.

| Branch | Model / 8 | Average / 8 | Common | Model MAE | Average MAE | MAE gain | Model RMSE | Average RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| missing_n1000 | 8 | 8 | 8 | 1.6007 | 1.9570 | 0.3563 | 2.4765 | 2.6966 |
| primary | 8 | 8 | 8 | 1.7103 | 1.9570 | 0.2467 | 2.5808 | 2.6966 |
| publication_lag10 | 8 | 8 | 8 | 1.7608 | 1.9775 | 0.2166 | 2.5782 | 2.6889 |
| verified_only | 2 | 2 | 2 | 2.6197 | 2.5336 | -0.0861 | 3.6260 | 3.6080 |

| Branch | CRPS | Energy | 50% coverage | 90% coverage | 50% width | 90% width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| missing_n1000 | 1.1942 | 4.3081 | 0.4107 | 0.8393 | 2.0863 | 5.1022 |
| primary | 1.2668 | 4.5364 | 0.3571 | 0.7857 | 2.0317 | 4.9778 |
| publication_lag10 | 1.2748 | 4.5440 | 0.3750 | 0.7857 | 2.0414 | 4.9918 |
| verified_only | 1.8474 | 6.4445 | 0.5000 | 0.9286 | 3.6861 | 9.1491 |

Full pools require eight cases. Incomplete available-only pools renormalize the frozen 1/8 case weights and are labelled accordingly; they are not equivalent to complete coverage. Pooled RMSE takes the square root after pooling squared errors, never averages fold RMSEs.

### publication_lag10

| Case | Model status | Model MAE | Average MAE | Model RMSE | Average RMSE | MAE gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2014 / 14d | accepted | 0.7516 | 1.6013 | 0.9974 | 2.0104 | 0.8497 |
| 2014 / 56d | accepted | 0.9547 | 2.0522 | 1.3787 | 2.5075 | 1.0975 |
| 2017 / 14d | accepted | 1.8986 | 1.6585 | 2.4254 | 2.3242 | -0.2402 |
| 2017 / 56d | accepted | 2.9339 | 2.9685 | 4.5098 | 4.4066 | 0.0346 |
| 2020 / 14d | accepted | 1.4746 | 1.4240 | 1.7622 | 1.8581 | -0.0506 |
| 2020 / 56d | accepted | 2.6483 | 2.4646 | 3.4616 | 2.9611 | -0.1837 |
| 2023 / 14d | accepted | 1.2267 | 1.2391 | 1.5017 | 1.5838 | 0.0124 |
| 2023 / 56d | accepted | 2.1984 | 2.4117 | 2.5923 | 2.8221 | 0.2133 |

### missing_n1000

| Case | Model status | Model MAE | Average MAE | Model RMSE | Average RMSE | MAE gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2014 / 14d | accepted | 0.6984 | 1.5147 | 0.9079 | 1.8976 | 0.8164 |
| 2014 / 56d | accepted | 1.1095 | 2.1618 | 1.7404 | 2.6907 | 1.0523 |
| 2017 / 14d | accepted | 1.3628 | 1.6585 | 2.0452 | 2.3242 | 0.2956 |
| 2017 / 56d | accepted | 2.7730 | 2.9685 | 4.2656 | 4.4066 | 0.1955 |
| 2020 / 14d | accepted | 1.1888 | 1.3701 | 1.7611 | 1.9139 | 0.1813 |
| 2020 / 56d | accepted | 2.5941 | 2.4646 | 3.4032 | 2.9611 | -0.1295 |
| 2023 / 14d | accepted | 0.9000 | 1.1060 | 1.2137 | 1.4543 | 0.2060 |
| 2023 / 56d | accepted | 2.1791 | 2.4117 | 2.5839 | 2.8221 | 0.2326 |

### verified_only

| Case | Model status | Model MAE | Average MAE | Model RMSE | Average RMSE | MAE gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2014 / 14d | data_abstention | — | — | — | — | — |
| 2014 / 56d | data_abstention | — | — | — | — | — |
| 2017 / 14d | data_abstention | — | — | — | — | — |
| 2017 / 56d | data_abstention | — | — | — | — | — |
| 2020 / 14d | accepted | 2.1168 | 1.8761 | 2.4332 | 2.1939 | -0.2407 |
| 2020 / 56d | data_abstention | — | — | — | — | — |
| 2023 / 14d | accepted | 3.1226 | 3.1911 | 4.5139 | 4.6067 | 0.0684 |
| 2023 / 56d | data_abstention | — | — | — | — | — |

## Numerical attempts

All relevant sampled paths, initial states, house/method effects, cycle biases and election-day outputs are checked coordinate by coordinate. The frozen gates are rank R-hat ≤1.01, bulk/tail ESS ≥400 and no divergences. Exact constants are identified separately. Failed first attempts remain saved; only the frozen retry was allowed. Depth contacts and BFMI remain visible. Identical complete signatures reuse the same fit, not a fresh run.

| Saved case | Attempt | Status | Seconds | Max R-hat | Min bulk / tail ESS | Divergences | Depth contacts | BFMI range |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| missing_n1000-2014-14 | 1 | accepted | 254.1406 | 1.0045 | 2255.9995 / 1892.7308 | 0 | 0 | 0.920–0.992 |
| missing_n1000-2014-56 | 1 | accepted | 224.0742 | 1.0033 | 2304.3506 / 1282.9398 | 0 | 0 | 0.916–0.951 |
| missing_n1000-2017-14 | 1 | accepted | 527.9231 | 1.0040 | 1716.8764 / 2843.3894 | 0 | 0 | 0.880–0.953 |
| missing_n1000-2017-56 | 1 | accepted | 501.3859 | 1.0037 | 2141.3578 / 3428.9931 | 0 | 0 | 0.919–0.987 |
| missing_n1000-2020-14 | 1 | accepted | 1228.8820 | 1.0046 | 2485.1044 / 3730.3902 | 0 | 0 | 0.913–0.991 |
| missing_n1000-2020-56 | 1 | accepted | 1324.5034 | 1.0041 | 1541.9827 / 3117.5333 | 0 | 0 | 0.934–1.005 |
| missing_n1000-2023-14 | 1 | accepted | 2590.6582 | 1.0040 | 2133.1603 / 3270.7985 | 0 | 0 | 0.940–0.987 |
| missing_n1000-2023-56 | 1 | accepted | 2382.0299 | 1.0046 | 2207.7620 / 3538.1119 | 0 | 0 | 0.935–0.977 |
| primary-2014-14 | 1 | accepted | 132.0111 | 1.0030 | 2399.2318 / 2762.6391 | 0 | 0 | 0.940–1.000 |
| primary-2014-56 | 1 | accepted | 95.8146 | 1.0041 | 3028.4520 / 3975.7245 | 0 | 0 | 0.963–1.017 |
| primary-2017-14 | 1 | accepted | 376.7098 | 1.0048 | 1800.2882 / 3531.9001 | 0 | 0 | 0.952–0.999 |
| primary-2017-56 | 1 | accepted | 240.4924 | 1.0038 | 1443.0068 / 2051.5424 | 0 | 0 | 0.929–0.988 |
| primary-2020-14 | 1 | accepted | 927.6688 | 1.0070 | 947.1071 / 2359.7454 | 0 | 0 | 0.912–0.985 |
| primary-2020-56 | 1 | accepted | 842.3465 | 1.0097 | 628.0174 / 2428.5023 | 0 | 0 | 0.941–0.976 |
| primary-2023-14 | 1 | accepted | 2570.7898 | 1.0096 | 703.4320 / 460.4636 | 0 | 0 | 0.890–0.993 |
| primary-2023-56 | 1 | accepted | 2286.6056 | 1.0046 | 1715.2571 / 3775.7469 | 0 | 0 | 0.938–0.969 |
| publication_lag10-2014-14 | 1 | accepted | 179.3060 | 1.0039 | 1816.1675 / 1064.2883 | 0 | 0 | 0.927–1.000 |
| publication_lag10-2014-56 | 1 | accepted | 130.6262 | 1.0035 | 2982.5027 / 3974.5642 | 0 | 0 | 0.963–1.022 |
| publication_lag10-2020-14 | 1 | accepted | 900.5719 | 1.0059 | 1101.9931 / 1804.7510 | 0 | 0 | 0.947–0.976 |
| publication_lag10-2023-14 | 1 | accepted | 2715.7107 | 1.0037 | 1685.6667 / 3287.7223 | 0 | 0 | 0.918–0.975 |
| verified_only-2020-14 | 1 | numerical_failure | 224.5696 | 1.0056 | 1039.1841 / 1363.9609 | 14 | 0 | 1.016–1.095 |
| verified_only-2020-14 | 2 | accepted | 339.9431 | 1.0045 | 1320.1904 / 1796.9427 | 0 | 0 | 0.978–1.084 |
| verified_only-2023-14 | 1 | numerical_failure | 272.2290 | 1.0042 | 965.1290 / 1026.6251 | 25 | 0 | 0.945–1.019 |
| verified_only-2023-14 | 2 | accepted | 524.5376 | 1.0037 | 1017.2534 / 1399.9667 | 0 | 0 | 0.984–1.054 |

Archived sampling time summed over distinct attempts: 6.05 worker-hours. Two disjoint queues overlapped in wall time; cache reuse is excluded. Recorded platform/dependencies are in `environment.json`; exact run signatures and seeds are archived with each attempt.


## Independent verification and preservation

Independent arithmetic checked 485 poll projections, 26 average vectors, 192 paired transformed draws, 48 expected-share vectors, 68 point/pooling checks and 410 probability/interval/aggregation checks. All 1514 earlier data artifacts remain byte-identical.

The check uses independent constrained SLSQP projections, scalar Helmert/exp calculations and compensated summation, prefix-pair CRPS, manual linear quantiles and SciPy pair distances. Routine CI verifies saved outputs without historical MCMC; isolated local synthetic tests validate likelihoods/gradients and a four-chain smoke run. Neither the smoke run nor saved-output reproduction establishes empirical calibration.

## Interpretation and boundaries

- Four reused election environments and two dependent horizons per election provide limited calibration evidence. Poll count is not election replication.
- Publication timing is mostly inferred; current source snapshots are not proven archived as-of releases. Five-/ten-day assumptions and verified-only coverage are explicit.
- The first holdout has no earlier completed polling-cycle anchor to estimate common error; its uncertainty is especially prior-driven. Reported hyperparameter summaries are not proof of calibration.
- Gaussian interval observations are conditionally independent approximations, not multinomial ballots. Nominal n and assumed decided fractions are not measured effective sample sizes.
- Future diffusion is additional to current-state uncertainty; common polling error is already in the latent posterior and must not be drawn a second time downstream.
- NumPy emitted floating-status matmul warnings after JAX. Finite/conservation checks and independent scalar reconstructions verify the saved values; no equation or tolerance was altered to suppress warnings.
- A pre-score source audit corrected three distinct benchmark waves (15 case instances) to obey supported coarse-Other lower rounding bounds. The original unconstrained-remainder checkpoint is retained. No MCMC inputs or historical target errors informed this correction.
- Fine-party allocation within Other remains unavailable. Joint national draws cannot yet feed a complete candidate replay without a separately authorized allocation/interface decision.
- No candidate replay, national variants, live2026 output or operational choice follows. S/S+R stay active, R challenger and baseline control.

## Reproduction and resume

Install `requirements-polling.lock` in the isolated `.venv-polling`; retain the recorded runtime/environment. `MPLCONFIGDIR=/tmp/stage36-matplotlib .venv-polling/bin/python -m scripts.polling.national_model.inference` resumes all registered cases using exact signatures. Bounded queue wrappers keep private indexes and share exact fit archives. Never rerun completed MCMC for tables.

After forecast archival: run `archive --check`, `evaluation --check`, `verification --check`, and `report --check` under `scripts.polling.national_model`. Deterministic readers use the original project environment; no inference dependency installation is required in routine CI.
