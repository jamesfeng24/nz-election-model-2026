# Stage78 findings: no-poll fallback for the unpolled Māori seats (internal, not published)

Design: [stage78-maori-fallback-design.md](stage78-maori-fallback-design.md), frozen before any transition error or score was computed (one wording clarification, made before any score, is recorded in it). Reproduce with `python3 -m scripts.maori_seat_fallback.run` (add `--check` to verify; about 20 seconds, no network). Stage66, Stage71, the configuration and the assembly are unchanged.

## Finding (frozen rules): `mixed_report_to_james`; James chose the 2023-only fallback (F)

**Rule 1, does borrowing the polled seats' swing help?** The held-out scores cannot separate the options. Leave-one-election-out, 21 seat contests, every candidate scored:

| Arm | Probability of actual winner | Log score of winner | Brier (multi) | Favourite: predicted / won, z | Share coverage 50 / 80 / 90% | Rule 2 class |
|---|---|---|---|---|---|---|
| F: 2023 result carried forward, no polls | 0.565 | -1.003 | 0.544 | 0.753 / 0.667, -0.98 | 0.48 / 0.70 / 0.80 | calibrated |
| FC: F plus polled-seat swing (Stage66 layer) | 0.600 | -0.993 | 0.545 | 0.815 / 0.657, -2.03 | 0.38 / 0.64 / 0.74 | overconfident |
| FP: F plus polled-seat swing (Stage71 layer) | 0.582 | -0.995 | 0.544 | 0.786 / 0.657, -1.55 | 0.43 / 0.68 / 0.74 | overconfident |

- FC against F: log score +0.009 (paired 90% interval -0.068 to +0.075), Brier +0.0008 (worse). FP against F: log score +0.007, Brier +0.00004 (worse). The pooled log score improves and the pooled Brier does not, so both arms are `mixed_report_to_james` (evidence `weak`). The registration rule therefore returns `none_report_to_james`: the choice is James's. **James chose F (2023 results only) on 2026-10-09**, as recommended.
- Rule 2: only F passes the calibration check on the leave-one-election-out scheme. The favourite z of FC is -2.03 (limit 1.645) and FP's coverage is 0.12 below nominal on average.
- **Chronological check (2023 only)** disagrees with the headline for F: `overconfident` (favourite z -4.08, log score -2.12). The fallback trained on 2017 and 2020 alone has `tau^2 = 0` (those elections were quiet), so it ignores any election-wide shift and the swing arms collapse onto F (`kappa = 0`). Every number is then the 2023 wave arriving unanticipated: the Māori Party-versus-Labour log-odds moved +0.80 on average against -0.08 (2017) and +0.10 (2020), and the model predicted 2 of 7 favourites correctly. The headline `calibrated` class for F must not be quoted without this qualifier.

## What the 2023 wave does to everything

- Election means of the contrast `D` (19 contrasts): -0.08 (2017, 6 seats), +0.10 (2020, 6), +0.80 (2023, 7). With all three transitions: `sigma` 0.257 (16 degrees of freedom), `tau` 0.443 (3 elections), both carried with parameter uncertainty.
- Leave-one-election-out the 2017 and 2020 folds are scored with the 2023 wave in training (log score of the winner -0.49 and -0.37, favourites right in 6 of 7 each); the 2023 fold has no wave in training (-2.14, favourites right in 2 of 7). Fold means are in `scores.json`.
- Coverage by candidate kind (leave-one-election-out, F): Māori Party and Labour candidates 0.51 / 0.71 / 0.73, other matched candidates 0.50 / 0.71 / 1.00, entrants 0.44 / 0.68 / 0.79. The 90% interval for the contrast `D` covers 14 of 19 (0.74). The shortfall is the 2023 fold.
- Diagnostic (never adopted): matched candidates outside the two main groups have a mean squared log-odds error 1.53 times `2 sigma^2` (flag 1.5), borderline as in Stage66.

## 2026 readout: the four unpolled seats (100,000 draws)

Win probability by candidate (party in brackets); the polled layers are re-simulated exactly as Stage71 produced its forecast (tested).

| Seat | F: 2023 only | FC | FP | FC or FP excluding Te Tai Tonga's swing |
|---|---|---|---|---|
| Waiariki | Waititi (TPM) 0.96, Boynton (LAB) 0.04 | 0.97 / 0.03 | 0.91 / 0.07 | 0.98 / 0.94 |
| Ikaroa-Rāwhiti | Tangaere-Manuel (LAB) 0.64, Maxwell (TPM) 0.36 | 0.83 / 0.17 | 0.76 / 0.24 | LAB 0.72 / 0.67 |
| Tāmaki Makaurau | Kaipara (TPM) 0.50, Leoni (LAB) 0.50 | LAB 0.70 | LAB 0.65 | LAB 0.55 / 0.54 |
| Te Tai Tokerau | Prime (LAB) 0.66, Edwards (TPM) 0.20, Kapa-Kingi (Te Tai Tokerau Party) 0.13 | Prime 0.76 | 0.72 | Prime 0.70 / 0.67 |

