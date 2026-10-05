# Stage46 development assessment — 6 October 2026

## Decision

**Retain the Stage45 Gaussian implementation as the development default; do not adopt the Student-t correction.** Preserve the matched robust-scale Gaussian as an informative diagnostic. Its candidate major-party results favour modest central-scale shrinkage, but its complete composed scores are effectively unchanged and its new conditional remainder integration fails the frozen mean-preservation tolerance. This is a forecasting judgment using magnitude, proper scores and numerical reliability, not a significance requirement or an automatic all-fold screen. No operational selection changes.

The residual audit supports a concentrated candidate National/Labour centre with some large seat departures, qualified by residual-availability/geography heterogeneity and substantial shared election movements. It does **not** establish a universal heavy-tail mechanism. The particular frozen nu=4 correction is not supported by these predictive diagnostics. Neither manual judgment nor the possibility of future dated overrides justifies removing any observation; all257 seats remain.

## What changed, and what did not

Earlier-election seat MAD about the median is pooled with three fixed prior environments. Shared effects remain Stage45 Gaussian estimates; no median bias correction is fitted. Gaussian SD, Student central scale and Student implied SD are distinct:

| Holdout | Gaussian SD | Student scale | Student implied SD | Earlier candidate residual elections |
|---|---:|---:|---:|---|
| 2014 | .3500 | .3187 | .4507 | none: prior only |
| 2017 | .3254 | .2963 | .4191 | 2014 |
| 2020 | .3042 | .2770 | .3917 | 2014, 2017 |
| 2023 | .2837 | .2583 | .3653 | 2014, 2017, 2020 |

Units are raw log National/Labour ratio. Nu=4 is assumed, not estimated; SD=scale×sqrt(2). The Student/Gaussian comparison matches central MAD, not variance. Major/remainder mass, within-remainder distributions, shared effects, national draws, zero semantics, coefficients, preprocessing and continuous mean transport are unchanged. Gaussian/Student local-party and candidate mass/remainder arrays are identical. The extra tails do not automatically narrow central intervals.

## Proper-score evidence

See [complete deterministic tables](stage46-uncertainty-findings.md) and `data/processed/uncertainty-tails/evaluation.json` for all twelve cases,50/80/90 counts/widths/interval scores, energy, margins, group bias, expected shares and substantial misses. Lower scores are better. Reused elections and correlated options are not independent calibration replications.

| Candidate conditional case | Stage45 CRPS | Robust Gaussian | Student |
|---|---:|---:|---:|
| 2014 | 2.0048 | 2.0054 | 2.0278 |
| 2017 | 1.8363 | 1.8321 | 1.8557 |
| 2020 | 1.4720 | 1.4694 | 1.4819 |
| 2023 | 1.8331 | 1.8208 | 1.8407 |
| Contest-weighted pooled | 1.7853 | 1.7807 | 1.8003 |

| Cached-gauss composition | Stage45 CRPS | Robust Gaussian | Student |
|---|---:|---:|---:|
| 2017 | 2.5109 | 2.5162 | 2.5320 |
| 2020 | 1.5838 | 1.5819 | 1.6041 |
| 2023 | 2.3053 | 2.3032 | 2.3189 |
| Contest-weighted pooled | 2.1305 | 2.1309 | 2.1488 |

Student has higher CRPS and complete-vector energy than matched Gaussian in all seven candidate/composed cases. Pooled conditional candidate50/80/90 widths are4.603/9.041/11.979pp versus Gaussian4.514/8.678/11.250. Coverage is1177/1697/1801 of1902 versus1170/1687/1791. Greater tail coverage comes with worse pooled proper interval scores at all three levels (8.017/12.272/16.182 versus7.944/12.082/15.827). There is no sharper-centre benefit in this frozen experiment. Composed widths similarly increase;2017 composed90 interval score improves slightly, so the result is not an assertion that every metric worsens everywhere.

Major-party counts are514 conditional and386 composed candidate observations. Their pooled CRPS is3.6635/3.6473/3.7123 (Stage45/Gaussian/Student) conditional, and4.3745/4.3523/4.4163 composed. Gaussian major50/80/90 widths9.500/17.925/22.860pp become9.814/19.170/25.332 under Student. All smaller-option predictions are unchanged between these matched methods; their errors are retained. Thus the tail-law comparison is not driven by changes in minor-option integration. Whole-slate averages must not be mistaken for typical major-party interval widths.

