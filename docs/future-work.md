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

Current state: Stage7 [PR #14](https://github.com/jamesfeng24/nz-election-model-2026/pull/14) is merged as `fa1dda3`. Stage8 candidate persistence is under post-fit audit correction on `stage/08-candidate-persistence`, with [PR #15](https://github.com/jamesfeng24/nz-election-model-2026/pull/15) open and unmerged. Its corrected person/history/status layer has169 directly confirmed occurrences,793 probable and2,045 unresolved. Outcome-independent source-anchored validation has39 same-seat general pairs (20/16/3); target identity may be probable and the2023 cohort is too small for operational selection. Target-win-selected pairs are retrospective diagnostics only. Selected operational coefficient remains null. See `docs/candidate-persistence.md`. Exact next stage after Stage8 review/merge and separate authorization: **Freshman incumbency only**. Reuse the shared history layer, obtain separate electorate/list tenure evidence and fit no replacement effect in that stage.

Before starting separately authorized persistence work, verify canonical main contains the actual merged Stage7 work; the merge SHA need not equal the branch completion SHA. Shared person/history/status infrastructure belongs at the start of persistence; fitting freshman-incumbency and replacement effects remains in their later stages.
