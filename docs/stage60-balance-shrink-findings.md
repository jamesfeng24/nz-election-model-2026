# Stage60: stronger candidate-balance scale test, findings

Pre-registered design: [stage60-balance-shrink-design.md](stage60-balance-shrink-design.md), frozen (commit `30beda3`) before any Stage60 arm was simulated or scored. Machine contract: [design-contract.json](../data/processed/balance-shrink/design-contract.json). All figures are percentage points unless stated; lower scores are better. Decision seats are the 193 general-electorate seats of 2017, 2020 and 2023; 2014 is reported separately. Māori electorates are excluded by electorate type (none are in the candidate inventory).

## Finding under the frozen rule

**recommend_free_for_james_signoff.** The recommended arm is **free (earlier-trained, penalty-free)**, fitted on earlier elections only (leave-future-out). This is a recommendation only: the corrected control remains the default until James signs off, and nothing is adopted.

Each arm against the control on the 193 decision seats. Delta major CRPS is the mean over seats of the mean CRPS of that seat's National and Labour candidates, arm minus control (negative favours the arm).

| Arm | Delta major CRPS | Relative | Delta interval score | Delta energy | Elections improving | Resolution gap (16,384 vs 32,768) | Stage48 class | Coverage floor | Qualifies |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grid 0.95 | -0.0192 | -0.56% | -0.257 | -0.024 | 3/3 | 0.00002 | IMPROVES | pass | yes |
| grid 0.90 | -0.0365 | -1.07% | -0.481 | -0.046 | 3/3 | 0.00004 | IMPROVES | pass | yes |
| grid 0.85 | -0.0517 | -1.51% | -0.685 | -0.065 | 3/3 | 0.00005 | IMPROVES | pass | yes |
| grid 0.80 | -0.0648 | -1.89% | -0.853 | -0.082 | 3/3 | 0.00005 | IMPROVES | FAIL | no |
| free (earlier-trained, penalty-free) | -0.0616 | -1.80% | -0.811 | -0.076 | 3/3 | 0.00006 | IMPROVES | pass | yes |
| Stage48 K (reference) | -0.0226 | -0.66% | -0.299 | -0.028 | 3/3 | 0.00003 | IMPROVES | pass | reference |

Among the qualifying arms the lowest pooled CRPS is **free (earlier-trained, penalty-free)**. Paired seat bootstrap (2,000 draws, seed 60) of each qualifier minus the best:

| Arm | 90% interval of CRPS(arm) minus CRPS(best) | Within noise of the best |
| --- | --- | --- |
| free (earlier-trained, penalty-free) | 0.0000 to 0.0000 | yes |
| grid 0.85 | 0.0075 to 0.0121 | no |
| grid 0.90 | 0.0196 to 0.0302 | no |
| grid 0.95 | 0.0331 to 0.0509 | no |

The least aggressive qualifying arm within noise of the best is **free (earlier-trained, penalty-free)**. The descriptive alternative (least aggressive qualifier within 0.01pp of the best pooled CRPS) is grid 0.85.

## Multipliers

The multiplier applies to the frozen Stage45 seat balance scale only. The free arm is trained on earlier elections only with the ridge removed; its 2014 value is 1 (no earlier data).

| Target | Free arm trained on | Free multiplier | Stage48 K multiplier | Free log multiplier a | Bound contact |
| --- | --- | --- | --- | --- | --- |
| 2014 | none | 1.0000 | 1.0000 | 0 | none |
| 2017 | 2014 | 0.8336 | 0.9460 | -0.1821 | none |
| 2020 | 2014/2017 | 0.8540 | 0.9525 | -0.1579 | none |
| 2023 | 2014/2017/2020 | 0.7818 | 0.9299 | -0.2461 | none |

Descriptive 2026 refit (all four elections, never scored): log multiplier -0.2355, multiplier **0.7901**. This is the value the free arm would take for the 2026 forecast.

## Scores

### Pooled on the 193 decision seats (32,768 draws)

