# Stage47: numerical expectation repair and width attribution

## Decision and scope

**Recommendation B: one separately authorized Gaussian dispersion comparison.** Carry the numerical-only corrected Stage45 Gaussian law forward; preserve original Stage44–46 decisions and controls. S+R remains preferred, S active, baseline mandatory; no mean, scale or national model was fitted here.

The future frozen contract compares the corrected control, one earlier-trained constant candidate-seat balance adjustment, and one strongly pooled conditional adjustment. The two future characteristics are R-support deficit and continuous historical nonmajor support. Historical support replaces geography rather than adding a third predictor; it does not encode a target-result exception or an undated challenger-strength claim. No challengers are fitted in Stage47. See [future contract](../data/processed/uncertainty-expectation/next-test-contract.json).

## Numerical repair

Stage46’s worst reported conditional gap was **0.738928pp**. Larger independent references reduce the old-location discrepancy to **0.589445pp**, with **0.000157pp** reference spread. The reference error was material to the reported number, but the underlying location error remains real. This is a numerical expectation correction, not a new statistical distribution or bias fit.

All **578 component conditional inputs** and **197632 composed local/candidate conditional inputs** passed the retained **0.05pp** criterion using a stricter 0.02pp construction/reference target. Maximum accepted composed reference gap **0.01999996pp**. Finite independent-reference convergence is not a rigorous absolute error bound.

Independent raw-option covariance references on 12 first/middle/last candidate seats have maximum conditional gap **0.009563pp**, reference disagreement **0.000190pp**. Repeated labels, unique labels, zero faces and near-boundary fixtures are separately tested. Every constructed input is checked by two independent scrambled Gaussian integrations or escalating GH rules; a separate 262,144-node reference was not calculated for every composed input.

Shared ballot-label effects and individual effects use their actual contrast covariance. Supported active faces alone enter the softmax solve; predicted zeros remain locked. One-dimensional Gaussian reductions and damped analytic Newton solving are reusable, with independent convergence checks and fixed caps. No scale, mean coefficient, source, national inference or observation was changed.

### Separate numerical limitations

Components use 32,768 draws; composed cases use the prespecified 512 common stream indices across all 193 seats, selected from the preserved national permutation. Representative composed checks use 256/512/1,024 draws. **Both control and corrected banks fail the simulation precision gates at the cap.** This does not invalidate conditional-location checks, but prevents fine score/probability claims. No draw count or tolerance was selected after scores.

| 512→1,024 representative change | maximum pp |
| --- | --- |
| crps | 0.232508 |
| energy | 0.211687 |
| means | 0.560931 |
| width50 | 1.447053 |
| width80 | 2.164639 |
| width90 | 2.255378 |

Maximum component simulated mean shift **0.008847pp**. Composed candidate finite-bank shift **0.557030pp**, while genuine local-to-candidate nonlinear expectation shift reaches **1.807275pp**. The latter is retained: no final mean is forced back to the national-input-only deterministic prediction. Component expected shares remain frozen arithmetic means; composed expected shares use averaged conditional candidate means (Rao–Blackwell), with finite upstream precision explicit. Ordinary paired MAE compares both finite-bank means; separate expected-share summaries are not falsely presented as a pure numerical-effect comparison against an exact control expectation.

## Major-candidate full interval widths

All widths are full percentage-point spans, **not ± margins**. Conditional candidate distributions use observed local-party inputs. Composed distributions use cached external gauss 56-day draws plus local/candidate shocks. All 257 candidate seats and 193 composed seats remain. The forecast-leading pair is chosen from the fixed deterministic prediction, never the observed winner.

### national

