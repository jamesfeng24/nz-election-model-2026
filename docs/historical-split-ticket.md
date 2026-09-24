# Stage 11 historical split-ticket modelling

## Evidence checkpoint — before fitting

Stage 10 PR #17 is merged as `8ae94ccc`; Stage 11 starts from that merged main. `evidence.json`, `applicability.json` and a snapshot of the 384 consumed official local split sources were produced before a Stage 11 statistical specification or fit. No historical numerical file or raw source has been changed.

Each local split row is a party-ballot group with an exact published count, including **Informal Party Votes**. Its columns are named candidate destinations, Informal Candidate Votes and Party Vote Only. Cell entries are two-decimal **percentages conditional on that party-ballot row**; local joint counts are not published. A source row count times the reported percentage is a rounded-cell approximation, not an observed count. Rows and columns are joined election-locally to independently published party and candidate totals. The total party-ballot denominator includes informal party ballots and differs from valid candidate votes, so split percentages cannot be silently substituted for published candidate shares. Candidate-only ballots are represented within the informal-party row where reported, not assigned to a valid-party group. A forecast using only valid-party votes would leave that contribution unresolved.

| Election | General local matrices | Candidate columns | Supporting Māori local matrices | Cancelled/non-behavioural | Reviewed source discrepancies |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2008 | 63 | 499 | 0 | 0 | 0 |
| 2011 | 63 | 423 | 0 | 0 | 0 |
| 2014 | 64 | 451 | 0 | 0 | 0 |
| 2017 | 64 | 431 | 0 | 0 | 0 |
| 2020 | 65 | 561 | 1 | 0 | 0 |
| 2023 | 65 | 468 | 0 | 1 | 21 |

The 2023 Port Waikato local publication allocates no candidate destinations after cancellation; it is non-behavioural. The 21 preserved aggregate reconciliation failures involve Party Vote Only and related row/column checks, not 21 independent errors. They are pinned from `data/source-plans/2023-split-discrepancies.json`; none is repaired by rescaling, arbitrary midpoints or allocating cancelled ballots. National exact split/non-split summaries do not reveal exact local joint cells. General/Māori/national **aggregate** split matrices group destinations by party rather than named local candidate; they cannot substitute for the missing Māori local candidate panel. The one 2020 supporting Māori local matrix does not create a comparable six-election series.

The pre-fit applicability inventory covers every target candidature in adjacent elections. It requires the already validated unchanged-boundary transitions (2008→2011, 2014→2017, 2020→2023), same named seat, held contest and Stage5 party continuity. It records exact-chain name evidence as **probable**, never confirmed person identity or proof that a different name is a replacement. No target votes or winner flags enter eligibility. On those three transitions, 247/285/271 general candidates have a source candidate of the same continuing party and a comparable source local matrix. **Zero** candidates have every target party-ballot group represented in that source local matrix: party entry/exit creates unmatched row mass. Thus naive complete transport of local conditional percentages is not a defensible prediction of published target candidate totals. A bounded model must retain that mass or use a separately justified training-only fallback. Changed-boundary transitions, Māori scope, candidates without supported party continuity, cancelled contests, missing source candidacies and unresolved identity remain explicit in `applicability.json`.

The 2014 Internet MANA, 2020 Advance NZ/NZ Public Party and 2023 Freedoms NZ report groupings are source-local aggregate controls, not cross-election party-continuity permissions. Historical TOP is not a 2026 Opportunity prior. Split tables describe joint ballot **aggregates**; they do not identify an individual's voting transition or personal vote. Later modelling must distinguish conditional target-party-vote evaluation from an actual forecast using predicted party votes.

**Next checkpoint:** freeze a parsimonious prediction design and its benchmarks against these recorded coverage limits before calculating any fitted split parameters or holdout errors.
