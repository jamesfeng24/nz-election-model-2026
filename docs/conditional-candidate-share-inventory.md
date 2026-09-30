# Stage 18 pre-fit input inventory

This inventory was generated and committed before fitting or scoring. It uses the frozen Stage 14 213-contest frame and all six preserved election-local general-seat tables. No candidate votes, elected flags, residuals, person links or profiles determine mapping or eligibility. They remain separate evaluation or unused evidence. The [machine inventory](../data/processed/models/conditional-candidate-share/inventory.json) lists each official occurrence, source affiliation, mapping tier and frame decision. The [source snapshot](../data/source-plans/stage18-conditional-candidate-share-sources.json) pins every consumed general-seat registry record and raw bytes; unrelated new records are permitted.

| Year | All general training seats | Complete mapping | Ambiguous report-only mapping | Cancelled |
| --- | ---: | ---: | ---: | ---: |
| 2008 | 63 | 63 | 0 | 0 |
| 2011 | 63 | 63 | 0 | 0 |
| 2014 | 64 | 38 | 26 | 0 |
| 2017 | 64 | 64 | 0 | 0 |
| 2020 | 65 | 65 | 0 | 0 |
| 2023 | 65 | 44 | 20 | 1 |

The fixed evaluation frame has 63/64/64 held general contests in 2011/2017/2023, with **423/431/459 = 1,313** standing candidate occurrences. The separate frame also retains 21 Māori coverage-only and cancelled Port Waikato. On this conservative mapping, 20 held 2023 frame contests have an ambiguous Vision New Zealand/Freedoms NZ report grouping; 171 held general contests have complete mapping before training gates. The 2014 Internet Party/MANA Movement and 2023 Vision New Zealand affiliations are not assigned to their report-only joint party-vote groups. Those groupings do not establish an individual candidate's unique party-ballot category. No unsupported candidate is quietly assigned zero party support.

An exact candidate affiliation key in the official local party-ballot roster maps to that group. `Independent` has an affirmative no-party-group classification. Another affiliation absent from the exhaustive official registered party-ballot roster for that election is recorded as an unregistered no-group affiliation unless it belongs to the documented report-only groupings above. The source label is immutable. The entire standing slate is retained in each record, including losers and candidates without a party-ballot group. A missing local group for an otherwise registered party and duplicate mappings are explicit failures or abstentions. This election-local classification says nothing about person identity, party continuity, career history or the candidate's own strength.

The inventory does not score or fit. Its exclusions are not adjusted after seeing outcomes. The 2014 ambiguity reduces the earlier training pool but does not restrict it to the comparable evaluation frame. Historical target party vectors are observed after the election, so subsequent scores are conditional development diagnostics, not as-of forecasts.
