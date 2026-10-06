# Stage48: frozen candidate-balance scale comparison, pre-registration

**Status: frozen before any restriction other than the numerically corrected control was fitted or scored.** This file and [design-contract.json](../data/processed/balance-scale/design-contract.json) are committed as a frozen checkpoint; the code reads every threshold below from the JSON, and the manifest hashes both. Later edits to either file are a change of design and must be recorded as an amendment with a reason, never as a silent rewrite.

## The one question

The Stage45/46/47 Gaussian law gives candidate-seat National/Labour (N/L) balance a pooled scale that the Stage47 attribution found is mostly prior (2023 prior share 55.17% of combined shared/seat balance variance). Stage47 produced Recommendation B (D083) and froze its design as [stage47-next-gaussian-scale-contract.md](stage47-next-gaussian-scale-contract.md) and [next-test-contract.json](../data/processed/uncertainty-expectation/next-test-contract.json). Stage48 runs exactly that contract and nothing else:

> Is the candidate balance scale globally too conservative, and is any heteroskedasticity predictable from pre-result information?

Exactly three Gaussian restrictions are scored, on identical records:

1. **C, control.** Numerically corrected Stage45 Gaussian (`a = b_R = b_T = 0`); this is Stage47's `corrected` bank, reproduced exactly (verified to 0.0 difference before this document was written, for six 2017 component seats and five 2017 composed seats).
2. **K, constant.** Earlier-trained constant seat-balance log multiplier `a` (`b_R = b_T = 0`).
3. **F, conditional.** Earlier-trained, strongly pooled `a + b_R (x_R - m_R) + b_T (x_T - m_T)`.

Seat scale is `sigma_seat,i = sigma_frozen,e * exp(a + b_R (x_R - m_R) + b_T (x_T - m_T))`. The shared election scale, all local/shared-candidate/mass/remainder/national laws, all means and the transport are unchanged.

## Interpretations resolved here (before any fit)

The Stage47 contract leaves a few details to implementation. They are fixed now, with the reason:

