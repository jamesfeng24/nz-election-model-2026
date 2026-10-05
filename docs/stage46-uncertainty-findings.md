# Stage46 bounded robust centre/tail findings

Post-Stage45 development test; all historical observations retained. Student nu4 is assumed, not estimated. Shared Gaussian effects and frozen continuous S+R mean coefficients remain unchanged.

| Layer / election | Stage45 CRPS | Robust Gaussian | Student | Point | Student − Gaussian |
|---|---:|---:|---:|---:|---:|
| local_party 2011 | 0.5307 | 0.5315 | 0.5315 | 0.6242 | +0.0000 |
| local_party 2014 | 0.3985 | 0.3980 | 0.3980 | 0.4304 | +0.0000 |
| local_party 2017 | 0.4126 | 0.4124 | 0.4124 | 0.5182 | +0.0000 |
| local_party 2020 | 0.4394 | 0.4388 | 0.4388 | 0.5840 | +0.0000 |
| local_party 2023 | 0.4858 | 0.4856 | 0.4856 | 0.5511 | +0.0000 |
| candidate 2014 | 2.0048 | 2.0054 | 2.0278 | 2.7173 | +0.0224 |
| candidate 2017 | 1.8363 | 1.8321 | 1.8557 | 2.3695 | +0.0236 |
| candidate 2020 | 1.4720 | 1.4694 | 1.4819 | 2.1324 | +0.0125 |
| candidate 2023 | 1.8331 | 1.8208 | 1.8407 | 2.2466 | +0.0198 |
| composed 2017 | 2.5109 | 2.5162 | 2.5320 | 3.5418 | +0.0158 |
| composed 2020 | 1.5838 | 1.5819 | 1.6041 | 1.9266 | +0.0222 |
| composed 2023 | 2.3053 | 2.3032 | 2.3189 | 3.0545 | +0.0157 |

## Central/tail intervals and complete-vector scores

Entries are covered/total option observations; widths and interval scores use contest-equal means in pp. Category observations are correlated. Lower proper scores are better.