| case | seats | 50 width | 80 width | 90 width | 50 covered | 80 covered | 90 covered | CRPS | IS50 | IS80 | IS90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| candidate:2014 | 64 | 9.99 | 18.81 | 23.96 | 24/64 | 52/64 | 56/64 | 4.781 | 21.540 | 29.173 | 36.200 |
| candidate:2017 | 64 | 10.33 | 19.48 | 24.81 | 38/64 | 57/64 | 62/64 | 3.811 | 16.932 | 24.670 | 30.647 |
| candidate:2020 | 65 | 9.21 | 17.42 | 22.21 | 20/65 | 55/65 | 59/65 | 4.361 | 19.181 | 22.973 | 27.770 |
| candidate:2023 | 64 | 10.02 | 18.89 | 24.10 | 45/64 | 62/64 | 63/64 | 3.247 | 14.535 | 24.223 | 33.360 |
| composed:2017 | 64 | 11.58 | 21.75 | 27.88 | 29/64 | 48/64 | 57/64 | 5.341 | 23.977 | 31.428 | 35.178 |
| composed:2020 | 65 | 13.02 | 24.47 | 30.87 | 48/65 | 62/65 | 63/65 | 3.643 | 16.848 | 26.590 | 31.954 |
| composed:2023 | 64 | 13.28 | 24.81 | 31.41 | 50/64 | 63/64 | 63/64 | 3.686 | 16.592 | 27.449 | 35.206 |

### labour

| case | seats | 50 width | 80 width | 90 width | 50 covered | 80 covered | 90 covered | CRPS | IS50 | IS80 | IS90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| candidate:2014 | 64 | 8.84 | 16.70 | 21.31 | 23/64 | 52/64 | 59/64 | 4.000 | 17.826 | 21.358 | 24.376 |
| candidate:2017 | 64 | 10.28 | 19.37 | 24.69 | 49/64 | 59/64 | 61/64 | 3.199 | 14.558 | 23.053 | 28.697 |
| candidate:2020 | 65 | 10.39 | 19.57 | 24.91 | 46/65 | 61/65 | 63/65 | 3.098 | 13.905 | 21.621 | 25.999 |
| candidate:2023 | 64 | 8.98 | 16.96 | 21.65 | 42/64 | 59/64 | 61/64 | 2.810 | 12.806 | 19.102 | 23.473 |
| composed:2017 | 64 | 10.45 | 19.81 | 25.22 | 19/64 | 39/64 | 54/64 | 5.714 | 25.864 | 31.372 | 31.695 |
| composed:2020 | 65 | 14.62 | 27.37 | 34.62 | 47/65 | 59/65 | 62/65 | 4.459 | 20.117 | 31.348 | 35.855 |
| composed:2023 | 64 | 12.93 | 24.22 | 30.74 | 50/64 | 62/64 | 63/64 | 3.469 | 15.745 | 25.153 | 31.527 |

### forecast pair

| case | seats | 50 width | 80 width | 90 width | 50 covered | 80 covered | 90 covered | CRPS | IS50 | IS80 | IS90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| candidate:2014 | 64 | 17.22 | 32.47 | 41.46 | 21/64 | 49/64 | 58/64 | 8.410 | 37.873 | 45.749 | 52.453 |
| candidate:2017 | 64 | 19.54 | 36.86 | 46.99 | 47/64 | 59/64 | 62/64 | 6.098 | 27.386 | 44.837 | 57.475 |
| candidate:2020 | 65 | 17.93 | 33.91 | 43.28 | 32/65 | 58/65 | 62/65 | 6.577 | 28.724 | 40.157 | 48.686 |
| candidate:2023 | 64 | 17.14 | 32.42 | 41.45 | 43/64 | 61/64 | 62/64 | 5.581 | 24.661 | 38.667 | 50.783 |
| composed:2017 | 64 | 20.32 | 38.70 | 49.15 | 23/64 | 39/64 | 56/64 | 10.506 | 48.400 | 57.959 | 57.706 |
| composed:2020 | 65 | 26.75 | 50.30 | 63.44 | 49/65 | 61/65 | 62/65 | 7.701 | 35.079 | 55.408 | 66.454 |
| composed:2023 | 64 | 24.30 | 45.13 | 57.44 | 46/64 | 63/64 | 64/64 | 6.504 | 29.169 | 46.409 | 57.440 |

