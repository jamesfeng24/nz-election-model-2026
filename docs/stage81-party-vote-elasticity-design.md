# Stage81 design (frozen before any closed-vector transition error or score was computed): how the local party vote moves with the national change

Decision number D119 (as allocated by the coordinator; D116 to D118 are held by other stages). Internal only: the nowcast configuration default, the draw bank, the TypeScript, the export and every frozen stage are unchanged by this stage. General electorates only; the Māori seats stay on their separate layers.

**One question.** When the national party vote moves from one election to the next, how should a general electorate's previous party vote move with it: in proportion to its own level (the current local party layer), by the same points everywhere, by the same change in log-odds, or somewhere between? Which transform, if any, predicts the held-out 2014 to 2017, 2017 to 2020 and 2020 to 2023 general-seat party votes better, and if the evidence cannot separate them, how should the 2026 forecast carry the difference?

This is the NAT/LAB (and minor-party) elasticity sensitivity reserved by AGENTS.md ("parameterize the retained baseline transformation in one reusable pipeline"; stop if conclusions are materially invariant) and left `unresolved_between_methods` by Stage5 (D026). James agreed to open it on 2026-10-09 after the local preview showed National at about 29.5 general electorates under the current proportional layer against 36 to 37 under same-points movement.

## Disclosure about what was known when this was frozen

- **Stage5 results were known** (METHODOLOGY, "Stage 5"). On the open-ended per-party records, with no closing of the party vector, the log-odds transform led generic macro-party MAE (general 0.496pp against proportional 0.596pp and additive 0.609pp); additive was clearly better for general-seat Labour (2.15pp against proportional 3.58pp and log-odds 2.49pp); National favoured log-odds then additive (2.02, 2.05 against proportional 2.27). Selection stayed `unresolved_between_methods`. Those scores treat each party separately. **Nothing closed (the composition used by the live layer), no margin, lead-count or large-mover score has been computed.**
- The local preview (National about 29.5 electorates proportional against 36 to 37 same-points; Northland a three-way party-vote tie under the proportional layer) was read. It is a 2026 prediction, not a held-out score, and takes no part in the adoption rule below.
- The national shares of every election (NAT 47.0, 44.4, 25.6, 38.1; LAB 25.1, 36.9, 50.0, 26.9; NZF 8.7, 7.2, 2.6, 6.1; ACT 0.7, 0.5, 7.6, 8.6; GRN 10.7, 6.3, 7.9, 11.6) are known and are the conditioning input, so the backtest tests the transform and not a national forecast. The 2017 to 2020 and 2020 to 2023 moves are far larger than the 2026 move being modelled (National x0.73 and Labour x1.06 from 2023), so the backtest is not a small-extrapolation test.
- The 2026 nowcast state is read for the preview only (below). No arm has been run on any 2026 input.

## Inputs (no new sources)

1. The Stage5 per-record file `data/processed/models/party-vote-transform/backtest-records.json` (sha256 `06464b70a46f4efd40297560d100ab969515b8a2f58a971ec6397d5dfbcea602`): canonical-party identity matches, source local share with Stage4 bounds, actual target share, national source and target shares, for the general electorates of five transitions. Its eligibility rules (existing canonical identity, unique source and target match, 0 < P0, P1 < 1; entrants and exits excluded without invented zeros) are unchanged. Primary transitions here: 2014 to 2017 and 2020 to 2023 (observed, same boundaries) and 2017 to 2020 (Stage4 reconstructed boundaries with source-share bounds of at most 0.31pp, mean 0.007pp). Secondary, reported but outside the rule: 2008 to 2011 (observed) and 2011 to 2014 (reconstructed; a few seats have bounds up to 3pp).
2. For the 2026 readout only: the live configuration `config/nowcast-2026.json` (sha256 `745aa827b1c6efc75ca66db4eff27ce7fd5ba93e646e64418ceda162ec7751cf`), the Stage69 baseline `baseline-party-vectors.json` and the national fit it points to.

## The transforms (one parameterised pipeline)

