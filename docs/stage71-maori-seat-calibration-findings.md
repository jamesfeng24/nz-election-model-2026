# Stage71 findings: calibrating the Māori seat layer (internal, nothing adopted)

Design: [stage71-maori-seat-calibration-design.md](stage71-maori-seat-calibration-design.md), frozen before any corrected arm was scored (one clarification, made before any score was displayed, is recorded in it). Reproduce with `python3 -m scripts.maori_seat_calibration.run` (add `--check` to verify; about 12 seconds, no network). Stage66's code, data and outputs are unchanged; the control arm reproduces its stored leave-one-election-out backtest to 1e-16 and its 2026 forecast exactly.

## Finding (frozen rule): `improves_not_restored`

A single variance inflation fitted only on earlier elections improves every pre-registered score over Stage66 but leaves the layer overconfident about poll leaders. Chronological scheme, 21 held-out polls (2017, 2020, 2023):

| Arm | Predicted leader win | Observed | Calibration z | Brier (leader) | Log score of winner | Closed-share coverage 50 / 80 / 90% |
|---|---|---|---|---|---|---|
| C: Stage66 | 0.826 | 13 of 21 (0.619) | -2.65 | 0.223 | -0.602 | 0.36 / 0.72 / 0.81 |
| P: inflation | 0.765 | 0.619 | -1.66 | 0.195 | -0.551 | 0.47 / 0.88 / 0.95 |
| PB: inflation plus Curia-era bias | 0.714 | 0.619 | -1.08 | 0.149 | -0.449 | 0.53 / 0.90 / 0.95 |

P against C: Brier -0.028 (paired poll bootstrap 90% [-0.054, -0.005]), log score +0.050 ([-0.009, +0.117]), Brier better in all three folds, coverage guard met. The only `restored` condition missed is the calibration z: -1.66 against the pre-registered limit of 1.645 (14-poll 2020 plus 2023 subset: -1.71). The overconfidence shrinks from 0.21 to 0.15 (predicted minus observed leader-win rate), it does not close. The poll bootstrap ignores that polls in an election share a shift, so those intervals are too narrow. Both robustness repeats (2020 plus 2023 only; leave-one-election-out, 25 polls: control 0.815 against 0.600, P 0.716, Brier 0.208 to 0.184, coverage guard missed there) give the same class.

**Where the gain comes from.** Almost all of it is the 2023 fold (Brier 0.373 to 0.297, predicted 0.753 to 0.659, 2 of 7 leaders won); 2017 (0.184 to 0.180) and 2020 (0.113 to 0.107) barely move. The multiplier is learned from the Curia-era misses: fitted `lambda` 0.94 on 2014 alone (4 polls), 1.68 on 2014 and 2017, 2.82 on 2014 to 2020, 3.03 on all four elections (leave-one-election-out 2.24 to 4.05). A correction that is learned from the same event it then repairs is the only evidence there is, which is why the bootstrap interval is wide.

## The correction and its own uncertainty

`lambda_hat` (variance multiplier on sigma^2 and tau^2; error scale `kappa = sqrt(lambda)`, so about 1.74 on all four elections) is 3.03 with a two-stage bootstrap 90% interval of **1.72 to 7.02** (1,000 replicates, none skipped). The interval excludes 1 for the 2023 fold (1.26 to 7.9) but not for 2017 or 2020 (0.65 to 9.2; 0.89 to 5.4), so the rule's `insufficient_data` test (no informative fold excludes 1) does not fire, narrowly. Every probability below carries this uncertainty: each draw uses a `lambda_hat` from the bootstrap replicates.

**The single factor is a compromise.** The multiplier is estimated from every named candidate, so it is driven by the minor candidates (Green, National, Mana, independents) whose errors Stage66 already flagged as 4.0 times what the contrast fit allows. It over-widens the Māori Party-versus-Labour contest, which is the whole race in two-way seats: the 80 and 90% intervals of that contrast cover 20 of 20 chronological polls under P (0.35 / 0.80 / 0.95 under C). A structure-specific noise model (separate scale for minor candidates) would address that, but it is on this stage's do-not list, so it is not tested here.

## Era-bias arm PB (reported, capped)

