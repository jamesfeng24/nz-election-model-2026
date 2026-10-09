# Stage83: ordinary-seat minor-candidate spread, frozen pre-registration

**Status: frozen before any Stage83 arm was fitted, simulated or scored.** This file and [design-contract.json](../data/processed/ordinary-minor-spread/design-contract.json) are the frozen checkpoint; the code reads every threshold, arm and rule from the JSON. Later edits are a change of design and must be recorded as a dated amendment. Approved by James on 2026-10-10 in the project thread, with the existing flag list kept unchanged.

## Principle (James)

Seats with two-tick campaigns, electorate arrangements or past minor-party wins are flagged: their outcomes are hard to predict and keep the full, wide spread. Normal seats are consistent and low, so minor candidates there get a narrower spread. D107 narrowed only the National/Labour balance in ordinary seats; this stage tests the same split on the two other candidate components that set a minor candidate's width.

## Question

> Do ordinary-seat multipliers on the candidate **within-remainder** noise (and, separately, the **major-mass** noise), seat and shared parts together, fitted on earlier elections only, beat the D107-only control on the 257 historical candidate records, with flagged seats held at 1.00?

Uncertainty only. No mean, S, R, κ, ratio-offset, elasticity, local-party, national, balance-multiplier or Māori change.

## Why now

The diagnostic that prompted it (not part of the frozen evidence):
- `scaled()` (`scripts/nowcast_assembly/general.py`) multiplies only `balance.seat`; the within and mass components never see the class.
- In 2014–2023 all 10 minor-party electorate wins were in flagged seats and none in the 219 ordinary seats, where the model gives party-affiliated minor candidates 80%/50% intervals that cover 0.93/0.71.
- Stage61 already found candidate within over-covering (R = 0.75) but called it immaterial because it measured only National/Labour widths.

## Arms

| Arm | Ordinary within | Ordinary mass | Role |
|---|---|---|---|
| control | 1.00 | 1.00 | D107 only (balance 0.60 ordinary, 1.00 flagged in every arm) |
| within | m_within | 1.00 | candidate |
| within_mass | m_within | m_mass | candidate |
| within17 | as within, 17-flag ordinary set | 1.00 | sensitivity, never recommendable |
| within_mass17 | as within_mass, 17-flag ordinary set | | sensitivity, never recommendable |

Flagged seats are 1.00 in every arm. No multiplier above 1. Folds as Stage67: 2017 uses 2014; 2020 uses 2014 and 2017; 2023 uses 2014, 2017 and 2020; 2014 is control only.

## Fit

Penalty-free, as Stage67. For each component the Stage48-style per-seat-normalised Gaussian likelihood on standardised total-law residuals, equal elections, ordinary seats only, has the closed-form minimiser `m = sqrt(mean_y r_y)`, capped at 1, where `r_y` is the equal-seat mean ratio of the realised to the model's expected squared residual at that election's own Stage45 fold scales. Seat and shared parts take the same multiplier.
- **Within:** per seat `‖P e‖² / trace(P Σ P)`, `e` the raw within-remainder CLR residual among non-major candidates, `Σ = seat² I + shared² T Tᵀ` (T the party-tag indicator), `P` the centring. The raw residual carries the small mean-preserving location shift, which biases the ratio slightly upward (less narrowing).
- **Mass:** per seat `e² / (shared² + seat²)`, `e` the observed major-mass logit minus the Gaussian-logistic location (the Stage61 residual).
- This is the diagonal (within-election-independence) form, as Stage61's R; shared effects are not separately identified from three or four elections.

## Scoring

Candidate-only harness on the Stage44 records (`component`, 32,768 common-stream draws per seat, Stage45 fold scales): coverage at 50/80/90, CRPS and interval score for party-affiliated minor candidates (independents separately), major-mass CRPS and coverage, National and Labour candidate coverage, CRPS and width, actual-winner probability and minor-win mass. Reported by ordinary and flagged group and by election.

## Decision rule (frozen)

An arm qualifies only if, on ordinary seats in 2017, 2020 and 2023:
- minor 80% coverage is within 0.74–0.86 and nearer 0.80 than control; 90% coverage is at least 0.85; for within_mass, mass 80% coverage is also within 0.74–0.86;
- pooled minor CRPS falls by at least 1% (relative) and is lower in at least 2 of 3 elections;
- **major guard:** National and Labour candidate 80% coverage stays at least 0.70 and drops by no more than 0.03 from control, and their pooled CRPS rises by no more than 1%;
- flagged seats are identical to control;
- the matching 17-flag arm has the same direction (lower minor CRPS, coverage nearer nominal);
- coverage from the first 16,384 draws agrees with the full bank to 0.005.

Selection: both qualify → within_mass only if it beats within by a further 1% and passes every guard, else within; one qualifies → that arm; none → keep control (negligible, worse or mixed). Poor results do not authorise a family search.

## Pre-freeze observations and deviations from the approved draft (disclosed)

The coordinator-level diagnostic had already shown, before this freeze, that narrowing mass ×0.75 in ordinary seats lowers National candidate 80% coverage from 0.731 to 0.689 (Labour 0.799 to 0.776). The reference values 0.55 (within) and 0.75 (mass) were seen on all four elections and are not pre-registered fits. Three changes from the draft James approved, made before any fit:
1. **Penalty-free** (Stage67 precedent) instead of the Stage48 ridge the draft named; Stage67 does not use a ridge.
2. **Within and mass are separate arms**, because of the National-coverage trade-off above.
3. **The composed 193-seat National/Labour width check** is replaced by the candidate-only major guard, since the composed harness needs cached national forecasts.

## Leak (named)

The flags were assigned knowing results and 21 of the 38 came from a residual-ranked list, so ordinary-group narrowing is partly mechanical (Stage67 estimates about 0.72× from trimming alone). The 17-flag arms are the check. As with D107, an adopted multiplier is James's operational choice on development-informed evidence, not a validated calibration; the Stage57 blind replay remains the clean test.

## Consequence for the 2026 classification

A seat's class now sets minor-candidate width too: a wrong "ordinary" understates uncertainty for every candidate there, a wrong "exceptional" only restores today's width. The classification file is unchanged by this stage (James, 2026-10-10).

## Do not

See `doNot` in the contract: no extra arms or searches, no Student-t or other do-not-reopen item, no flag changes, no mean, ratio-offset, elasticity, local-party, national or balance change, no multiplier above 1, no composed bank or national MCMC, no CI or registry edit, no `data/sources.json` edit.

## Wiring, if the rule recommends an arm

`config/nowcast-2026.json` gains ordinary/exceptional within and mass multipliers (exceptional 1.00), `scaled()` and the bank gate read them, and the Stage73 development gate and Stage74 fixture are regenerated. If the rule keeps the control, the mechanism ships with ordinary values 1.00 and the config is behaviourally unchanged.