| Arm | Major CRPS | Energy | Width 50 | Width 80 | Width 90 | Coverage 50 | Coverage 80 | Coverage 90 | IS 50 | IS 80 | IS 90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control (1.00) | 3.4225 | 6.584 | 9.87 | 18.61 | 23.73 | 0.622 | 0.915 | 0.956 | 15.33 | 22.61 | 28.32 |
| grid 0.95 | 3.4032 | 6.560 | 9.58 | 18.07 | 23.05 | 0.596 | 0.904 | 0.951 | 15.23 | 22.30 | 27.94 |
| grid 0.90 | 3.3860 | 6.539 | 9.29 | 17.53 | 22.37 | 0.573 | 0.891 | 0.946 | 15.17 | 22.04 | 27.60 |
| grid 0.85 | 3.3708 | 6.520 | 9.01 | 17.01 | 21.71 | 0.557 | 0.878 | 0.943 | 15.11 | 21.81 | 27.28 |
| grid 0.80 | 3.3577 | 6.503 | 8.73 | 16.49 | 21.06 | 0.544 | 0.870 | 0.938 | 15.06 | 21.61 | 27.02 |
| free (earlier-trained, penalty-free) | 3.3609 | 6.508 | 8.87 | 16.76 | 21.40 | 0.557 | 0.878 | 0.938 | 15.06 | 21.67 | 27.09 |
| Stage48 K (reference) | 3.3999 | 6.557 | 9.54 | 18.00 | 22.96 | 0.593 | 0.904 | 0.948 | 15.22 | 22.25 | 27.88 |

### Major CRPS by election

| Arm | 2014 | 2017 | 2020 | 2023 | Equal-election mean (2017-2023) |
| --- | --- | --- | --- | --- | --- |
| control (1.00) | 4.3905 | 3.5049 | 3.7292 | 3.0285 | 3.4209 |
| grid 0.95 | 4.3891 | 3.4796 | 3.7192 | 3.0060 | 3.4016 |
| grid 0.90 | 4.3905 | 3.4565 | 3.7115 | 2.9850 | 3.3843 |
| grid 0.85 | 4.3948 | 3.4356 | 3.7061 | 2.9655 | 3.3691 |
| grid 0.80 | 4.4020 | 3.4171 | 3.7029 | 2.9477 | 3.3559 |
| free (earlier-trained, penalty-free) | 4.3905 | 3.4292 | 3.7064 | 2.9417 | 3.3591 |
| Stage48 K (reference) | 4.3905 | 3.4776 | 3.7196 | 2.9974 | 3.3982 |

### Coverage by election (pooled N/L coordinates), with the coverage floor

Floor at each election and level: min(nominal - 0.10, control coverage - 0.05). A cell below its floor is marked `*`.

| Arm | 2014 @50 | 2014 @80 | 2017 @50 | 2017 @80 | 2020 @50 | 2020 @80 | 2023 @50 | 2023 @80 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control (1.00) | 0.367 | 0.812 | 0.680 | 0.906 | 0.508 | 0.892 | 0.680 | 0.945 |
| grid 0.95 | 0.352 | 0.781 | 0.641 | 0.898 | 0.477 | 0.877 | 0.672 | 0.938 |
| grid 0.90 | 0.352 | 0.758 | 0.609 | 0.883 | 0.454 | 0.862 | 0.656 | 0.930 |
| grid 0.85 | 0.352 | 0.734 | 0.602 | 0.875 | 0.431 | 0.838 | 0.641 | 0.922 |
| grid 0.80 | 0.344 | 0.688* | 0.586 | 0.875 | 0.415 | 0.823 | 0.633 | 0.914 |
| free (earlier-trained, penalty-free) | 0.367 | 0.812 | 0.602 | 0.875 | 0.438 | 0.846 | 0.633 | 0.914 |
| Stage48 K (reference) | 0.367 | 0.812 | 0.641 | 0.898 | 0.477 | 0.885 | 0.664 | 0.930 |
| floor | 0.317 | 0.700 | 0.400 | 0.700 | 0.400 | 0.700 | 0.400 | 0.700 |

### Widths by election (N/L, 90% interval)

| Arm | 2014 | 2017 | 2020 | 2023 |
| --- | --- | --- | --- | --- |
| control (1.00) | 22.64 | 24.75 | 23.56 | 22.88 |
| grid 0.95 | 21.91 | 23.97 | 22.88 | 22.29 |
| grid 0.90 | 21.19 | 23.20 | 22.20 | 21.71 |
| grid 0.85 | 20.49 | 22.43 | 21.54 | 21.15 |
| grid 0.80 | 19.79 | 21.69 | 20.89 | 20.60 |
| free (earlier-trained, penalty-free) | 22.64 | 22.19 | 21.59 | 20.40 |
| Stage48 K (reference) | 22.64 | 23.91 | 22.91 | 22.06 |

