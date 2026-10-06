# Stage55 findings: is neutral R right for an ordinary incumbent replacement?

Frozen design: [stage55-replacement-effect-design.md](stage55-replacement-effect-design.md) (committed `b4affd9` before any fit or score). Artifacts: `data/processed/replacement-effect/` (`summary.json`, `scores.json`, `seat-scores.json`, `sample.json`, `stage10-gap.json`, `manifest.json`). Reproduce: `python3 -m scripts.replacement_effect.run --check` (about 3 seconds, no network, no national inference). Recommendation only: nothing is adopted, `selectedOperationalReplacementEffectPP` stays `null` and Stage10's -6.64pp stays undeployed.

## Headline

**The pre-registered finding is `mixed_report_to_james`.** That is the rule's output because the constant-shift arm is a borderline, unsupported improvement; it is not evidence for a replacement effect. Reading the numbers (my interpretation, not rule output): **there is no support for changing the neutral R assumption for an ordinary retirement.** Adding partial transfer of the outgoing candidate's R makes the candidate layer clearly worse; a constant shift is indistinguishable from neutral.

| Comparison (31 affected seats, 2017/2020/2023) | Relative change in balance CRPS | 90% seat bootstrap (absolute CRPS) | By election 2017 / 2020 / 2023 | Label |
|---|---:|---|---|---|
| K (constant) vs C (neutral) | -0.40% | [-0.0035, +0.0026] | -0.0066 / +0.0040 / +0.0003 | MIXED |
| P (partial transfer) vs C | +20.0% | [+0.0147, +0.0370] | +0.0302 / +0.0367 / +0.0123 | WORSE |
| P vs K | +20.4% | [+0.0138, +0.0386] | +0.0368 / +0.0327 / +0.0119 | WORSE |
| T (full transfer, reference) vs C | +36.4% | [+0.0200, +0.0734] | +0.0872 / +0.0334 / +0.0258 | WORSE |

K clears the 0.3% bar in size only. It fails the frozen conditions: it helps in 1 of 3 elections (2017), and its interval spans zero. Both sensitivities agree: the extended sample (all election-time exits, 40 affected seats) gives the same `mixed`; the sample without list-only exits (25 seats) gives K vs C -0.28% (NEGLIGIBLE) and `neutral_adequate`. P is WORSE by 16% to 23% in all three samples.

## Answers to the four questions

1. **Neutral on average?** Yes within noise. Across the 31 scored successors, mean `R_new - mu_f` is +0.43pp (90% bootstrap interval -0.51 to +1.39pp; sd 3.47pp); by election +1.64, +1.01, -0.97pp. `mu_f` is the layer's neutral centring (about 0.9 to 1.1pp), so neutral R is right on average for a retirement successor even though the outgoing winner averaged about 4.3pp and a continuing incumbent's R_new averages 5.2pp.
2. **Negative mean shift?** Not supported. In the scored years the shift is +0.43pp (above). A negative mean appears only in the two earliest elections: the 16 successors of 2011 and 2014 average -0.78pp, which is why the earlier-only constant `a-hat` changes sign across folds (-0.78, +0.42, +0.87pp) and why K helps in 2017 only. The pooled primary mean R_new (0.69pp over all 47 seats) mixes both periods; the unfitted pooled intercept (-1.23pp with `rho` 0.44) mixes intercept and slope.
3. **Partial transfer (`rho < 1`)?** Descriptively yes, but it is unstable and does not help the layer. Pooled over 47 primary seats `rho` = 0.44 (90% interval 0.27 to 0.63; correlation 0.46), against 0.58 (0.47 to 0.69) for continuations. By pair `rho` is 0.84, 0.84, 0.11, 0.49, -0.08 (2008-11 to 2020-23, n = 6, 10, 9, 10, 12): the pooled value is carried by 2011 and 2014 and is near zero in 2020 and 2023. Fold-trained `rho-hat` is 0.84, 0.67, 0.60 and the P arm still loses 20% in CRPS and in R units (out-of-fold RMSE of R-hat_new is worse than neutral in 2017 and 2023: 4.20 vs 2.75pp and 4.62 vs 3.39pp; better only in 2020: 3.58 vs 4.02pp).
4. **Does modelling it reduce candidate-balance variance?** No. Mean squared balance error on the affected seats: C 0.0395, K 0.0391, P 0.0661, T 0.0917.

Why transfer hurts: the layer already moves the incoming candidate's weight with the outgoing seat-party split (S, `theta_S` about 0.9), and the control's replaced-candidate shares are essentially unbiased (mean predicted minus actual -0.31pp against a mean absolute error of 3.44pp). Adding `theta_R x (a + rho R_old - mu_f)` on top overshoots. The descriptive S-overlap regression (41 seats) shows R_old and the outgoing split correlate 0.51 but `rho` hardly moves when the split is controlled (0.40 to 0.41), so this diagnostic does not itself explain the loss; the layer-level score is what decides.

