<!-- fold: changelog -->
## Stage79 — general-seat candidate polls: frozen update, scoring and assembly hook switched on, 2026-10-10

- **Preserved:** the Wikipedia opinion-polling pages for 2014, 2017, 2020, 2023 and 2026 (`data/raw/polling/seat-polls/2026-10-09/`; 2011 was rate-limited and is not needed), registered with checksums in the new standalone `data/processed/seat-polls/source-registry.json`. `data/sources.json` untouched.
- **Transcribed:** 22 general-seat candidate-vote polls to `data/source-plans/seat-polls/polls.json`; every number is checked against the preserved table text (`scripts/seat_polls/data.py`).
- **Frozen first:** `docs/stage79-seat-poll-design.md` and `data/processed/seat-polls/design-contract.json` (commit `294ddc5`) before any score. Four pre-scoring amendments are recorded in the document.
- **Scored:** leave-one-seat-election-out on 9 eligible polls (7 seat-elections): +1.85 nats, 80% coverage 0.78, frozen finding `adopt`. Weak: −0.02 nats without the four polls whose sample size is assumed. Findings in `docs/stage79-seat-poll-findings.md`.
- **Wired and switched on (D117, James 2026-10-09):** `scripts/seat_polls/apply.py` and `general.simulate_with_poll` update the candidate National/Labour balance of a polled seat before the unchanged Stage47 inversion; `assemble` uses it when `config.seatPolls.enabled` is true, which the config now sets (version 2026-10-10.2). The config validator refuses `enabled: true` unless the frozen finding is `adopt`. The development gate, synthetic fixture bank and rehearsal report were regenerated; the TypeScript draw-bank schema accepts the optional per-seat `seatPoll` record (general seats only).
- **Readout:** `data/processed/seat-polls/readout-2026.json` (2,048 draws, five eligible 2026 seats). Internal; not a forecast.

<!-- fold: state -->
# Stage79 general-seat polls — review-ready, 2026-10-10