## 2014, explicitly

2014 has no earlier election, so the free arm and Stage48 K equal the control there. The control already under-covers at 50% (0.367) while covering 80% and 90% at about nominal (0.812, 0.898). The fixed grid arms are not trained on anything, so they can be scored there; shrinking does not help 2014:

| Arm | Major CRPS | Coverage 50 | Coverage 80 | Coverage 90 | Width 90 |
| --- | --- | --- | --- | --- | --- |
| control (1.00) | 4.3905 | 0.367 | 0.812 | 0.898 | 22.64 |
| grid 0.95 | 4.3891 | 0.352 | 0.781 | 0.891 | 21.91 |
| grid 0.90 | 4.3905 | 0.352 | 0.758 | 0.883 | 21.19 |
| grid 0.85 | 4.3948 | 0.352 | 0.734 | 0.867 | 20.49 |
| grid 0.80 | 4.4020 | 0.344 | 0.688 | 0.859 | 19.79 |
| free (earlier-trained, penalty-free) | 4.3905 | 0.367 | 0.812 | 0.898 | 22.64 |
| Stage48 K (reference) | 4.3905 | 0.367 | 0.812 | 0.898 | 22.64 |

The coverage floor blocks grid 0.80 on the 2014 80% level; its pooled score is otherwise competitive, so this floor is the binding constraint on how far the fixed grid could go.

## Composed-width implication (arithmetic, no new bank)

Approximate National and Labour composed 90% interval widths from the Stage47 nine-seat ablation (full 29.89pp National; no candidate balance 20.84pp). "Seat only" scales only the seat part of the balance variance, which is what the arms change; "all balance" scales the whole balance variance and is an upper bound on the effect. The free arm row uses each ablation seat's own fold multiplier; the 2026 refit row applies the refit multiplier to every seat.

| Arm | National 90 seat only | Change | National 90 all balance | Change | Labour 90 seat only | Change |
| --- | --- | --- | --- | --- | --- | --- |
| control (1.00) | 29.89 | 0.0% | 29.89 | 0.0% | 31.01 | 0.0% |
| grid 0.95 | 29.32 | -1.9% | 29.14 | -2.5% | 30.50 | -1.7% |
| grid 0.90 | 28.78 | -3.7% | 28.41 | -5.0% | 30.00 | -3.3% |
| grid 0.85 | 28.25 | -5.5% | 27.70 | -7.3% | 29.52 | -4.8% |
| grid 0.80 | 27.74 | -7.2% | 27.01 | -9.6% | 29.05 | -6.3% |
| free (earlier-trained, penalty-free) | 28.02 | -6.3% | 27.37 | -8.4% | 29.28 | -5.6% |
| Stage48 K (reference) | 29.26 | -2.1% | 29.05 | -2.8% | 30.43 | -1.9% |
| free, 2026 refit (descriptive) | 27.65 | -7.5% | 26.88 | -10.1% | 28.97 | -6.6% |

Sanity check: the same arithmetic with Stage48 K's multipliers predicts a National composed 90% width change of -2.1% (seat only) to -2.8% (all balance); the Stage48 composed bank (193 seats, 512 draws, precision gates unmet) shows -1.9% (30.06 to 29.48pp). The arithmetic is consistent in size and slightly overstates; treat the table as a rough guide, not a composed result.

## Numerical and independent checks

| Arm | Doubling gates (8,192 to 16,384 to 32,768, representative seats) | mean | crps | energy | width50 | width80 | width90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| control (1.00) | pass | 0.0140 | 0.0076 | 0.0330 | 0.0777 | 0.0764 | 0.1658 |
| grid 0.95 | pass | 0.0140 | 0.0076 | 0.0309 | 0.0777 | 0.0764 | 0.1490 |
| grid 0.90 | pass | 0.0140 | 0.0076 | 0.0288 | 0.0777 | 0.0764 | 0.1523 |
| grid 0.85 | pass | 0.0140 | 0.0076 | 0.0268 | 0.0777 | 0.0764 | 0.1466 |
| grid 0.80 | pass | 0.0140 | 0.0076 | 0.0249 | 0.0777 | 0.0830 | 0.1137 |
| free (earlier-trained, penalty-free) | pass | 0.0140 | 0.0076 | 0.0262 | 0.0777 | 0.0764 | 0.1137 |
| Stage48 K (reference) | pass | 0.0140 | 0.0076 | 0.0307 | 0.0777 | 0.0830 | 0.1467 |