PB scores best (Brier 0.149, z -1.08, calibration closest to nominal), but only two same-pollster transitions exist chronologically and the one that matters is 2020 to 2023 (bias 0.34 predicts 2023's 0.45); the 2014 to 2017 transition has a bias near zero (-0.07). The pre-registered cap applies: `suggestive_not_adopted` (testable folds 2017 and 2023, neither worse than P). It rests on one Curia transition and on the assumption that the shift persists into 2026 (the 2026 polls share Curia's method); the 2026 bias used is +0.39 (mean of the 2020 and 2023 election means).

## 2026 readout: three polled seats (100,000 draws, Stage66 seed; unchanged polls)

Win probability of the poll leader; the unnamed remainder is not scored.

| Seat (leader) | C (Stage66) | P (inflation) | P, lambda fixed at 5th / 95th percentile | PB |
|---|---|---|---|---|
| Hauraki-Waikato (Maipi-Clarke, TPM) | 0.881 | 0.741 | 0.818 / 0.675 | 0.919 |
| Te Tai Hauāuru (Ngarewa-Packer, TPM) | 0.775 | 0.655 | 0.718 / 0.598 | 0.867 |
| Te Tai Tonga (Ramsden, LAB) | 0.853 | 0.616 | 0.751 / 0.499 | 0.531 |

- Inflation lowers every leader's probability by 0.12 to 0.24 (Te Tai Tonga most) and widens the 90% share interval from about 0.35 to 0.62 in the two-way and three-way seats and from 0.23 to 0.43 in Te Tai Tonga. At the fitted `lambda` held fixed the changes are -0.13, -0.11 and -0.21; across the interval of the correction itself the leader probabilities span 0.68 to 0.82, 0.60 to 0.72 and 0.50 to 0.75. All three shifts exceed the 0.10 flag.
- Māori Party wins among the three polled seats: mean 1.76 (C, distribution 0.06 / 0.21 / 0.63 / 0.10 for 0 to 3 wins), 1.61 (P, 0.15 / 0.27 / 0.41 / 0.17), 2.11 (PB, 0.01 / 0.13 / 0.60 / 0.26).
- Te Tai Tonga is the most sensitive seat in every arm. The era bias moves it the other way (Labour 0.53, Murch 0.33), because the +0.39 shift lifts the Māori Party candidate, while raising the other two seats.
- The four unpolled seats stay `unpolled` with no values.

## Limits

25 polls, 24 contrasts, four elections, two pollsters in two eras; the fold-trained corrections for 2017 rest on one election (four polls). The scoring set is the one the correction was designed against (the Stage66 backtest result was known); only the earlier-elections-only fitting and the frozen rule guard against leakage, and with two Curia elections no result here is a pristine out-of-sample test. The poll-level bootstrap treats polls as independent. Calibration is of the leader-win probability on 21 to 25 polls, so an observed rate has about ±0.1 of sampling noise. The 2026 polls are 37 to 44 days before the election, longer than nearly all historical ones; no horizon term is added. A fresh fit on later polls was not attempted. No calibrated-probability claim is made for 2026.

## Not done

No adoption (the corrected layer is not the default and no probability is released), no per-candidate-type noise, no covariates, no use of general-seat data or party-vote figures, no change to Stage66, the national model or the MMP allocator, no new source, no CI registry edit, no later stage, no new Whakatau polls.

## Recommendation for James (not a decision of this stage)

Inflation P is better than the control on every pre-registered score and in every chronological fold, so quoting Stage66's 0.88 / 0.78 / 0.85 for leaders is the weaker default; if any Māori-seat probability is shown before more polls arrive, P's range (leader probabilities of roughly 0.6 to 0.75, Te Tai Tonga about 0.5 to 0.75) is the more honest one. It is not a finished calibration: leaders are still over-predicted, and the single factor over-widens the Māori Party-versus-Labour contest. The era question (PB) is a judgement about whether the Curia-era Māori Party over-performance persists, which these data cannot settle. Two bounded follow-ups, neither started: a structure-specific noise test for minor candidates (the likely source of the inflation), and re-running this frozen design when more 2026 Whakatau polls give a second estimate of the Curia-era shift.