For a seat, let `p` be its previous party vote, `P0` and `P1` the national shares before and after, all over the same set of categories. Every transform maps `(p, P0, P1)` to unclosed values `x_i` and then closes: `q_i = x_i / sum_j x_j`. A category with `p_i = 0` keeps `x_i = 0` in every arm (zero faces are preserved as in the current layer). Clipping is at zero only.

| Arm | Meaning | `x_i` |
|---|---|---|
| **P** | proportional (the current local party layer; Stage23 affinity form) | `p_i P1_i / P0_i` |
| **A** | same points everywhere | `max(p_i + P1_i - P0_i, 0)` |
| **L** | same change in log-odds (the Stage5 `log_odds` rule) | `p_i OR_i / (1 - p_i + p_i OR_i)`, `OR_i = P1_i (1 - P0_i) / (P0_i (1 - P1_i))` |
| **H** | halfway between P and A on the power scale (theta = 0.5) | `(sqrt p_i + sqrt P1_i - sqrt P0_i)_+^2` |

Arms P, A and H are members of one family indexed by `theta in [0, 1]`: `x_i = (p_i^theta + P1_i^theta - P0_i^theta)_+^(1/theta)`, which is A at `theta = 1` and tends to P as `theta -> 0`. L is a separate odds-scale arm, kept because Stage5 and the coordinator asked for it. The family is a convenience for parameterising the question; no `theta` is fitted. `theta = 0.25` and `0.75` are computed as a **profile** that shows the shape of the loss between the arms, never as selectable arms.

- Arm P must reproduce the existing `local_vectors` (`scripts/polling/candidate_integration/propagation.py`) to numerical precision; a test enforces it.
- The composition. In the backtest, `p`, `P0`, `P1` and the actual target share are each restricted to the transition's eligible (persistent) parties and renormalised to sum to one, so the composition among persistent parties is predicted and compared; entrants' and exits' mass is common to all arms and excluded. In the live layer the same transform runs over the whole baseline vector (including the seat's own Other mix). Closing over the persistent parties is the backtest analogue of the live closing and is a stated approximation.
- Source bounds. For 2017 to 2020 (and the secondary 2011 to 2014) every arm is evaluated twice, with each seat's lower and then upper source bounds (each vector renormalised); the rule below is applied at both and must agree. No midpoint is taken.
- No fitted parameter, no leakage: the national shares are the realised target shares (conditioning, as in Stage5); nothing from 2026 and no candidate effect is used.

## Metrics (general seats, each transition separately; seats equal-weighted)

Everything is on the closed persistent-party composition, in percentage points.

- **M1 (primary): National minus Labour margin.** Mean absolute error of `(q_NAT - q_LAB)` against the actual `(a_NAT - a_LAB)`. Reported with the signed bias (mean predicted minus actual) overall and by tercile of the seat's previous National minus Labour margin.
- **M2 (primary): minor-party composition.** Macro-party MAE over every persistent party other than National and Labour with national share at least 1% in either election of the transition (the 1% Stage5 threshold): 2014 to 2017 Green, NZ First, Māori Party, Conservative; 2017 to 2020 ACT, Green, NZ First, Māori Party, Conservative, TOP; 2020 to 2023 ACT, Green, NZ First, Māori Party, TOP, Conservative.
- **M3 (reported): lead calls.** Share of seats where the sign of the predicted National minus Labour margin matches the actual, and the predicted minus actual number of seats with National ahead of Labour.
- **M4 (reported): all persistent parties.** Macro-party MAE, RMSE and vote-weighted MAE of the closed composition.
- **D1 (reported, not in the rule): large movers in their strongest seats.** For every party-transition with `|ln(P1/P0)| >= ln 1.5`, the seats in the top quartile of that party's previous share: mean signed error and MAE of the arm's party share. This is the diagnostic closest to "does NZ First nearly double in its strongest seat" (NZ First 2020 to 2023 is x2.3, ACT 2017 to 2020 is x15, National 2017 to 2020 is x0.58).
- Paired seat-level bootstrap (5,000 resamples, seed 2026081) of the M1 and M2 differences between arms, descriptive only: it ignores the dependence between seats within a transition, understates uncertainty, and there are three transition clusters.

