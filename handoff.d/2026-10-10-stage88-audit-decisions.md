<!-- fold: changelog -->
## Stage88 — James's audit decisions: Māori C–P range, pinned electorate-poll run, list-party overhang, 2026-10-10

- D128: `seatPolls.electorateRun` pins the electorate-poll run that the assembly, its seat evidence and the Stage79 readout read (`scripts/polling/electorate_live.py`). Māori seat polls are cut at the data cutoff. `weekly_refresh.adopt` sets the run with the national input. The development gate, fixture and readout checks join the CI `live` job. No forecast change.
- D129: an electorate win by a party on the 2026 party-list ballot whose vote is inside Other (Te Tai Tokerau Party) is that party's overhang seat, not an s 191(8) independent. The bank gains `partyVote.ballotPartyIds`; the seat layer gains `zeroVotePartyIds`.
- D127: polled Māori seats are also simulated under Stage71's arm P (`scripts/maori_seat_calibration/inflation.py`). The bank's `inflationWinners` becomes the snapshot's per-candidate `winProbabilityInflation`, beside `winProbability` (C), and the release gate checks both. Seat totals stay on C.
- Config `2026-10-10.4`: the decisions list is completed (audit C6). The development gate and synthetic fixture are regenerated. Stage doc: `docs/stage88-audit-decisions.md`.

<!-- fold: state -->
# Stage88 James's audit decisions (D127–D129) — review-ready, 2026-10-10

Branch `claude/audit-fixes-jdkx6w` (restarted from main `ad2937d` after #118 merged). One commit per decision: J2 pin (D128), J3 overhang (D129), J1 range (D127). James chose Range, Pin and Overhang on 2026-10-10 and approved one PR.

**What changed.**
- `seatPolls.electorateRun` is pinned to the 2026-10-10 run (12 polls, sha256 `e746a5da…1641`).
- Māori polls are cut at `national.dataCutoff`.
- The bank gains `inputs.electorateRun`/`electorateRunSha256` and `partyVote.ballotPartyIds` (17 parties), plus `inflationWinners` on polled Māori seats.
- In TypeScript: `zeroVotePartyIds` (seat layer), `winProbabilityInflation` (export detail) and the release gate check on it.
- Config version `2026-10-10.4`.

**What did not change.** Stage66, 71 and 78 outputs, D107 and D121 multipliers, frozen pipelines, `data/sources.json`, the site.

**Effects.**
- Pin: none today, because all pinned polls ended by the 2026-10-07 cutoff.
- Overhang (development bank, 4,096 rows): a bucketed list party wins an electorate in 13.1% of draws. Mean Parliament size goes from 124.73 to 124.83, and bloc majorities move by at most 0.002.
- Range (65,536 draws), leader's chance C to P: Hauraki-Waikato 0.88 to 0.74, Te Tai Hauāuru 0.74 to 0.64, Te Tai Tonga 0.84 to 0.61, Waiariki 0.97 to 0.82.

**Checks.** See the PR body.

**Limits.**
- A list party's own vote stays in Other, so a list-entitled seat for it is not modelled.
- The fallback seats have no P.
- A full frozen replay still takes about 170 of 180 minutes.

**Exact next action.** The coordinator merges on James's go. The site thread then renders `winProbabilityInflation` as the labelled range. Then come the final checks (parallel CI PR, then the production run, which also refreshes the Stage80 rehearsal report: audit C4).

<!-- fold: decisions -->
## D127 — 2026-10-10 — Māori seats show the C–P range: Stage71 arm P beside the Stage66 control for each polled seat (Stage88, James)

D114 said Māori probabilities are shown as a labelled C–P range or withheld, but only C was built (audit J1). James chose the range (2026-10-10).
- Each polled seat is also simulated under Stage71's arm P: the control fit, with σ² and τ² times a λ drawn per draw from Stage71's frozen bootstrap.
- The snapshot carries `winProbabilityInflation` beside `winProbability`. The release gate holds both to MCSE ≤ 0.01.
- Seat totals, MMP and electorate predictions stay on C, one law per draw.
- Fallback seats keep their single labelled number.

Alternatives rejected: C only (known overconfident, Stage71), and P only (Stage71's P was `improves_not_restored` and not adopted). Number from the coordinator.

## D128 — 2026-10-10 — the configuration pins the electorate-poll run; Māori polls are cut at the data cutoff (Stage88, James)

The assembly read the newest electorate-live run, so merging a poll refresh changed the forecast before adoption, and the bank did not record which run it used (audit J2). James chose to pin (2026-10-10).
- `seatPolls.electorateRun {date, pollsSha256}` is required when seat polls are enabled. It is set by `weekly_refresh.adopt` and recorded in the bank inputs.
- Māori seat polls take the same `dataCutoff` as general-seat polls.

Alternative rejected: keep reading the newest run. Number from the coordinator.

## D129 — 2026-10-10 — an electorate win by a party-list party simulated inside Other is overhang (Stage88, James)

The seat layer counted any winner outside the simulated party groups as an s 191(8) independent. That includes Te Tai Tokerau Party, which is on the 2026 party list (audit J3). James chose overhang (2026-10-10).
- Such a party qualifies by its electorate (s 191(4)(b)) with zero party votes of its own, so its seat is overhang (s 192(5)) and Parliament grows.
- Party-less winners stay s 191(8).
- Approximation: the party's own vote stays in Other, so a list-entitled seat for it (about 0.4% of the vote) is not modelled.

Alternative rejected: keep the independent rule as an approximation. Number from the coordinator.

<!-- fold: roadmap -->
| Stage88 | James's audit decisions: Māori C–P range, pinned electorate-poll run, list-party overhang (D127–D129) | review-ready: range built for the four polled seats; pin changes no number; overhang moves bloc majorities by at most 0.002 |