### Individual shares of the forecast-leading two candidates

These spans concern each selected candidate, averaged within its contest; they are not the difference/margin interval above. Two correlated candidates are not two independent temporal replications. No selected-party renormalization is used.

| case | candidates | 50 width | 80 width | 90 width | CRPS | 90 covered | IS90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| candidate:2014 | 128 | 9.44 | 17.79 | 22.68 | 4.388 | 115/128 | 30.335 |
| candidate:2017 | 128 | 10.31 | 19.43 | 24.75 | 3.505 | 123/128 | 29.672 |
| candidate:2020 | 130 | 9.95 | 18.77 | 23.90 | 3.691 | 123/130 | 26.702 |
| candidate:2023 | 128 | 9.71 | 18.31 | 23.36 | 3.131 | 125/128 | 28.505 |
| composed:2017 | 128 | 11.17 | 21.05 | 26.86 | 5.515 | 112/128 | 33.471 |
| composed:2020 | 130 | 14.01 | 26.24 | 33.12 | 4.073 | 125/130 | 34.282 |
| composed:2023 | 128 | 13.43 | 25.09 | 31.76 | 3.691 | 127/128 | 33.663 |

### Width distributions and weighting

| case | group | original8000 full90 | common control full90 | corrected full90 |
| --- | --- | --- | --- | --- |
| candidate:2014 | national | 23.97 | 23.96 | 23.96 |
| candidate:2014 | labour | 21.34 | 21.31 | 21.31 |
| candidate:2014 | forecast_pair | 41.54 | 41.46 | 41.46 |
| candidate:2017 | national | 24.74 | 24.81 | 24.81 |
| candidate:2017 | labour | 24.61 | 24.69 | 24.69 |
| candidate:2017 | forecast_pair | 46.81 | 46.99 | 46.99 |
| candidate:2020 | national | 22.18 | 22.21 | 22.21 |
| candidate:2020 | labour | 24.86 | 24.91 | 24.91 |
| candidate:2020 | forecast_pair | 43.16 | 43.28 | 43.28 |
| candidate:2023 | national | 23.99 | 24.10 | 24.10 |
| candidate:2023 | labour | 21.50 | 21.65 | 21.65 |
| candidate:2023 | forecast_pair | 41.21 | 41.45 | 41.45 |
| composed:2017 | national | 27.89 | 27.87 | 27.88 |
| composed:2017 | labour | 25.56 | 25.22 | 25.22 |
| composed:2017 | forecast_pair | 49.55 | 49.12 | 49.15 |
| composed:2020 | national | 31.80 | 30.86 | 30.87 |
| composed:2020 | labour | 35.29 | 34.61 | 34.62 |
| composed:2020 | forecast_pair | 65.05 | 63.40 | 63.44 |
| composed:2023 | national | 31.75 | 31.40 | 31.41 |
| composed:2023 | labour | 31.75 | 30.73 | 30.74 |
| composed:2023 | forecast_pair | 58.54 | 57.32 | 57.44 |

