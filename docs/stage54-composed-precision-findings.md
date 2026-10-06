# Stage54: composed Monte Carlo precision, findings

Pre-registered design: [stage54-composed-precision-design.md](stage54-composed-precision-design.md), frozen before any block other than the Stage47/Stage48 frame was simulated. Machine contract: [design-contract.json](../data/processed/composed-precision/design-contract.json). All figures are percentage points unless stated; no model default, scale, law or Stage47/Stage48 result is changed.

## Finding under the frozen rules

**CAPS_NOT_ATTAINABLE_WITHIN_CACHED_BANK.** The frozen composed caps are not met even when the whole cached 4,096-draw national subset is used (last doubling 2,048 to 4,096 exceeds the cap for crps, energy, mean, width80, width90). The i.i.d. scaling prediction holds (observed last-doubling change over predicted: crps 1.09, energy 1.29, mean 0.93, width50 1.10, width80 1.02, width90 0.83), so this is ordinary Monte Carlo noise at a draw count that is too small for 0.05pp caps, not a harness defect. Paired composed differences and seat-win probabilities, however, are bounded well enough to be settled or quantified (below), so the failed gate limits absolute composed levels, not the Stage48 supporting comparison.

## Harness

Block 0 equals the Stage47/Stage48 composed frame exactly: maximum absolute difference to Stage48's stored composed records is 0.0e+00 (control), 0.0e+00 (K), 0.0e+00 (F) over all 193 seats. The substituted Sobol stream equals the Stage46 stream exactly for scramble 0, the eight national blocks are disjoint and cover the cached 4,096 subset, and the reused-remainder rebalance equals a full re-inversion (maximum 0.0e+00).

## Frozen gate ladder (control, 9 representative seats)

Nested union banks of 1, 2, 4, 8 blocks; maximum change over representative seats and candidates at each doubling, against the frozen caps.

| Doubling | mean | CRPS | energy | width50 | width80 | width90 |
| --- | --- | --- | --- | --- | --- | --- |
| 512 to 1024 | 0.373 (fail) | 0.268 (fail) | 0.315 (fail) | 0.834 (fail) | 1.069 (fail) | 2.101 (fail) |
| 1024 to 2048 | 0.280 (fail) | 0.133 (fail) | 0.357 (fail) | 0.805 (fail) | 1.441 (fail) | 1.729 (fail) |
| 2048 to 4096 | 0.128 (fail) | 0.139 (fail) | 0.132 (fail) | 0.439 | 0.730 (fail) | 0.747 (fail) |
| Cap | 0.05 | 0.05 | 0.1 | 0.5 | 0.5 | 0.5 |

The Stage47/48 first doubling (512 to 1,024) used different national subsets and scrambles here, so its numbers differ from Stage47's 0.561/0.233/0.212/2.255; the failure and its size are the same.

## Where the error comes from and what would be needed

s512 is the sd of a 512-draw composed bank across blocks (representatives: 8 blocks, 80 seat-candidates; all seats: 4 blocks). The layer share is the variance share left when only the layer stream is re-scrambled on the same 512 national draws (pooled over representative seat-candidates; above 1.0 is clipped). The chain bound is the multi-chain sd of the 4,096 estimate over the four cached chains (reported only; 3 degrees of freedom, maximum over 80 seat-candidates, so biased high). Required draws apply the frozen 3-sigma rule to the worst representative seat-candidate (`N` is the larger bank of the doubling).

| Quantity | Cap | s512 max (reps) | s512 median (reps) | s512 max (all seats) | Layer share | Chain bound at 4,096 | Required draws | 3 sigma / cap at 4,096 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| simulated mean | 0.05 | 0.388 | 0.039 | 0.726 | 0.44 | 0.236 | 524,288 | 8.23 |
| Rao-Blackwell mean (alternative statistic) | 0.05 | 0.362 | 0.032 | 0.567 | 0.11 | n/a | 262,144 | 7.69 |
| CRPS | 0.05 | 0.361 | 0.016 | 0.547 | 0.69 | 0.230 | 262,144 | 7.66 |
| energy score | 0.1 | 0.288 | 0.178 | 0.628 | 0.81 | 0.237 | 65,536 | 3.05 |
| 50% width | 0.5 | 1.129 | 0.079 | 2.193 | 1.00 | 0.534 | 32,768 | 2.40 |
| 80% width | 0.5 | 2.030 | 0.172 | 2.741 | 1.00 | 0.818 | 131,072 | 4.31 |
| 90% width | 0.5 | 2.545 | 0.310 | 3.329 | 1.00 | 0.885 | 131,072 | 5.40 |

The frozen caps need between 32,768 and 524,288 composed draws under the 3-sigma rule, that is up to 37,224,448 seat-draws for a 71-seat slate. At about 14 ms per draw per seat for the unchanged Stage47 conditional-location solves (one pre-freeze timing, not an artifact) the largest requirement is of order 145 CPU hours, so the caps are out of reach for the current numerics at any feasible bank size rather than merely above 4,096. The cached national bank holds 8,000 draws (4,096 balanced subset used), so the national dimension cannot be enlarged without a new fit.

