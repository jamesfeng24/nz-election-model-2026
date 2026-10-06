# Stage67 findings: ordinary versus exceptional candidate-balance seat scale

Frozen design: [stage67-exceptional-balance-scale-design.md](stage67-exceptional-balance-scale-design.md). The original freeze is commit `790cae1`, before any fit. Amendment 1 is commit `e60142b`: it came after the original arms were fitted and before any score was read; one unread bank was deleted. Artifacts are in `data/processed/exceptional-balance-scale/` (`fit.json`, `evaluation.json`, `decision.json`). Decision D101. **Nothing is adopted.**

## Headline

The finding under the frozen rule is **`recommend_twogroup_exc1_for_james_signoff`**, with **`flag_selection_sensitive`** stated.

Reading (interpretation, not rule output): holding flagged seats at the frozen scale and narrowing the rest beats Stage60's single multiplier on these elections. But the extra narrowing appears only when the flags made with outcome knowledge are used. With the 17 flags that were not taken from the residual-ranked list, there is no gain over Stage60. So this stage does not establish that ordinary seats deserve a narrower scale than Stage60's free arm; that needs blindly made flags.

| Arm vs free (193 decision seats) | ΔN/L CRPS pp | Relative | By election 2017 / 2020 / 2023 | 90% bootstrap | Label | Floors |
|---|---:|---:|---|---|---|---|
| twogroup_exc1 | −0.0368 | −1.09% | −0.080 / −0.003 / −0.027 | [−0.054, −0.019] | IMPROVES | pass |
| twogroup (fitted exceptional) | −0.0083 | −0.25% | −0.091 / +0.043 / +0.023 | [−0.038, +0.023] | NEGLIGIBLE | pass |
| twogroup17 (sensitivity) | +0.0052 | +0.15% | +0.013 / +0.012 / −0.009 | [−0.005, +0.016] | NEGLIGIBLE | exceptional 50% fails |

**twogroup versus twogroup_exc1 is WORSE**: +0.0285pp, bootstrap [+0.008, +0.050]. A fitted exceptional multiplier (1.74 / 1.89 / 1.53, trained on earlier elections) overshoots. On the 30 flagged decision seats it covers 0.62/0.88/0.92 at 50/80/90 with a 90% width of 31.3pp, against 0.43/0.82/0.88 and 22.8pp at the frozen scale, and its CRPS there is worse (4.99 vs 4.80). The coordinator's caution was right: the frozen scale is enough for flagged seats on this evidence.

Against the control, twogroup_exc1 scores −0.098pp (bootstrap in `decision.json`). Stage60's free arm scores −0.061pp.

## Multipliers (earlier-trained; scale on the frozen seat balance sd)

| Arm | 2017 | 2020 | 2023 | 2026 refit (not scored) |
|---|---|---|---|---|
| free (Stage60) | 0.834 | 0.854 | 0.782 | 0.790 |
| twogroup_exc1 ordinary (flagged at 1.00) | 0.595 | 0.615 | 0.607 | 0.604 |
| twogroup ordinary / exceptional | 0.595 / 1.737 | 0.615 / 1.889 | 0.607 / 1.526 | 0.603 / 1.458 |
| twogroup17 ordinary / exceptional | 0.839 / 0.373 | 0.869 / 0.281 | 0.802 / 0.239 | 0.814 / 0.268 |

The 2017 fold has only 8 flagged training seats (1 for twogroup17).

## Coverage and widths (N/L candidate coordinates, 50 / 80 / 90)

| Population | Arm | Coverage | Width pp |
|---|---|---|---|
| ordinary, 163 seats | free | 0.583 / 0.893 / 0.954 | 8.92 / 16.85 / 21.50 |
| ordinary, 163 seats | twogroup_exc1 | 0.543 / 0.828 / 0.933 | 7.73 / 14.63 / 18.70 |
| ordinary 2020, 55 seats | twogroup_exc1 | 0.436 / 0.755 / 0.918 | 7.71 / 14.60 / 18.65 |
| flagged, 30 seats | twogroup_exc1 (= control) | 0.433 / 0.817 / 0.883 | 9.49 / 17.89 / 22.83 |
| all 193 | twogroup_exc1 | 0.526 / 0.826 / 0.925 | 8.00 / 15.14 / 19.34 |

The ordinary-seat floor holds in every election, but 2020 sits close to it (50%: 0.436 against a threshold of 0.40). Even at the frozen scale, flagged seats under-cover at 50%.

## The leak, and the 17-flag check (amendment 1)

The scored seats were flagged by an author who knew their results. Removing them therefore narrows what remains partly mechanically (the coordinator estimates about 0.72× from trimming alone, against the roughly 0.76 seen in-sample). Earlier-only fitting does not remove that.

The 17-flag arm is the check:

| Population (17-flag sets, decision years) | Arm | Coverage 50 / 80 / 90 | CRPS pp | 90% width pp |
|---|---|---|---|---|
| ordinary17, 177 seats (includes the 21 list-derived flags) | free | 0.562 / 0.876 / 0.935 | 3.373 | 21.37 |
| ordinary17, 177 seats | twogroup17 | 0.565 / 0.876 / 0.938 | 3.377 | 21.54 |
| exceptional17, 16 seats | free | 0.500 / 0.906 / 0.969 | 3.224 | 21.64 |
| exceptional17, 16 seats | twogroup17 | 0.344 / 0.656 / 0.875 | 3.249 | 16.20 |

By election, ordinary17 coverage under twogroup17 is 0.608/0.883/0.933 (2017), 0.449/0.839/0.924 (2020) and 0.638/0.905/0.957 (2023).

When the residual-derived flags stay in the ordinary group, the fitted ordinary scale stays at the free arm's size (0.80–0.87) and nothing improves. The 17 flags made without the residual list were, if anything, *less* variable than ordinary seats. Taken together, the stage cannot separate a genuine ordinary/exceptional difference from the mechanical effect of removing known misses. The primary gain of about 1.1% over free should be read as an upper bound.

## Checks

- Original-arm fits: Powell agreement ≤ 1e-15 and central-difference gradients ≤ 1e-10 for every fold and arm, with no bound contact. The Powell check runs over the free parameters only, because an inert third coordinate stalled its line searches; this is an implementation detail, and the tolerance is unchanged.
- Control and free records equal Stage60's seat by seat (difference 0).
- Non-balance draws and the N+L mass are identical across arms (2.2e-16).
- Resolution and doubling gates pass for every arm that was labelled.
- `python3 -m scripts.exceptional_balance_scale.{inputs,fit,evaluation,decision} --check` pass locally (evaluation about 53s on 4 cores).
- `scripts.tests.test_stage67_exceptional_balance_scale`: 8 pass, about 18s.

## Limits

- Three reused development elections, flags made with outcome knowledge, and 30 flagged decision seats.
- Applying this in 2026 needs 2026 seats flagged through the Stage56 manual interface.
- The shared scale, local-party and national layers are unchanged.
- No composed bank and no calibrated-probability or seat-win claim.

## Recommendation (for James; nothing adopted)

1. Do not adopt the narrower ordinary multiplier (about 0.60) on this evidence. The leak-free check gives it no support.
2. Treat "flagged seats at the frozen scale (1.00), never narrowed" as the structural lesson. It is cheap and safe, and it beat a fitted wider scale.
3. If the narrower ordinary scale matters, test it with blind flags from the Stage57 manual replay. That is the clean version of this stage.
4. Stage60's free arm (about 0.79) remains the single-scale recommendation pending James.
