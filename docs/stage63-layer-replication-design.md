# Stage63: layer-replicated composed simulation, pre-registration

**Status: frozen before any replicate bank was scored.** This file and [design-contract.json](../data/processed/layer-replication/design-contract.json) are committed as a frozen checkpoint; the code reads every threshold from the JSON and the manifest hashes both. Later edits are a change of design and must be recorded as an amendment with a reason. Before this freeze only three things were measured, none kept as an output: wall-clock and a profile of the unchanged Stage47 composed inversion on one 2017 seat (about 8.0 s per 512-draw bank, 97% of it in the conditional-location solves, about half in the local-party layer and half in the candidate layer); that the first 512 points of a scrambled 4,096-point Sobol stream equal the 512-point stream with the same seed (maximum difference 0); and the panel selection below, computed from the already committed Stage54 file.

## The one question

Stage54 found that the frozen composed precision caps are not met at the cached 4,096 national draws (one layer draw per national draw) and that layer noise dominates the variance of CRPS, energy and interval widths. Its recommendation was layer replication on fixed national draws. Stage63 asks:

> Does drawing M independent local-party and candidate layer draws for every fixed national draw (no new national fit) cut composed Monte Carlo error enough to meet the frozen caps, or the seat-win probability precision we need, at an affordable CPU cost, and what variance floor does the finite national bank leave?

It is a report. No model default, scale, law or frozen cap changes, and Stage60 may later change the balance scale, so the method takes the scale file as an input and the finding is stated for the pinned Stage45 scales.

## Frozen design

**Pool and replicates.** For each election the 4,096 balanced cached national draws in the Stage47 order are used whole (no new fit). Replicate `r` is a 4,096-point scrambled Sobol stream with the unchanged Stage46 key registry and seed `460046 + year + 1000 r` (the Stage54 scramble `r`). Position `i` of every replicate pairs national draw `order[i]` with Sobol point `i`. The first 512 points of replicate `r` equal Stage54's 512-point stream for scramble `r`, so the first 512 positions of replicate 0 are Stage54 block 0 and of replicates 8, 9, 10 are the Stage54 layer-only replicates. **Arm M** is the union of replicates `0..M-1` (`4,096 M` composed draws, nested); the baseline is M = 1. Arms reported: 1, 4, 16, 64, with the nested ladder 1, 2, 4, 8, 16, 32, 64 supplying every doubling. Control restriction only (the gates are control gates in Stage47 and Stage54); the composed point forecast is the national-only control mean over the same national draws for every arm.

**Populations.** *Representatives:* the nine Stage47/Stage48/Stage54 representative seats (first, middle, last of each election), 64 replicates. *Win panel:* per election the three non-representative seats whose Stage54 control National win probability (mean over its four blocks) is closest to 0.5, ties by electorate id; chosen from the committed Stage54 file only: 2017 electorates 29, 31, 09; 2020 electorates 57, 04, 30; 2023 electorates 48, 62, 27; 8 replicates each. Maori electorates are not in this composed inventory and stay out.

**Numerics.** The Stage47 inversion is unchanged and run through the Stage54 stream substitution. One engineering reuse is added, exact and tested bit-identical to the uncached path: the local-party layer's conditional-location solves depend on the national draw only (the replicate's noise enters after the offsets), so within a task they are computed once and reused for every replicate; the candidate layer's solves depend on the replicate's local draws and are never shared. No emulator or approximation is added.

**Per bank record:** per-candidate simulated mean (pp), CRPS, 50/80/90% widths, per-candidate win probability (maximum share, ties split, as Stage54), and the complete-vector energy score.

### Gates against the unchanged caps (mean, CRPS 0.05pp, energy 0.1pp, widths 0.5pp)

*Gate B, layer doubling (the simulation error relative to the cached national draws).* For arm M = 2..64 the maximum, over representative seats and candidates, of the change when M/2 replicates are doubled to M at the full 4,096 national pool (nested banks), exactly the Stage47/Stage54 doubling statistic. *3-sigma rule:* `s1` is the maximum over representative seat-candidates of the sd across the 64 single-replicate banks; the required replication is the smallest power of two M with `3 s1 / sqrt(M) <= cap` (the change on doubling M/2 to M has sd `s1 / sqrt(M)` under i.i.d. layer noise); the observed sd across non-overlapping groups of size 1, 2, 4, 8, 16, 32 tests that scaling. Verdict: **`CAPS_MET_BY_REPLICATION`** if some arm passes all six caps at its doubling and is at least the 3-sigma requirement (the cheapest such arm is reported, with its composed draws and CPU); **`CAPS_MET_NOT_3SIGMA_SAFE`** if some arm passes but none at or above the 3-sigma requirement (a pass without margin); **`CAPS_NOT_MET_BY_64`** otherwise.

