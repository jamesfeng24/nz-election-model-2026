<!-- fold: changelog -->
## Stage78 — no-poll fallback for the unpolled Māori seats, 2026-10-10

- **Question:** can Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau and Te Tai Tokerau get candidate shares and winners without a seat poll, and does borrowing the polled seats' swing help? Frozen design `docs/stage78-maori-fallback-design.md` committed before any score.
- **Model** (`scripts/maori_seat_fallback/`): the 2023 official result carried forward by party label; Stage66 estimators with `b = 0` calibrated on the 2014→2017, 2017→2020 and 2020→2023 changes (`sigma` 0.257, `tau` 0.443 on 19 contrasts); entrants resampled from history; one split-incumbent record (the Te Tai Tokerau Party candidate, `phi` uniform); optional Gaussian posterior of the shared shift from the polled seats' simulated outcomes (arms FC with the Stage66 layer, FP with the Stage71 layer).
- **Result:** the frozen swing rule returns `mixed_report_to_james` for both swing arms (leave-one-election-out, 21 contests: log score -0.993 / -0.995 against -1.003 for 2023-only, Brier no better). Only 2023-only passes the calibration class; the 2023 wave is unanticipated in the chronological check. James chose 2023-only (F) on 2026-10-09; recorded in `inputs-2026.json`.
- **Artifacts:** `data/processed/maori-seat-fallback/` (design contract, calibration, scores, findings, 2026 forecast, 200-draw preview, summary, manifest); judgement inputs `data/source-plans/maori-seat-fallback/inputs-2026.json`.
- **Not touched:** Stage66/71, the configuration, the assembly, the draw bank, TypeScript, `data/sources.json`. 35 new tests.

<!-- fold: state -->
# Stage78 no-poll fallback for the unpolled Māori seats — review-ready, 2026-10-10

