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

Current state: Stage7 [PR #14](https://github.com/jamesfeng24/nz-election-model-2026/pull/14), Stage8 [PR #15](https://github.com/jamesfeng24/nz-election-model-2026/pull/15) and Stage9 [PR #16](https://github.com/jamesfeng24/nz-election-model-2026/pull/16) are merged. Stage8 persistence and Stage9 freshman-incumbency operational effects remain null. Stage10 [PR #17](https://github.com/jamesfeng24/nz-election-model-2026/pull/17) is unmerged. Its post-review evidence correction finds five independently corroborated general source-winner replacements and 39 continuations; chronological fitted scores are retrospective evidence-selected diagnostics. The acquisition queue partly used inherited identity gaps that can depend on target/later winner anchors, so the operational replacement coefficient remains null despite favourable numerical gates. Official Māori source winners are recovered but person identity remains unresolved for a separate Māori fit. See `docs/replacement-candidate.md` and D037. The next item in the authorized sequence is historical split-ticket modelling, requiring separate authorization; D029's conditional Stage6 elasticity review is a dependency before later integration, not a Stage10 refit.

Historical note: before separately authorized persistence work, canonical main had to contain the actual merged Stage7 work; the merge SHA need not equal a branch completion SHA. The shared person/history/status infrastructure was added in Stage8 and extended with dated tenure in Stage9. Replacement effects remain a later stage.
