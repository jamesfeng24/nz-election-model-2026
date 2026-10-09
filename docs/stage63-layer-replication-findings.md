# Stage63: layer-replicated composed simulation, findings

Pre-registered design: [stage63-layer-replication-design.md](stage63-layer-replication-design.md), frozen before any replicate bank was scored. Machine contract: [design-contract.json](../data/processed/layer-replication/design-contract.json). All figures are percentage points unless stated; no model default, scale, law or frozen cap is changed. The scale file is an input (the pinned Stage45 scales); Stage60 may change the balance scale and this study then reruns unchanged.

## Finding under the frozen rules

**CAPS_MET_BY_REPLICATION.** The cheapest arm that meets all six frozen caps at its layer doubling is M = 16 replicates per national draw (65,536 composed draws per seat on the fixed 4,096 national draws); the 3-sigma rule requires M = 16. Its measured cost is about 0.19 CPU hours per seat, 14 CPU hours for a 71-seat slate.

## Harness

The first 512 positions of replicate 0 equal Stage54 block 0 and those of replicates 8, 9, 10 equal its layer-only records for every representative seat, and replicate 0 equals block 0 for the nine panel seats: 45 checks over 18 seats, maximum absolute difference 0.0e+00 (verdict MATCHES_STAGE54). Equivalence diagnostic: the two half banks of arm 32 differ by `z` with mean `z^2` 0.89 and maximum |z| 2.53 over 409 seat-candidate quantities (band 0.6 to 1.6 and 4.5): **EQUIVALENT**.

## Gate B: layer doubling at the full 4,096 national pool

Maximum change over representative seat-candidates when the replicate count is doubled from M/2 to M (nested banks), against the unchanged caps; (fail) marks a cap exceeded.

| Replicates | Composed draws | mean | crps | energy | width50 | width80 | width90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 to 2 | 8,192 | 0.054 (fail) | 0.097 (fail) | 0.088 | 0.296 | 0.553 (fail) | 0.863 (fail) |
| 2 to 4 | 16,384 | 0.051 (fail) | 0.068 (fail) | 0.080 | 0.263 | 0.305 | 0.422 |
| 4 to 8 | 32,768 | 0.019 | 0.044 | 0.030 | 0.139 | 0.198 | 0.241 |
| 8 to 16 | 65,536 | 0.010 | 0.019 | 0.043 | 0.111 | 0.192 | 0.152 |
| 16 to 32 | 131,072 | 0.010 | 0.015 | 0.018 | 0.087 | 0.178 | 0.188 |
| 32 to 64 | 262,144 | 0.004 | 0.006 | 0.012 | 0.060 | 0.072 | 0.112 |
| Cap |  | 0.05 | 0.05 | 0.1 | 0.5 | 0.5 | 0.5 |

Three-sigma requirement from the 64 single-replicate banks (`s1` is the largest sd over representative seat-candidates, so it is biased high; the change on doubling M/2 to M has sd `s1 / sqrt(M)`).

| Quantity | Cap | s1 max | s1 median | Required replicates | 3 sigma / cap at M = 64 |
| --- | --- | --- | --- | --- | --- |
| simulated mean | 0.05 | 0.042 | 0.0096 | 8 | 0.31 |
| CRPS | 0.05 | 0.059 | 0.0048 | 16 | 0.44 |
| energy score | 0.1 | 0.065 | 0.0479 | 4 | 0.25 |
| 50% width | 0.5 | 0.267 | 0.0250 | 4 | 0.20 |
| 80% width | 0.5 | 0.351 | 0.0507 | 8 | 0.26 |
| 90% width | 0.5 | 0.449 | 0.0950 | 8 | 0.34 |

Observed sd across non-overlapping groups of M replicates relative to the i.i.d. prediction `s1 / sqrt(M)` (median over seat-candidates; 1.0 is exact 1/M variance scaling; M = 32 rests on two groups and is only indicative).

