<!-- fold: changelog -->
## Stage81 — how the local party vote moves with the national change, 2026-10-10

- **Question:** should a general seat's 2023 party vote move proportionally with the national change (the current layer), by the same points, by the same log-odds, or between? Frozen design `docs/stage81-party-vote-elasticity-design.md` (with a knock-on amendment) committed before any closed-vector score.
- **Backtest:** closed persistent-party compositions of the Stage5 general-seat records, 2014 to 2017, 2017 to 2020 (evaluated at both source bounds) and 2020 to 2023, arms P, A, L and H (a power-family arm halfway between P and A). Metrics: National minus Labour margin (M1), minor-party composition (M2), lead calls, all parties, the Stage44 residual scale (M5) and large movers in their strongest seats (D1).
- **Finding:** `carry_mixture` of P, L, H, evidence weak; no arm beats another on the margin and A is rejected on minor parties. The 2026 National electorate count is invariant across arms (29.61 P, 29.65 A, 29.79 L, 29.65 H at 256 draws, general seats); the arms move Northland (NZ First win probability 0.43 P to 0.32 A) and a few minor-party-strong seats.
- **Code:** `scripts/party_vote_elasticity/`; an optional `localParty` configuration key (`transform` P, A, L, H or `mixture` with `arms`) read by `scripts/nowcast_assembly/general.py` and `assemble.py`. The committed configuration has no such key, so the frozen layer runs and the development gate is reproduced.
- **Not touched:** `config/nowcast-2026.json`, the Stage5 records, the candidate fit, the noise scales, the draw bank, the export, TypeScript and `data/sources.json`. 24 new tests.

<!-- fold: state -->
# Stage81 party-vote elasticity — review-ready, 2026-10-10

Branch `claude/stage81-elasticity-ge0ebx` from main `b0fc604`. Opened by James on 2026-10-09; design approved by James the same day, who kept the choice of default for himself after the results.

**Results.** See `docs/stage81-party-vote-elasticity-findings.md`.
- **Rule:** `carry_mixture` of P, L, H, `weak`. Pooled M1 (margin error, pp): P 4.05, A 3.85, L 3.95, H 3.77; M2 (minor parties): 0.62, 0.87, 0.58, 0.62. A is beaten on M2 by every other arm; no arm beats another on M1 (H beats P pooled by 0.27pp but is lower in only one of three elections). Proportional is best on National's 2017 to 2020 fall and on NZ First's 2020 to 2023 rise in its strongest seats (signed error +0.2 and -0.9pp).
- **2026 readout** (256 draws, general seats, PR #104 classification as a copy): National 29.6 to 29.8 electorates under every arm; the arms differ only in minor-party-strong seats (Northland NZ First 0.43 P, 0.41 L, 0.36 H, 0.32 A).
- **Knock-on if the default changes:** S, R, kappa (trained on proportional-built party vectors) and the local noise scales need a refit; the candidate balance scale and D107 multipliers a recheck; M5 shows P and L share a residual scale while A and H do not.

**Checks.** See the PR body. **Limits.** Three elections; persistent-party closure; realised national shares; readout is development-size and general seats only.

**Exact next action.**
1. James decides whether to keep proportional (default, recommended), adopt a P/L mixture (no noise recalibration needed), or the rule's P/L/H mixture (needs the refits above).
2. If the default changes, a separate small stage sets `localParty` in the configuration, rebuilds the constructed party vectors with the new transform, refits S, R, kappa and the party noise scales, and regenerates the development gate and rehearsal.
3. The candidate-vote ratio and minor-party spread questions are handled elsewhere.

<!-- fold: decisions -->
## D119 — 2026-10-10 — party-vote elasticity: the backtest cannot separate proportional, log-odds and the halfway transform; default stays proportional pending James (Stage81)

- **Rule outcome.** `carry_mixture` of proportional, log-odds and the halfway transform (weak). Same-points movement is rejected on minor-party composition and produces exact zero shares the noise scales were not calibrated for.
- **2026 consequence.** The National general-electorate count is invariant across arms (29.6 to 29.8); only minor-party-strong seats move. The earlier preview's 30 versus 36 to 37 is not explained by this transform.
- **Registration.** Nothing is adopted; the live default is unchanged. James decides after reading the findings. Number D119 as allocated by the coordinator.

<!-- fold: methodology -->
## Stage81 local party vote and the national change (D119)

Estimand: the closed party composition of a general electorate in the target election given its source composition and the source and target national compositions. Arms map `(p, P0, P1)` to unclosed `x` and close: P `p P1/P0`; A `max(p + P1 - P0, 0)`; L `p OR/(1 - p + p OR)` with `OR = P1(1 - P0)/(P0(1 - P1))`; H `(sqrt p + sqrt P1 - sqrt P0)_+^2`; a category with `p = 0` stays zero. Backtest on the Stage5 general-seat records restricted to each transition's persistent parties and renormalised, so the national shares are realised, not forecast. Adoption: an arm beats another on a metric if it is lower on average by the threshold (0.25pp on the National minus Labour margin, 0.10pp on minor-party composition) and in at least two of three elections; the retained arms are those no other arm beats on either metric; one retained arm is adopted, several are carried as an equal-weight mixture drawn once per national draw and shared by all seats.

<!-- fold: roadmap -->
| Stage81 | Party-vote elasticity: how a general seat's previous party vote moves with the national change (internal; frozen pre-registered design) | review-ready (D119): `carry_mixture` P/L/H, weak; default unchanged, James decides |