Layer noise dominates the widths, CRPS and energy variance (layer share CRPS 0.69, energy score 0.81, 90% width 1.00), while the simulated mean is split (0.44) and the Rao-Blackwell mean is mostly national (0.89). So extra layer draws on fixed national draws could in principle remove most of the score and width noise without a new national fit; whether that is affordable is a question about the conditional-location solves and was not tested here.

## Are the composed differences settled?

Blocks 0 to 3 (4 blocks of 512 draws, 193 seats); estimate is the block mean, SE the sd over blocks divided by 2, 95% t interval with 3 degrees of freedom. Negative favours the first restriction. Stage48's own composed value is block 0.

| Comparison | Stage48 block 0 | Delta major CRPS (4-block mean) | SE | 95% interval | State | Delta interval score | Delta energy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| K vs C | -0.0171 | -0.0167 | 0.0002 | [-0.0173, -0.0162] | SETTLED_MATERIAL | -0.1664 (SETTLED_MATERIAL) | -0.0198 (SETTLED_MATERIAL) |
| F vs K | -0.0003 | -0.0003 | 0.0000 | [-0.0004, -0.0003] | SETTLED_SIGN | -0.0054 (SETTLED_SIGN) | -0.0004 (SETTLED_SIGN) |
| F vs C | -0.0174 | -0.0170 | 0.0002 | [-0.0176, -0.0165] | SETTLED_MATERIAL | -0.1718 (SETTLED_MATERIAL) | -0.0202 (SETTLED_MATERIAL) |

| Delta major CRPS by election | 2017 | 2020 | 2023 |
| --- | --- | --- | --- |
| K vs C | -0.0001 (UNRESOLVED) | -0.0245 (SETTLED_MATERIAL) | -0.0255 (SETTLED_MATERIAL) |
| F vs K | -0.0001 (SETTLED_SIGN) | -0.0006 (SETTLED_SIGN) | -0.0002 (SETTLED_SIGN) |
| F vs C | -0.0002 (UNRESOLVED) | -0.0251 (SETTLED_MATERIAL) | -0.0257 (SETTLED_MATERIAL) |

The paired composed differences are tiny relative to their noise because both restrictions share every draw except the N/L split. The sign agreement that Stage48 could only report as unresolved is settled for K vs C and F vs C pooled and in 2020 and 2023; 2017 is flat at about zero (K and F do not differ from C there). F vs K is settled in sign but immaterial (about 0.0003pp). This labels Stage48's supporting check only; its decision and finding are unchanged.

## Seat-win probabilities (control, all 193 seats)

Design effect D = 0.594 over 260 seat-candidate probabilities in [0.05, 0.95] (D below 1: the scrambled layer stream beats an i.i.d. binomial bank). Largest per-seat sd across 512-draw blocks 0.0287.

| Draws N | SE of a probability of 0.5 |
| --- | --- |
| 2048 | 0.0085 |
| 4096 | 0.0060 |
| 512 | 0.0170 |

Draws for SE(0.5) <= 0.01: 2,048; for <= 0.005: 8,192 (power of two). These are arithmetic bounds relative to the cached national draws; no probability-release threshold is set here (open decision for James).

| Leading-candidate win probability, National | Seats changed | Seats resolved (95%) | Moved 1pt or more, unresolved | Max abs mean difference | Median SE | Max SE |
| --- | --- | --- | --- | --- | --- | --- |
| K vs C | 164 | 53 | 0 | 0.0093 | 0.0012 | 0.0033 |
| F vs K | 46 | 1 | 0 | 0.0020 | 0.0000 | 0.0010 |

K moves no seat's National win probability by as much as one percentage point, so the Stage48 narrowing is invisible in seat-win probabilities at this precision.

## Limits

- Blocks are sampled without replacement from a 4,096 pool, so s512 is up to a factor sqrt(7/8) below an i.i.d. sd; this is recorded, not corrected. Block sds have 3 (all seats) or 7 (representatives) degrees of freedom and maxima over seat-candidates are biased high; the 3-sigma requirement is deliberately conservative.
- Precision here is relative to the cached national draws. The chain bound at 4,096 draws is larger than the pool-subsampling bound (s512 over sqrt(8)) for the mean, CRPS and energy, which would mean the four cached chains disagree by more than i.i.d. subsampling implies; with 3 degrees of freedom this is suggestive only, and no composed simulation improves the effective size of the national bank.
- Representative seats are the Stage47/48 first, middle and last of each election, not the worst-precision seats; the all-seat s512 maxima are larger for every quantity.
- Horizon (56 days versus about 32 at publication), prior/parameter uncertainty and omitted uncertainty are outside this stage, and no calibration claim is made.

## Recommendation

1. **Record the bound; change nothing operational.** Composed absolute levels (means, CRPS, widths, energy) must carry the s512 table above and must not be called settled at a 0.05pp scale; composed paired differences and seat-win probabilities can be reported with the SEs above. The frozen caps stay as they are.
2. **Treat the layer share as the lever, not more national draws.** If composed precision of scores or widths matters for a later stage, the separately authorised engineering question is the cost of the conditional-location solves under layer replication on the fixed 4,096 national draws (or a verified cheaper solver), with the same caps. Not started here.
3. **Item 4 is resolved as a bound.** Stage48's composed supporting check is settled in sign and size; the composed-precision limit no longer qualifies it. The probability-release policy remains open.

