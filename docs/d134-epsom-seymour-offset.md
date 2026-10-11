# D134: Epsom, David Seymour's candidate weight (James, 2026-10-11)

**Question.** Why is Seymour only about 65% to win Epsom, and should the model expect more of his split-ticket vote?

**Finding.** The model's mean was sound arithmetic with the wrong split rate. With National's Epsom party vote falling from 52% (2023) to 36% in the national draws, the fitted candidate step gives Seymour about 36% of the candidate vote. The 2023 split-ticket tables (Stage 11, D038/D039) show ACT voters giving Seymour 93%, National voters 56% and National voters in 2020 70%. Applied to the 2026 party vote, 2023 rates give 38.7%; the 2020 and 2023 average gives about 45%.

**Change.** `candidate.candidateExponentOffsets` in `config/nowcast-2026.json` adds a log-weight offset to one named candidate in one seat: Seymour, +0.40 (the Epsom S-feature shift of +0.45 at the fitted slope is +0.404). `general.candidate_exponent_offsets` reads it, `candidate_row` adds it to the exponent next to the D132 party offsets, and the validator checks the shape. `assemble` applies it only to the live slates; invented slates (tests, the synthetic fixture) carry no real candidate. Nothing else changes: seat noise (Epsom is exceptional, multipliers 1.00), the national, local-party and Māori layers and MMP are untouched.

**Effect (4,096 national draws x 16 replicates, no Epsom poll).**

| | Seymour mean share | Seymour 10th percentile | Seymour wins | Green wins |
|---|---|---|---|---|
| before | 36.0% | 12.6% | 64.8% | 17.2% |
| after | 45.2% | 19.1% | 79.2% | 11.4% |

A 90% win needs a mean near 54% at this noise, which is above any split rate observed in 2014 to 2023, so 90% is not reachable without narrowing the spread. That is not done.

**Status.** James's judgement, not a fitted value. To be reconsidered when an Epsom poll appears: with the D133 rule the poll would then move every candidate, on top of this offset. Reproduce: `python3 -m scripts.tests.test_d134_epsom_seymour_offset`.
