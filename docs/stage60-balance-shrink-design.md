# Stage60: stronger candidate-balance scale test, frozen pre-registration

**Status: frozen before any Stage60 arm was simulated or scored.** This file and [design-contract.json](../data/processed/balance-shrink/design-contract.json) are committed as a frozen checkpoint; the code reads every threshold, margin and arm from the JSON, and the manifest hashes both. Later edits are a change of design and must be recorded as a dated amendment with a reason, never a silent rewrite.

**What the author had seen before freezing (disclosed).** Stage48 already scored the corrected control and the penalised constant K on these seats, so the control's and K's per-election coverage and widths are known (for example the control's N/L 50% coverage is 0.680, 0.508, 0.680 in 2017, 2020, 2023 and 0.367 in 2014). Stage48 also reported, descriptively, the penalty-free constants (log multipliers -0.182, -0.158, -0.246; multipliers 0.83, 0.85, 0.78) for the three folds. The fixed grid 0.95/0.90/0.85/0.80 was set after those values were known, so **the fixed-grid arms are development-informed on these elections: they are not held out, and a good grid score is weaker evidence than the same score for an arm fitted on earlier elections only**. The penalty-free fitted arm (below) is the only arm whose multiplier is chronologically blind to its target. No new arm has been simulated or scored.

## The one question

> Does a stronger global shrink of the National/Labour candidate-balance seat scale than Stage48's penalised 0.93 to 0.95 improve calibration and proper scores?

Stage48 found the earlier-trained constant K better than the corrected control in all three fitted folds (major CRPS -0.0226pp, N/L 90% width 23.73 to 22.96pp), and noted that its ridge keeps the multiplier within 5 to 7% of the frozen scale while the likelihood alone prefers about 0.78 to 0.85. That preferred size was never scored. Stage60 scores it, and a fixed grid across it, under a rule written first.

## Arms (exactly the six below, plus one reference)

The multiplier applies to the **frozen Stage45 seat balance scale only**; the shared election balance scale, every other coordinate, the means and the transport are unchanged, exactly as for Stage48's K. The candidate layer is the Stage44/45 layer with the deployed neutral centred R for any replacement candidate; Stage55 found no replacement shift or transfer supported, so nothing in the layer's means changes.

| Arm | Seat balance multiplier | Role |
|---|---|---|
| control | 1.00 | the corrected Stage45 Gaussian, the deployed default |
| grid95, grid90, grid85, grid80 | 0.95, 0.90, 0.85, 0.80, the same in every election | candidate (fixed, development-informed) |
| free | exp(a), `a` the penalty-free constant fitted on earlier elections only (Stage48 objective, ridge removed); 1.0 where no earlier election exists (2014) | candidate (leave-future-out) |
| penalised | Stage48's K, read from `balance-scale/fit.json` | reference only, never recommendable; reproduces Stage48 as a harness check |

No other arm: no multiplier search, no prior-strength search, no variance predictor, no conditional (heteroskedastic) scale, no feature. The conditional line was closed by Stage48.

**Free arm fit (frozen).** Minimise the Stage48 objective with the ridge term removed, equal environments and equal seats within an environment, only `a` free (`b_R = b_T = 0`), bound plus or minus log 4, L-BFGS-B (ftol 1e-12, gtol 1e-8, maxiter 1000) from the three Stage48 starts, lowest objective wins, ties by start order. Each earlier election enters with the frozen Stage45 fold scales in force for that election. An independent Powell run must agree on the objective (<= 1e-6) with projected and central-difference gradients <= 1e-6, and the fitted `a` must agree with Stage48's reported descriptive unpenalised value to 1e-6. Folds: 2017 trains on 2014, 2020 on 2014/17, 2023 on 2014/17/20; 2014 has no earlier data and is control. A **descriptive 2026 refit** on all four elections gives the value the free arm would take for the 2026 forecast; it is reported, never scored.

## Population, scores and resolution

Score all four elections wherever the harness supports it: the 257 general-electorate candidate records (64/64/65/64) at the Stage48 component bank, 32,768 common-stream draws per seat per arm (the same streams as Stage48; only the balance scale differs). **Decision population:** the 193 seats of 2017, 2020 and 2023. 2014 is reported explicitly beside them (all grid arms are scored there; the free arm equals control by construction). No composed bank is run; the composed-width implication is arithmetic only (below).

**Māori seats.** Excluded by electorate type, never by party: every record used must have `scope = general`, and the pipeline asserts and reports the count of excluded records (none are present in the Stage44 inventory; the seven Māori electorates are modelled separately).

Per arm and election and pooled: N/L candidate major CRPS (mean over seats of the mean CRPS of that seat's National and Labour candidates), 50/80/90% coverage, widths and interval scores of the N/L coordinates, complete-vector energy, plus the equal-election mean.

## Decision rule (frozen; thresholds in the JSON)

An arm **qualifies** only if both parts hold, each arm compared with the control on the 193 decision seats:

1. **Stage48 IMPROVES.** Resolution (ΔCRPS on the first 16,384 draws agrees with the 32,768-draw value to 0.002pp); pooled ΔCRPS <= -0.01pp (Stage48's materiality: about 0.3% of the control's N/L CRPS); mean N/L interval score over 50/80/90 not worse (ΔIS <= 0); Stage48's coverage guard (pooled coverage at each level may not move further from nominal than the control's by more than 0.02); Δenergy <= +0.02; ΔCRPS < 0 in at least 2 of the 3 elections; and the representative 8,192/16,384/32,768 doubling gates (Stage48 gates, never relaxed) pass for the arm (an arm failing them is MIXED and cannot qualify).
2. **Coverage floor, every election including 2014.** At the 50% and 80% levels, the arm's pooled N/L coverage in each of 2014, 2017, 2020 and 2023 must be at least `min(nominal - 0.10, control coverage - 0.05)`. The 0.10 margin is about 1.6 binomial standard errors at 50% and 2.0 at 80% for a 64-seat election (the same nominal-versus-observed noise any election-level coverage carries), so only a miss clearly beyond sampling noise fails; the `control coverage - 0.05` term handles an election the control already under-covers (2014 at 50%) by allowing at most a further 0.05 loss rather than failing every arm against a standard the control itself misses. The free arm equals the control in 2014 and passes there by construction.

**Selection.** Among qualifying arms, let the best be the one with the lowest pooled major CRPS. An arm is within noise of the best if the lower end of the 90% paired seat bootstrap interval (2,000 draws, seed 60, seats resampled with replacement within election, pooled equal-seat mean) of CRPS(arm) minus CRPS(best) is at most 0. The recommended arm is the **least aggressive** (highest equal-seat mean multiplier on the decision seats) qualifying arm within noise of the best. The least aggressive arm within 0.01pp of the best pooled CRPS is reported as a descriptive alternative, not as the rule.

| Outcome | Finding |
|---|---|
| at least one arm qualifies | `recommend_<arm>_for_james_signoff` (recommendation only; also stated: whether the arm is leave-future-out or development-informed, and the free arm's 2026 refit beside it) |
| no arm qualifies, at least one arm Stage48-IMPROVES but fails the floor | `floor_blocked_report_to_james`: stop and report |
| no arm Stage48-IMPROVES | `no_arm_qualifies_keep_corrected_control` |

**No operational adoption under any outcome.** Stage60 is the first stage that could change the default. It reports a recommendation; adoption needs James's sign-off, and `operationalAdoption` stays null. The corrected control remains the development default.

## Composed-width implication (arithmetic, no new bank)

The question bears on the width behind the open probability-release decision, so the findings convert each arm's multiplier into an approximate National and Labour composed 90% width using the Stage47 nine-seat ablation (`uncertainty-expectation/attribution.json`): per ablation seat, `width(m)^2 = width(no balance)^2 + (width(full)^2 - width(no balance)^2) g(m)`, with `g = m^2` if the multiplier scaled all balance variance (an upper bound on the effect) and `g = s m^2 + (1 - s)` if only the seat part scales (what the arms actually do; `s` is the seat share of the seat-plus-shared balance variance from the seat's frozen fold scales, 0.73 to 0.78 across 2017 to 2023). The arithmetic is checked against the Stage48 composed K-versus-control National full-90 width change (193 seats, 512 draws, precision gates unmet) as a sanity check. It is approximate, nine seats and not a composed bank; no composed bank is run and no composed superiority is claimed.

## Do not

- Do not simulate or score any arm beyond the six above and the Stage48 reference; no multiplier or prior-strength search; no variance predictor or conditional scale (Stage48 closed that).
- Do not run a new composed bank, national MCMC, acquisition or source work; do not edit `data/sources.json`.
- Do not reopen Student-t, mixtures, regimes, sigma shrinkage, geography fragmentation, candidate-quality scores, S reset, covariance fitting or national MCMC backtest reruns.
- Do not change any frozen Stage45/46/47/48 output, scale, mean, draw count, gate or tolerance.
- Do not change a threshold, margin, floor or arm after any Stage60 score is read; do not relax numerical gates.
- Do not use Māori electorate data in any fit, score or calibration.
- Do not flip the default: no adoption without James's sign-off. Do not make a calibrated-probability or seat-win claim; none is evaluated.
