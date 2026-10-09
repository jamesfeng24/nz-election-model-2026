# Stage83 findings: ordinary-seat minor-candidate spread

Decision D121 (number from the coordinator). Frozen design: `docs/stage83-ordinary-minor-spread-design.md` and `data/processed/ordinary-minor-spread/design-contract.json` (committed `d1fd448`; amendment 1 committed `192cbab`, before any score). Outputs: `data/processed/ordinary-minor-spread/{fit,evaluation,decision}.json`. Code: `scripts/ordinary_minor_spread/`.

## Question

Do ordinary-seat multipliers on the candidate within-remainder noise (and, separately, the major-mass noise), fitted on earlier elections only, beat the D107-only control on the 257 historical candidate records, with the 38 Stage67 flagged seats held at 1.00? The flag list is the Stage67 list, unchanged.

## Finding

**By the frozen rule the answer is `keep_control_mixed`: no fitted arm is adopted.** James then set the ordinary-seat within-remainder multiplier at 0.55 as a judgement (next section); that value is not a result of the frozen rule. Every candidate arm improves, and every guard passes, except one condition.

| Arm (ordinary seats, 2017/2020/2023, 163 seats) | Minor CRPS vs control | Folds negative | Minor 80% coverage (control 0.924, nominal 0.80) | Minor 90% | National / Labour 80% (control 0.779 / 0.877) |
|---|---|---|---|---|---|
| `within` | −2.6% | 3 of 3 | 0.884 | 0.937 | 0.779 / 0.877 |
| `within_mass` | −3.7% | 3 of 3 | 0.871 | 0.927 | 0.767 / 0.877 |
| `within_robust` | −2.4% | 3 of 3 | 0.894 | 0.950 | 0.779 / 0.877 |
| `within_mass_robust` | −3.4% | 3 of 3 | 0.882 | 0.941 | 0.767 / 0.877 |

- **What passes for all four arms:** CRPS gain of at least 1% pooled and in all three folds (paired seat bootstrap, 90% interval for the `within_mass` change in minor CRPS: −0.040 to −0.028 percentage points, which excludes zero); minor 80% coverage moves toward nominal; minor 90% coverage at least 0.85; mass 80% coverage in the 0.74–0.86 band (`within_mass` 0.816); the major guard (National and Labour 80% coverage at least 0.70 and down no more than 0.03; major CRPS change at most +1%); flagged seats bit-identical to control; prefix versus full coverage within 0.005; the matching 17-flag arm has the same direction (pooled minor CRPS −1.5% to −2.3%, coverage nearer nominal).
- **What fails for all four:** the registered requirement that minor 80% coverage lies in [0.74, 0.86]. The control covers 92.4% at the nominal 80%; the best arm reaches 87.1%.
- **Reading.** The direction is supported out of sample and no check is violated, but the earlier-trained multipliers narrow the ordinary-seat minor candidates only by about 10 to 20 percent, which leaves them over-wide against the registered band. The result is mixed, not negative. Whether a modest, out-of-sample-supported narrowing is worth adopting despite the failed band is a decision for James, not the rule.

Earlier-trained multipliers (primary flags; moment estimator; 2014 has no earlier election, so 1.00): within 0.73 (2017 fold), 0.84 (2020), 0.83 (2023); mass 0.69, 0.97, 0.92. Descriptive refit on all four elections, not scored: within 0.80 and mass 0.91 (robust 0.80 and 0.85).

## James's decision: 0.55 on the within-remainder noise (2026-10-10)

James chose **0.55** on the candidate within-remainder noise (seat and shared parts), ordinary seats only; major-mass noise stays 1.00 and exceptional seats stay 1.00. This is his judgement over the fitted value (about 0.80), recorded in the same way as D107 (0.60 where the fit said about 0.79). `config/nowcast-2026.json` holds `candidateWithinSeatMultiplier {ordinary 0.55, exceptional 1.00}`. It is not one of the frozen arms and the frozen rule did not select it.

Descriptive in-sample check on the 163 ordinary decision-year seats (2017, 2020, 2023; the same records and the 38 flagged seats excluded; 16,384 draws), D107 balance multiplier in both columns:

| | Control | Within 0.55 |
|---|---|---|
| Minor ('other') 80% / 90% coverage | 0.923 / 0.971 | 0.808 / 0.885 |
| Minor CRPS (PP) | 0.937 | 0.893 (−4.7%) |
| Independents 80% / 90% coverage | 0.656 / 0.836 | **0.367 / 0.477** |
| Independents CRPS (PP) | 0.536 | 0.579 (+8%) |
| National / Labour 80% coverage | 0.779 / 0.877 | unchanged |
| Predicted minor-win mass (actual: 0 wins) | 0.39 | 0.25 |

The value matches nominal coverage for party-affiliated minor candidates and has the best pooled CRPS of any variant seen, but it was chosen with all four elections known, so it has no out-of-sample support and is not independent evidence. Stated costs:

- **Thinner tails.** Ordinary-seat minor candidates can no longer produce large surprises as often as the fitted law allowed (90% coverage 0.885, just under nominal).
- **Independents are hurt.** Their intervals were already too narrow (80% coverage 0.656) and now cover under 40% of results. Any strong independent in an ordinary seat is under-forecast in its upside. The multiplier could be limited to party-affiliated candidates; that is not what was chosen.
- **Little effect on win probabilities.** Narrowing only the within noise moves the named seats by about one point (below). The large movements in the earlier diagnostic came from narrowing the mass noise, which the guard on National coverage limited and which James did not choose.