| layer | weights | group | 90 mean width | seat p10 | seat median | seat p90 |
| --- | --- | --- | --- | --- | --- | --- |
| candidate | contestWeighted | forecast_pair | 43.30 | 33.26 | 44.22 | 52.23 |
| candidate | contestWeighted | labour | 23.15 | 16.91 | 24.73 | 26.96 |
| candidate | contestWeighted | national | 23.76 | 18.96 | 24.95 | 27.07 |
| candidate | contestWeighted | other | 6.57 | 4.17 | 6.04 | 9.34 |
| candidate | equalElection | forecast_pair | 43.30 | 33.26 | 44.22 | 52.23 |
| candidate | equalElection | labour | 23.14 | 16.91 | 24.73 | 26.96 |
| candidate | equalElection | national | 23.77 | 18.96 | 24.95 | 27.07 |
| candidate | equalElection | other | 6.57 | 4.17 | 6.04 | 9.34 |
| composed | contestWeighted | forecast_pair | 56.71 | 41.53 | 56.78 | 69.29 |
| composed | contestWeighted | labour | 30.21 | 20.75 | 31.24 | 36.90 |
| composed | contestWeighted | national | 30.06 | 23.36 | 31.16 | 35.30 |
| composed | contestWeighted | other | 8.04 | 4.13 | 7.35 | 12.57 |
| composed | equalElection | forecast_pair | 56.68 | 41.53 | 56.78 | 69.29 |
| composed | equalElection | labour | 30.19 | 20.75 | 31.24 | 36.90 |
| composed | equalElection | national | 30.05 | 23.36 | 31.16 | 35.30 |
| composed | equalElection | other | 8.05 | 4.13 | 7.35 | 12.57 |

Whole-slate averages do not describe competitive-seat intervals. Other candidates are reported separately in the inventory with their actual errors and denominators. Candidate-equal and contest/equal-election weighting are distinct; seat distributions describe the selected exact/continuous-transport sample, not the whole country.

## Numerical-only comparison to original Gaussian controls

Original Stage45 8,000-draw artifacts are untouched; missing 80% summaries were calculated from their cached banks. The unchanged-law Stage46 32,768 control is a separate numerical companion, not a rewritten original result. Composed repaired/control comparisons below use identical 512 indices; the original 8,000-bank summaries do not have identical sampling precision.

| case | common control CRPS | corrected CRPS | corrected−control CRPS | corrected−control finite-mean MAE |
| --- | --- | --- | --- | --- |
| candidate:2014 | 2.004768 | 2.004741 | -0.000027 | -0.000072 |
| candidate:2017 | 1.836317 | 1.836303 | -0.000014 | -0.000028 |
| candidate:2020 | 1.472024 | 1.471991 | -0.000033 | -0.000067 |
| candidate:2023 | 1.833102 | 1.833060 | -0.000042 | -0.000082 |
| composed:2017 | 2.531934 | 2.536273 | +0.004339 | -0.000510 |
| composed:2020 | 1.586718 | 1.592748 | +0.006030 | +0.001055 |
| composed:2023 | 2.286658 | 2.292088 | +0.005431 | -0.002511 |

Conditional N/L draws are **exactly unchanged in all 578 component seats**, verified from cached arrays: within-remainder repair cannot change aggregate major balance/mass under this tree. Tiny conditional whole-slate changes are in other options. Composed differences also reflect repaired local remainder allocation passing through candidate normalization. Their small score changes are not a new statistical improvement or calibration claim; finite-bank uncertainty is larger.

## Width drivers

The bounded ablation covers exactly nine prespecified first/middle/last composed seats. Each row removes one block, keeps common random streams and recomputes outcome-free locations for that changed covariance. Width differences are **not additive variance shares** and the sample is not a national average. National-at-mean uses the full 4,096 cached-national mean; its comparison to 512 selected scenarios includes finite sampling differences.

| policy | NAT full90 width | LAB full90 width | pair margin full90 width |
| --- | --- | --- | --- |
| full | 29.89 | 31.01 | 57.81 |
| national_at_mean | 25.41 | 25.60 | 48.89 |
| no_local_shared | 29.60 | 30.75 | 56.87 |
| no_local_seat | 27.77 | 29.46 | 54.29 |
| no_candidate_shared | 27.73 | 29.23 | 54.75 |
| no_candidate_seat | 21.16 | 23.12 | 43.28 |
| no_candidate_balance | 20.84 | 22.84 | 40.18 |
| no_candidate_mass | 27.32 | 28.92 | 55.75 |
| no_candidate_within | 29.89 | 31.01 | 57.49 |