- **Which frozen scale applies to a training environment.** Each earlier environment `e'` enters the likelihood with the frozen Stage45 fold scales that were in force for `e'` itself (`scales.json` fold `e'`: 2014 prior-only 0.35 seat/0.15 shared; 2017 uses 2014; and so on). Reason: they are chronologically valid, and `a` is then a multiplier relative to the frozen scale, which is exactly how it is applied to the target. The target fold's own frozen scale multiplies at prediction time.
- **Likelihood location.** `ell_i` is the exact Gaussian logistic location for the frozen arithmetic ratio mean `p_i = N/(N+L)` and total sd `sqrt(sigma_shared,e^2 + sigma_seat,i^2)`, recomputed for every candidate multiplier (the one-dimensional case of the corrected Stage47 numerics, 81-node Gauss-Hermite with Newton; agreement with the simulation's 41-node bisection location is checked to 1e-9). It is not held at the control's location.
- **Observations.** `v_i = log((y_N+eps)/(y_L+eps))` with the unchanged Stage45 replacement (`coordinates()['balance']`); all 257 seats have both a valid observation and a valid mean (64/64/65/64).
- **Features.** `x_R = 1 - supportedR` from `heterogeneity.json` (defined for 257/257); `x_T = sourceNonmajorSupportProxy` from `structure.json` (defined for 257/257, no unavailable source occurrences). Neutral (centred 0) with a flag would apply to a missing value; none occurs. Centres `m_R, m_T` are the mean over the training environments of each environment's seat mean (equal election, equal seat).
- **2014.** No earlier candidate residual exists, so `a = b = 0` for K and F: all three restrictions are identical in 2014 by design, labelled prior/control. Decisions below use the 193 seats of 2017/2020/2023, where restrictions can differ; the 257-seat pooled values (2014 contributes exact zeros) are reported beside them.
- **Which seats the supporting composed check uses.** The existing 193 composed 56-day cases (2017/2020/2023) at the frozen 512 common stream indices, same allocation scenario as Stage47; the fitted multiplier is applied to the candidate layer inside the composition. Local-party layer scales are unchanged.

## Fit (frozen, from the contract)

Minimise `0.5 * mean_e[(logdet(Sigma_e) + (v_e - ell_e)^T Sigma_e^-1 (v_e - ell_e)) / n_e] + 0.5 * ((a/0.5)^2 + (b_R/0.5)^2 + (b_T/0.5)^2)` with `Sigma_e = diag(sigma_seat,i^2) + sigma_shared,e^2 11^T`, equal environments, equal seats within an environment, parameters bounded to +/- log 4. L-BFGS-B (ftol 1e-12, gtol 1e-8, maxiter 1000) from the three contract starts `(0,0,0)`, `(-0.2,0,0)`, `(0.2,0,0)`; the lowest objective wins, ties broken by start order. The gradient is analytic (Sherman-Morrison for `Sigma_e`, implicit differentiation for `ell_i`) and is checked against synthetic central differences (<= 1e-6); an independent Powell run (ftol/xtol 1e-10, maxiter 2000) must agree on the objective (<= 1e-6) with projected gradient <= 1e-6. Bound contacts are reported and never expanded. Likelihood information rank and conditioning (Hessian of the unpenalised part) are reported separately from the penalty. Folds: 2017 trains on 2014, 2020 on 2014/17, 2023 on 2014/17/20.

**Descriptive only, not a restriction.** For context the unpenalised likelihood maximiser of `a` (with `b = 0`) is also reported per fold, using the same objective with the penalty removed. It is never scored, never adopted and not a fourth candidate; it shows how much the frozen penalty (one prior sd 0.5 against a per-seat-normalised likelihood) limits what K can move. No prior-strength search follows from it.

## Numerical plan (frozen)

Primary: 257 seats x 32,768 common-stream draws per restriction, the same Stage47 component machinery with only the balance seat scale changed (common random numbers; the shared Sobol uniforms are untouched). Corrected conditional integration keeps its 0.05pp criterion; the balance location for the new scale is the binary Gaussian location for the new total sd, preserving the frozen ratio mean. Independent equality check: for every seat, the National+Labour mass and every non-major draw are identical across restrictions (only the N/L split moves). Representative doubling 8192/16384/32768 on the first/middle/last seat of each election: gates 0.05pp mean/CRPS, 0.1pp energy, 0.5pp 50/80/90 widths, reported per restriction, never relaxed. Supporting composed check: 193 seats at 512, representatives 256/512/1024, cap 1024; Stage47's known composed precision failure is not repaired here. The remainder block of each composed seat is reused for K and F only after an independent equality check: with control scales, the recomputed N/L columns equal the full control bank to 1e-12, and for the first and last seat of each election a full independent `invert` under the adjusted scales equals the reused result to 1e-12. Compute cap 90 CPU minutes is a documented cost bound, not a machine-speed gate inside `--check`. No new national MCMC, acquisition or data source.

## Decision rule (frozen; thresholds in the JSON)

Population: the 193 seats of 2017/2020/2023 in the 32,768-draw conditional candidate bank. All records are the identical complete records with equal contest weights; equal-election views are reported separately.

Quantities (pp), for restriction X versus Y:

- `Delta_CRPS` = mean over seats of the mean CRPS of that seat's National and Labour candidates, X minus Y. These are the only coordinates the balance scale moves directly; the other candidates' draws are bit-identical across restrictions, so whole-slate averages only dilute the same difference by an arbitrary slate size and are reported but are not the decision quantity.
- `Delta_IS` = mean over the 50/80/90 levels of the mean N/L interval score, X minus Y.
- Coverage guard: at each level, pooled N/L coverage may not move further from nominal than Y's by more than 0.02.
- `Delta_energy` = complete-vector contest-equal energy, X minus Y.
- Fold consistency: the sign of `Delta_CRPS` in each of the three elections (no per-fold magnitude gate).
- Resolution: `Delta_CRPS` computed on the first 16,384 draws must agree with the 32,768-draw value to 0.002pp.

**IMPROVES** if all hold: resolution; `Delta_CRPS <= -0.01`; `Delta_IS <= 0`; coverage guard; `Delta_energy <= +0.02`; `Delta_CRPS < 0` in at least 2 of 3 elections. **WORSE** if resolution holds and `Delta_CRPS >= +0.01`. **NEGLIGIBLE** if resolution holds and `|Delta_CRPS| < 0.01`. Otherwise **MIXED**.

Rationale for 0.01pp: one fifth of the frozen 0.05pp CRPS gate and about 0.3% of the control's N/L CRPS (about 3.7pp), set before any restriction other than the control was scored; narrowing alone is never success.

Comparisons: K versus C and F versus K decide; F versus C is reported.

| K vs C | F vs K | Finding |
|---|---|---|
| IMPROVES | not IMPROVES (NEGLIGIBLE or WORSE) | Constant only: global recalibration of the balance scale; no predictable heteroskedasticity shown |
| IMPROVES | IMPROVES | Global scale change and predictable heteroskedasticity |
| NEGLIGIBLE or WORSE | IMPROVES and F beats C | Conditional only |
| NEGLIGIBLE or WORSE | NEGLIGIBLE or WORSE | Neither: do not force narrowing; keep the corrected control |
| any MIXED | any | Mixed: stop, report to James, no adoption |

The composed 193-seat check is supporting: its pooled N/L `Delta_CRPS` for K versus C and F versus K is reported with the Stage47 caveat that composed precision gates are unmet. A sign disagreement of at least 0.01pp with the conditional result is flagged for review; it does not change the table above.

**No operational adoption in Stage48 under any outcome.** The question bears on the interval widths that feed the open probability-release decision, so the finding is recorded and the decision stays with James. The retained development default stays the corrected Stage45 Gaussian.

## Do not

- Do not fit or score any restriction beyond C, K and F; no prior-strength, feature, family or grid search; no unpenalised or differently penalised challenger scored.
- Do not reopen Student-t, mixtures, regimes, sigma shrinkage, geography fragmentation, candidate-quality scores, S reset, covariance fitting or national MCMC backtest reruns.
- Do not change any frozen Stage45/46/47 output, scale, mean, draw count, gate or tolerance; do not append to `data/sources.json`; add no source and no acquisition.
- Do not use target results to define features, centres, exclusions or thresholds; keep every seat.
- Do not relax numerical gates, enlarge bounds after seeing scores, or claim calibrated probabilities or fine composed superiority where gates are unmet.
- Do not bundle dated rosters, fragment composition, Other scenarios, the Maori baseline, nominations, reconciliation, MMP, manual adjustment or the S-continuity mean hypothesis.
