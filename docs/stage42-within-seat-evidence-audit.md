# Stage42 — within-electorate party-vote geography audit

Audit date: 2026-10-05 (Australia/Sydney). This audit precedes Stage42 feature construction and scoring. It uses preserved sources only; it introduces no fragment vote estimates, political covariates or new adjudications.

## Decision

**The preserved data do not identify whether a transferred residential fragment is more National- or Labour-leaning than its entire source electorate.** They identify geographic membership and bounded population transfers, plus complete source-electorate party votes. They do not link party ballots to the residential meshblocks constituting a transferred fragment.

Continue with Stage41's single feasible population-flow witness and its explicit uniform-within-source party-voting assumption. Do not implement a finer flow scenario in Stage42. Party-mass weighting of S/R can change how existing information is used; it cannot recover political composition absent from the party-flow evidence.

No external acquisition is recommended for this audit: **zero discovery queries and zero new resources**. An official bulk party-votes-by-voting-place dataset is a concrete potential source route, but its additional fact is voting-location party composition, not voter-residence composition. A public residential-unit party-vote allocation or an authoritative residence-to-voting-place catchment/ballot linkage, with ordinary/advance/special coverage, would materially resolve the specific missing fact. None is present or pointed to by the consumed source contracts. Discovering booth tables alone would not justify a directly usable finer flow; adopting catchments and allocating advance/special votes would be an additional transport model. Defer that opportunity rather than spend this bounded stage geocoding polling places.

## What the sources actually contain

| Preserved evidence | Spatial unit / vintage | What is observed | What is not identified |
| --- | --- | --- | --- |
| 2011 Electoral Commission electorate party tables (`e9_part4.csv`, turnout controls) | Source 2007-boundary electoral district at the 2011 election | Registered-party counts and distinct valid-party denominator; ordinary/special aggregate controls | Party votes by meshblock, residential fragment or transferred subarea |
| 2017/2023 `votes-for-registered-parties-by-electorate.csv` and `party-votes-and-turnout-by-electorate.csv` | Source 2014/2020-boundary district at its election | Complete party counts, valid totals, ordinary/special counts, informal/disallowed controls | Within-seat party allocation or voter residence for ballots |
| 2011 `e9_part8_cand_*.csv`; 2017/2023 `candidate-votes-by-voting-place-*.csv` | Voting location plus the voter's electorate ballot; election-specific sites | **Candidate**, not party, counts by casting location; advance/special/overseas and disclosure rows | Residence-to-place catchments; party composition of residential fragments; candidate ballots on target boundaries |
| Local split matrices | Entire source general-electorate party row and candidate destinations | Rounded party-to-candidate behavioural proportions and separate row/column denominators | Any subelectorate or residential split behaviour |
| Stats NZ / Commission crosswalk inputs | Meshblock membership and bounded residential/electoral-population quantities, listed below | Source/target memberships, rounding/suppression constraints, coupled parent splits and target controls | Turnout, enrolled-voter movement, party votes, individual voters or candidate support |
| Stage4 notional party bounds and Stage41 point scenario | Complete target electorate with source contributions | Derived assumption-dependent mass-conserving vote/share scenarios | An additional observation of fragment political leaning |

The headline “Party and Electorate Candidate Votes Recorded at each Voting Place” is not a promise that our acquired file includes both ballots. Scanning all acquired source voting-place files finds **70/71/72 candidate tables for 2011/2017/2023**, each with `Candidate Vote Details`, and **zero** with `Party Vote Details`. The source registry contains no acquired party-votes-by-voting-place counterpart for these years. Do not relabel candidate counts as party counts or infer a party preference from the candidate's affiliation.

### Concrete location-versus-residence checks

`data/raw/elections/2011/e9/csv/e9_part8_cand_1.csv` records Auckland Central candidate votes cast at Auckland Grammar in **Epsom**, ordinary votes before polling day taken in Epsom, and separately aggregated special and overseas votes. The addresses locate ballot casting; they do not locate the voters' homes.

`data/raw/elections/2017/statistics/csv/candidate-votes-by-voting-place-1.csv` includes `Advance Voting Places`, Auckland Airport in **Mangere**, a UNITEC advance site in **Mt Albert**, and these electorate-wide rows:

- `Overseas Special Votes Including Defence Force - Auckland Central`;
- `Special Votes BEFORE Polling Day - Auckland Central`;
- `Special Votes ON Polling Day - Auckland Central`;
- `Voting places where less than 6 votes were taken`.

The corresponding 2023 table includes Westfield **Albany**, advance sites across Auckland, and the same special/overseas/disclosure structure. The small-place aggregate can combine locations; it is not an observed residential population cell. Advance voting sites need not serve only surrounding residents; special and overseas totals have no preserved within-electorate residence join. Even a perfectly geocoded booth point would not establish a residential catchment or resolve these aggregates.

## Coverage, denominators and reconciliation

Official electorate party totals include valid ordinary and valid special party ballots. They exclude informal/disallowed ballots from the valid-party denominator. Candidate ballots have their own denominator and can differ materially. For Auckland Central:

| Source election | Valid party votes | Ordinary valid party | Special valid party | Valid candidate votes |
| --- | ---: | ---: | ---: | ---: |
| 2011 | 34,206 | 27,206 | 7,000 | 33,129 |
| 2017 | 30,007 | 21,749 | 8,258 | 29,170 |
| 2023 | 35,378 | 23,340 | 12,038 | 34,447 |

Do not use ordinary candidate-location counts to distribute those special party totals. The turnout table's ordinary/special partition does not supply party-by-vote-mode counts or within-seat residence. Advance voting is included in the ordinary/special ballot classifications as applicable; the location tables expose separate advance rows but do not create a mutually exhaustive residential partition.

