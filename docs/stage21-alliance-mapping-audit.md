# Stage 21 preserved alliance/category audit

This is a supplemental evidence overlay, not a change to Stage 18/20 predictions,
features or samples. The pre-search factual questions, authoritative routes and
12-query/10-resource ceilings are saved in
`data/source-plans/stage21-alliance-questions.json`. No external query or new
resource was needed for the grouping facts below. A query cannot recover a
constituent-specific count when the official party ballot reported only one
joint group.

## Preserved evidence and exact question

| Election | Official party-ballot group | Official candidate affiliations | Relevant preserved evidence | Finding |
| --- | --- | --- | --- | --- |
| 2014 | Internet MANA | Internet Party; MANA Movement | Electoral Commission overall results `ec-2014-e9-csv-e9_part1.csv`, local party votes `ec-2014-e9-csv-e9_part4.csv`, local candidate and split tables pinned in the overlay source contract | One party-ballot group, distinct candidate affiliations. The local split destination uses the joint Internet MANA reporting label and a unique candidate ID. No constituent-specific party-vote count exists. |
| 2023 | Freedoms NZ | Vision New Zealand; Rock the Vote NZ; NZ Outdoors & Freedom Party | Electoral Commission overall results `ec-2023-statistics-csv-overall-results-summary.csv`, local party/candidate/split tables pinned in the overlay source contract | The grouped summary lists Freedoms NZ party votes and separate candidate-vote lines for all three constituents. Local split destinations retain the candidates' affiliations. No constituent-specific party-vote count exists. |

The 2014 summary has an Internet MANA party-vote row of **34,094** and
separate Internet Party and MANA Movement candidate-vote lines. The 2023
summary has a Freedoms NZ party-vote row of **9,586** and separate NZ Outdoors
& Freedom Party, Rock the Vote NZ and Vision New Zealand candidate-vote lines.
These are election-wide controls. Local party counts and candidate IDs are
joined election-locally and pinned in the 118-record stage-specific source
contract; source labels and earlier processed records are unchanged.

Every affected *held general* electorate has one constituent candidate for
the joint group and one local party-vote group. The published local split row
mass equals the reported local group party votes, and the constituent candidate
is a unique destination in that split matrix. This establishes a **shared
ballot group with one local standing destination**. It does not reveal how a
group ballot would have been attributed to the constituent affiliations, nor
does it establish personal-vote transfer or cross-election continuity.

## Complete exclusion and classification audit

| Case | Held general seats | Earlier Stage 18 classification | Evidence state |
| --- | ---: | --- | --- |
| 2014 Internet Party/MANA Movement | 26 | Ambiguous; excluded from 2014 training | Shared group, one local constituent destination in each seat |
| 2023 Vision New Zealand | 20 | Ambiguous; all 20 target contests and 147 total candidate occurrences abstained | Shared group, one local constituent destination in each seat |
| 2023 Rock the Vote NZ/NZ Outdoors & Freedom Party | 6 | Incorrectly labelled unregistered no-party-group; constructed with base support zero | Same shared group; six **input-classification defects**, not newly eligible contests |
| 2023 Port Waikato Vision New Zealand | 1 | Cancelled/unheld | Remains cancelled; outside the held-general candidate denominator |

The last held group is **four** Rock the Vote NZ and **two** NZ Outdoors &
Freedom Party candidates. The generated overlay covers **53** general seats
in total: 26 in 2014, 26 held in 2023 and cancelled Port Waikato. None has
multiple constituent candidates in the same seat. The overlay records each
source occurrence ID, group, affiliation, old mapping status and raw source IDs.

The old no-party-group classification for six 2023 candidates must not be
retained as if the evidence established zero party support. It affects the
Stage 18 conditional input and the Stage 20 original sample's predictors. The
old numerical and feature outputs remain historical checkpoints; this audit
does not rewrite or score them.

## Counterfactual coverage and representation decision

The preserved evidence can support a **group-level route**: assign the joint
group party share once to its sole constituent candidate in that electorate,
while retaining the original affiliation in a separate field. This is an
explicit baseline representation assumption, not an empirical allocation of
group votes by constituent party. The synthetic accounting kernel rejects
zero or multiple standing destinations and never duplicates group mass.

If that representation is adopted before future fitting, the 26 excluded 2014
training seats and 20 excluded 2023 target contests would become mapping
eligible, subject to all other existing gates. The six already constructed
2023 seats would keep their contest IDs but require corrected nonzero joint
group base inputs. The cancelled seat would remain excluded. If the model
requires a constituent-specific party share, none of these 52 held seats has
that observed input and the group must remain unresolved. These are
**counterfactual coverage counts**, not new model results.

The smallest representation change is to keep candidate affiliation and
ballot-group key separately, and mark `shared_group_single_local_destination`.
Only the group-level party share enters the intensity once. A contest with two
constituent candidates for that group must abstain unless a separately frozen
joint-allocation rule is authorized. No arbitrary split, zero fill or group
duplication is permitted. This rule gives no cross-election continuity to
Internet MANA or Freedoms NZ and changes no Stage 11 split percentage.

The original Stage 20 four-model feature inventory and fitting contract must
remain pinned. A future fit must either use their original IDs with a
transparent limitation/correction decision or commit a pre-fit amended sample
and predictor contract, rerun applicability/rank checks and preserve the old
checkpoint. No Stage 20 fit or Stage 18 rescoring occurs here.