| Group size M | Groups | mean | crps | energy | width50 | width80 | width90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 64 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 2 | 32 | 1.02 | 1.04 | 1.00 | 1.01 | 1.00 | 0.99 |
| 4 | 16 | 1.03 | 1.03 | 0.99 | 0.98 | 1.02 | 1.00 |
| 8 | 8 | 0.98 | 1.02 | 0.91 | 1.05 | 0.98 | 0.99 |
| 16 | 4 | 0.89 | 0.98 | 1.00 | 1.08 | 1.00 | 0.84 |
| 32 | 2 | 0.58 | 0.81 | 0.59 | 0.76 | 0.81 | 0.54 |

## Gate A: the literal Stage54 national doubling (2,048 to 4,096 national draws)

Includes the difference between two national half-samples, which no layer replication can reduce; reported for comparability.

| Replicates | mean | crps | energy | width50 | width80 | width90 | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.121 (fail) | 0.165 (fail) | 0.235 (fail) | 0.463 | 0.394 | 0.853 (fail) | NATIONAL_DOUBLING_NOT_MET |
| 4 | 0.119 (fail) | 0.079 (fail) | 0.078 | 0.180 | 0.326 | 0.536 (fail) | NATIONAL_DOUBLING_NOT_MET |
| 16 | 0.121 (fail) | 0.076 (fail) | 0.049 | 0.164 | 0.314 | 0.432 | NATIONAL_DOUBLING_NOT_MET |
| 64 | 0.118 (fail) | 0.061 (fail) | 0.043 | 0.156 | 0.293 | 0.367 | NATIONAL_DOUBLING_NOT_MET |
| Cap | 0.05 | 0.05 | 0.1 | 0.5 | 0.5 | 0.5 |  |

## What the finite national bank leaves

Eight disjoint 512-draw national blocks, each pooled over all 64 replicates, give the variance that no replication removes (floor for a 4,096-draw estimate relative to the national population; 7 degrees of freedom, maxima biased high, blocks drawn without replacement from the pool so up to sqrt(7/8) below i.i.d.; reported only).

| Quantity | Cap | Floor sd max | Floor sd median | 3 sd floor / cap | Seat-candidates at zero | Negative raw variances |
| --- | --- | --- | --- | --- | --- | --- |
| simulated mean | 0.05 | 0.124 | 0.0070 | 7.45 | 6 of 80 | 6 |
| CRPS | 0.05 | 0.128 | 0.0015 | 7.67 | 5 of 80 | 5 |
| energy score | 0.1 | 0.113 | 0.0449 | 3.40 | 0 of 9 | 0 |
| 50% width | 0.5 | 0.118 | 0.0024 | 0.71 | 18 of 80 | 18 |
| 80% width | 0.5 | 0.204 | 0.0118 | 1.22 | 16 of 80 | 16 |
| 90% width | 0.5 | 0.264 | 0.0207 | 1.58 | 11 of 80 | 11 |

Total sd of a (4,096, M) bank relative to the national population (maximum over representative seat-candidates), and the median variance ratio to the one-draw baseline.

| M | mean | crps | energy | width50 | width80 | width90 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.125 / 1.00 | 0.139 / 1.00 | 0.123 / 1.00 | 0.275 / 1.00 | 0.398 / 1.00 | 0.510 / 1.00 |
| 4 | 0.124 / 0.52 | 0.131 / 0.36 | 0.116 / 0.55 | 0.169 / 0.27 | 0.261 / 0.27 | 0.336 / 0.28 |
| 16 | 0.124 / 0.40 | 0.129 / 0.21 | 0.114 / 0.44 | 0.133 / 0.08 | 0.220 / 0.09 | 0.282 / 0.09 |
| 64 | 0.124 / 0.37 | 0.128 / 0.17 | 0.114 / 0.41 | 0.122 / 0.04 | 0.208 / 0.05 | 0.269 / 0.05 |

## Seat-win probabilities

Seat-candidates with a probability in [0.05, 0.95]: 31 (13 representative, 18 panel). Layer design effect D1 0.388 (representatives 0.386, panel 0.389), national design effect Dn 0.131; Stage54 measured 0.594 for both at once with 512-draw banks. The standard error of a probability of 0.5 left by the national bank alone is 0.0028.

