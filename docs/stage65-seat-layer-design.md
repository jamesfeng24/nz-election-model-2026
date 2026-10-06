# Stage65: per-draw MMP seat layer, frozen design and verification plan

**Status: frozen before any verification test was written or run.** Later changes are amendments recorded below, never silent rewrites. Authorised by James on 2026-10-06 ("anything that can currently be run concurrently should be"). Decision number D097 (coordinator).

## The one question

Can the merged Stage49 allocator (`src/models/mmp/allocate.ts`, unchanged) be wrapped into a per-draw seat layer that takes simulated national party-vote shares and electorate winners, including Māori electorate winners as a separate input, and returns Parliament outcomes and summaries, such that fed actual votes and winners it reproduces the official 2008–2023 results exactly?

This stage builds and verifies the layer. It forecasts nothing, publishes nothing, exports nothing to the site and produces no probabilities for release (the release policy is still open). Live inputs (Stage62 national fit, Stage64 boundaries, Stage66 Māori seat layer) are plugged in at final assembly; this stage defines the interface and tests it with historical and synthetic inputs only.

## Interface (frozen)

**Configuration** (`SeatLayerConfig`, plain JSON): `rulesVersion`, `rulesSourceIds`, optional `nominalSeats` (default 120), `listedPartyIds` (parties on the party-vote ballot, which may win seats), optional `unlistedBucketIds` (aggregate vote buckets such as "other": their votes count in the valid-vote total, they can never qualify or win list seats), optional `voteScale` (integer total used to turn shares into integer votes; default 10^9), optional `expectedElectorateIds` (`general`, `maori`: when given, every draw must name exactly one winner for each, because a missing electorate is never treated as zero), and `blocs`.

**Blocs are configuration, not code.** `blocs: {id, label, partyIds[]}[]`; every party must be in `listedPartyIds`. A bloc has a majority in a draw when its summed total seats exceed half of that draw's Parliament size (strictly more than half; exactly half is reported separately as a tie). No 2026 bloc is declared in the source tree; the choice of blocs is James's. Tests use clearly synthetic ones.

**Draw input** (`SeatLayerDraw`): `partyVoteShares` over listed parties plus buckets (non-negative, sum 1 within 1e-6, else error, never silently renormalised), `generalWinners` and `maoriWinners` (`ElectorateWinner[]` as in the Stage53 pipeline interface, so the layer composes with it). A winner whose `partyId` is null or is not a listed party is an independent or non-listed-party winner (s 191(8)): it removes a seat from the Sainte-Laguë total. A winner for a bucket id is treated the same way. An alternative `SeatLayerVotesDraw` takes integer party votes directly (used for the official historical results).

**Per-draw rule.** Shares to integer votes by largest remainder at `voteScale`; the buckets' votes are split into pieces each strictly below 5% of the total so the Stage49 allocator, which treats every input party as potentially qualifying, sees them in the total but can never qualify them (checked after the call); electorate winners are counted per listed party as constituency seats; `allocateSeats` is called unchanged. Output per draw: seats per party (electorate, list, total, entitlement, overhang, qualification and reason), Parliament size, overhang, unfilled seats, independents, and whether a lot was needed.