The existing parsers validate candidate table rows/columns against official candidate totals; they independently validate registered-party sums, electorate valid-party totals, percentages and general/Māori/national controls. Those successful arithmetic joins do not create an unobserved spatial join. The complete source national valid-party denominators are **2,237,464 (2011), 2,591,896 (2017), 2,851,211 (2023)**, including the separately supported seven Māori electorates in each year. Stage41 uses all source districts, not the selected overlap sample. In 2023, Port Waikato's party ballots remain substantive although its candidate contest was cancelled.

## Boundary/population compatibility and limits

| Transition | Source / target boundary | Preserved population basis | Compatibility and uncertainty |
| --- | --- | --- | --- |
| 2011→2014 | 2007 / 2014 | 2013 Census meshblock evidence and 2013/2016 official geographic concordances | Level B necessary-constraint outer feasible set; local electoral roll/imputation inputs absent. Rounded descent/resident partitions, 22 split parent meshblocks and target Schedule C controls stay coupled. Not an exact electoral microdataset or 2011 resident-vote sample. |
| 2017→2020 | 2014 / 2020 | 2018 Census electoral population on final Meshblock 2020; official 2020/2021 lineage | Official source/target membership, final target controls and disclosure-aware population bounds. Population vintage differs from 2017 ballot casting; no within-source party allocation is observed. |
| 2023→2026 | 2020 / final 2025 | 2023 Census electoral population, final August 2025 release; official 2025/2026 concordances | Suppressed population cells and random rounding to base three; genuine and technical changes remain distinguishable, coupled controls retained.2025 population membership is not the residential location of each 2023 voter. |

For 2025, `-999` means a suppressed unrounded count in [0,5]; a released multiple of three has compatible integer bounds ±2 under the frozen disclosure rule, not nearest-rounding ±1. Suppression bounds are not probability distributions. The historical adapters preserve their source-specific constraints; no new bounds or interval midpoints are introduced here.

Whole-electorate election IDs join to official geographic membership via the preserved contracts. Meshblock identity can certify equal membership, but not equal residents, voters or turnout. Population-share bounds are not party-vote-share or candidate-error bounds. General and Māori population systems remain separately identified; national Te Pāti Māori party support and Māori candidate votes are distinct quantities.

## Information timing

Completed source election results precede each target election. Nevertheless these saved bytes were retrieved in September 2026, not preserved as historical pre-target snapshots. Registry retrieval time does not prove historical publication time of every revision. The 2023 statistics index notes an informal-count update dated 2 May 2024. The geographical controls were constructed/published for the target redistribution, using population vintages after the source election. This is permissible evidence for the explicitly retrospective historical transport diagnostic; it does not certify a fully dated as-of forecast.

The 2023→2026 controls and Stage40 official 2025 boundary snapshot are present before the recorded 2026 acquisition cutoff. Their availability does not make an incomplete 2026 candidate slate complete, and does not demonstrate historical availability of identity biographies or all party-selection facts.

## Pinned evidence / reproducibility references

Consumed originals are recorded with URL, retrieval time, source limitations and SHA-256 in `data/sources.json`; complete consumed boundary hashes are in the three boundary manifests. Examples checked directly:

| Source record / path | SHA-256 |
| --- | --- |
| `ec-2011-e9-csv-e9_part4.csv` / `data/raw/elections/2011/e9/csv/e9_part4.csv` | `440dc42763577169dd723e1ce69d9ddbbfe98a5184ec9e4ae4f574b0c87070f7` |
| `ec-2011-e9-csv-e9_part8_cand_1.csv` | `744caf2a93ca938159431be5158890bf5507a3753b0570200e7facd3c831b10c` |
| `ec-2017-statistics-csv-candidate-votes-by-voting-place-1.csv` | `4f52c9c03cd9b211a3aaa0d20e32ec7f6622d0351fbc070e4fd54e0fd9a80374` |
| `ec-2023-statistics-csv-candidate-votes-by-voting-place-1.csv` | `f13138b53dc532676785e899e2ee83f72c1eeb23dc0cc4e8ca83185ca89b79a1` |
| `data/processed/boundaries/2011-2014/manifest.json` | `38c1a982f817df6e29b88b8026ffea7b68a01b0d64839ba478bb5c3aa178468b` |
| `data/processed/boundaries/2017-2020/manifest.json` | `b995a6cd492fe0b4f4bed2423bbf9480d545e73286258e929c481592e11af17f` |
| `data/processed/boundaries/2023-2026/manifest.json` | `19314f39832ab42a0917a075a74cb2657ab7d8c118f5948a3060b82db1fbd452` |
| `data/processed/boundaries/secondary-availability.json` | `d68d64318ab35cd3c2f1f993a29fb9e07bf37d93ca06edec68fea4e965822d07` |
| `data/processed/forecast-transport/party-construction.json` | `3e2462f85a89527f23c7753f298c9480e4d5af445869eb3031bcae8657063d10` |

Numerical/source contracts inspected: `scripts/transform/historical.py`, `historical_2011.py`, `modern_election.py`, `modern_tables.py`; `scripts/boundaries/{inputs_2014,transition_2014,population,notional,party_inputs,secondary}.py`; `scripts/transport/party.py`. The historical election parsers expose electorate observations; the notional code explicitly labels its output `synthetic_notional_party_vote_bounds`. Stage41's construction is one exact feasible witness within those assumptions, not a more detailed political geography observation.

The audit changes no raw bytes, source records, earlier derived outputs or model coefficients. It records an identification limit; Stage42 may still evaluate continuous feature weighting as the authorized modelling scenario without claiming that it resolves the limit.
