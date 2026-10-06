# Stage66 findings: Māori electorate seat layer (internal, no publication)

Design: [stage66-maori-seat-layer-design.md](stage66-maori-seat-layer-design.md), frozen before any calibration error was displayed (two amendments, both made before any value was shown, are recorded in it). Everything below is development output. Reproduce with `python3 -m scripts.maori_seat_layer.run` (add `--check` to verify; about 3 seconds, no network).

## What was built

- Source acquisition: 25 historical Māori electorate polls (2014: 4, 2017: 7, 2020: 7, 2023: 7), preserved as raw bytes with a dated registry; official Māori-seat candidate results 2014 to 2023 read from the preserved Electoral Commission files; the three 2026 Whakaata Māori–Curia seat polls from the Stage52 captures. All transcriptions are checked against the preserved bytes by `scripts.maori_seat_layer.verify` (Wikipedia table rows for the historical polls; verbatim release text for 2026 and for the 2023 and 2020 news cross-checks).
- A calibrated error model (`fit.py`), a per-draw simulator with per-seat random streams (`simulate.py`), a runner with `--check` (`run.py`), and 27 tests.
- A data-file interface for the missing four polls: add a record to `polls-2026.json`, remove the seat from `unpolledSeats`, rerun.

## Calibration (frozen rule)

| Election | polls with an MP and a Labour candidate | mean error D (MP minus Labour log-odds) | within-election sd |
|---|---|---|---|
| 2014 | 4 | -0.07 | 0.45 |
| 2017 | 6 | -0.11 | 0.34 |
| 2020 | 7 | +0.34 | 0.26 |
| 2023 | 7 | +0.45 | 0.30 |

- `sigma` (per-candidate log-share noise) 0.231 (20 degrees of freedom); `tau` (election-wide shared shift of the MP candidates) 0.253, from four elections only, so very uncertain. Both carry parameter uncertainty in every draw.
- **Bias term not adopted.** The equal-weight mean shift is +0.15, but leave-one-election-out scoring is worse than zero (-0.33 nats against the +1.0 required) and only 2 of 4 election means share its sign. Under the rule `b = 0` and `tau` is computed about zero, so the shift is carried as shared uncertainty, not removed.
- Descriptive pattern the rule did not adopt: the MP candidate beat the poll against Labour in 17 of 24 polls, but the sign splits by pollster era: Reid Research (2014, 2017) about -0.1, Curia (2020, 2023) +0.34 and +0.45 (odds of the MP candidate against Labour 1.4 and 1.6 times the poll's). Era and pollster are confounded and there are two Curia elections, so this is a hypothesis, not an estimate.
- **Diagnostic flag (never adopted by design).** Candidates outside the MP and Labour groups (Green, National, Mana, independent) beat the poll against Labour by +0.30 on average, with a mean squared error 4.0 times what `2 sigma^2` allows (flag at 1.5). The model understates the noise for these minor candidates. It only matters where they are contenders, which is Te Tai Tonga.
- **Horizon.** Polls closed 21 days or more before the election (9 polls) give a larger `sigma` (0.305, 5 degrees of freedom) and a smaller `tau`; the 2026 polls closed 37 to 44 days before the election. Winner probabilities under that arm move by at most 0.09 (Te Tai Tonga), below the 0.10 flag.
- **Backtest of the default model (leave one election out, 25 polls).** Mean predicted probability that the poll leader wins 0.82; observed 15 of 25 (0.60; 2 of 7 in 2023). Brier 0.208 against 0.240 for always predicting 0.6. The default is overconfident about poll leaders: treat the leader probabilities below as optimistic.

## Current state: three polled seats, four unpolled

Default (registered) model, 100,000 draws, Monte Carlo error at most 0.0013:

| Seat | Candidate (party) | Poll % | Win probability | Share, 5th to 95th percentile |
|---|---|---|---|---|
| Hauraki-Waikato | Maipi-Clarke (TPM) | 45 | 0.88 | 42% to 77% |
| | Kiriona (LAB) | 26 | 0.12 | 20% to 54% |
| Te Tai Hauāuru | Ngarewa-Packer (TPM) | 38 | 0.78 | 31% to 66% |
| | Katene (LAB) | 27 | 0.22 | 21% to 50% |
| | Raukawa (NAT) | 10 | 0.00 | 7% to 20% |
| Te Tai Tonga | Ramsden (LAB) | 30 | 0.85 | 25% to 48% |
| | Murch (TPM) | 17 | 0.11 | 11% to 35% |
| | Te Morenga (GRN) | 16 | 0.03 | 13% to 28% |
| | Ferris (IND) | 15 | 0.02 | 12% to 26% |

Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau and Te Tai Tokerau have no published poll: they are `unpolled` and carry no shares or winner. Among the three polled seats the default gives the Māori Party-affiliated candidates 1.76 wins on average (0, 1, 2, 3 wins: 0.06, 0.21, 0.63, 0.10); if the same three seat probabilities were independent the distribution would be 0.02, 0.26, 0.64, 0.07, so the shared shift is what makes all-or-nothing outcomes (0 or 3 wins) likelier across seats.

**Sensitivities (reported, not adopted).** Te Tai Tonga is the fragile seat:

| Arm | Hauraki-Waikato MP win | Te Tai Hauāuru MP win | Te Tai Tonga Labour win |
|---|---|---|---|
| Default | 0.88 | 0.78 | 0.85 |
| Horizon (sigma, tau from polls 21+ days out) | 0.84 | 0.74 | 0.76 |
| Curia-era bias (post hoc, +0.39 shift for MP candidates) | 0.97 | 0.94 | 0.63 |
| Wider noise for non-MP, non-Labour (post hoc) | 0.88 | 0.76 | 0.65 |
| No shared shift (tau = 0) | 0.95 | 0.85 | 0.91 |

The Te Tai Tonga Labour win probability ranges from 0.63 to 0.91 across arms; the other two seats stay on the same side of 0.5 in every arm. Te Tai Tonga is a four-way race with a fragmented non-Labour field and an independent (Ferris) who left Te Pāti Māori, so its poll closure and the minor-candidate noise assumption matter most there.

## Limits

- 25 polls, 24 contrasts, four elections; two pollsters in two eras, and the 2026 poll shares the Curia method with the last two elections. `tau` and any pollster-era effect are weakly identified.
- Historical polls are transcribed from a volunteer-edited compilation (spot-checked against news reports for all seven 2023 polls and three 2017 and 2020 polls); sample sizes are known only for 2023 (500) and 2026; fieldwork end dates for some 2014 polls are month-end assumptions (`dateQuality`).
- Closure over named candidates: the unnamed remainder (0 to 14% of valid votes, median about 3%) is drawn from history and cannot win. Nominations close on 8 October 2026; the polled candidate lists (for example Hauraki-Waikato's 13% "other" with no other named candidate) may change.
- The 2026 polls are 37 to 44 days before the election, older than nearly all historical polls. A single poll per seat is used; later polls replace earlier ones, they are not averaged.
- Party-vote questions, the Māori-roll poll and national Te Pāti Māori support are deliberately unused; the cross-seat link is the shared shift only. The draw bank exposes the standardised factor for a later coupling with the national draw.
- No calibrated-probability claim. The default model is overconfident about poll leaders on the backtest.

## Not done

No fallback for unpolled seats; no bias or pollster-era adoption; no covariates (incumbency, party, candidate quality); no use of the Stage45 to Stage48 pipeline or any general-seat calibration; no publication; no `data/sources.json` edit; no CI registry edit; no later stage. The bias question (pre-registered rule says no) and the pollster-era hypothesis are for James to weigh before any probability release.