Branch `claude/project-thread-nzkrgh` from main `4b20089`, merged with main `d29fbe6` (#103, #104). Authorized by James on 2026-10-09 after the brief of that day; the coordinator allocated Stage79 and D117. The raw acquisition (`3b7bea3`) and the frozen design (`294ddc5`) were committed before any score.

**Results.**
- **Frozen finding `adopt`.** Nine eligible polls in seven seat-elections (2020, 2023): total leave-one-out log score gain +1.85 nats (threshold 1.0); model-plus-poll 80% coverage 0.78 (band 0.65 to 0.95); mean CRPS 0.147 to 0.125; 7 polls improved, 2 worsened.
- **Weak evidence.** Dropping the four 2020 polls with an assumed sample size (S1): −0.02 nats, `not_established`. Fixed inflation 1 (S2): +1.48. Inflation from all N/L polls (S3): +1.50. The gain splits +0.73 narrowing only, +0.43 centre only; the model alone is already over-wide in these (mostly flagged) seats.
- **Poll error.** Variance inflation 5.3 over the sampling floor; poll weight about 0.4 to 0.6 (cap 0.60).
- **2026 readout.** Five eligible seats (Hutt South, Kāpiti, Mt Albert, Waitaki, West Coast-Tasman). The only large move is West Coast-Tasman (National win about 16% to 32% in its configured ordinary class). Auckland Central and Wellington Bays polls are Green-led, so they are context only.

**Not changed.** The Māori layer, D107 multipliers, the classification, the national and party layers, every frozen stage and `data/sources.json`.

**Checks.** See the PR body for exact counts.

**Limits.** Small, selected sample; the historical reference is conditional on the observed local party vote; independence of poll and model error assumed; the 6-week half-life, the 0.60 cap and the 0.12 SD Labour-aligned allowance are development choices; the decay is not validated. The update moves only the National/Labour coordinate, so a Green-led contest cannot use a poll (a third candidate can gain when the poll closes the National–Labour gap).

**Exact next action.** The coordinator reviews and merges the PR. Not started: showing the polls on the published site, Green-led seat polls, any change to the shared candidate-split shift, and one combined Māori poll update.

<!-- fold: decisions -->
## D117 — 2026-10-10 — Stage79: general-seat candidate polls update the National/Labour balance; the frozen rule passes on weak evidence; James switches it on

A published general-seat candidate-vote poll can move the model's candidate National/Labour balance for that seat, but only when the poll's two leading candidates are those two. The update is a precision-weighted shift on the log(N/L) scale (poll variance equals the sampling variance times a fitted inflation, 5.3, plus a 0.12 SD allowance for the Labour-aligned source that ran the Hutt South and Kāpiti polls; weight capped at 0.60; stationary AR(1) decay with a 6-week half-life; total seat SD floored at the shared candidate-split SD). Nothing else changes: no sponsor lean is fitted, no directional shift is applied, party-vote crosstabs are unused, and the Māori and unpolled seats are untouched. The design was frozen before scoring; four amendments made while writing the code (current model reference, N/L-led polls only, one AR(1) rule, shared-SD floor) are recorded in the design document.

Leave-one-seat-election-out on nine eligible 2020 and 2023 polls gave +1.85 nats and 80% coverage 0.78, so the frozen finding is `adopt`. The evidence is weak and the record says so: the gain vanishes (−0.02 nats) when the four polls with an assumed sample size are dropped, and much of it is narrowing in seats where the model is already over-wide. James chose to switch it on (2026-10-09), recording the weak evidence in the decision; `config.seatPolls` is enabled and the validator refuses to enable it unless the finding is `adopt`. Green-led polls (Auckland Central, Wellington Bays) have no matching coordinate and remain context. Number allocated by the coordinator.

<!-- fold: methodology -->
## General-seat candidate polls (Stage79)

For a polled general seat the candidate balance `z = log(National / Labour)` is a Gaussian on the logit scale around the location the Stage47 draw uses, with total SD `sigma = hypot(shared, multiplier * seat)` (D107). A poll with value `y = log(NAT share / LAB share)` and variance `c * (1/(n pNAT) + 1/(n pLAB)) + allowance^2` (c fitted on historical polls; no bias term) moves the location by `rho * w * (y - mu)` with `w = min(0.60, sigma^2 / (sigma^2 + pollVariance))` and `rho = 0.5^(ageWeeks/6)`, and sets the total seat SD to the AR(1) posterior, floored at the shared SD. The conditional probability is rewritten so the unchanged inversion recovers that location and SD; the major-party mass and the remainder split are untouched. Eligible polls are those whose two highest candidate shares are National and Labour; two polls of one pollster within 14 days merge (the later one with 1.5 times the variance). Calibrated and scored leave-one-seat-election-out on 2020 and 2023 polls against the Stage44 out-of-sample replay; see `docs/stage79-seat-poll-findings.md`.

<!-- fold: sources -->
## General-electorate poll pages (Stage79)

The electorate-polling sections of the Wikipedia opinion-polling pages for 2014, 2017, 2020, 2023 and 2026 are preserved unchanged under `data/raw/polling/seat-polls/2026-10-09/` and registered with SHA-256 in the standalone `data/processed/seat-polls/source-registry.json` (secondary compilation, `aggregator_only`; James confirmed on 2026-10-09 that the 2026 numbers match the underlying articles). The 2011 page was rate-limited (HTTP 429, four attempts) and not retrieved; the out-of-sample replay starts in 2014. The 22 candidate-vote rows are hand-transcribed to `data/source-plans/seat-polls/polls.json`, which `scripts.seat_polls.data` checks against the preserved text. `data/sources.json` is untouched. Sponsor facts for Hutt South and Kāpiti (one Labour-aligned operator; Community Engagement Limited conducted both) come from James (2026-10-09).

<!-- fold: roadmap -->
| Stage79 | General-seat candidate polls: frozen update of the National/Labour balance, leave-one-out scoring, assembly hook | review-ready (D117): frozen finding adopt on weak evidence (+1.85 nats; −0.02 without assumed-n polls); switched on by James in the config |
