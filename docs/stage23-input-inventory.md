# Stage 23 preserved-input inventory (before construction or scoring)

The [machine inventory](../data/processed/models/complete-party-vector/input-inventory.json)
uses the Stage 5 validated official party tables and the fixed Stage 14
unchanged-boundary frame. There are 213 electorate pairs: 191 held general,
21 held Māori and one cancelled candidate contest (2023 Port Waikato). The
latter still has a party ballot and is part of the full national party-vote
population. The corresponding target elections contain 70, 71 and 72 party
ballot electorates, respectively. These are complete national populations,
not selected 191-seat aggregates.

| Transition | Continuing ballot groups | Entrants | Exits |
| --- | ---: | ---: | ---: |
| 2008→2011 | 11 | 2 | 8 |
| 2014→2017 | 11 | 5 | 4 |
| 2020→2023 | 10 | 7 | 7 |

The Stage 5 continuity record distinguishes Internet MANA's 2014 group from
the 2017 constituent parties and Vision New Zealand's 2020 group from
Freedoms NZ in 2023. The Stage 21 alliance overlay informs election-local
candidate mapping only; it does not create a party continuity bridge.
Independents are absent from the registered party ballot category universe.
All source local category cells are complete exact counts: zero is a recorded
zero, not a failed lookup. Target national shares are supplied, retrospectively
observed conditional inputs. Source and target party-valid denominators are
separate. Target local party counts and shares are reserved for later evaluation;
the target denominator is marked evaluation-only in the inventory.

Every frame record matches the independently validated seat mapping and the
official source/target party table. The Māori table is retained for coverage
and separate evaluation; it is not pooled into general candidate effects.
Historical source geography is exact for these unchanged-boundary pairs.
The 2023-on-2026 bounded geographic artifact cannot be substituted for an
exact future local party vector and is not used here.

The [source contract](../data/processed/models/complete-party-vector/source-contract.json)
pins the consumed official raw files, processed tables, continuity, frame and
alliance overlay. Reproduce with
`python3 -m scripts.models.complete_party_vector.inventory --check`.
No new prediction or historical score was calculated for this checkpoint.