| Replicates M | Composed draws | SE(0.5) relative to the cached pool | SE(0.5) relative to the national population |
| --- | --- | --- | --- |
| 1 | 4,096 | 0.0049 | 0.0056 |
| 2 | 8,192 | 0.0034 | 0.0045 |
| 4 | 16,384 | 0.0024 | 0.0037 |
| 8 | 32,768 | 0.0017 | 0.0033 |
| 16 | 65,536 | 0.0012 | 0.0031 |
| 32 | 131,072 | 0.0009 | 0.0030 |
| 64 | 262,144 | 0.0006 | 0.0029 |

Replicates needed for SE(0.5) <= 0.01: 1 (pool), 1 (population); for <= 0.005: 1 (pool), 2 (population). No release threshold is set (open decision for James).

## CPU cost

Measured on the generating run (process CPU seconds): 38.0 s per replicate bank of 4,096 draws (9.28 ms per composed draw, with the exact reuse of the local-layer solves), plus 76.3 s once per seat for those solves. Stage54 used about 14 ms per composed draw without the reuse. Total CPU of the run: 7.59 hours (hardware dependent; `timing.json` is compared by structure only).

| Arm M | Composed draws per seat | CPU hours per seat | CPU hours, 71-seat slate |
| --- | --- | --- | --- |
| 4 | 16,384 | 0.06 | 4.5 |
| 16 | 65,536 | 0.19 | 13.5 |
| 64 | 262,144 | 0.70 | 49.5 |

## Reading

1. **Layer replication removes the layer noise, as Stage54 predicted.** The observed sd across groups of M replicates follows `s1 / sqrt(M)` (ratios near 1.0 up to M = 8 and at M = 16), the half-split diagnostic is EQUIVALENT, and every harness comparison with Stage54 is exact. The doubling changes fall below every frozen cap from M = 8 onward and the 3-sigma rule asks for M = 16. These caps are met relative to the cached national draws, for the control restriction and the pinned scales.
2. **The literal Stage54 national-doubling gate is still not met at any arm** (it fails for CRPS, simulated mean even at M = 64). That is the finite national bank, not simulation: the floor left by the 4,096 national draws is up to 0.13pp for CRPS and 0.12pp for the mean at the worst seat-candidate (medians 0.0015 and 0.0070), so absolute composed CRPS and mean levels cannot be called settled at 0.05pp whatever M is; replication cuts the median variance of these by roughly 2 to 6 times and that of the interval widths by 10 to 25 times.
3. **Win probabilities gain little beyond M = 4.** The layer design effect is 0.39 (Stage54: 0.594 with both sources); the national bank alone leaves SE(0.5) 0.0028, so SE(0.5) is 0.0056 at M = 1 and 0.0037 at M = 4 against a floor that M cannot lower.

## Recommendation

- If composed score, interval or mean precision matters for a later stage, use M = 16 layer replicates per national draw on the fixed 4,096 national draws (14 CPU hours for a 71-seat slate with the exact local-solve reuse, against a Stage54 estimate of about 145 CPU hours for the same caps by more draws without replication). For seat-win probabilities alone M = 4 (4.5 CPU hours) is within a floor-limited 0.0037 and M = 1 already gives SE(0.5) below 0.006.
- State absolute composed CRPS and mean levels with the national floor above, not as settled at 0.05pp. The frozen caps are unchanged and no default is changed; adopting replication in any release path needs separate authorisation, and a Stage60 change of the balance scale reruns this study unchanged with the new scales file.

## Limits

- Representatives are the Stage47/48/54 first, middle and last seats of each election, not the worst-precision seats; maxima over 80 seat-candidates of noisy sds are biased high, so the 3-sigma requirements are conservative.
- Layer replicates are independent scrambles of a 4,096-point stream; the scrambled stream beats an i.i.d. bank for smooth statistics, so the measured layer sds are specific to this construction.
- Precision is relative to the cached national draws; the national floor is an estimate from 8 blocks without replacement. No composed simulation improves the effective size of the national bank. The four cached chains disagree more than subsampling implies (Stage54), which this study does not address.
- Control restriction, the pinned Stage45 scales, the 56-day horizon; K and F, a different balance scale (Stage60), horizon, parameter uncertainty and calibration are outside this stage. Nothing is adopted.