| Case | Method | 50% count / width / score | 80% count / width / score | 90% count / width / score | Energy | Expected-share MAE / RMSE |
|---|---|---|---|---|---:|---:|
| local_party:2011 | point | 0/819 / 0.000 / 2.497 | 0/819 / 0.000 / 6.242 | 0/819 / 0.000 / 12.483 | 4.068 | 0.624 / 1.395 |
| local_party:2011 | robust_gaussian | 538/819 / 1.742 / 2.473 | 719/819 / 3.339 / 4.038 | 756/819 / 4.320 / 5.194 | 3.294 | 0.625 / 1.395 |
| local_party:2011 | stage45 | 543/819 / 1.742 / 2.470 | 721/819 / 3.339 / 4.034 | 756/819 / 4.319 / 5.189 | 3.293 | 0.624 / 1.395 |
| local_party:2011 | student | 538/819 / 1.742 / 2.473 | 719/819 / 3.339 / 4.038 | 756/819 / 4.320 / 5.194 | 3.294 | 0.625 / 1.395 |
| local_party:2014 | point | 0/960 / 0.000 / 1.722 | 0/960 / 0.000 / 4.304 | 0/960 / 0.000 / 8.608 | 3.004 | 0.430 / 0.897 |
| local_party:2014 | robust_gaussian | 654/960 / 1.628 / 1.901 | 847/960 / 3.110 / 3.319 | 888/960 / 4.010 / 4.246 | 2.743 | 0.431 / 0.898 |
| local_party:2014 | stage45 | 652/960 / 1.628 / 1.904 | 844/960 / 3.110 / 3.319 | 887/960 / 4.010 / 4.245 | 2.743 | 0.430 / 0.897 |
| local_party:2014 | student | 654/960 / 1.628 / 1.901 | 847/960 / 3.110 / 3.319 | 888/960 / 4.010 / 4.246 | 2.743 | 0.431 / 0.898 |
| local_party:2017 | point | 0/1024 / 0.000 / 2.073 | 0/1024 / 0.000 / 5.182 | 0/1024 / 0.000 / 10.363 | 4.455 | 0.518 / 1.281 |
| local_party:2017 | robust_gaussian | 658/1024 / 1.225 / 1.921 | 872/1024 / 2.337 / 2.894 | 936/1024 / 3.011 / 3.590 | 3.355 | 0.517 / 1.280 |
| local_party:2017 | stage45 | 657/1024 / 1.226 / 1.922 | 871/1024 / 2.339 / 2.896 | 936/1024 / 3.014 / 3.594 | 3.357 | 0.518 / 1.281 |
| local_party:2017 | student | 658/1024 / 1.225 / 1.921 | 872/1024 / 2.337 / 2.894 | 936/1024 / 3.011 / 3.590 | 3.355 | 0.517 / 1.280 |
| local_party:2020 | point | 0/1105 / 0.000 / 2.336 | 0/1105 / 0.000 / 5.840 | 0/1105 / 0.000 / 11.680 | 4.761 | 0.584 / 1.313 |
| local_party:2020 | robust_gaussian | 703/1105 / 1.416 / 1.997 | 926/1105 / 2.718 / 3.084 | 988/1105 / 3.520 / 3.822 | 3.509 | 0.583 / 1.312 |
| local_party:2020 | stage45 | 698/1105 / 1.416 / 1.999 | 926/1105 / 2.717 / 3.088 | 990/1105 / 3.520 / 3.828 | 3.513 | 0.584 / 1.313 |
| local_party:2020 | student | 703/1105 / 1.416 / 1.997 | 926/1105 / 2.718 / 3.084 | 988/1105 / 3.520 / 3.822 | 3.509 | 0.583 / 1.312 |
| local_party:2023 | point | 0/1105 / 0.000 / 2.204 | 0/1105 / 0.000 / 5.511 | 0/1105 / 0.000 / 11.022 | 4.248 | 0.551 / 1.094 |
| local_party:2023 | robust_gaussian | 747/1105 / 1.737 / 2.240 | 999/1105 / 3.334 / 3.584 | 1053/1105 / 4.316 / 4.503 | 3.529 | 0.552 / 1.094 |
| local_party:2023 | stage45 | 751/1105 / 1.737 / 2.242 | 994/1105 / 3.333 / 3.593 | 1054/1105 / 4.313 / 4.510 | 3.530 | 0.551 / 1.094 |
| local_party:2023 | student | 747/1105 / 1.737 / 2.240 | 999/1105 / 3.334 / 3.584 | 1053/1105 / 4.316 / 4.503 | 3.529 | 0.552 / 1.094 |
| candidate:2014 | point | 0/451 / 0.000 / 10.869 | 0/451 / 0.000 / 27.173 | 0/451 / 0.000 / 54.345 | 10.694 | 2.717 / 4.847 |
| candidate:2014 | robust_gaussian | 258/451 / 4.525 / 8.989 | 395/451 / 8.693 / 12.777 | 418/451 / 11.264 / 16.117 | 7.816 | 2.718 / 4.848 |
| candidate:2014 | stage45 | 259/451 / 4.524 / 8.984 | 394/451 / 8.693 / 12.775 | 420/451 / 11.264 / 16.110 | 7.815 | 2.717 / 4.847 |
| candidate:2014 | student | 257/451 / 4.600 / 9.083 | 397/451 / 9.072 / 12.857 | 422/451 / 12.073 / 16.250 | 7.909 | 2.718 / 4.848 |
| candidate:2017 | point | 0/431 / 0.000 / 9.478 | 0/431 / 0.000 / 23.695 | 0/431 / 0.000 / 47.389 | 8.667 | 2.369 / 4.294 |
| candidate:2017 | robust_gaussian | 250/431 / 4.592 / 8.158 | 365/431 / 8.785 / 12.581 | 402/431 / 11.342 / 16.301 | 6.728 | 2.371 / 4.296 |
| candidate:2017 | stage45 | 254/431 / 4.657 / 8.183 | 367/431 / 8.905 / 12.640 | 403/431 / 11.492 / 16.387 | 6.745 | 2.369 / 4.294 |
| candidate:2017 | student | 251/431 / 4.694 / 8.239 | 368/431 / 9.216 / 12.858 | 405/431 / 12.219 / 16.962 | 6.815 | 2.371 / 4.296 |
| candidate:2020 | point | 0/561 / 0.000 / 8.530 | 0/561 / 0.000 / 21.324 | 0/561 / 0.000 / 42.649 | 9.393 | 2.132 / 3.622 |
| candidate:2020 | robust_gaussian | 344/561 / 4.018 / 6.538 | 502/561 / 7.767 / 9.441 | 533/561 / 10.110 / 11.945 | 6.629 | 2.134 / 3.622 |
| candidate:2020 | stage45 | 353/561 / 4.120 / 6.546 | 501/561 / 7.958 / 9.526 | 534/561 / 10.347 / 12.013 | 6.649 | 2.132 / 3.622 |
| candidate:2020 | student | 349/561 / 4.099 / 6.581 | 505/561 / 8.075 / 9.602 | 534/561 / 10.708 / 12.144 | 6.701 | 2.134 / 3.622 |
| candidate:2023 | point | 0/459 / 0.000 / 8.986 | 0/459 / 0.000 / 22.466 | 0/459 / 0.000 / 44.931 | 7.946 | 2.247 / 4.574 |
| candidate:2023 | robust_gaussian | 318/459 / 4.928 / 8.110 | 425/459 / 9.480 / 13.570 | 438/459 / 12.303 / 19.006 | 6.314 | 2.243 / 4.571 |
| candidate:2023 | stage45 | 323/459 / 5.054 / 8.168 | 426/459 / 9.713 / 13.741 | 438/459 / 12.598 / 19.210 | 6.359 | 2.247 / 4.574 |
| candidate:2023 | student | 320/459 / 5.028 / 8.188 | 427/459 / 9.816 / 13.813 | 440/459 / 12.934 / 19.434 | 6.393 | 2.243 / 4.571 |
| composed:2017 | point | 0/431 / 0.000 / 14.167 | 0/431 / 0.000 / 35.418 | 0/431 / 0.000 / 70.836 | 13.076 | 3.542 / 5.670 |
| composed:2017 | robust_gaussian | 234/431 / 5.709 / 11.393 | 349/431 / 10.929 / 15.401 | 397/431 / 14.128 / 18.044 | 9.279 | 3.545 / 5.676 |
| composed:2017 | stage45 | 234/431 / 5.690 / 11.355 | 350/431 / 10.897 / 15.293 | 397/431 / 14.090 / 17.896 | 9.275 | 3.544 / 5.674 |
| composed:2017 | student | 235/431 / 5.844 / 11.466 | 354/431 / 11.316 / 15.328 | 402/431 / 14.790 / 17.864 | 9.346 | 3.545 / 5.676 |
| composed:2020 | point | 0/561 / 0.000 / 7.706 | 0/561 / 0.000 / 19.266 | 0/561 / 0.000 / 38.532 | 8.693 | 1.927 / 3.635 |
| composed:2020 | robust_gaussian | 344/561 / 4.821 / 7.122 | 503/561 / 9.285 / 11.167 | 531/561 / 12.056 / 13.905 | 7.082 | 1.930 / 3.638 |
| composed:2020 | stage45 | 343/561 / 4.873 / 7.143 | 506/561 / 9.367 / 11.225 | 530/561 / 12.144 / 13.948 | 7.109 | 1.928 / 3.634 |
| composed:2020 | student | 345/561 / 4.964 / 7.228 | 503/561 / 9.630 / 11.424 | 532/561 / 12.591 / 14.229 | 7.193 | 1.930 / 3.638 |
| composed:2023 | point | 0/459 / 0.000 / 12.218 | 0/459 / 0.000 / 30.545 | 0/459 / 0.000 / 61.090 | 10.543 | 3.054 / 4.970 |
| composed:2023 | robust_gaussian | 276/459 / 6.622 / 10.123 | 409/459 / 12.732 / 16.358 | 425/459 / 16.514 / 21.697 | 7.834 | 3.054 / 4.966 |
| composed:2023 | stage45 | 272/459 / 6.638 / 10.152 | 408/459 / 12.755 / 16.404 | 425/459 / 16.527 / 21.759 | 7.849 | 3.053 / 4.967 |
| composed:2023 | student | 280/459 / 6.772 / 10.198 | 410/459 / 13.098 / 16.677 | 425/459 / 17.075 / 22.158 | 7.896 | 3.054 / 4.966 |

