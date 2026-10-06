# Stage54: composed Monte Carlo precision, pre-registration

**Status: frozen before any composed block other than the Stage47/Stage48 frame (block 0) was simulated or scored.** This file and [design-contract.json](../data/processed/composed-precision/design-contract.json) are committed as a frozen checkpoint; the code reads every threshold below from the JSON and the manifest hashes both. Later edits are a change of design and must be recorded as an amendment with a reason, never as a silent rewrite. Before this freeze only wall-clock timing of the unchanged Stage47 upstream/candidate inversion on one 2017 seat was measured (no score, no output kept).

## The one question

Roadmap item 4 (D082) asks, as an engineering gate, for the finite-simulation precision of the composed (national, then local-party, then candidate) 56-day bank. Stage47 found that the composed 512 to 1,024 representative comparison fails its frozen caps for both control and corrected banks (largest changes: mean 0.5609pp, CRPS 0.2325pp, energy 0.2117pp, 90% width 2.2554pp), and Stage48's composed supporting check failed the same gates for all three restrictions, so both stages could report only the sign of composed differences. Stage54 asks:

> How large is the Monte Carlo error of the composed 56-day quantities, can the frozen caps be met with the cached national bank, and which composed differences and seat-win probabilities are therefore settled?

Nothing statistical changes. The Gaussian law, scales, means, Stage48 multipliers, scores and caps are exactly Stage47/Stage48's; only the number and arrangement of simulated draws is studied.

## What limits precision (the structural point)

A composed draw pairs one cached national draw with one point of the scrambled Sobol stream that drives the local-party and candidate shocks. The cached external-gauss national bank holds 8,000 draws (4 chains of 2,000); Stage47/Stage48 use the balanced 4,096-draw subset in a fixed random order and the first 512 of it. Layer draws are cheap to multiply, national draws are not: more would need a new national fit, which is excluded (historical national MCMC reruns). So the answer has two parts, kept separate: error that more layer draws would remove, and error that only more national draws would remove.

## Frozen design

**Blocks.** A block is a composed bank of 512 draws: national draws are the slice `[512 b, 512 (b+1))` of the Stage47 order (`permutation(4096, 'national:<year>')`), layer noise is a 512-point scrambled Sobol stream with seed `460046 + year + 1000 s` for scramble index `s` and the unchanged Stage46 key registry. **Block 0 (b = 0, s = 0) is exactly the Stage47/Stage48 frame**; blocks 1 to 7 are disjoint national subsets (together the whole 4,096 pool) with independent scrambles s = b. **Layer-only replicates** reuse national block 0 with scramble indices 8, 9, 10. All use the same implementation of the Stage47 inversion (`scripts/uncertainty_expectation/simulation.py`, unchanged); only the stream is substituted.

**Populations.**
- *All seats:* the 193 composed seats of 2017/2020/2023, blocks 0 to 3 (2,048 draws per seat), all three restrictions C (control), K (constant), F (conditional) with the Stage48 multipliers (`balance-scale/fit.json`; remainder reuse as Stage48).
- *Representatives:* the 9 Stage47/48 representative seats (first, middle, last by sorted id of each election), control only, blocks 0 to 7 (all 4,096 pool draws) plus the three layer-only replicates.

**Harness check (first, stops the stage on failure).** Block 0 for every seat and restriction must equal Stage48's stored composed records (crps, energy, simulated means, interval widths/scores/coverage, ranking pair) to 1e-9; block-0 noise must equal the unchanged Stage46 `noise()` exactly. If not, the verdict is `STOP`, nothing below is interpreted and the thread reports to James.