**Exact ties.** If the allocator returns `tie-at-cutoff` (s 191(9) requires a lot), the layer draws the lot from an injected uniform stream (the draw's own seeded stream in the pipeline), by adding one vote to the chosen tied party and re-running, repeated for each remaining tied seat; the count of lots is recorded. With no stream supplied it throws rather than choosing silently. With continuous simulated shares on a 10^9 scale a tie is a measure-zero event.

**Summaries** (`SeatSummaryAccumulator`, serialisable, mergeable so Web Worker chunks combine exactly): per party, seat histogram with mean and 5/25/50/75/95 quantiles, probability of any seat, probability of clearing the threshold split into by 5% of party votes and by the electorate lifeboat only, mean electorate/list seats, probability of overhang attributable to the party; for Parliament, probability of any overhang, overhang and size distributions, mean size; for each configured bloc, seat distribution, probability of a strict majority, probability of exactly half. Every probability carries its Monte Carlo standard error `sqrt(p(1-p)/n)`; nothing is reported as more precise than the draw count allows.

## Verification (frozen)

1. **Official reproduction.** For each of 2008, 2011, 2014, 2017, 2020, 2023: general electorate winners from the preserved processed candidate results (`data/processed/historical/2008-2023/candidate-votes.json`, `elected` flag), Māori electorate winners as the party-count residual between the oracle's constituency seats per party and the general winners (those files carry no Māori candidates; allocation needs only counts, and the residual is checked to be exactly seven seats in each year), official party votes from `data/processed/mmp/oracle-seat-tables.json`. Pass: every listed party's list seats and Parliament size equal the official values, through both the integer-votes path and the shares path (`votes / total`), including the four overhang elections. 2023 excludes Port Waikato as in the oracle (declaration-day size 122).
2. **Property tests** on seeded synthetic draws (labelled synthetic, never used in a result): seat accounting reconciles with the `MmpAllocationSchema`; Parliament size is nominal plus overhang; the entitlements sum to the seats allocated; non-qualifying parties hold no seats; overhang only where electorate seats exceed entitlement; a party's entitlement never falls when only its own vote count rises; invariance to the order of parties and winners and to scaling votes; determinism; the bucket never qualifies at any size; independents reduce the allocated total.
3. **Accumulator tests:** chunk invariance (merging two halves equals one pass, bit for bit), JSON round trip, hand-worked tiny cases for each summary, majority versus tie at exactly half.
4. **Interface tests:** missing, duplicate or cross-listed electorates fail; shares not summing to one fail; Māori winners are accepted only through `maoriWinners`; a bloc naming an unlisted party fails; the adapter satisfies the Stage53 `MmpStage` interface and its allocation passes `MmpAllocationSchema`.

## Do not

No change to `allocate.ts`, any model scale or any frozen output; no `data/sources.json` edit; no new data acquisition; no live inputs, 2026 bloc choices, probabilities for release, site export or publication; no edit to Stage60–64, 66, 56 or PR #68 files; no CI registry change.

## Results

All pre-registered checks pass, first run, no design amendment.

- **Official reproduction:** all six elections reproduce every listed party's list seats and the Parliament size exactly, through both the integer-vote path and the shares path (shares = votes / total, converted at 10^9): 2008 122, 2011 121, 2014 121, 2017 120, 2020 120, 2023 122, including the four overhang elections. General winners are the 63–65 per election in the preserved candidate results (64 in 2023, Port Waikato excluded as in the oracle); the Māori residual is exactly seven seats in every year. No lot was needed in any election.
- **Tests:** `src/models/mmp/seatLayer.test.ts`, 37 tests (13 historical: 12 election replays plus the overhang-case check; 7 property tests on 400 seeded synthetic draws; 4 bucket/threshold; 2 tie; 6 validation; 4 summary; 1 adapter), all passing; the 26 Stage49 allocator tests still pass unchanged.
- **Property checks held on every draw:** accounting reconciles with `MmpAllocationSchema`; Parliament size is 120 plus overhang; entitlements sum to 120 minus independents; only qualified parties hold seats; list = max(0, entitlement - electorate) and overhang = max(0, electorate - entitlement) per party; order and scale invariance; own-vote monotonicity of entitlements. Overhang and non-overhang draws and independents all occurred in the synthetic set, so the properties were not vacuous.
- **Summaries** carry Monte Carlo standard errors and merge exactly across chunks (a 77/123 split reproduces the single-pass state byte for byte).

## Limits

- Nothing here is a forecast. Synthetic draws are test fixtures only. The historical Māori winners are party-count residuals, not electorate identities; allocation needs only counts, and the Māori seat layer (Stage66) will supply identities.
- Bloc majority uses a simple strict-majority-of-Parliament rule; confidence-and-supply arrangements, a party declining to sit, vacancies, list exhaustion (list lengths are not an input) and the by-election seat arithmetic are not modelled.
- Component-party registrations and the 2026 ballot roster stay open (see mmp-rules-verification.md); a winner for a party that is not in `listedPartyIds` is counted as an independent seat (s 191(8)).
- Share-to-vote conversion treats simulated shares as continuous (10^9 scale); sampling noise in real vote counts is not added.
- Seat-count and threshold probabilities inherit all upstream uncertainty and calibration limits of the national, local and candidate layers, none of which are assessed here.

## Amendments

None.
