<!-- fold: changelog -->
## D134 — Epsom: Seymour's expected candidate share lifted to about 45%, 2026-10-11

- New `candidate.candidateExponentOffsets` (config `2026-10-11.1`, decisions list gains D134): one named candidate's log-weight in the candidate step, Seymour +0.40 in Epsom. His expected share moves from 36% to 45% and his win probability from 65% to 79%; spread, other seats, the national and Māori layers and MMP unchanged. The development gate and readout are regenerated; injected (test and fixture) slates ignore it. See `docs/d134-epsom-seymour-offset.md`.

<!-- fold: decisions -->
## D134 — 2026-10-11 — Epsom: Seymour's candidate weight raised by 0.40

James (2026-10-11, project thread; "45% is good, if a poll appears that drastically changes things we can reconsider later"). The model gives Seymour 36% of the Epsom candidate vote because National's party vote falls from 52% to 36%; the 2020 and 2023 split-ticket tables give an average of about 45%. His candidate log-weight is raised by 0.40 (`candidate.candidateExponentOffsets`), taking his expected share to 45.2% and his win probability from 64.8% to 79.2% with the seat's noise unchanged (exceptional, multipliers 1.00). James's judgement, not a fitted value. Reconsider when an Epsom poll appears. Not done: any narrowing of the spread, other seats' split rates.

<!-- fold: methodology -->
### Candidate-specific weight offset (D134)

A single named candidate can carry a log-weight offset in the candidate step, added to the exponent beside the D132 party-level offsets. It is James's judgement and is recorded in the config with its evidence; it is used once (Seymour, Epsom, +0.40).

<!-- fold: state -->
# D134 Epsom Seymour offset — local and pushed to `claude/project-thread-83gu96`, 2026-10-11

Built on the seat-poll branch (D133) with the TOP offset (D132) merged in. New: `docs/d134-epsom-seymour-offset.md`, `scripts/tests/test_d134_epsom_seymour_offset.py`; changed: `config/nowcast-2026.json`, `scripts/nowcast_assembly/general.py`, `assemble.py`, `scripts/seat_polls/readout.py`, `scripts/nowcast_config/validate.py`, development gate (regenerated; gate, fixture and readout reproduced). Decision number D134 is provisional until the coordinator confirms. **Exact next action:** fold this branch into #127 (one push), run the full Python tests and `npm run test/typecheck/build`, then the PR owner asks James for the merge go.
