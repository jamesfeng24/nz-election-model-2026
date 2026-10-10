# Stage86: Māori seat polls come from the weekly refresh (D125)

Internal development record, not published. Authorized by James on 2026-10-10 (the "Māori poll switch-over" in the coordinator's proposal: "yeah go ahead"). Decision D125 (number allocated by the coordinator). A data-path change only: no refit, no new model, no parameter change.

## What changed

- **Reader** (`scripts/maori_seat_layer/live.py`). Reads the Māori rows of the newest Stage82 live-inputs run (`data/processed/polling/electorate-live/`, hash and count checked against `index.json`) and returns them in the form the Stage66 simulation already takes. As in Stage66, the latest poll per seat by fieldwork end is used; earlier polls of a seat are returned as superseded.
- **Assembly** (`scripts/nowcast_assembly/maori.py`). The polled seats are now the seats with a Māori poll in the live file, not the three in the pinned transcription. A seat with a poll runs the Stage66 default layer; a seat without one keeps the Stage78 arm F fallback (D115, D118). The live file names parties, not people, so each poll party is resolved to the one active official candidate whose ballot group is that party's (an independent column resolves only when the seat's roster has exactly one independent). The existing surname-and-party match against the roster still runs afterwards.
- **Waiariki is polled.** The live file holds the 21 September to 1 October Whakaata Māori–Curia poll of Waiariki, so the seat moves from the fallback to the Stage66 layer. Hauraki-Waikato, Te Tai Hauāuru and Te Tai Tonga stay polled.
- **Unchanged.** Stage66 calibration and its stored artifacts, Stage71 (inflation and era-bias arms, the 2026 readout), Stage78 (fallback arms and its stored forecast, still for the four seats it was run on), the pinned `polls-2026.json`, `config/nowcast-2026.json`, the Stage82 files (read only), the export code, `data/sources.json`. The Māori seats keep their own calibration and are not merged into the general-seat poll layer.

Regenerated: the development gate digest and, at full size, the Stage77 rehearsal report (only digests and Māori seat records change).

## Why today's Māori numbers move

Same seed, same calibration, same per-seat random streams (a seat's draws do not depend on the other seats), 200,000 draws (win probability Monte Carlo error at most 0.0011):

| Seat | Winner | Pinned transcription | Live file |
|---|---|---|---|
| Hauraki-Waikato | Māori Party | 0.881 | 0.884 |
| Te Tai Hauāuru | Māori Party (Labour) | 0.772 (0.228) | 0.745 (0.255) |
| Te Tai Tonga | Labour (Māori Party) | 0.853 (0.106) | 0.844 (0.118) |
| Waiariki | Māori Party | 0.957 (fallback F) | 0.966 (poll) |

The cause is the poll shares, nothing else. The pinned file holds each candidate's share of all respondents as the primary release published it (for example Te Tai Hauāuru 38, 27, 10 with 6 other and 18 undecided). Wikipedia lists the shares excluding undecided respondents, as whole numbers (46, 34, 13). The Stage66 simulation closes shares over the named candidates, so the exclusion does not matter, but the rounding does: the closed shares differ by at most 1.2 points (Te Tai Hauāuru Māori Party 0.507 against 0.495, Labour 0.360 against 0.366, National 0.133 against 0.140), which moves that seat's Māori Party win probability by 2.7 points. That is smaller than the rounding uncertainty of either source and is not a model change. Waiariki's move from 0.957 to 0.966 comes from replacing the fallback's carried-forward 2023 result with the poll (Waititi 52, Waikato 20, Boynton 18, Wharewera 3 excluding undecided).

Reproduce: `python3 -m scripts.maori_seat_layer.live_comparison 200000`.

## Limits

- **Evidence grade.** Every live row is `aggregator_only`: a volunteer-edited transcription of the primary release, rounded, and not checked against the primary page. The pinned transcription was verified against preserved primary bytes. Any future poll comes in at the weaker grade and relies on the Stage82 blockers and the review PR.
- **Parties the page can carry.** The Stage82 parser accepts only its fixed column labels. A Te Tai Tokerau Party column (Kapa-Kingi) or any other new label stops the refresh for a human; the Māori reader also refuses a label it has no code for. A poll share for a party without exactly one official candidate in the seat stops the build.
- **One poll per seat.** Two pollsters in a seat are not combined (Stage66 design: the later poll is used, `do not` list: no poll averaging). The combining rule used for general seats (D123) was not applied; a Māori poll from another pollster or with a different sample is treated as the Curia polls were.
- **Poll age.** The Stage66 layer does not age a poll; the live reader applies no cutoff beyond Stage82's own rule that fieldwork cannot end after the run date.
- **Recorded artifacts now describe a snapshot.** Stage66 `forecast-2026.json`, Stage71's 2026 readout and Stage78's fallback forecast still report the three-seat 2026-10-07 transcription, and Stage78 still lists Waiariki as unpolled. They are historical and are not regenerated; the live view is the assembly. `config/nowcast-2026.json` still says "the four unpolled seats" in the text of the D114 decision record; the config is not edited.
- **Stale checks after a refresh.** A weekly refresh that adds a Māori poll changes poll ids in the seat records, so the development gate digest and the rehearsal report are stale until regenerated, as for general seats under D123.

## Reproduction

```
python3 -m unittest scripts.tests.test_stage86_maori_live_polls scripts.tests.test_stage80_maori_wiring scripts.tests.test_maori_seat_layer scripts.tests.test_maori_seat_calibration scripts.tests.test_maori_seat_fallback
python3 -m scripts.nowcast_assembly.run --check
python3 -m scripts.maori_seat_layer.live_comparison 200000
python3 -m scripts.release_rehearsal.run --check   # full size, about 35 minutes on 4 cores
```
