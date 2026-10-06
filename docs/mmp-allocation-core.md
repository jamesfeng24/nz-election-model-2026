# Stage49 MMP allocation core — frozen design and results, 2026-10-06

One question: does a deterministic, DOM-free, serializable TypeScript allocator reproduce the official 2008–2023 New Zealand seat allocations exactly, under the Electoral Act 1993 as at 1 January 2026? Rule sources and open items are in [mmp-rules-verification.md](mmp-rules-verification.md). Authorized by James on 2026-10-06 (concurrent MMP work, D082 scope). This stage allocates seats from given inputs only; it forecasts nothing.

## Frozen design (written before the code was run against the oracle)

1. **Qualification (s 191(4)).** A party listed on the party-vote ballot qualifies if its valid party votes are at least 5% of the valid party votes of all listed parties (integer test `20 × votes ≥ total`, inclusive), or it has at least one constituency win (component-party wins are attributed to the listed party by the caller).
2. **Seats to allocate (s 191(7)–(8)).** `N = nominalSeats − independentElectorateSeats`, where the second term counts electorate winners who are independents or belong to a party not on the party-vote list.
3. **Quotients (s 191(5)–(7)).** Divide each qualifying party's votes by 1, 3, 5, …; take the N highest quotients. Comparisons use exact integer cross-multiplication, guarded to stay within the safe-integer range. An exact tie that straddles the cut-off returns `tie-at-cutoff` (s 191(9) requires a lot, which the code never draws).
4. **List seats and overhang (s 192).** Entitlement = quotients taken. List seats = max(0, entitlement − constituency seats); overhang = max(0, constituency seats − entitlement). Equal seats give zero list seats and no overhang. Other parties' entitlements are never recomputed.
5. **Size and unfilled seats (s 193(4)).** Parliament = nominal + total overhang. If a party's available list candidates (after removing electorate winners) are fewer than its list seats, the shortfall is `unfilledSeats`.
6. **Output.** The existing `MmpAllocation` contract (validated by `MmpAllocationSchema` in the tests) plus an audit object with the quotient order, entitlements and per-party overhang.

Not implemented, by design: the by-election seat added after a cancelled electorate poll, party-to-component-party mapping, list ordering and eligibility, vacancies, forecasting inputs.

## Oracle

`scripts/mmp/oracle.py` builds `data/processed/mmp/oracle-seat-tables.json` from the Electoral Commission "Summary of Overall Results" CSVs already preserved for 2008–2023 (party votes, constituency seats won, list seats allocated), with each raw file's SHA-256. `python3 -m scripts.mmp.oracle --check` regenerates it byte-for-byte; a Python test covers that and the parser. No data was imputed. Official Parliament sizes derived from the tables: 2008 122, 2011 121, 2014 121, 2017 120, 2020 120, 2023 122 (declaration day, Port Waikato pending).

## Results

- All six elections reproduce exactly: every party's list seats and the Parliament size, including four overhang elections (2008 overhang 2; 2011 and 2014 overhang 1; 2023 overhang 2) and three elections with no overhang. No tie occurred in any official election.
- 26 allocator tests (hand-worked 620/300/80 example, 4.99% vs 5.00% boundary, one-electorate bypass, independent winner, tie flag, list exhaustion, overhang with unchanged entitlements, scale invariance, input validation, JSON round trip, 300 seeded synthetic accounting trials against the domain schema). Synthetic fixtures are labelled and not used in any application result.
- The Act text is preserved and registered in the separate dated `data/processed/mmp/source-registry.json` (Stage40 pattern), deliberately **not** in `data/sources.json`, which about 25 historical stages hash.

## Limits

This validates the rule implementation on historical vote totals, not any forecast. The oracle covers six elections and four overhang cases; component-party registrations, the by-election seat arithmetic and 2026 ballot roster remain open (see the verification doc). The allocator makes no statement about which minor parties will win electorates.

## Do not (this stage)

No Monte Carlo wiring, electorate probabilities, frontend changes, `.github/workflows`, Stage47 files or later stages.