## Group diagnostics

Group CRPS uses equal selected options on their original share denominator; complete slates remain primary. No subgroup coefficients or outcome-selected admission.

| Candidate/composed case | Method | National CRPS | Labour CRPS | Other mapped CRPS | No-group CRPS | Winner zero-bank count | Prediction-time margin CRPS |
|---|---|---:|---:|---:|---:|---:|---:|
| candidate:2014 | point | 6.4970 (n=64) | 5.7092 (n=64) | 1.3658 (n=289) | 0.6431 (n=34) | 8 | 11.975 |
| candidate:2014 | robust_gaussian | 4.7811 (n=64) | 4.0000 (n=64) | 1.0681 (n=289) | 0.3140 (n=34) | 0 | 8.410 |
| candidate:2014 | stage45 | 4.7811 (n=64) | 4.0000 (n=64) | 1.0669 (n=289) | 0.3156 (n=34) | 0 | 8.410 |
| candidate:2014 | student | 4.8490 (n=64) | 4.0761 (n=64) | 1.0681 (n=289) | 0.3140 (n=34) | 0 | 8.567 |
| candidate:2017 | point | 5.0509 (n=64) | 4.0973 (n=64) | 1.4397 (n=258) | 0.9482 (n=45) | 3 | 7.485 |
| candidate:2017 | robust_gaussian | 3.7971 (n=64) | 3.1810 (n=64) | 1.1290 (n=258) | 0.7180 (n=45) | 0 | 6.054 |
| candidate:2017 | stage45 | 3.8106 (n=64) | 3.1993 (n=64) | 1.1281 (n=258) | 0.7146 (n=45) | 0 | 6.098 |
| candidate:2017 | student | 3.8800 (n=64) | 3.2421 (n=64) | 1.1290 (n=258) | 0.7180 (n=45) | 0 | 6.223 |
| candidate:2020 | point | 6.3837 (n=65) | 4.0726 (n=65) | 1.1984 (n=376) | 0.4766 (n=55) | 10 | 9.320 |
| candidate:2020 | robust_gaussian | 4.3661 (n=65) | 3.0658 (n=65) | 0.7984 (n=376) | 0.2630 (n=55) | 0 | 6.545 |
| candidate:2020 | stage45 | 4.3607 (n=65) | 3.0976 (n=65) | 0.7977 (n=376) | 0.2605 (n=55) | 0 | 6.577 |
| candidate:2020 | student | 4.4025 (n=65) | 3.1328 (n=65) | 0.7984 (n=376) | 0.2630 (n=55) | 0 | 6.657 |
| candidate:2023 | point | 4.0109 (n=64) | 3.5390 (n=64) | 1.4608 (n=281) | 0.9040 (n=50) | 7 | 7.281 |
| candidate:2023 | robust_gaussian | 3.2118 (n=64) | 2.7730 (n=64) | 1.1928 (n=281) | 0.6824 (n=50) | 1 | 5.497 |
| candidate:2023 | stage45 | 3.2472 (n=64) | 2.8099 (n=64) | 1.1947 (n=281) | 0.6849 (n=50) | 1 | 5.581 |
| candidate:2023 | student | 3.2771 (n=64) | 2.8367 (n=64) | 1.1928 (n=281) | 0.6824 (n=50) | 1 | 5.626 |
| composed:2017 | point | 7.4413 (n=64) | 7.8984 (n=64) | 1.7108 (n=258) | 0.9825 (n=45) | 3 | 14.526 |
| composed:2017 | robust_gaussian | 5.2877 (n=64) | 5.6566 (n=64) | 1.1813 (n=258) | 0.7288 (n=45) | 0 | 10.390 |
| composed:2017 | stage45 | 5.2958 (n=64) | 5.6501 (n=64) | 1.1744 (n=258) | 0.7257 (n=45) | 0 | 10.383 |
| composed:2017 | student | 5.3439 (n=64) | 5.6964 (n=64) | 1.1813 (n=258) | 0.7288 (n=45) | 0 | 10.484 |
| composed:2020 | point | 4.2250 (n=65) | 5.6312 (n=65) | 1.0223 (n=376) | 0.4585 (n=55) | 8 | 9.297 |
| composed:2020 | robust_gaussian | 3.5940 (n=65) | 4.3950 (n=65) | 0.8707 (n=376) | 0.2544 (n=55) | 0 | 7.589 |
| composed:2020 | stage45 | 3.6338 (n=65) | 4.4258 (n=65) | 0.8608 (n=376) | 0.2536 (n=55) | 0 | 7.662 |
| composed:2020 | student | 3.6856 (n=65) | 4.4826 (n=65) | 0.8707 (n=376) | 0.2544 (n=55) | 0 | 7.779 |
| composed:2023 | point | 4.6223 (n=64) | 4.8345 (n=64) | 2.2768 (n=281) | 0.9052 (n=50) | 8 | 8.506 |
| composed:2023 | robust_gaussian | 3.6880 (n=64) | 3.5035 (n=64) | 1.6979 (n=281) | 0.6829 (n=50) | 0 | 6.423 |
| composed:2023 | stage45 | 3.7220 (n=64) | 3.5306 (n=64) | 1.6866 (n=281) | 0.6847 (n=50) | 0 | 6.486 |
| composed:2023 | student | 3.7459 (n=64) | 3.5538 (n=64) | 1.6979 (n=281) | 0.6829 (n=50) | 0 | 6.533 |

