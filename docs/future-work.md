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

Current state: Stage4 is merged through PR #11. Stage5 local party-vote transformation backtesting is complete for review; selection remains unresolved among additive, proportional and log-odds. Exact next task after review/merge and explicit authorization: **NAT/LAB electorate elasticity only**. Use one parameterized baseline pipeline and materiality-directed sensitivity, not three separate systems.
