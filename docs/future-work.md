# Authorized project sequence

Revised by the user on 2026-09-08; supersedes earlier proposed implementation ordering.

1. 2008
2. 2011
3. 2014
4. Integrate 2008–2014
5. 2017
6. 2020
7. 2023
8. Full 2008–2023 historical panel
9. 2023→2026 boundary reconstruction
10. Local party-vote transformation backtesting
11. NAT/LAB electorate elasticity
12. Normalized candidate overperformance
13. Candidate persistence
14. Freshman incumbency
15. Replacement-candidate effects
16. Historical split-ticket model
17. Three independent electorate models
18. Historical backtesting and freeze ensemble weights
19. Only then build the 2026 Opportunity model
20. Ingest 2026 candidate slate
21. Ingest latest 2026 polling
22. Produce 2026 seat model
23. Monte Carlo
24. MMP/overhang
25. Final website/coalition outputs

Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Freeze the historical backtesting design and ensemble weights before Opportunity-specific modelling or current 2026 polling ingestion. Each later task requires explicit authorization.

Current state: Stage7 [PR #14](https://github.com/jamesfeng24/nz-election-model-2026/pull/14) and Stage8 [PR #15](https://github.com/jamesfeng24/nz-election-model-2026/pull/15) are merged; Stage8's corrected person/history/status layer has169 directly confirmed occurrences,793 probable and2,045 unresolved, with a null operational persistence coefficient. Stage9 freshman incumbency is in open, unmerged [PR #16](https://github.com/jamesfeng24/nz-election-model-2026/pull/16). Bounded dated electorate/list evidence gave a committed pre-fit inventory of125 comparable source-winner recontesters and93 initially primary-eligible pairs. A post-fit counterfactual audit removed three inherited target/later-winner-dependent pair links. The corrected90-pair general validation improves the no-freshman benchmark in2017 but worsens MAE/RMSE in2023; operational freshman effect remains **null**. See `docs/freshman-incumbency.md`. Exact next stage, requiring separate authorization after Stage9 review/merge, is **replacement-candidate effects only**. Do not fit them as part of Stage9.

Historical note: before separately authorized persistence work, canonical main had to contain the actual merged Stage7 work; the merge SHA need not equal a branch completion SHA. The shared person/history/status infrastructure was added in Stage8 and extended with dated tenure in Stage9. Replacement effects remain a later stage.