Branch `claude/project-thread-0lxx4d` from main `2287e57` with the Stage50 part 2 branch (PR #102) merged in, because the 2026 slates are read from its official table; rebase onto main once #102 has merged. Authorized by James (release-checklist item 15 and D114, 2026-10-07); started after the official candidate list was published.

**Results.**
- **Calibration** (3 transitions, 19 contrasts): `sigma` 0.257 (16 degrees of freedom), `tau` 0.443 (3 elections). Election means of the MP-versus-Labour log-odds change: -0.08 (2017), +0.10 (2020), +0.80 (2023).
- **Leave-one-election-out, 21 seat contests:**
  - 2023-only (F): log score of the winner -1.003, favourites 0.753 predicted against 0.667 observed (z -0.98), class `calibrated`;
  - swing arms FC and FP: -0.993 and -0.995, Brier no better, class `overconfident`; rule `mixed_report_to_james`, evidence `weak`.
- **Chronological 2023:** F `overconfident` (favourite z -4.08): trained on quiet elections, `tau^2 = 0`; the 2023 wave was unanticipated.
- **2026, win probability by seat (F; FC to FP):** Waiariki Waititi (TPM) 0.96; 0.97 to 0.91. Ikaroa-Rāwhiti Tangaere-Manuel (LAB) 0.64; 0.83 to 0.76. Tāmaki Makaurau Leoni (LAB) 0.50; 0.70 to 0.65. Te Tai Tokerau Prime (LAB) 0.66; 0.76 to 0.72. The whole gap between F and the swing arms is Te Tai Tonga's poll (the incumbent is an independent). Without it the swing arms land near F.
- **Assumption:** `phi` (share of the 2023 Te Pāti Māori vote that follows the Te Tai Tokerau Party candidate) is uniform; 0.2, 0.5 and 0.8 move the Te Tai Tokerau Labour probability from 0.60 to 0.79.

**Checks.** See the PR body. **Limits.** Three transitions; `tau` rests on one wave; party-label carry-forward only (no incumbency or mean reversion); leave-one-election-out is not out of sample in time; no national input.

**Exact next action.**
1. A separate small stage wires the chosen F into `scripts/nowcast_assembly/maori.py`, sets `maori.unpolledFallbackModel`, maps the official Māori candidates to export ids and adds the export label.
2. Then the first real run once the general-seat classification is entered.

<!-- fold: decisions -->
## D115 — 2026-10-10 — labelled fallback for the four unpolled Māori seats (Stage78)

- **Model.** The 2023 official Māori-seat result carried forward by party label, with Stage66's estimators at `b = 0` calibrated on the 2014 to 2023 changes, entrants resampled from history, and a split-incumbent fraction `phi ~ U(0,1)` for the Te Tai Tokerau Party candidate. Optionally the shared Māori Party-label shift takes its Gaussian posterior from the polled seats' simulated outcomes (FC with the Stage66 layer, FP with the Stage71 layer).
- **Finding.** `mixed_report_to_james`: the held-out scores cannot separate 2023-only from the swing arms; only 2023-only is `calibrated` (and overconfident on the 2023 fold). The 2026 gap between them is Te Tai Tonga's poll.
- **Registration.** James chose 2023-only (F) on 2026-10-09 (`data/source-plans/maori-seat-fallback/inputs-2026.json`); the swing arms stay as flagged sensitivities. Nothing is wired into the configuration or the assembly by this stage.
- Number D115 is the next free on main; the coordinator may renumber.

<!-- fold: methodology -->
## Stage78 no-poll Māori seat fallback (D115)

Estimand: for a Māori electorate without a seat poll, per draw, each candidate's share of valid candidate votes over the complete 2026 slate and the winner. A candidate whose party label stood once in the seat in the previous election carries that predecessor's closed share (`log m`); other candidates are entrants whose share is resampled from the training transitions (two pools). Log shares get independent noise `sigma^2` and the Māori Party label one shared shift `u ~ N(0, tau^2)`, both estimated with the unchanged Stage66 functions on the change in Māori Party-versus-Labour log-odds between consecutive elections (`b = 0`, parameter uncertainty by scaled inverse chi-square). Borrowing the polled seats' swing uses the exact Gaussian posterior `u | xbar ~ N(kappa xbar, kappa 2 sigma^2 / k)`, `kappa = tau^2 / (tau^2 + 2 sigma^2 / k)`, drawn per draw from the polled layer's simulated outcomes, so the polled and unpolled seats stay dependent. Scored on 21 official results (leave-one-election-out) and 7 (chronological 2023) by log score and multi-candidate Brier score of the winner, favourite calibration and share coverage. The split-incumbent fraction is an assumption, not a fit.

<!-- fold: roadmap -->
| Stage78 | No-poll fallback for the four unpolled Māori seats: previous result carried forward, optionally with the polled seats' swing (internal; frozen pre-registered design) | review-ready (D115 provisional): `mixed_report_to_james`; James chose 2023-only (F) |

<!-- fold: sources -->
## Waiariki poll of 2026-10-07 (Whakaata Māori–Curia), recorded 2026-10-09

- Page bytes of The Spinoff's republication of the Te Ao Māori News story preserved under `data/raw/polling/maori-seat-polls-2026-10/` with headers and fetch log; dated registry and transcription in `data/processed/polling/maori-seat-polls-2026-10/` (`python3 -m scripts.polling.waiariki_poll_2026_10 --check` re-verifies the bytes and every transcribed phrase). `data/sources.json` is untouched.
- Candidate vote: Waititi (TPM) 42, Waikato (GRN) 16, Boynton (LAB) 14, Wharewera (TOP) 3; undecided 18, other 6; 500 respondents, fieldwork 21 September to 1 October, ±4.5. Party vote: LAB 24, TPM 23, GRN 22, TOP 0, unsure 14 (base not stated). The Te Ao Māori News original and Curia tables were not found.
- **Recorded only.** The pinned `data/source-plans/maori-seat-layer/polls-2026.json` (hash pinned by Stage66, Stage71 and Stage78) is unchanged, so Waiariki stays an unpolled seat (fallback). James (2026-10-09) preferred not to update the layer each time one electorate poll appears; adopting this record, and any other new seat polls, is one later authorized update that regenerates the pinned artifacts.