## What the fitted values would have changed in 2026 (descriptive; not adopted)

Preview seats, current slate and baseline, D107 balance multipliers, win probability for the named candidate:

| Seat (candidate) | Current | Within 0.80, mass 0.91 | In-sample diagnostic (0.55, 0.75; not a fitted value) |
|---|---|---|---|
| Tauranga (ACT) | 3.1% | 2.2% | 1.2% |
| Banks Peninsula (Green) | 11.9% | 10.3% | 7.7% |
| Mt Albert (Green) | 23.5% | 22.6% | 21.0% |
| Dunedin (Green) | 12.6% | 11.5% | 9.6% |
| Kaikōura (NZ First) | 15.6% | 13.9% | 11.8% |
| Waimakariri (NZ First) | 6.9% | 5.7% | 3.7% |

For the adopted 0.55 on within only (same preview, 2,048 draws, win probability for the named candidate): Tauranga ACT 3.1% to 2.1%, Banks Peninsula Green 11.9% to 11.0%, Dunedin Green 12.6% to 11.7%, Kaikōura NZ First 15.6% to 14.7%, Waimakariri NZ First 6.9% to 6.0%. Mt Albert, Northland and Epsom are exceptional and unchanged.

The table uses 2,048 draws per seat, so differences under about 0.5 point are Monte Carlo noise. Northland is now an exceptional seat (#105) and would not be narrowed; it is omitted.

The earlier-trained values would trim the oddities James named (Tauranga ACT, Banks Peninsula, Dunedin) by roughly 10 to 30 percent of their win probability. They do not make a minor candidate with a far lower mean share clearly less likely than a major-party candidate, because most of that comes from the skewed tail of the within-remainder law and from the local-party layer upstream, neither of which this stage changes (Stage61 did not support narrowing the local-party layer).

## Limits

- **Flag selection.** The Stage67 flags were assigned with every 2014–2023 result known; 21 of 38 came from a residual-ranked list. The 17-flag arms are the check and agree in direction, but narrower gains (−1.5% to −2.3%).
- **The coverage metric pools many tiny candidates.** Most 'other' candidates have mean shares near zero and are easily covered. Restricting after the fact (descriptive only, not a gate) to ordinary-seat minor candidates with a mean share of at least 5% (186 candidates) gives control 0.930, `within_mass` 0.882 at the 80% level, so the over-width is not an artefact of the near-zero candidates.
- **Scale versus coverage.** The squared-residual fit (moment, and the robust median version) recovers multipliers of about 0.8, but matching the 80% coverage needs about 0.55 in-sample (coordinator diagnostic). That mismatch is a heavy-tail signature in the Gaussian law (many residuals well inside the interval, a few far outside). Student-t and mixtures are on the do-not-reopen list and are not touched.
- **Independents are not helped.** Independent (no group) 80% coverage is 0.656 in the control and falls to 0.52–0.55 under the narrowing; independents are under-covered already, and the arms worsen their CRPS slightly (0.536 to 0.553–0.557). None of the arms is gated on independents.
- **No ratio change.** Candidate-to-party-vote ratios above 2023 actuals for minor parties are a pre-existing backtest bias (NZ First, ACT) plus closure, not addressed here; offsets are unstable across elections and any NZ First or ACT offset waits for the Stage81 elasticity result.
- **Winner calibration.** Across 163 ordinary seats no minor candidate won; the control puts 0.39 of a minor win in total, `within_mass` 0.25. The actual-winner probability is 0.873 against 0.874. This is a count of zero events, so it is weak evidence either way.

## Not done

No mean, S, R, kappa, ratio-offset, elasticity, local-party, national, balance-multiplier or Māori change; no flag change; no multiplier above 1; no Student-t, mixture, regime or sigma shrinkage; no change to the fitted arms, flags or any other multiplier; the only operational change is the 0.55 wiring above, which is James's decision; `data/sources.json` untouched.

## Wiring of the adopted value

`config/nowcast-2026.json` (`candidateWithinSeatMultiplier`), `scripts/nowcast_config/validate.py` (pinned to 0.55/1.00), `scripts/nowcast_config/scales.py` (effective within scales by class in `scales-2026.json`), `scripts/nowcast_assembly/general.py` (`scaled(..., within)`), `assemble.py` (seat records carry `withinMultiplier`; the gate check `classificationMultipliers` compares both multipliers), and the TypeScript draw-bank schema (optional `withinMultiplier`). Regenerated: the Stage73 development gate (bank digest only), `scales-2026.json`, the Stage74 synthetic fixture. Not regenerated: the Stage77 release rehearsal report, which already predates the configured Stage69 baseline and is owned by the release work.

## Reproduction

```
python3 -m scripts.ordinary_minor_spread.inputs --check
python3 -m scripts.ordinary_minor_spread.fit --check
python3 -m scripts.ordinary_minor_spread.evaluation --check   # about 10 minutes on 4 cores
python3 -m scripts.ordinary_minor_spread.decision --check
python3 -m unittest scripts.tests.test_stage83_ordinary_minor_spread
```