Candidate seat/balance variation is the largest removable block in this diagnostic; national and local uncertainty remain consequential. Shared shocks still matter to cross-seat dependence; moving a shock from shared to seat-specific would not itself reduce its marginal variance. Within-remainder shocks cannot directly widen conditional N/L intervals, though they can affect a nonmajor leading pair and upstream candidate composition.

For each representative seat, analytic law of total variance partitions candidate variance into E[Var(candidate | national, local)] plus Var(E[candidate | national, local]). It retains the finite upstream sample and the mass×balance interaction. In 2020 several upstream contributions are as large as or larger than the candidate contribution. We do not assign independent national/local percentages without nested local replication. Full-frame 578-vector analytic mass/balance variance and covariance identities are in prior-audit.json.

## Prior versus data

Three prior election-equivalents remain unchanged. Prior **weight** is 3/(E+3); actual variance contribution depends on prior scale and observed second moments. Candidate2014 is fully prior-driven. At2023 the candidate balance shared/seat prior weight is 50%, but its actual combined variance fraction is **55.1714%**. Local balance’s combined fraction is47.2336%; local major mass71.8946%. Broad widths therefore reflect both data and substantial prior assumptions, not merely numerical integration.

Every layer/coordinate/fold/kind follows below. Variance is dimensionless log-unit squared; within scales are raw exchangeable log-intensities with projection/label covariance, not each CLR coordinate SD. Empirical-only estimates are descriptive and never substituted as forecasts.