## Pooled descriptive weighting

| Layer | Method | Contest-weighted CRPS | Equal-election CRPS |
|---|---|---:|---:|
| candidate | point | 2.3655 | 2.3664 |
| candidate | robust_gaussian | 1.7807 | 1.7819 |
| candidate | stage45 | 1.7853 | 1.7866 |
| candidate | student | 1.8003 | 1.8015 |
| composed | point | 2.8362 | 2.8410 |
| composed | robust_gaussian | 2.1309 | 2.1338 |
| composed | stage45 | 2.1305 | 2.1334 |
| composed | student | 2.1488 | 2.1516 |
| local_party | point | 0.5415 | 0.5416 |
| local_party | robust_gaussian | 0.4531 | 0.4533 |
| local_party | stage45 | 0.4532 | 0.4534 |
| local_party | student | 0.4531 | 0.4533 |

CRPS is in percentage points, lower is better. Equal contests within each election; pooled and equal-election views are saved separately. Gaussian/Student share robust central MAD and conditional remainder integration. Their difference isolates the tail law; differences from Stage45 include the disclosed numerical location correction.

Representative draw-doubling status: **precision_gates_passed**, 32768 draws. Independent conditional-location maximum gap **0.7389pp**, separate .05pp gate **unmet**. Maximum energy pair-estimate difference 0.0909pp. No tolerance relaxation.

Full per-candidate records, 50/80/90 intervals, group counts, proper interval and energy scores, margin/winner diagnostics and substantial misses are in evaluation.json. Winner frequencies are finite-bank diagnostics, not calibrated probabilities. For positive-mean simulated options, finite-bank zero does not establish mathematical zero probability; no floor. Frozen zero-mean options remain locked, and the degenerate point control deliberately has deterministic probabilities.

National draws are shared once. Composed cases use a fixed chain-balanced4096 cached national bank with repeated local scenarios, not additional independent national forecasts. No national inference, mean refit, transport variance, coefficient jitter, sources or retrospective overrides. Cross-layer independence, omitted scale/parameter uncertainty, uniform fragment flow, fine-party scenarios and national reconciliation remain limitations.

The analysis has only four reused candidate-election environments and three composed environments. Prior-driven2014 is explicit. Limited replication and remaining conditional quadrature error restrict fine claims and deployment; wider intervals or better coverage alone do not establish success.