## Frozen adoption rule

Primary arms: P, A, L, H. Transitions: 2014 to 2017, 2017 to 2020, 2020 to 2023, equal weight (the 2017 to 2020 value is computed at both bounds and must give the same outcome of every comparison below, otherwise the class is `mixed_report_to_james`). Thresholds follow the repository's earlier materiality screens: `delta1 = 0.25pp` on M1 and `delta2 = 0.10pp` on M2.

1. Arm X **beats** arm Y on a metric when X's mean over the three transitions is lower by at least the threshold **and** X is lower in at least two of the three transitions.
2. The **retained set** S is the set of primary arms that no other primary arm beats on M1 and that no other primary arm beats on M2.
3. Classes, applied in order:
   - `adopt_X`: S contains exactly one arm X.
   - `carry_mixture`: S contains two or more arms. The 2026 forecast then carries the structural uncertainty as an equal-weight mixture of the arms in S, with one arm drawn **per national draw and shared by every seat** (so the seat counts inherit the dependence), not an average of the arms.
   - `mixed_report_to_james`: S is empty (one arm wins M1 and another wins M2, or the result flips at the 2017 to 2020 bounds). Nothing is chosen; the result is reported to James.
4. **Materiality override (AGENTS.md).** The 2026 readout (below) is computed for the four primary arms. If across all four arms the number of general electorates in which National leads Labour on party vote differs by at most 2 and no seat's top party differs, the class is recorded as `materially_invariant`, the best arm is still named, and no further refinement is pursued.
5. The evidence qualifier is `clear` if the 90% paired-bootstrap interval of the pooled M1 difference between the chosen arm (or the best member of S) and the runner-up excludes zero, otherwise `weak`; no significance claim is made from three clusters.

The adoption is for the **local party layer's mean transform only**. It does not change the local party layer's noise scales (Stage72/73 inversion), the candidate layer, the candidate-balance multiplier, the classification, or the Māori seats.

## The 2026 readout (not part of the rule except step 4)

For each primary arm, using the live configuration's baseline and the national fit's mean (deterministic, no draws): the number of general electorates with National ahead of Labour on party vote, the mean National minus Labour lead change in the general seats against the national change, the largest per-seat differences between arms, and the Northland party-vote composition. Then a development-size run of the live general-seat layer (common random numbers across arms) giving each arm's expected National electorate count and Northland and the most arm-sensitive seats' winner probabilities. The Māori seats are not run (their fallback is not yet wired); results are labelled general seats only.

## Implementation boundary

A reusable `scripts/party_vote_elasticity/` module holds the transforms and the backtest. The live assembly gets an optional `localParty.transform` configuration key (arms P, A, L, H and the mixture) that defaults to the current behaviour, so every existing output and `--check` is reproduced unchanged; this stage does **not** change the default or the live release inputs. Switching the default (or enabling the mixture) is a separate one-line configuration change after the finding is read, because it regenerates the development gate and rehearsal artifacts.

## Explicit do-not list

No fitted elasticity or `theta`, no regression of seat change on national change, no per-party or per-seat-type exponent, no candidate-quality or incumbency terms, no change to the candidate-vote ratio, minor-party spread or classification (other threads), no geography fragmentation, no Student-t or mixture noise, no regime or sigma shrinkage, no national MCMC backtest rerun, no Māori-seat work, no new sources and no `data/sources.json` edit, no change to the live configuration default, the draw bank, the export or the TypeScript, no publication, no later stage.

## Decisions for James

1. The four primary arms and the rule above (in particular `delta1 = 0.25pp`, `delta2 = 0.10pp` and the equal-weight per-draw mixture when the evidence cannot separate arms).
2. Recommended default: this PR adds the switch and the finding but leaves the live default as proportional; the coordinator or James flips it (or enables the mixture) in a small follow-up. The alternative is to flip it in this PR when the rule returns `adopt_X` or `carry_mixture`.