| layer | target | coordinate | kind | earlier E | prior weight | history variance | prior variance | result SD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local_party | 2011 | balance | shared | 0 | 1.000 | 0.000000 | 0.006400 | 0.080000 |
| local_party | 2011 | balance | seat | 0 | 1.000 | 0.000000 | 0.022500 | 0.150000 |
| local_party | 2011 | mass | shared | 0 | 1.000 | 0.000000 | 0.010000 | 0.100000 |
| local_party | 2011 | mass | seat | 0 | 1.000 | 0.000000 | 0.040000 | 0.200000 |
| local_party | 2011 | within | shared | 0 | 1.000 | 0.000000 | 0.022500 | 0.150000 |
| local_party | 2011 | within | seat | 0 | 1.000 | 0.000000 | 0.250000 | 0.500000 |
| local_party | 2014 | balance | shared | 1 | 0.750 | 0.000046 | 0.004800 | 0.069612 |
| local_party | 2014 | balance | seat | 1 | 0.750 | 0.008135 | 0.016875 | 0.158147 |
| local_party | 2014 | mass | shared | 1 | 0.750 | 0.000122 | 0.007500 | 0.087302 |
| local_party | 2014 | mass | seat | 1 | 0.750 | 0.002754 | 0.030000 | 0.180980 |
| local_party | 2014 | within | shared | 1 | 0.750 | 0.041077 | 0.016875 | 0.240732 |
| local_party | 2014 | within | seat | 1 | 0.750 | 0.048095 | 0.187500 | 0.485381 |
| local_party | 2017 | balance | shared | 2 | 0.600 | 0.000150 | 0.003840 | 0.063170 |
| local_party | 2017 | balance | seat | 2 | 0.600 | 0.009359 | 0.013500 | 0.151191 |
| local_party | 2017 | mass | shared | 2 | 0.600 | 0.000223 | 0.006000 | 0.078888 |
| local_party | 2017 | mass | seat | 2 | 0.600 | 0.003628 | 0.024000 | 0.166215 |
| local_party | 2017 | within | shared | 2 | 0.600 | 0.051500 | 0.013500 | 0.254950 |
| local_party | 2017 | within | seat | 2 | 0.600 | 0.123151 | 0.150000 | 0.522638 |
| local_party | 2020 | balance | shared | 3 | 0.500 | 0.000403 | 0.003200 | 0.060025 |
| local_party | 2020 | balance | seat | 3 | 0.500 | 0.013717 | 0.011250 | 0.158009 |
| local_party | 2020 | mass | shared | 3 | 0.500 | 0.000208 | 0.005000 | 0.072163 |
| local_party | 2020 | mass | seat | 3 | 0.500 | 0.004701 | 0.020000 | 0.157167 |
| local_party | 2020 | within | shared | 3 | 0.500 | 0.077517 | 0.011250 | 0.297937 |
| local_party | 2020 | within | seat | 3 | 0.500 | 0.138394 | 0.125000 | 0.513220 |
| local_party | 2023 | balance | shared | 4 | 0.429 | 0.000831 | 0.002743 | 0.059780 |
| local_party | 2023 | balance | seat | 4 | 0.429 | 0.013006 | 0.009643 | 0.150495 |
| local_party | 2023 | mass | shared | 4 | 0.429 | 0.000309 | 0.004286 | 0.067782 |
| local_party | 2023 | mass | seat | 4 | 0.429 | 0.008068 | 0.017143 | 0.158780 |
| local_party | 2023 | within | shared | 4 | 0.429 | 0.086382 | 0.009643 | 0.309879 |
| local_party | 2023 | within | seat | 4 | 0.429 | 0.170410 | 0.107143 | 0.526833 |
| candidate | 2014 | balance | shared | 0 | 1.000 | 0.000000 | 0.022500 | 0.150000 |
| candidate | 2014 | balance | seat | 0 | 1.000 | 0.000000 | 0.122500 | 0.350000 |
| candidate | 2014 | mass | shared | 0 | 1.000 | 0.000000 | 0.022500 | 0.150000 |
| candidate | 2014 | mass | seat | 0 | 1.000 | 0.000000 | 0.160000 | 0.400000 |
| candidate | 2014 | within | shared | 0 | 1.000 | 0.000000 | 0.040000 | 0.200000 |
| candidate | 2014 | within | seat | 0 | 1.000 | 0.000000 | 0.490000 | 0.700000 |
| candidate | 2017 | balance | shared | 1 | 0.750 | 0.019860 | 0.016875 | 0.191663 |
| candidate | 2017 | balance | seat | 1 | 0.750 | 0.020861 | 0.091875 | 0.335761 |
| candidate | 2017 | mass | shared | 1 | 0.750 | 0.001325 | 0.016875 | 0.134907 |
| candidate | 2017 | mass | seat | 1 | 0.750 | 0.032643 | 0.120000 | 0.390695 |
| candidate | 2017 | within | shared | 1 | 0.750 | 0.046612 | 0.030000 | 0.276789 |
| candidate | 2017 | within | seat | 1 | 0.750 | 0.052157 | 0.367500 | 0.647809 |
| candidate | 2020 | balance | shared | 2 | 0.600 | 0.016088 | 0.013500 | 0.172013 |
| candidate | 2020 | balance | seat | 2 | 0.600 | 0.033290 | 0.073500 | 0.326788 |
| candidate | 2020 | mass | shared | 2 | 0.600 | 0.014152 | 0.013500 | 0.166289 |
| candidate | 2020 | mass | seat | 2 | 0.600 | 0.058818 | 0.096000 | 0.393470 |
| candidate | 2020 | within | shared | 2 | 0.600 | 0.094254 | 0.024000 | 0.343881 |
| candidate | 2020 | within | seat | 2 | 0.600 | 0.087938 | 0.294000 | 0.618011 |
| candidate | 2023 | balance | shared | 3 | 0.500 | 0.024690 | 0.011250 | 0.189578 |
| candidate | 2023 | balance | seat | 3 | 0.500 | 0.034219 | 0.061250 | 0.308980 |
| candidate | 2023 | mass | shared | 3 | 0.500 | 0.022655 | 0.011250 | 0.184132 |
| candidate | 2023 | mass | seat | 3 | 0.500 | 0.063537 | 0.080000 | 0.378863 |
| candidate | 2023 | within | shared | 3 | 0.500 | 0.196164 | 0.020000 | 0.464935 |
| candidate | 2023 | within | seat | 3 | 0.500 | 0.104725 | 0.245000 | 0.591375 |