Independent checks (all passed): the control equals Stage48's control and the reference arm equals Stage48's K seat by seat on all 257 seats (maximum CRPS difference 0.0e+00 and 0.0e+00, identical coverage indicators); the free arm reproduces Stage48's descriptive unpenalised constant; non-balance draws and the National+Labour mass are identical across arms (maximum gap 2.2e-16); conditional-mean gap of every location 6.9e-12pp against the 0.05pp gate; pairwise-formula CRPS agrees with the vectorised score to 3.6e-15pp; plain-loop pooled differences agree to 5.5e-16; the 2014 free and reference arms are exactly the control; all 257 scored records are general electorates (none excluded, none Māori).

## Reading the result

**What the frozen test shows.** A stronger global shrink of the candidate-balance seat scale than Stage48's penalised K is supported. The recommended arm (free (earlier-trained, penalty-free)) lowers pooled N/L CRPS by 0.0616pp (1.80%, 2.7 times Stage48 K's gain), improves all three elections (0.0757, 0.0227, 0.0869pp for 2017, 2020, 2023), lowers the mean N/L interval score by 0.81 and complete-vector energy by 0.076, and narrows the N/L candidate intervals (50/80/90 widths 9.87/18.61/23.73 to 8.87/16.76/21.40) with pooled coverage still at or above nominal (0.557/0.878/0.938 against 0.622/0.915/0.956). The gain is concentrated in 2017 and 2023; 2020 improves least (0.0227pp). The fitted multipliers are stable across folds (0.834, 0.854, 0.782) and the all-election refit is 0.790.

**The fitted and fixed arms agree.** Every qualifying arm improves every pooled criterion and the fixed grid is monotone: more shrink lowers pooled CRPS all the way to 0.80, which only the 2014 coverage floor stops. The free arm, the only one not set after seeing the likelihood-preferred size, lands in the same place as the fixed grid (0.78 to 0.85), so the leave-future-out fit and the grid agree rather than conflict.

**Where the limit is.** The shrink does not help 2014 (no arm can: the free arm has no earlier data, and the fixed grid worsens 2014 coverage at 80%), and in 2020 the free arm leaves 50% coverage at 0.438, below nominal. Pooled 80% coverage (0.878) and 90% (0.938) are still above nominal, and the grid already shows the cost of cutting further (grid 0.80 takes 2014 80% coverage to 0.688 and 2020 50% coverage to 0.415); reading, not a tested claim: what remains is a distribution-shape question (Student-t was tested and rejected in Stage46), not one a smaller scale answers.

## Limits

- Three fitted folds from reused development elections, chronologically fitted after the fact; this is not untouched validation. The fixed grid values were chosen after Stage48 had reported the likelihood-preferred size, so grid scores are development-informed; the free arm is the only chronologically blind arm, and the 2026 result will be the first genuine out-of-sample test.
- 2014 has no earlier data and is control for the free arm; the 2014 balance miss is not addressed and is made no better by any fixed shrink.
- Composed 56-day precision gates remain unmet; the composed widths are arithmetic from nine ablation seats, not a bank. The 56-day horizon differs from the roughly 32-day horizon at publication; not measured here.
- Parameter and scale uncertainty remain omitted; the multiplier is a point value. Only the seat balance scale moves: the shared election scale, local-party layer and national uncertainty are unchanged, so the composed 90% intervals stay wide (about 27 to 28pp National).
- Seat-win and winner probabilities were not evaluated; nothing here is a calibrated-probability claim.

## Recommendation for James (not adopted)

1. **Sign-off decision.** Adopt, for the automatic output, the earlier-trained penalty-free constant, with the 2026 value set by the all-election refit (0.790 on the seat balance scale), or keep the corrected control. The scores favour adoption on every pre-registered criterion; the cost is that the default changes, which James keeps open. The stage does not flip it.
2. **Treat the size as near its limit.** The coverage floor and 2014/2020 coverage argue against going below about 0.80; no further balance-scale test is needed on these data.
3. **Width implication.** This narrows the N/L candidate intervals by 10% and, by arithmetic, the composed National 90% width by 6% to 8% (28.0 to 27.4pp from 29.9pp); the 2026 refit multiplier gives 8% to 10%. Bigger gains need other layers (Stage61) or the live poll fit.