The Gaussian-versus-Stage45 comparison also changes numerical conditional remainder location treatment. Its tiny whole-slate gains are not solely attributable to robust scale estimation. For conditional major predictions, remainder offsets do not affect the major mass or balance, making those group results a cleaner central-scale diagnostic. No new model is fitted to exploit this distinction.

## Numerical findings and expected shares

The original Stage458000 cap failure remains unchanged. Its Stage46 higher-precision companion uses exactly its original equations/scales. All771 control expectations agree with the completed pre-covariance checkpoint, and all75,792,384 simulated simplex vectors pass conservation. Independent arithmetic verifies four scale folds and108 representative score records within the frozen1e-10 arithmetic tolerance; this is not Monte Carlo accuracy or statistical certainty.

The frozen8192→16384→32768 sequence passes **representative** last-doubling gates: maxima .0281pp mean,.0395pp CRPS,.1417/.2448/.2673pp50/80/90 width and.0384pp energy. This covers first/middle/last canonical seats in each case, not full-frame draw-doubling. Full-frame energy pair-estimate difference is at most.0909pp. Tiny Gaussian/Stage45 differences should not be treated as precise superiority.

The separate conditional integration gate **fails**: maximum historical check.73893pp versus.05pp. These checks cover every component vector and first/middle/last national/local inputs within each composed seat, not every conditional input. Independent synthetic repeated/unique-label contrast Gauss-Hermite41/81 integration differs by at most1.6e-13pp while showing up to.14146pp error from the64-node location. Student binary quadrature is considerably better: independent adaptive integration with shared GH41 nodes gives at most.001622pp gap, with reported numerical reference errors below1e-11 shares.

Within-remainder conditional approximation creates component arithmetic-mean shifts up to.2012pp local and.5585pp candidate; the largest component National/Labour shift is.0113pp. Combined local-to-candidate nonlinearity plus approximation shifts an individual expected share by up to1.8361pp (Stage45 companion1.4770). Gaussian/Student share these remainder shifts. These are not outcome-fitted bias corrections. Convergence of a finite simulation bank does not fix a low-node conditional expectation error. Preserve the frozen cap/tolerance failure; no higher node count or altered gate was selected after scores.

The dependence correction is numerical: `within_factor/within_nodes`, `conditional_offsets/inverse/check` now use shared ballot-label plus individual-seat covariance, matching `streams.noise`. Same-label contrasts cancel shared noise; distinct-label contrasts retain it. It changes offsets, draws and expectations in the two new methods, not merely validation. The original failed Sobol endpoint attempt and completed unscored pre-covariance banks are retained; no superseded bank is reused for scoring. Digital-cell midpoints and independently checked array reuse are preserved. No full comparative evaluation preceded the corrected seal `a036d4a`. Outcome-based CRPS/energy precision monitors did precede it under the frozen numerical plan; their superseded values remain in pre-covariance-convergence.json. They did not choose scales, nu or the covariance correction.

## Substantial misses and limits

Tāmaki2023 remains included. In the conditional candidate case the observed winner has0/32768 wins for all three distributions; its43.65% observed share lies well outside roughly3.9–14.7%90 intervals. This is finite-bank zero frequency, not mathematically impossible victory. The correction changes National/Labour balance only; it does not repair an unmodelled major-versus-remainder departure. Composed winner frequencies are about.0050/.0053/.0053 and remain diagnostics, not calibrated probabilities. No probability floor or historical override is inserted.

Only four reused candidate environments and three composed environments support this exercise;2014 scale is prior-driven. Shared effects remain strongly pooled; parameter/scale uncertainty, cross-layer independence, unresolved reconciliation, uniform fragment composition, fine-party scenarios, incomplete2026 slates and the separate Māori baseline/polling layer remain explicit limits. No new sources, inference, mean coefficients or historical selection changes occur.

Carry forward the Gaussian development foundation, not a new heavy-tail default. Preserve the central-scale evidence and conditional-integration failure for a separately bounded numerical readiness decision before probability deployment. No further uncertainty family is automatically authorized. Official nomination refresh, Māori baseline/electorate polls, dated manual adjustments, all-seat reconciliation/turnout and MMP/live assembly remain separate tasks.