## Heterogeneity, dependence and remaining persistence

Frozen R-support and target-incoming population fragmentation diagnostics retain unknowns, full/partial/no support and all seats. Within-election balance-error dispersion versus R support is inconsistent (Pearson2014/17/20/23: +0.038,+0.053,+0.307,−0.096). Fragmentation versus squared balance error is −0.190/−0.064 in2014/20; exact-only folds have no fragmentation variation. This does not support a blanket claim that more history or stronger continuity makes seats less uncertain.

Matched local/candidate raw-log balance and mass residual associations, centered within election with equal total election weight, are −0.011 and −0.091. Across just four election means the balance association is −0.764; this is sparse shared-environment evidence, not many independent seat replications. Conditional definitions can induce relationships; they do not establish independence or automatic double-counting of national error. A new covariance fit is not the next priority.

Remaining complete-S+R balance-error correlations on certified exact seat pairs2014→17/2017→20/2020→23 are −0.111,+0.274,−0.048. Mass correlations are +0.114,+0.227,+0.307. These are descriptive persistence checks after the full mean, not Stage30 personal strength evidence or authorization for a latent seat effect.

## Structural-continuity amendment

The amendment was recorded after Stage47 began and before its new structural tables. All257 seats, including successful forecasts, use identical evidence rules; no viability threshold or exceptional-seat list is chosen from errors. Every nonmajor source occurrence contributes a continuous source-support proxy; this population-weighted candidate-share proxy is not a reconstructed target candidate vote.

Coverage: 1741 source occurrence representations, {'accepted_contender_continuation': 229, 'documented_departure_from_target_contest': 1, 'unresolved': 1511}. Target states: {'accepted_contender_continuation': 500, 'major_party_turnover_supported_by_evidence': 6, 'unresolved': 1396}. There are **no preserved dated new-strength facts** and **no verified complete56-day rosters**. Nonmatch remains unresolved, not departure. Documentary distinctness alone is not evidence of retirement or contender viability. 721 target candidates retain source S without an accepted person link; this is permitted party/geography behavior, not proof that their S is obsolete.

| year | seats | source support vs centered squared balance | source support vs centered squared mass | unknown target states |
| --- | --- | --- | --- | --- |
| 2014 | 64 | 0.704 | 0.132 | 302 |
| 2017 | 64 | 0.604 | 0.111 | 307 |
| 2020 | 65 | -0.044 | 0.107 | 444 |
| 2023 | 64 | 0.242 | -0.025 | 343 |

Historical nonmajor support is associated with balance dispersion in2014/17, weakly in2023 and not2020. The pooled impression is not a universal tactical regime; election composition and small-share log denominators matter. Descriptive centering/standardization subtracts election errors for diagnosis only and is not actual forecast-standardized uncertainty.

### Highlighted hypotheses verified against actual features