*Gate A, national doubling (the literal Stage54 gate).* For arms 1, 4, 16, 64 the last doubling 2,048 to 4,096 national draws (each replicate's first n positions), maximum change against the caps. It includes the difference between two national half-samples, which no replication can reduce, so it is reported for comparability: **`NATIONAL_DOUBLING_MET`** or **`NATIONAL_DOUBLING_NOT_MET`** per arm. If gate B passes and gate A fails the interpretation is that the remaining error is the finite national bank, not simulation.

### National variance floor

Eight disjoint national blocks of 512 positions (with the matching Sobol points), each pooled over all 64 replicates, estimate the error that no layer replication removes: the block variance (ddof 1, 7 degrees of freedom) of the M = 64 estimate minus the mean layer variance of the single-replicate estimates divided by 64, floored at zero, divided by 8 for a 4,096-draw estimate. Reported per quantity (maximum and median over seat-candidates) with `3 sqrt(floor) / cap`, and the total sd of a (4,096, M) bank relative to the national population `sqrt(floor + s1^2 / M)`. Reported only, never a gate; it is relative to the cached national draws and biased high at the maximum.

### Replication leaves the target distribution unchanged

Harness (stops the stage on failure): the first 512 positions of replicate 0 reproduce Stage54 block 0 and those of replicates 8, 9, 10 the Stage54 layer-only records, to 1e-9, for every representative seat; replicate 0 first-block records of the panel seats reproduce their Stage54 block 0 control records. Equivalence diagnostic: the non-overlapping half banks of arm 32 differ by `z = (T_a - T_b) / (s1 sqrt(2/32))`; EQUIVALENT if the mean `z^2` over representative seat-candidates and quantities is in [0.6, 1.6] and max |z| <= 4.5, otherwise FLAG (reported to James, no rule adjusted). Also reported: single-replicate mean minus 64-replicate value for the non-linear statistics (finite-bank bias).

### Seat-win probabilities

Over representative and panel seat-candidates whose largest-arm probability is in [0.05, 0.95]: layer design effect `D1 = sum 4096 var_r(p) / sum p(1-p)` (variance across single-replicate banks), national design effect `Dn` from the national-floor formula, and `SE(p = 0.5)` at 4,096 M composed draws, both relative to the cached pool (`sqrt(0.25 D1 / (4096 M))`) and to the national population (`sqrt(0.25 (Dn + D1/M) / 4096)`), with the smallest M reaching 0.01 and 0.005 (or "unreachable: floor") and the CPU of that arm. Stage54's baseline was D = 0.594 and SE(0.5) = 0.0060 at 4,096 draws. No release threshold is set.

### CPU

Process CPU seconds of every replicate bank and of the one-off local-layer solves are written to `timing.json` (hardware dependent; `--check` validates its structure only). Arm cost = one-off local solves + M x replicate cost; reported per seat, for a 71-seat slate, and against Stage54's about 14 ms per composed draw per seat.

## Compute plan (documented bound, not a gate)

About 7.7 ms per composed draw with the exact local-solve reuse (against about 15 ms without). Representatives: 9 seats x 64 x 4,096 = 2.36 M draws, about 5.0 CPU hours; panel 9 x 8 x 4,096 = 0.3 M draws, about 0.6 CPU hours; analysis a few CPU minutes. Parallel by independent (seat, replicate-chunk) tasks, results independent of worker count; about 1.5 to 2 hours wall on 4 cores. No machine-speed gate inside `--check`.

## Interpretation rules (frozen)

- `STOP` (harness mismatch): report, change nothing.
- Gate B decides the headline; gate A, the floor, the equivalence diagnostic and the win-probability bound are reported alongside. A FLAG, or a gate-B verdict that contradicts the 3-sigma requirement by more than one doubling, is reported to James as mixed and no rule is adjusted.
- Under no outcome is any model default, scale, cap or earlier-stage result changed. A recommendation about adoption is a recommendation only; it needs separate authorisation.

## Do not

- Do not change any model default, scale, mean, law, existing draw count or frozen cap; do not alter Stage47, Stage48 or Stage54 results, decisions or findings.
- Do not run new national MCMC, regenerate national draws or use cached draws outside the balanced 4,096 subset.
- Do not add an emulator, interpolation or approximation of the solves; only exact reuse of identical-input solves.
- Do not choose or change arms, replicate counts, populations, panel seats, scramble indices, caps, multiples, tolerances or rules after any replicate result is read.
- Do not add K or F restrictions, horizon refits, Maori electorates, replacement, manual-adjustment, MMP, nominations or Stage60/61/62 content.
- Do not add sources or touch `data/sources.json`; do not set a probability-release threshold, publish, claim calibration or produce a 2026 forecast.
