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

## 2026 effect (development readout, 2,048 national draws)

National and Labour win probability, model alone to model plus poll, in the seat's configured class (James's classification, D107: Hutt South, Waitaki and West Coast-Tasman ordinary at 0.60; Kāpiti and Mt Albert exceptional at 1.00). The other class is in `readout-2026.json`.

| Seat | Class | Poll (aged to 7 Oct) | National | Labour |
|---|---|---|---|---|
| Hutt South | ordinary | Victor Consulting, Labour-aligned, 17–19 Sep, LAB 42 NAT ~30; rho 0.74 | 12→6% | 82→88% |
| Kāpiti | exceptional | Community Engagement Ltd (same operator), 29–31 Jul, LAB 37.5 NAT 33.6; rho 0.33 | 16→19% | 81→78% |
| Mt Albert | exceptional | Curia, two polls merged, 21 Sep–5 Oct, LAB 33/31 NAT 32/26; rho 0.97 | 8→8% | 61→57% |
| Waitaki | ordinary | Curia, 18–25 Sep, NAT 44 LAB 21; rho 0.82 | 87→94% | 7→1% |
| West Coast-Tasman | ordinary | Curia, 10–17 Sep, NAT 36 LAB 30; rho 0.72 | 16→32% | 67→50% |

- **The only large move is West Coast-Tasman**, where the poll has National ahead and the model has Labour ahead. Waitaki's National lead is firmed up, and Hutt South moves toward Labour.
- **Mt Albert:** the poll narrows the National–Labour gap, and the vote it takes from Labour goes to the Green candidate, whose win probability rises a few points (about 26→29%). The update moves only the National/Labour coordinate; Green-led contests have no matching coordinate (design amendment A2).
- Auckland Central and Wellington Bays are not usable here (Green-led polls). Waiariki and the other Māori seats are untouched.

## What was and was not done

- **Done.** Raw Wikipedia pages preserved (`data/raw/polling/seat-polls/2026-10-09/`), 22 polls transcribed and verified against the preserved text, standalone dated registry, leave-one-out scoring, 2026 fit and readout, assembly hook, a fail-closed config validator rule.
- **The layer is switched on (D117).** James chose "Switch on" on 2026-10-09: `config/nowcast-2026.json` (version 2026-10-10.2) has `seatPolls: {enabled: true, decision: "D117"}`. The validator still refuses `enabled: true` unless `findings.json` says `adopt`. The development gate, the synthetic fixture bank and the rehearsal report were regenerated in the same change, and the TypeScript bank schema accepts the optional per-seat `seatPoll` record. The published site does not yet display the poll; that is a later step.
- **Cheap to regenerate.** The update reads only the candidate balance scales (shared SD and the seat SD with the D107 multiplier). It does not read the minor-candidate noise, so a later change to that noise leaves the weights alone. In Mt Albert the Green win probability moves with the remainder split and would change with such a change. To refresh after any upstream change: `python3 -m scripts.seat_polls.readout --draws 2048` (a few minutes), then the development gate, fixture and rehearsal commands in the PR body.
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