- **Ōhāriu2017:** United Future’s replacement retains Dunne-derived centered S(+0.294), but receives no outgoing R. National retains its own suppressed S(−0.275) and same-person R(−0.347). Saved baseline/S/R/joint balance errors are−0.306/+0.433/+1.082/+1.427; joint mass error+0.471. The preserved secondary chronology dates Dunne’s retirement21August, **after** the actual29July56-day cutoff; publication is unverified. This supports a retrospective obsolete-participant hypothesis, not a known forecast-time reset rule.
- **Auckland Central2020:** Swarbrick receives Roche-derived negative S(−0.328), R0; the major replacement also receives predecessor party S without outgoing R. Baseline versus joint mass errors−0.247/−0.546 show allocation error alongside balance error(+0.440). No preserved dated pre-cutoff challenger-strength fact establishes an eligible reset. In2023 Swarbrick is linked, with positive S/R, while balance error remains sizeable: continuity is not sufficient to ensure accuracy.
- **Tāmaki2023:** van Velden receives Claridge-derived negative ACT S(−0.375) and no outgoing R; O’Connor retains his own positive S/R. Joint balance error−1.026 and major-mass error−2.046 are both large. ACT’s actual-minus-joint share error is a major pp miss, not only a small-denominator log artefact. Stage46’s balance-only t test did not test third-party allocation. This identifies a separately scoped mean-continuity hypothesis; it does not authorize a reset or historical override.
- **Epsom:** accepted Seymour/Goldsmith continuation coexists with large2017/20 balance errors(+0.897/+0.604) but near-zero2023 balance error(+0.018), while2023 mass error is+0.400. Stable tactical participants are not interchangeable with tactical transitions and do not automatically require wider intervals.

All saved four-model comparisons are loaded only on matching complete exact IDs; changed-seat baseline/R predictions are not manufactured. Source S names, centered contributions, supported masses, accepted links, strict flags, fallback reasons and balance/mass/pp errors are separately preserved. The actual source-only R constructor and outcome-counterfactual tests verify the existing no-outgoing-transfer guard. Structural evidence is insufficient for a universal forecast-time departure/strength classifier; a future S-continuity mean test needs its own authorization, coherent complete-slate formulation and dated information.

## Practical next action and deployment blockers

Implement the frozen three-restriction Gaussian candidate-seat balance scale comparison only if separately authorized. Constant recalibration distinguishes scale-level adequacy from conditional heterogeneity. The conditional model is strongly pooled, can increase or decrease scales, and must earn complexity on proper scores and fold-specific coverage/sharpness. There is no every-fold materiality veto or promise to halve widths. No additional coordinates, tail families, covariance, mean reset or new acquisition are bundled into it.

Current blockers remain finite composed simulation precision, scarce repeatedly reused election environments, prior/parameter uncertainty, fragment composition and fine-party allocation assumptions, historical cutoff/roster availability, complete live nominations, separate Māori baseline and electorate-poll measurement, turnout/reconciliation and MMP assembly. Winner frequencies are development diagnostics; finite-bank zero is not mathematical impossibility.

Manual adjustments must keep dated reasons, unadjusted outputs, author/review/expiry and coherent slate changes; a mean change does not justify lower variance. Electorate polls are uncertain measurements (question, denominator, dates, sample and dependence), with Māori polls separately scoped. National Te Pāti Māori party support differs from Māori candidate support. Party-vote reconciliation must not constrain candidate-vote totals.

## Validation and reproduction

Independent checks cover **19,038,720 corrected simplex vectors**, all578 component major-vector equivalences, scalar CRPS/proper intervals on first/middle/last each case, independent raw-covariance references, prior contributions/product covariance, leakage/chronology, zero faces, repeated labels and random-stream separation. Local/Ubuntu check status is recorded in PROJECT_STATE and the final PR handoff; hashes alone do not prove Linux reconstruction.

Use the pinned `.venv/bin/python`. `construction --check` explicitly reconstructs the new bounded companions; normal construction resumes exact signatures. `evaluation/attribution/verification --check` reuse sealed banks. `pilot/prior/audits/structure/structural_diagnostics/report/manifest --check` reproduce derived findings. Original banks are never regenerated merely for local repetition; final existing archival Ubuntu commands remain intact. No MCMC or acquisition occurs.

New artifacts are under `data/processed/uncertainty-expectation/`; producer signature, consumed helper/source closure, separate structural evidence hashes and prior-file preservation are sealed. Cache files under `.cache/stage47/` are local reproducible conveniences, not off-device backups. Routine checkpoints stay local; only the consolidated unskipped review head is pushed. Leave the PR unmerged.