Share 5th to 95th percentile under F: Waiariki Waititi 41% to 89%; Ikaroa-Rāwhiti Tangaere-Manuel 25% to 73%, Maxwell 16% to 69%; Tāmaki Makaurau Kaipara 19% to 72%, Leoni 21% to 65%; Te Tai Tokerau Prime 22% to 50%. The intervals are wide on purpose.

- **Where F and the swing arms differ, and why.** The swing from the three polled seats averages -0.34 in the MP-versus-Labour log-odds (poll point values: Hauraki-Waikato +0.29, Te Tai Hauāuru -0.49, Te Tai Tonga -0.82), taken up almost fully (mean `kappa` 0.82) because `tau^2` is large against the noise of three seats. Without Te Tai Tonga the average is -0.10 and the swing arms land close to F. Te Tai Tonga's Māori Party candidate is not the 2023 incumbent (the incumbent is now an independent), so its change is not a clean party-level swing. This is why the choice is James's.
- **Shift flags (more than 0.10):** FC and FP are within 0.07 of each other in every seat. The swing against F changes Ikaroa-Rāwhiti by 0.19 (FC) and 0.12 (FP) and Tāmaki Makaurau by 0.20 and 0.15. Leaving Te Tai Tonga out of the swing moves FC by 0.11 (Ikaroa-Rāwhiti) and 0.14 (Tāmaki Makaurau) and FP by 0.11 (Tāmaki Makaurau).
- **Te Tai Tokerau and the split vote.** Kapa-Kingi stands for the Te Tai Tokerau Party. With `phi` uniform, she wins about 13% and the Te Pāti Māori candidate about 20% under F; the split mostly helps Labour. Fixed `phi` (F): 0.2 gives Prime 0.60 and Edwards 0.39; 0.5 gives Prime 0.79 and Edwards 0.16; 0.8 gives Prime 0.66 and Kapa-Kingi 0.31. Every value moves the seat by more than 0.10, so the Te Tai Tokerau number is a labelled assumption about how a split incumbent's vote divides, not an estimate (two reference points in the design: about 0.47 in the Te Tai Tonga poll, much less in Ikaroa-Rāwhiti 2023).
- **Māori Party-label wins among the four seats:** mean 2.02 (F), 1.53 (FC), 1.63 (FP). Among all seven (FC / FP, with the draws shared between polled and unpolled seats): mean 3.29 / 3.24; the polled seats alone give 1.76 / 1.61.

## Limits

- Three transitions and 19 contrasts; `tau` rests on three elections, one of which is the 2023 wave. Parameter uncertainty makes the election-wide shift heavy-tailed; the 90% share intervals are correspondingly wide.
- The carry-forward is by party label. It does not know that a candidate is an incumbent, new or retiring, nor that Waiariki's 76% in 2023 was an outlier; mean reversion and incumbency were excluded by the design. Tāmaki Makaurau and Ikaroa-Rāwhiti both have a new Te Pāti Māori candidate, and Tāmaki Makaurau has two new main candidates; typical turnover is inside the calibrated error, this turnover is not tested.
- The leave-one-election-out scheme is not out of sample in time (the 2023 wave trains the earlier folds), and with three elections the folds share dependence that the contest-level bootstrap ignores, so its intervals are too narrow.
- The polled layers inherit Stage66/71 limits (single poll per seat, 37 to 44 days before the election, no calibrated-probability claim).
- Entrants are an empirical resample from 6 established-party and 29 other entrant shares. A Green candidate where the Greens did not stand last time draws from a pool that includes a Māori Party entrant at 26%; no entrant wins more than 2% of draws in any of these seats, but the entrant shares themselves are crude.
- No national party-vote input: the unpolled seats' link to the national Te Pāti Māori vote, and to the overhang, is independence by default, as for the polled seats.

## Not done

No wiring of the chosen fallback (the frozen rule returned `none_report_to_james` and James chose F; it is recorded in `inputs-2026.json`), no change to the configuration (`maori.unpolledFallbackModel` stays null), the assembly, the draw bank, the TypeScript or the export; no variance inflation of the fallback; no incumbency, mean-reversion, national or Māori-roll input; no change to Stage66 or Stage71; no new sources and no `data/sources.json` edit; no publication; no later stage.

## Decision and next step

James chose **F, the 2023 result carried forward with no polled-seat swing**, on 2026-10-09. The swing arms stay in the artifacts as flagged sensitivities (the two seats that move by more than 0.10 are Ikaroa-Rāwhiti and Tāmaki Makaurau, because of Te Tai Tonga's poll). The choice is recorded in `data/source-plans/maori-seat-fallback/inputs-2026.json` (`registration.choice = "F"`). The next separately authorized stage wires F into `scripts/nowcast_assembly/maori.py`, sets `maori.unpolledFallbackModel`, maps the official Māori candidates to export ids and adds the export label. The label should say the four seats are carried forward from 2023 results, with wide uncertainty that was not calibrated for an election-wide wave like 2023; Te Tai Tokerau's split-vote share is an assumption.
