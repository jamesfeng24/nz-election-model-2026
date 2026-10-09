# Stage79 findings: general-seat polls in the nowcast

Design and contract: [stage79-seat-poll-design.md](stage79-seat-poll-design.md), frozen before any score was computed (commit `294ddc5`). Code: `scripts/seat_polls/`. Artifacts: `data/processed/seat-polls/`.

## Headline

- **Frozen finding: `adopt`.** Leave-one-seat-election-out, nine eligible polls in seven seat-elections (2020 and 2023): model plus poll beats the model alone by **+1.85 nats** (threshold 1.0), with 80% coverage **0.78** (band 0.65 to 0.95). Mean CRPS 0.147 to 0.125. Seven polls improved and two worsened.
- **The evidence is weak, and the design said it would be.** Three qualifiers:
  - **Assumed sample size.** Dropping the four 2020 polls whose sample size is not published (assumed 400) leaves five polls and a gain of **−0.02 nats** (sensitivity S1, finding `not_established`). The 2020 polls carry about 1.7 of the 1.85 nats.
  - **Narrowing versus information.** Of the 1.85 nats, +0.73 comes from the narrower variance alone, +0.43 from moving the centre alone, and the rest from the two together. The model alone is already over-wide in these seats (root-mean-square standardised miss 0.74; 80% coverage 1.00), because most historical polled seats were Stage67-flagged at the 1.00 multiplier. So much of the gain is the model's own width being reduced, not information in the polls.
  - **Centre coverage.** Model plus poll covers 3 of 9 at 50% and 8 of 9 at 90%, a small sample but slightly over-confident near the centre.
- **Sensitivities.** Fixing the inflation at 1 (S2) gives +1.48 and `adopt`; fitting the inflation on every poll that publishes both parties (S3) gives +1.50 and `adopt`.
- **Poll error.** Fitted variance inflation `c = 5.3` over the sampling floor (root-mean-square balance error 0.27 against a sampling floor of about 0.12 at n=400). With the model's seat SD (0.26 ordinary, 0.35 exceptional) this puts the poll weight at about 0.4 to 0.6 (capped at 0.60).

## 2026 effect (development readout, 2,048 national draws, both classes shown because the classification does not exist yet)

National win probability, model alone to model plus poll. Labour in brackets. Ordinary/exceptional class.

| Seat | Poll (aged to 7 Oct) | National | Labour |
|---|---|---|---|
| Hutt South | Victor Consulting, Labour-aligned, 17–19 Sep, LAB 42 NAT ~30; rho 0.74 | 12→6% / 21→12% | 82→88% / 74→83% |
| Kāpiti | Community Engagement Ltd (same operator), 29–31 Jul, LAB 37.5 NAT 33.6; rho 0.33 | 15→18% / 16→19% | 82→80% / 81→78% |
| Mt Albert | Curia, two polls merged, 21 Sep–5 Oct, LAB 33/31 NAT 32/26; rho 0.97 | 3→4% / 8→8% | 65→60% / 61→57% |
| Waitaki | Curia, 18–25 Sep, NAT 44 LAB 21; rho 0.82 | 87→94% / 81→93% | 7→1% / 13→3% |
| West Coast-Tasman | Curia, 10–17 Sep, NAT 36 LAB 30; rho 0.72 | 16→32% / 17→36% | 67→50% / 66→45% |

- **The only large move is West Coast-Tasman**, where the poll has National ahead and the model has Labour ahead.
- **Mt Albert:** the poll narrows the National–Labour gap, and the vote it takes from Labour goes to the Green candidate, whose win probability rises a few points (about 26→29%). The update moves only the National/Labour coordinate; Green-led contests have no matching coordinate (design amendment A2).
- Auckland Central and Wellington Bays are not usable here (Green-led polls). Waiariki and the other Māori seats are untouched.
- The classification of the 64 seats, still pending, decides which column applies.

## What was and was not done

- **Done.** Raw Wikipedia pages preserved (`data/raw/polling/seat-polls/2026-10-09/`), 22 polls transcribed and verified against the preserved text, standalone dated registry, leave-one-out scoring, 2026 fit and readout, assembly hook, a fail-closed config validator rule.
- **The layer is off by default.** `config/nowcast-2026.json` has no `seatPolls` section, so the assembly, the development gate and the rehearsal are unchanged. The validator refuses `seatPolls.enabled: true` unless `findings.json` says `adopt`. Enabling is a separate config change.
- **Not done.** No party-vote crosstabs, no Māori change, no D107 or classification change, no sponsor lean or directional shift, no published probability, no change to a frozen stage, no edit to `data/sources.json`.

## Limits

- Nine polls, seven seat-elections, mostly Taxpayers' Union–Curia, Colmar Brunton and Reid; seats are polled because they are close or newsworthy.
- The historical model reference is conditional on the observed local party vote, a stronger reference than the 2026 bank. The 2026 bank adds local-party uncertainty on top, which the update leaves alone.
- Poll and model error are assumed independent; the AR(1) half-life (6 weeks), the weight cap (0.60) and the 0.12 SD Labour-aligned allowance are development choices, not estimates. The decay is not validated (scoring uses `rho = 1`).
- Results use Python 3.13 and numpy 2.2.6 in this environment; the repository pins Python 3.12.

## Reproduction

```
python3 -m scripts.seat_polls.run --check
python3 -m scripts.seat_polls.readout --draws 2048 --check
python3 -m unittest scripts.tests.test_stage79_seat_polls
```
