# D132: TOP candidate-weight offset

**Decision (James, 2026-10-11).** Every TOP candidate's log-weight in the general-seat candidate step is lowered by 0.35, in every seat except Mt Albert. It is a manual override, not a fitted or backtested value.

## Why

On the live forecast TOP's candidate in Christchurch Central showed an 11.2% median. The model's TOP party vote in that seat is about 13.4% (5.1% in 2023, scaled by TOP's national rise from 2.3% to 6.4%), and the candidate step gives a candidate about the local share of its party (TOP's candidates average about 1.0 times local party vote across the 41 seats). TOP runs a party-vote-only campaign everywhere except Mt Albert, so James did not expect its electorate vote to rise as much as its party vote. He asked that it be compared with how NZ First, ACT and the Greens do in seats where they are not running two-tick campaigns.

## Evidence (descriptive; `python3 -m scripts.top_candidate_offset.evidence`)

Candidate share of candidate votes over the same party's share of party votes in the same seat, 2017–2023. Seats flagged in the Stage67 audit (a stand-in for two-tick campaigns, which are not recorded) and seats the party's candidate won are removed.

| Party | Seats | Ratio of sums | Party vote 4–7% | 7–10% | 10%+ | Change between elections (log slope) |
|---|---|---|---|---|---|---|
| ACT | 132 | 0.51 | 0.56 | 0.43 | 0.50 | 0.60 (84 seat pairs) |
| NZ First | 99 | 0.83 | 0.72 | 0.84 | 1.01 | 1.05 (56; party vote barely moved) |
| Greens | 140 | 0.87 | 1.07 | 0.88 | 0.68 | 0.49 (110) |
| TOP | 41 | 1.24 | 1.16 (5 seats) | – | – | 0.37 (9) |

- At 0.5–0.6 pass-through, TOP's ×2.9 party-vote rise is a ×1.7–1.9 candidate rise, about ×0.7 of what the model gives.
- Matching NZ First and the Greens would be about ×0.8 (offset −0.22); matching ACT, the closest list-vote-first party, about ×0.5 (−0.7). −0.35 is the middle.
- TOP's own clean history cannot test this: its party vote there was mostly 2–3%.

## Effect (prototype, 256 national draws × 4 layer replicates, so probabilities are good to about ±0.01–0.02)

| | before | after |
|---|---|---|
| Christchurch Central: TOP median / chance of winning | 11.9% / 4.5% | 8.5% / 1.2% |
| Christchurch Central: Labour chance | 78% | 82% |
| Epsom: TOP median / chance; ACT chance | 7.1% / 7.1%; 64% | 5.0% / 3.3%; 66% |
| Wellington North: TOP median / chance; Greens chance | 7.6% / 6.8%; 61% | 5.3% / 2.8%; 63% |
| Mt Albert (exempt) | unchanged | unchanged |
| TOP expected electorate wins; chance of at least one | 0.36; 24% | 0.14; 11% |
| National / Labour expected seat wins | 31.0 / 26.9 | 31.1 / 27.1 |

## What changed in the code

`config/nowcast-2026.json` `candidate.partyExponentOffsets` (validated: negative, at least −1, general seat ids for the exempt list); `general.exponent_offsets` and `general.weights`, used by the assembly and the Stage79 readout. Config `2026-10-11.1`. The development gate, the synthetic fixture and the readout are regenerated. Scales, means, the local-party layer, the balance, within and mass multipliers, the Māori layer and MMP are unchanged.
