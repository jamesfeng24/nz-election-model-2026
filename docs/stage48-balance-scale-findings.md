# Stage48: frozen candidate-balance scale comparison, findings

Pre-registered design: [stage48-balance-scale-design.md](stage48-balance-scale-design.md), frozen before any restriction other than the corrected control was fitted or scored. Machine contract: [design-contract.json](../data/processed/balance-scale/design-contract.json). All figures are percentage points unless stated; lower scores are better.

## Finding under the frozen rule

**constant only.** No restriction is adopted: the question bears on the interval widths behind the open probability-release decision, so the choice stays with James. The development default remains the numerically corrected Stage45 Gaussian (control).

| Comparison | Delta major CRPS | Delta interval score | Delta energy | Folds improving (of 3) | Resolution (16,384 vs 32,768) | Class |
| --- | --- | --- | --- | --- | --- | --- |
| K vs C | -0.0226 | -0.2986 | -0.0277 | 3 | 0.00003 (pass) | **IMPROVES** |
| F vs K | -0.0005 | -0.0081 | -0.0006 | 3 | 0.00000 (pass) | **NEGLIGIBLE** |
| F vs C | -0.0231 | -0.3067 | -0.0283 | 3 | 0.00003 (pass) | **IMPROVES** |

Delta major CRPS is the mean over the 193 fitted-fold seats (2017/2020/2023) of the mean CRPS of that seat's National and Labour candidates, first minus second; negative favours the first. The 2014 seats are identical across restrictions by design (no earlier data) and contribute exact zeros to the 257-seat values below.

## Fitted adjustments

Each row is trained only on earlier elections with ridge sd 0.5 on a log-multiplier scale. The multiplier applies to the frozen Stage45 seat balance scale; the shared scale and all other laws are unchanged.

| Target | Trained on | Seats | K: a | K multiplier | F: a / b_R / b_T | F multiplier range | Unpenalised a (descriptive) | Bound contact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | 2014 | 64 | -0.0556 | 0.9460 | -0.0563 / -0.0045 / 0.0220 | 0.9413-0.9545 | -0.1821 | none |
| 2020 | 2014/2017 | 128 | -0.0487 | 0.9525 | -0.0498 / -0.0071 / 0.0275 | 0.9465-0.9611 | -0.1579 | none |
| 2023 | 2014/2017/2020 | 193 | -0.0726 | 0.9299 | -0.0733 / -0.0102 / 0.0191 | 0.9235-0.9418 | -0.2461 | none |

The last-but-one column is the likelihood-only maximiser of a constant, reported only to show how much the frozen penalty restrains the constant. It is not a restriction, was never scored and is not adopted. Likelihood information rank is 3 of 3 for F in the last fold (condition number 38.7), so the conditional terms are estimable from the likelihood; the penalty still dominates their size. 2014 has no earlier data, so a = b = 0 for all three.

## Scores on the 193 fitted-fold seats (32,768 draws)

| Restriction | Major (N/L) CRPS | Complete-slate CRPS | Energy | Prediction-time margin CRPS |
| --- | --- | --- | --- | --- |
| Control C | 3.4225 | 1.7125 | 6.584 | 6.0880 |
| Constant K | 3.3999 | 1.7056 | 6.557 | 6.0323 |
| Conditional F | 3.3994 | 1.7054 | 6.556 | 6.0313 |

National and Labour full-interval widths, coverage and interval scores (pooled N/L coordinates):

| Restriction | Level | N/L width | N/L covered | Coverage | Interval score | Margin width | Margin covered |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Control C | 50 | 9.87 | 240/386 | 0.622 | 15.326 | 18.20 | 122/193 |
| Control C | 80 | 18.61 | 353/386 | 0.915 | 22.605 | 34.39 | 178/193 |
| Control C | 90 | 23.73 | 369/386 | 0.956 | 28.317 | 43.90 | 186/193 |
| Constant K | 50 | 9.54 | 229/386 | 0.593 | 15.218 | 17.50 | 120/193 |
| Constant K | 80 | 18.00 | 349/386 | 0.904 | 22.254 | 33.09 | 177/193 |
| Constant K | 90 | 22.96 | 366/386 | 0.948 | 27.880 | 42.25 | 185/193 |
| Conditional F | 50 | 9.53 | 229/386 | 0.593 | 15.216 | 17.49 | 120/193 |
| Conditional F | 80 | 17.99 | 349/386 | 0.904 | 22.244 | 33.07 | 177/193 |
| Conditional F | 90 | 22.95 | 366/386 | 0.948 | 27.868 | 42.23 | 185/193 |

### By election (major CRPS)

| Election | Control C | Constant K | Conditional F | Seats |
| --- | --- | --- | --- | --- |
| 2014 | 4.3905 | 4.3905 | 4.3905 | 64 |
| 2017 | 3.5049 | 3.4776 | 3.4771 | 64 |
| 2020 | 3.7292 | 3.7196 | 3.7193 | 65 |
| 2023 | 3.0285 | 2.9974 | 2.9968 | 64 |

Equal-election mean over the three fitted elections: Control C 3.4209, Constant K 3.3982, Conditional F 3.3977. All 257 seats: Control C 3.6635, Constant K 3.6466, Conditional F 3.6462.

## Composed 56-day supporting check (193 seats, 512 draws)

Supporting only. Stage47 recorded that composed simulation precision gates are unmet for the control; no fine superiority claim is made.

