<!-- fold: changelog -->
## Stage86 — Māori seat polls come from the weekly refresh (D125), 2026-10-10

- `scripts/maori_seat_layer/live.py` reads the Māori rows of the newest Stage82 live-inputs run (hash-checked against `index.json`) in the form the Stage66 simulation reads; `scripts/nowcast_assembly/maori.py` uses it instead of the pinned `polls-2026.json`. A new Māori seat poll is a data-only addition: no refit, no stage regeneration. Poll parties are resolved to the one official candidate of that ballot group (an independent column only when the seat has exactly one independent).
- Waiariki is now polled (21 September to 1 October Whakaata Māori–Curia) and leaves the Stage78 fallback; three seats remain on the fallback. Māori Party win probability: Hauraki-Waikato 0.881 to 0.884, Te Tai Hauāuru 0.772 to 0.745, Te Tai Tonga 0.106 to 0.118, Waiariki 0.957 to 0.966. The only cause is the poll shares (published ex-undecided and rounded, against the primary release's shares of all respondents); see `docs/stage86-maori-live-polls.md`.
- Every officially nominated candidate now appears in a polled seat's output (audit finding): Neil Denby (Hauraki-Waikato), Christine Fisher and Tania Lee Henare (Te Tai Tonga) were missing because the Stage66 layer simulates only the candidates a poll names. Each unpolled candidate gets an equal part of the unnamed remainder (placeholder allocation); winners are unchanged, so they win with probability 0 by construction.
- Not changed: Stage66 calibration and artifacts, Stage71, Stage78, the pinned transcription, the config, the Stage82 files, the export code, `data/sources.json`. The development gate digest and the rehearsal report are regenerated.

<!-- fold: state -->
# Stage86 Māori seat polls from the weekly refresh — review-ready, 2026-10-10

Branch `claude/stage86-maori-poll-switchover-3mf6ym`, from main `50cb5e8` (Stage79 follow-up #113 merged). Authorized by James on 2026-10-10 (the "Māori poll switch-over" proposed by the coordinator: "yeah go ahead"); decision D125 (provisional number from the coordinator). Docs: `docs/stage86-maori-live-polls.md`.

**What changed.** A reader for the Māori polls of the Stage82 live file (`scripts/maori_seat_layer/live.py`), the assembly's Māori step (`scripts/nowcast_assembly/maori.py`) reading it, a reproducible comparison (`scripts.maori_seat_layer.live_comparison`), 14 new tests in `test_stage86_maori_live_polls.py`, the Stage80 wiring tests (polled set read from the live file), the electorate-live reader guard (two authorised readers), the development gate digest and the rehearsal report. **What did not.** Stage66 calibration and artifacts, Stage71, Stage78 and its stored forecast, `polls-2026.json`, `config/nowcast-2026.json`, Stage82 files, export code, `data/sources.json`, any fitted parameter.

**Audit fix.** Three officially nominated candidates were missing from polled-seat outputs (Neil Denby, Hauraki-Waikato; Christine Fisher and Tania Lee Henare, Te Tai Tonga). `nowcast_assembly.maori.with_unpolled_candidates` adds every rostered candidate; the equal split of the unnamed remainder is a placeholder and they cannot win (Stage66).

**Numbers.** Four Māori polls in the live file (Hauraki-Waikato, Te Tai Hauāuru, Te Tai Tonga, Waiariki); three seats on the arm F fallback (Ikaroa-Rāwhiti, Tāmaki Makaurau, Te Tai Tokerau). Closed poll shares differ from the pinned transcription by at most 1.2 points (rounding of ex-undecided published shares); Māori Party win probabilities move by at most 2.7 points (Te Tai Hauāuru), at 200,000 draws.

**Limits.** Live rows are `aggregator_only` and rounded; the pinned ones were checked against primary bytes. One poll per seat (latest by fieldwork end), no combining across pollsters. The Stage82 parser stops on a column label it does not know (a Te Tai Tokerau Party column would). The recorded Stage66, Stage71 and Stage78 artifacts still describe the three-seat 2026-10-07 snapshot and Stage78 still lists Waiariki as unpolled. A refresh that adds a Māori poll makes the development gate digest and the rehearsal report stale until regenerated.

**Exact next action.** The coordinator reviews and merges. Not started: Māori candidate-name entry in the live file, combining several pollsters in a Māori seat, any change to the Stage66 layer.

<!-- fold: decisions -->
## D125 — 2026-10-10 — Stage86: Māori seat polls are read from the Stage82 live file; Waiariki is polled

The nowcast assembly takes the 2026 Māori seat polls from the newest Stage82 live-inputs run instead of the pinned 2026-10-07 transcription. A new Māori seat poll is a data-only addition: the Stage66 calibration, Stage71 and Stage78 decisions and every fitted parameter are unchanged, and the Māori seats keep their own calibration (not merged into the general-seat layer). As in Stage66, the latest poll per seat by fieldwork end is used. The live file names parties, so each is resolved to the one active official candidate of that ballot group; anything that does not resolve to exactly one candidate stops the build. Waiariki, which the live file polls, leaves the Stage78 fallback (D115, D118); the other three unpolled seats keep arm F. James approved the switch-over on 2026-10-10. Number provisional (allocated by the coordinator).

<!-- fold: methodology -->
## Māori seat polls from the live file (Stage86, D125)

For each Māori seat the newest poll in the Stage82 live file (fieldwork end, then id) enters the unchanged Stage66 default layer: candidate shares are the published electorate-vote percentages, closed over the named candidates (the excluded undecided and "other" shares drop out, as in the pinned transcription). Candidates are ordered by descending share. A seat with a poll uses the Stage66 layer; a seat without one uses the Stage78 arm F fallback. No weight on pollster, sample size or age is added.

<!-- fold: sources -->
## Māori seat polls read by the nowcast assembly (D125)

`scripts/maori_seat_layer/live.py` reads `data/processed/polling/electorate-live/<newest run>/polls.json` (Stage82; Wikipedia aggregator evidence; hash and count checked against `index.json`), the Māori rows only. The pinned `data/source-plans/maori-seat-layer/polls-2026.json` still serves the recorded Stage66, Stage71 and Stage78 artifacts. The Waiariki poll also exists as the preserved Spinoff page (`data/processed/polling/maori-seat-polls-2026-10/`); the assembly does not read it. `data/sources.json` is untouched.