**Scale (materiality).** One percentage point of R moves the balance location by about 0.028 log units (`theta_R` about 2.83), 7.7% of the median total balance sd (0.369). The largest log-weight shift any arm applied was 0.057 (K), 0.257 (P) and 0.387 (T). The possible gain from any R shift is therefore small next to the scale, and the K result (-0.4%) shows it is.

## Sample

Stage51 ledger: 333 N/L incumbent seats, 258 continuations and 75 changes. Primary sample (frozen rule): 47 general-seat retirements (6, 10, 9, 10, 12 for the pairs 2008-11 to 2020-23). Excluded by rule (28 of the 75 changes): 3 Māori rows; 20 general rows of other types (8 by-election successions, 2 by-election party changes, 2 party changes, 1 boundary complication, 5 early resignations, 1 deselection, 1 death or illness withdrawal); and 5 general retirements carrying an excluded tag (3 `scandal_context`, one of which is also a boundary-change successor, and 2 boundary-change successors). Extended sensitivity: 59 rows; no-list-only: 39. All 31 primary successors in 2017/2020/2023 are in the candidate layer, none with their own R history, none excluded by the layer rules. Fold training sizes: 16, 25, 35 (primary).

Retirement successor R_new (0.94pp mean) sits far below continuing incumbents (5.24pp) and below the by-election successions (7.4pp, excluded), consistent with an incoming candidate carrying little personal premium.

## The 3 changes missing from the Stage10 inventory

Cause found and verified (`stage10-gap.json`): **a macron name-key mismatch**, not an evidence gap. Stage10 pairs seats by exact electorate name. The 2008 results are published without macrons and the 2011 results with them (Rangitikei/Rangitīkei, Tamaki/Tāmaki, Te Atatu/Te Atatū), so those seats found no same-named 2011 seat and dropped out. The same applies to eight seats in the 2008-11 transition (Kaikoura, Mangere, Ohariu, Otaki, Rangitikei, Tamaki, Taupo, Te Atatu): the inventory holds 55 of 63 general source seats. The Stage51 ledger has 7 National or Labour rows there: the 3 changes (Te Atatu party change, Rangitikei retirement, Tamaki death or illness withdrawal) and 4 continuations (Kaikoura, Mangere, Otaki, Taupo). Other pairs: 2011-14 loses Waitakere (renamed after boundary change) and Ōhariu (macron); 2017-20 loses 10 seats (nine renamed or abolished under the changed boundaries, Whangārei by macron); 2014-17 and 2020-23 lose none.

**Handling.** Stage51 and Stage55 join by occurrence ID through Stage25 geography, never by name, so all seven rows are in the ledger and Rangitikei 2011 (a retirement, R_old 11.2pp, R_new 4.6pp) is a primary-sample training seat here. Te Atatu is a party change and Tamaki a withdrawal after illness, so both are excluded from the primary sample by rule. Stage10 outputs are not changed: its 2008-11 cohort counts omit these seats and that remains a documented limitation (a knock-on for the other name-keyed inventories built from the same seat pairing, Stage8 and Stage10, is likely but was not audited here).

## Limits

- 31 scored seats in 3 elections, all used repeatedly in development; this is not pristine out-of-sample, and the scale and scores are conditional on the Stage44 candidate layer (local-party shares observed, earlier fit fixed).
- R_old is the winner's residual (selected on winning), which inflates its mean relative to an average candidate.
- Arm P is the roadmap equation and is not net of S. A transfer fitted on the residual after the layer's S shift is a different test, not run here and not recommended on this evidence (K, which has no R_old term, is already null).
- Tags (list-only exits and so on) are flagged, not modelled; strata are too small to fit.
- Composed scoring is not done; the Stage54 precision limit is unaffected.

## Observation outside the pre-registered question (untested, do not act)

The control's mean squared standardised balance residual is 0.29 on the 31 affected seats (90% bootstrap 0.19 to 0.40) against 0.70 across all 193 layer seats: ordinary-retirement seats are much less dispersed than the control scale assumes. This is a descriptive context number computed after scoring, not a decision quantity, and 31 seats in 3 elections is thin. It bears on the width track (Stage48 follow-up) and on any ordinary-seat calibration set, so it is recorded for James and the coordinator and not acted on here.

## Recommendation

1. Keep neutral centred R for an ordinary retirement successor. Do not add partial or full transfer of the outgoing R, and do not deploy a constant shift. Nothing here supports a replacement coefficient; the question for an ordinary retirement is closed unless James wants the net-of-S variant.
2. The stricter reading of the frozen rule is `mixed_report_to_james`, so the choice is James's: either accept the interpretation above (neutral retained) or treat K vs C as an open weak signal. The sensitivities, the sign pattern across elections and the interval all point to neutral.
3. Sequencing: the width/shrink stage after Stage58 can score against the unchanged control, since no replacement adjustment changes the candidate-balance mean.
4. Not covered and unchanged: by-election successors, party switchers and scandal exits (excluded by rule; these are manual-layer cases per the roadmap), and the Māori seats.