**Per seat and block record (all restrictions):** per-candidate CRPS, simulated mean, 50/80/90% widths, interval scores and coverage, complete-vector energy, per-candidate winner probability (maximum share, ties split as the Stage46 ranking), and for the control the Rao-Blackwell mean (average of the candidate-conditional mean over the block's draws).

### Quantities and estimators

For a quantity `x` (per seat and candidate) with block values `x_b`:
- `s512(x)` is the sample standard deviation (ddof 1) across the blocks, the empirical sd of a 512-draw composed bank around its expectation over national subsets and layer noise (B = 4 for all seats, B = 8 for representatives). The blocks are drawn without replacement from a 4,096 pool, so this sd is smaller than an i.i.d. draw from the national posterior by a factor of at most sqrt(7/8); this is recorded, not corrected.
- `sLayer(x)`: sd across the four scrambles of national block 0 (block 0 and the three layer-only replicates, representatives only). The layer share of variance is `sLayer^2 / s512^2` (clipped to [0, 1]); the remainder is the national-subset share. Reported as medians and maxima over seats and candidates per quantity; 3 degrees of freedom each, so only aggregates are read.
- `sChain(x)`: representatives only, the 4,096-draw union estimate recomputed on each of the four chains' 1,024 draws (chain taken from the cached draw ids); the multi-chain bound on the 4,096 estimate relative to the cached national chains is `sChain / sqrt(4)`. Reported, never a gate.

### Frozen gate test (control, 9 representatives)

Nested union banks of the first 1, 2, 4, 8 blocks give 512, 1,024, 2,048, 4,096 draws (complete-vector energy, intervals and CRPS computed on the union with the Stage46 estimators, point forecast the union mean of the national-only control). Using the six Stage47 caps unchanged (mean, CRPS 0.05pp, energy 0.1pp, widths 0.5pp) the maximum change over representative seats and candidates is computed at each doubling exactly as Stage47/48 did. **`CAPS_MET_AT_CACHED_BANK`** if every cap holds at the last doubling (2,048 to 4,096); otherwise **`CAPS_NOT_ATTAINABLE_WITHIN_CACHED_BANK`** is the finding (a larger bank than the cache holds is then required, see below). Caps are never relaxed. The observed last-doubling change divided by `s512 / sqrt(8)` (the i.i.d. prediction) is reported as a scaling diagnostic only.

### Required draws (arithmetic bound, not a gate)

For each quantity, the smallest power-of-two `N` with `3 * max(s512 over representative seats and candidates) * sqrt(512 / N) <= cap` (the 3-sigma rule; for the Rao-Blackwell mean the mean cap is used and it is labelled an alternative statistic, not Stage47's). `N` is the larger bank of the doubling `N/2 to N`: the change between nested banks of `N/2` and `N` draws has sd `s512 sqrt(512 / N)` under i.i.d. scaling, so this is the bank size at which the worst quantity's doubling would pass its cap about 99.7% of the time. Reported with seat-draws for a live-sized slate (`N` x 71 seats) so later stages can cost it.

### Settledness of composed differences (supporting check of Stage48)

Using blocks 0 to 3 (B = 4), for K versus C and F versus K: per-block pooled `Delta_CRPS` (mean over the 193 fitted seats of the mean N/L CRPS, first minus second, Stage48's definition), `Delta_IS` (mean over the three levels), `Delta_energy`, by pooled population and by election. The estimate is the block mean, `SE = sd/sqrt(4)`, two-sided 95% t interval (3 degrees of freedom). State: **`SETTLED_MATERIAL`** if the interval lies entirely beyond the Stage48 materiality 0.01pp on one side, **`SETTLED_SIGN`** if it excludes zero but not that, **`UNRESOLVED`** otherwise. This labels the existing supporting check only; it does not alter Stage48's decision or finding.

### Seat-win probabilities

Control, all 193 seats. Per candidate probability `p` (block mean) with `s512(p)` across B = 4 blocks; the design effect `D = sum_i 512 s512_i^2 / sum_i p_i (1 - p_i)` over seat-candidates with `0.05 <= p <= 0.95` (D = 1 is an i.i.d. binomial bank). The bound `SE(p) = sqrt(D p (1 - p) / N)` is reported with the `N` giving `SE(p = 0.5) <= 0.01` and `<= 0.005`. The seat-level K minus C difference in the leading candidate probability is reported with its SE and the count of seats whose 95% interval excludes zero. These are arithmetic precision bounds; **no probability-release threshold is set** (open decision for James).

## Compute plan (documented cost bound, not a gate)

Unchanged Stage47 numerics cost about 14 ms per composed draw per seat on one core (measured on one 2017 seat before the freeze): all seats 193 x 2,048 draws, representative blocks 4 to 7 (9 x 2,048) and the three layer-only replicates (9 x 1,536), about 95 CPU minutes in total; documented cap 120 CPU minutes, parallel by independent election and block tasks with results independent of the worker count. No machine-speed gate inside `--check`. No cache, no new national inference, no data source.

## Interpretation rules (frozen)

- `STOP` (harness mismatch): report, change nothing.
- `CAPS_MET_AT_CACHED_BANK`: record that a 4,096-draw frame meets the frozen composed caps; recommend it as the composed reporting frame for later stages (a recommendation, no default is changed here).
- `CAPS_NOT_ATTAINABLE_WITHIN_CACHED_BANK`: record the bound. From here a composed score or probability difference is called settled only by the rule above, composed seat probabilities carry the bound, and the draw requirements are the stated input to any live-fit and production stage. If the layer share of variance is small for the failing quantities, the limit is the national bank (fit/ESS), not layer simulation.
- Mixed or anomalous results (for example scaling far off the i.i.d. prediction, block sd inconsistent with the doubling changes) are reported as such to James; no rule is adjusted.
- Under no outcome is any model default, scale or Stage47/Stage48 result changed.

## Do not

- Do not change any model default, scale, mean, law, existing draw count or frozen gate; do not alter Stage48's results, decision or finding.
- Do not choose or change block count or size, scramble indices, seed formula, ladder, representative seats, caps, multiples or rules after any block 1+ result is read.
- Do not run new national MCMC, regenerate national draws or use cached draws outside the balanced 4,096 subset.
- Do not add an emulator, interpolation or approximation of the conditional-location solves.
- Do not reopen Student-t, mixtures, regimes, sigma shrinkage, geography fragmentation, candidate-quality scores, S reset, covariance fitting or national MCMC backtest reruns.
- Do not add sources or acquisitions or touch `data/sources.json`.
- Do not set a probability-release threshold, publish, claim calibration or produce a 2026 forecast.
- Do not bundle replacement effects, manual adjustment, the Maori baseline, nominations, reconciliation, MMP or the Stage48 weaker-penalty size question.
