# Stage89: seat polls move every candidate (James, 2026-10-11)

**Question.** Can a seat poll's figure for every candidate, not only the National/Labour pair, be blended into the fundamentals, simply and with the existing weights?

**Answer.** Yes. `seatPolls.rule = "all-candidates"` (config, default `balance` = the D117 rule) replaces the National/Labour balance update with one that uses every candidate the poll publishes and we can match to a party column (NAT, LAB, GRN, ACT, NZF, TOP, TPM). Requested by James on 2026-10-11 ("fundamentals + polls, like 538 used to do"; "no heavy backtesting"). It reopens the "National/Labour balance only" part of D117; the D107 multipliers (0.60 ordinary, 1.00 exceptional), the 6-week half-life and the 0.60 cap are kept.

## The rule (`scripts/seat_polls/candidates.py`)

1. **Observation.** The matched candidates' published shares rescaled to sum to 1, as log-odds against the poll's leading candidate. Unmatched columns (Others, independents, parties without a candidate in the seat) and undecideds are left out; a poll with fewer than two matched candidates is listed as not used.
2. **Poll error.** Multinomial sampling variance of those log-odds times `INFLATION = 10`, plus the sponsor allowance of the Stage79 contract (labour-aligned 0.12, on Labour's own log-share), divided by the square of the poll's age factor (half-life 6 weeks). Sample size is the published one, else 400 (as in Stage79).
3. **One poll per pollster.** Of one pollster only the newest poll counts (older ones are listed as superseded). Different pollsters are applied one after another, oldest first, which is the inverse-variance combination for independent errors. This replaces the D117 merge of same-pollster polls within 14 days (later poll at 1.5 times the variance): simpler, slightly more conservative.
4. **Update.** The model's own spread of those log-odds across the simulated elections (so its correlation with the national draw is kept) is combined with the poll, Gaussian-style, and every simulated election moves by the same gain with a perturbed observation per row (so the spread after the poll is right). The gain keeps the D117 cap of 0.60. The matched candidates keep their combined share and the unmatched keep theirs, so shares still sum to 1. Winners come from the updated shares. The perturbation stream is seeded from `simulation.seedNamespace` and the seat, so a bank is reproducible.
5. **Not touched.** National, local-party and Māori layers, MMP, the D107 multipliers, the seat's mean and spread before the poll.

**Inflation 10, not 5.29.** The Stage79 constant was fitted on the National/Labour contrast only (9 polls). `python3 -m scripts.seat_polls.rescore` re-scores all 13 usable historical seat polls (2017, 2020, 2023) on every candidate contrast against the leader: 40 contrasts, mean squared error 10.7 times the sampling variance (National/Labour contrasts 13.5, other candidates 9.2), error 0.61 on the log-odds scale against 0.27 for National/Labour alone. Minor candidates did better than their polls on average (actual about 20% above polled): Auckland Central 2023 Green polled 38, got 48; Wellington Central 2023 Green polled 27, got 41; Ilam 2023 TOP polled 14, got 26; Tāmaki 2023 ACT polled 34 to 38, got 44. **No bias term is applied** (13 polls cannot support one). The check is in-sample and small; it sets the constant and is not a test. No adoption gate, because James decided to use polls.

## Bank and evidence compatibility

The bank's `seatPoll` record and the Stage85 `pollUpdate` keep their shapes: they now summarise the update on the National/Labour balance (`modelBalance` is the draw mean of log(N/L) before, `updatedBalance` after, `pollBalance` the polls' own inverse-variance log(N/L) where they publish both). `weight` is the share of the gap to the poll actually closed (so `effectiveWeight` equals it exactly and `modelWeight` is what remains). It is a display summary; the update itself moves every candidate. Unused polls are listed with reasons (excluded, after the cutoff, superseded, fewer than two matched candidates); a National/Labour-only reason no longer exists. `shareOfPoll` is each poll's share of the combined precision. A seat with no National or no Labour candidate is still updated but has no `seatPoll` summary.

## Effect on the 7 polled seats (live 10 Oct inputs; 512 national draws x 16 replicates; win probabilities, Monte Carlo error about 1 to 2 points)

| Seat (polls) | Candidate | D117 rule | All candidates |
|---|---|---|---|
| Auckland Central (Curia/TU 22-29 Jul: NAT 30, GRN 25, LAB 23; not used before) | Swarbrick (Green) | 82.3% | 77.0% |
| | Kinser (National) | 10.7% | 14.7% |
| Wellington Bays (Curia/TU 4-10 Sep: GRN 29, LAB 29, NAT 15; not used before) | Genter (Green) | 67.5% | 60.4% |
| | Renney (Labour) | 26.9% | 37.6% |
| Hutt South | Andersen (Labour) | 82.8% | 85.8% |
| Kāpiti | Handford (Labour) | 71.8% | 75.8% |
| Mt Albert (Curia 28 Sep, Curia/TU 5 Oct) | White (Labour) | 59.0% | 79.7% |
| | March (Green) | 22.1% | 5.5% |
| Waitaki | Anderson (National) | 93.5% | 89.8% |
| West Coast-Tasman | Paterson (Labour) | 52.5% | 64.6% |
| Epsom (no poll in the data) | Seymour | 64.8% | 64.8% |

Read: Mt Albert moves most because both polls put the Greens at 14 to 18 and Labour at 31 to 33, which the National/Labour rule never saw. Waitaki goes the other way because the poll shows NZ First at 18 and a smaller National lead than the old rule's balance shift implied. An Epsom poll would move Seymour a lot: illustrative polls of ACT 42 / NAT 20 (his 2014 to 2023 range) give about 92 to 94%, a close 32 / 28 gives 82 to 85%. The model alone does not reach 90%.

## Limits

* Every 2026 seat poll is a Wikipedia transcription with no primary release checked (Stage82 flags `primary_verification_pending`).
* Poll columns are party names, not candidate names: a candidate is matched by party, so two candidates of one party, or an independent, cannot be matched.
* The update is a Gaussian approximation in log-odds; a candidate near zero share is floored at 1e-12 before the logarithm.
* Constants (`INFLATION`, `CAP`, half-life) live in `candidates.py`; changing them is a new decision.
