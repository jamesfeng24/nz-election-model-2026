# Stage 22 pre-fit shared-group amendment

This supplement was committed **after** Stage20's frozen inventory and Stage21's factual repair, but **before** any Stage22 coefficient fitting or target scoring. The original Stage18 and Stage20 files remain historical checkpoints. [The machine contract](../data/processed/checkpoints/stage22-shared-group-prefit/amended-fit-contract.json) pins every amended training and evaluation contest and candidate ID.

## Election-local baseline rule

The official Internet MANA (2014) and Freedoms NZ (2023) party-ballot groups each have one evidenced constituent candidate in 52 held general contests. That candidate receives the group's local party share **once** as the Stage18-style baseline input. The candidate's original affiliation remains a separate field. This is a modelling assumption about candidate-share allocation, not an identified constituent party-vote count. No group support is duplicated or divided. A group with no standing destination creates no candidate; multiple constituent destinations cause contest abstention. Port Waikato's cancelled contest remains excluded. A true independent/no-party-group candidate still receives the affirmative zero-party-support baseline plus fitted floor. A group constituent never does.

Stage5's party-continuity record classifies 2014 Internet MANA as an exit. Later Internet Party and MANA target categories are entrants. No constituent inherits alliance S or V. The 2023 Freedoms group is also a documented entrant relative to 2020. Missing source S/V remains neutral adjustment fallback, not a zero observed feature or zero candidate strength.

## Recomputed coverage and exact common samples

The supplemental mapping verifies all 26 excluded 2014 training seats, 20 excluded 2023 held general target contests, six previously constructed 2023 wrong no-group inputs, and one unchanged cancelled contest. The 20 added contests contain 147 candidates. The 2023 constructed fold becomes **64 contests/459 candidates**, from 44/312. S/V support becomes 271 candidates, from 192. The 2011 and 2017 evaluation folds remain **63/423** and **64/431**, with S/V support 280 and 285. The 2014 repair enters the election-local training mapping but does not directly add a Stage20 transition training record; its source continuity was audited and adds no 2017 S/V.

The 2017 fitted fold trains on the 63 admitted 2011 target contests/423 candidates and evaluates 64/431. The 2023 fold trains on those 2011 contests plus 64 admitted 2017 target contests, **127/854**, and evaluates **64/459**. All four restrictions and all three rounding scenarios must use these identical IDs. The intersection with the original Stage20 constructed 2023 sample is a **44-contest diagnostic subset of the same amended predictions**, never a separate fit. The 20 added contests are reported separately. Existing common contests use corrected group inputs, including the six misclassified cases. The full 213-contest frame remains 191 held general, 21 Māori coverage-only and one cancelled.

## Gate and provenance result

The frozen coverage gates pass in both trained holdouts. The training S/V within-slate design has rank 2 and the floor/S/V design has rank 3 at κ=0.0001, 0.01 and 0.1. The maximum scaled training condition ratio is **2.795**, below 10⁶. These algebraic checks do not show predictive value. Stage22's source contract is a deduplicated snapshot of Stage20/21 consumed records and verifies both registry metadata and raw bytes while allowing unrelated registrations. The output manifest pins input and generator hashes. Original artifacts were not regenerated.

**Next committed phase only:** implement the four frozen jointly fitted restrictions and coherent source-rounding sensitivities; save construction before inspecting evaluation actuals. Any rank, chronology, accounting or numerical solver failure stops fitting/scoring without relaxing the contract. Operational selections remain null.