| Comparison | Delta major CRPS | Delta interval score | Delta energy | Folds improving | Sign vs conditional bank |
| --- | --- | --- | --- | --- | --- |
| K vs C | -0.0171 | -0.1692 | -0.0198 | 2 | agrees or below flag size |
| F vs K | -0.0003 | -0.0061 | -0.0004 | 3 | agrees or below flag size |
| F vs C | -0.0174 | -0.1753 | -0.0202 | 2 |  |

## Numerical checks

| Restriction | Component 8,192 to 16,384 to 32,768 gates (representative seats) | Composed 256 to 512 to 1,024 gates |
| --- | --- | --- |
| Control C | pass | FAIL |
| Constant K | pass | FAIL |
| Conditional F | pass | FAIL |

Last component doubling, maximum change over representative seats and candidates (gates 0.05 mean/CRPS, 0.1 energy, 0.5 widths):

| Restriction | mean | crps | energy | width50 | width80 | width90 |
| --- | --- | --- | --- | --- | --- | --- |
| Control C | 0.0140 | 0.0076 | 0.0330 | 0.0777 | 0.0764 | 0.1658 |
| Constant K | 0.0140 | 0.0076 | 0.0307 | 0.0777 | 0.0830 | 0.1467 |
| Conditional F | 0.0140 | 0.0076 | 0.0307 | 0.0777 | 0.0828 | 0.1453 |

Last composed doubling:

| Restriction | mean | crps | energy | width50 | width80 | width90 |
| --- | --- | --- | --- | --- | --- | --- |
| Control C | 0.5609 | 0.2325 | 0.2117 | 1.4471 | 2.1646 | 2.2554 |
| Constant K | 0.5609 | 0.2451 | 0.2139 | 1.4471 | 2.1646 | 2.2554 |
| Conditional F | 0.5609 | 0.2455 | 0.2139 | 1.4471 | 2.1646 | 2.2554 |

Independent checks (all passed): the control equals Stage47's sealed corrected bank seat by seat (maximum CRPS difference 0.00e+00 component, 0.00e+00 composed); non-balance draws and the National+Labour mass are identical across restrictions (maximum gap 2.22e-16); composed remainder reuse equals full re-inversion (maximum 2.22e-16); conditional-mean gap of every location 6.89e-12pp against the 0.05pp gate; maximum finite-bank mean deviation 0.0088pp.

## Reading the result

**What the frozen test shows.** The earlier-trained constant (K) beats the corrected control on every pre-registered criterion: major CRPS falls 0.0226pp (0.66%), mean N/L interval score 1.35% lower, complete-vector energy lower, and all three elections improve (the 2020 fold is the smallest, 0.0095pp). N/L full interval widths narrow by about 3.3% and coverage moves toward nominal at every level (50/80/90: 0.622/0.915/0.956 to 0.593/0.904/0.948). So the candidate balance scale is mildly too conservative on these elections, in the direction the Stage47 attribution suggested.

**What it does not show.** The strongly pooled conditional adjustment (F) adds 0.0005pp over K, far below the 0.01pp threshold and with multipliers spread over only about 1 to 2%, so supported R deficit and historical non-major support do not identify predictable heteroskedasticity here. Under the frozen penalty the conditional terms had little room (|b| at most 0.028), so this is "no support under this design", not proof that none exists.

**The penalty limits the size, not only the direction.** The frozen ridge keeps K within 5 to 7% of the frozen scale (multipliers 0.946, 0.953, 0.930). The likelihood alone prefers a constant of -0.182, -0.158, -0.246 (multipliers about 0.83, 0.85, 0.78), about three times larger. Stage48 did not score that and the frozen design forbids a prior-strength search, so how much of the remaining over-coverage (N/L 50% coverage is still 0.593 against 0.5) a weaker penalty would remove is unmeasured. The size of the scale change, the quantity that matters for the open wide-interval question, is not settled by this stage.

## Limits

- Three fitted folds from reused development elections, chronologically fitted after the fact. This is not untouched validation, and fold-level consistency is the only replication available.
- 2014 has no earlier data and is prior/control for all three restrictions; the 2014 balance miss (control N/L 50% coverage 0.367 that year) is not addressed.
- Composed 56-day simulation precision gates are unmet for every restriction (as for the Stage47 control), so the composed check is supporting direction only. The composed K-versus-C difference is the same sign pooled and in 2020/2023, with 2017 flat (slightly positive).
- Parameter and scale uncertainty remain omitted; the multipliers are point values. The 56-day horizon differs from the roughly 32-day horizon at publication; not measured here.
- Seat-win and winner probabilities were not evaluated, and nothing here is a calibrated probability claim.

## Recommendation for James (not adopted)

1. **Record the finding; change nothing operational.** Retain the corrected control as the development default. K is a defensible, simple, earlier-trained candidate (about 0.7% lower N/L CRPS, about 3% narrower N/L intervals), but the gain is small, N/L 50% coverage stays near 0.59, and adopting it is a choice about the width question James keeps open.
2. **Close the conditional line.** Do not pursue R-deficit or non-major-support heteroskedasticity further on these data; the frozen test found no signal.
3. **If narrower balance intervals matter, authorise a separate, separately frozen question** on the size of the global constant (for example a single unpenalised or weakly penalised constant against K and the control, with the same scores and a pre-registered rule). The descriptive likelihood suggests a larger effect than K captures, but with three reused folds it should be tested, not assumed, and it would still leave the horizon and composed-precision limits.

