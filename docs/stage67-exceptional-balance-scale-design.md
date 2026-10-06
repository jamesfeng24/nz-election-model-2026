# Stage67: ordinary versus exceptional candidate-balance seat scale, frozen pre-registration

**Status: frozen before any Stage67 arm was fitted, simulated or scored.** This file and [design-contract.json](../data/processed/exceptional-balance-scale/design-contract.json) are the frozen checkpoint; the code reads every threshold, flag and arm from the JSON. Later edits are a change of design and must be recorded as a dated amendment with a reason.

**Authorization.** James authorized this stage on 2026-10-06 and chose the primary flag set, the sensitivity and the sequencing (Stage67 first, Stage68 descriptive later, one PR per stage). Decision number: to be allocated by the coordinator.

**What the author had seen before freezing (disclosed).**
- The author classified the flags and had seen every 2014–2023 balance residual.
- The author had seen an in-sample development diagnostic (draft PR #78, not merged). It fitted, on all four elections at once, an ordinary multiplier of 0.60 and an exceptional multiplier of 1.46 (ratio 2.4) relative to the frozen seat scale. The ratio fell to 1.2 in 2020 and to 1.7 without the five largest exceptional residuals.
- The author had also seen Stage60's results (free arm 0.834/0.854/0.782; recommended for sign-off, not adopted).

This stage is therefore development evidence on reused elections, not untouched validation. Its leave-future-out fit is the only part that does not use the target election.

## The one question

> Do separate earlier-trained ordinary and exceptional seat multipliers on the candidate National/Labour balance scale beat Stage60's single earlier-trained multiplier?

It is an uncertainty-only question. No mean, location, S, R, transport, shared scale or other coordinate changes.

**Not a reopened line.** The do-not-reopen list closes regimes and fitted variance predictors (Stage48's conditional arm). Stage67 uses neither. The exceptional indicator is a fixed human ex-ante judgement, not a fitted or data-derived feature. It is the "ordinary-seat calibration set" that D082 anticipated, and James authorized it explicitly.

## Flags (frozen inputs)

- **Primary set.** The frozen 2026-10-06 read-only audit: 38 of 257 seat-elections (2014: 8, 2017: 6, 2020: 10, 2023: 14), listed in the contract by year and electorate name. They are not re-researched or revised here.
- **Bias disclosed.** The audit prompt contained a residual-ranked list of cases at or above 0.5σ, and 21 of the 38 flags come from that list (listed separately in the contract). The primary set is therefore expected to overstate the separation.
- **Sensitivity set.** Only the other 17 flags are exceptional, and the 21 list-derived flags count as ordinary in both fitting and scoring. This is deliberately conservative: residual-selected seats sit in the ordinary group, so a separation that survives here is not produced by the list.

## Arms

All arms multiply the frozen Stage45 seat balance scale only, exactly as Stage48 K and Stage60 do.

| Arm | Seat balance multiplier | Role |
|---|---|---|
| control | 1.00 | corrected Stage45 Gaussian, the deployed default |
| free | Stage60 free arm, read unchanged from `balance-shrink/fit.json` | comparator (single earlier-trained constant) |
| twogroup | `exp(a)` for ordinary seats, `exp(a+b)` for flagged seats; `a`, `b` fitted on earlier elections only | candidate |
| twogroup17 | as twogroup with the 17-flag sensitivity set | sensitivity only, never recommendable |

There are no other arms: no grid, no prior-strength or penalty search, no further features, no Student-t or mixtures.

**Fit (frozen).** The Stage48 per-seat-normalised Gaussian objective (equal environments, equal seats), penalty-free, with the feature columns (flag indicator, 0) so that `b_T = 0`.
- Parameters `a` and `b` are free, bounded to ±log 4, with no expansion on contact; contact is reported.
- L-BFGS-B uses the Stage48 settings and starts `(0,0,0)`, `(-0.2,0,0)`, `(0.2,0,0)`; the lowest objective wins, ties by start order.
- An independent Powell run must agree on the objective (≤ 1e-6), and the analytic gradient must agree with central differences (≤ 1e-6).
- Each earlier election enters with its own frozen Stage45 fold scales.
- Folds: 2017 trains on 2014; 2020 on 2014 and 2017; 2023 on 2014, 2017 and 2020. In 2014 there is no earlier election, so every arm equals the control.
- Weakness disclosed: 2017's exceptional multiplier is trained on 8 flagged 2014 seats.
- A descriptive 2026 refit on all four elections is reported, never scored. Applying it in 2026 would need 2026 seats flagged through the Stage56 manual interface, which is outside this stage.

## Population, scoring and numerics

- **Harness.** The Stage60 harness unchanged (`scripts.balance_shrink.evaluation.seat`): the 257 general-electorate candidate records (64/64/65/64), 32,768 common-stream draws per seat per arm, and the same streams as Stage48/60. Only each seat's balance multiplier differs.
- **Māori electorates.** Excluded by electorate type.
- **Decision population.** The 193 seats of 2017/2020/2023; 2014 is reported beside them.
- **Scores.** N/L major CRPS (mean over seats of the mean CRPS of the seat's National and Labour candidates, pp), 50/80/90 coverage, widths and interval scores of the N/L coordinates, and complete-vector energy. Each is reported pooled, by election, and by group (ordinary or exceptional).
- **Numerical gates.** Representative doubling 8,192/16,384/32,768 on the first, middle and last seat of each election, with Stage48 gates that are never relaxed. Resolution: ΔCRPS on the first 16,384 draws must agree with the 32,768-draw value to 0.002pp.
- **Uncertainty.** A 90% paired seat bootstrap of ΔCRPS (2,000 draws, seed 67, seats resampled within election, pooled equal-seat mean), reported.

## Decision rule (frozen; thresholds in the JSON)

Compare twogroup with free on the 193 decision seats.

1. **Stage48 IMPROVES against free**, which requires all of:
   - resolution passes;
   - ΔCRPS ≤ −0.01pp;
   - mean N/L interval score over 50/80/90 is not worse;
   - pooled coverage at each level moves no further from nominal than free's by more than 0.02;
   - Δenergy ≤ +0.02pp;
   - ΔCRPS < 0 in at least 2 of the 3 elections;
   - doubling gates pass.
2. **Group coverage floors at 50% and 80%.**
   - Ordinary seats, in each decision election: coverage ≥ `min(nominal − 0.10, free − 0.05)`. This is Stage60's floor; the ordinary group is the one being narrowed.
   - Exceptional seats, pooled over the 30 decision-year flagged seats: coverage ≥ `min(nominal − 0.15, free − 0.05)`. Per election there are only 6 to 14 flagged seats, too few for a floor. 0.15 is about 1.6 binomial standard errors at 50% and 2.1 at 80% for 30 seats, the same strictness as Stage60's 0.10 for 64 seats.

| Outcome | Finding |
|---|---|
| IMPROVES and both floors hold | `recommend_twogroup_for_james_signoff` |
| IMPROVES, a floor fails | `floor_blocked_report_to_james` |
| resolution holds and \|ΔCRPS\| < 0.01pp | `negligible_keep_single_scale` |
| resolution holds and ΔCRPS ≥ +0.01pp | `worse_keep_single_scale` |
| otherwise | `mixed_report_to_james` |

**Sensitivity reading (frozen).** twogroup17 is scored against free on the same records and never changes the finding. If its pooled ΔCRPS against free is not negative while twogroup's is, the findings must state `flag_selection_sensitive`: the separation then depends on the residual-derived flags.

**No operational adoption under any outcome.** The default stays the corrected control. Stage60's free arm stays a recommendation pending James. `operationalAdoption` is null.

## Do not

- Do not fit or score any arm beyond the four above; no grid, penalty or prior-strength search, no further feature, and no variance predictor beyond the frozen human flag.
- Do not add, remove or reclassify any flag, or change the sensitivity set, after any Stage67 fit or score.
- Do not change any mean, location, S, R, shared scale, local-party layer or national component; no composed bank, national MCMC, acquisition, source or `data/sources.json` edit.
- Do not change any frozen Stage45/46/47/48/60 output, scale, draw count, gate or tolerance; do not relax numerical gates.
- Do not use Māori electorate data.
- Do not make CI, workflow or validation-registry edits; Stage67 is exercised in CI only through its unit test.
- Do not adopt anything or make a calibrated-probability or seat-win claim.

## Amendment 1 (2026-10-06): add `twogroup_exc1`, name the main leak, decision numbers

**Reason and timing.** The coordinator asked for this arm to test whether a fitted exceptional multiplier beats simply holding flagged seats at the frozen scale. The in-sample diagnostic's 1.46 fell to 1.02 without its five largest misses.

The amendment came after the original arms had been **fitted** but before any score was **read**. The author had seen the fitted multipliers:

| Arm | Ordinary | Exceptional |
|---|---|---|
| twogroup | 0.595 / 0.615 / 0.607 | 1.737 / 1.889 / 1.526 |
| twogroup17 | 0.839 / 0.869 / 0.802 | 0.373 / 0.281 / 0.239 |

(2017 / 2020 / 2023 folds.)

One evaluation bank had been written by then. It was deleted unread and regenerated after this amendment. No threshold, floor, flag or existing arm changes.

**New arm `twogroup_exc1` (candidate).**
- Ordinary seats take `exp(a)`; primary-flagged seats are held at the frozen seat scale (multiplier 1.00).
- `a` is fitted on earlier elections only, penalty-free, with the same Stage48 objective, starts, bounds and independent checks as twogroup.
- The fit uses the feature `1 - flag` on the second coefficient, with the constant fixed at 0.

**Revised decision.**
1. Each candidate arm (`twogroup`, `twogroup_exc1`) is judged against `free` with the unchanged rule: Stage48 IMPROVES plus both group coverage floors.
2. If both qualify, `twogroup` is recommended only if it Stage48-IMPROVES on `twogroup_exc1` (same thresholds). Otherwise `twogroup_exc1` is recommended: it fits one parameter fewer and is the less aggressive arm for flagged seats.
3. If exactly one qualifies, that arm is recommended.
4. If none qualifies:
   - `floor_blocked_report_to_james` if either arm Stage48-IMPROVES against free;
   - otherwise `negligible_keep_single_scale` if both are NEGLIGIBLE against free;
   - `worse_keep_single_scale` if both are WORSE;
   - else `mixed_report_to_james`.

Findings: `recommend_twogroup_for_james_signoff`, `recommend_twogroup_exc1_for_james_signoff`, or the four above. The `flag_selection_sensitive` statement is unchanged.

**The main leak, named.** The 2017–2023 seats being scored were flagged by an author who knew their results. Separating them out therefore narrows the ordinary group partly mechanically: removing large misses shrinks what remains. The coordinator estimates about 0.72× from trimming alone, against the roughly 0.76 seen in the in-sample diagnostic. This bias favours `twogroup` and `twogroup_exc1` over `free`, and it is not removed by earlier-only fitting. The check is the 17-flag arm. Its ordinary-seat and exceptional-seat coverage, width and CRPS are reported by election, as descriptive results beside the rule, not only as the sensitivity statement.

**Decision numbers** (from the coordinator): D101 for Stage67, D102 for Stage68.
