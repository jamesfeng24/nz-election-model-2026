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
17. Evidence-repair/design checkpoint before model integration: assess systematic identity coverage on a predetermined historical cohort, using one consistent protocol for winners, losers, continuations and replacements; distinguish occurrence identity from complete career history and retain unresolved cases and selection. Test whether repaired evidence improves complete historical predictions against simple benchmarks. Separately review conditional Stage 6 elasticity and establish a defensible target-boundary candidate baseline.
18. Three separately validated electorate prediction views, where evidence supports them
19. Historical backtesting and only then frozen ensemble weights
20. Only then build the 2026 Opportunity model
21. Ingest 2026 candidate slate
22. Ingest latest 2026 polling
23. Produce 2026 seat model
24. Monte Carlo
25. MMP/overhang
26. Final website/coalition outputs

Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Freeze the historical backtesting design and ensemble weights before Opportunity-specific modelling or current 2026 polling ingestion. Each later task requires explicit authorization.

Current state: Stage7–10 are merged; Stage10 [PR #17](https://github.com/jamesfeng24/nz-election-model-2026/pull/17) merged as `8ae94ccc` with its reviewed correction. Operational persistence, freshman and replacement effects remain null; the Stage10 descriptive replacement shift is not an operational adjustment. Stage11 historical split-ticket [PR #18](https://github.com/jamesfeng24/nz-election-model-2026/pull/18) is open for review. Its local split pattern improves matched ballot-component predictions over simple benchmarks, but incomplete party-ballot mapping and unvalidated candidate transfer keep the operational split view null. Before any integration or ensemble-weight freeze, complete the separate evidence-repair/design checkpoint above, the conditional Stage6 elasticity review and a target-boundary candidate baseline. Stage11 records evidence relevant to those dependencies; it does not carry out the broad identity repair, integrate models or fit weights.

Historical note: before separately authorized persistence work, canonical main had to contain the actual merged Stage7 work; the merge SHA need not equal a branch completion SHA. The shared person/history/status infrastructure was added in Stage8 and extended with dated tenure in Stage9. Replacement effects remain a later stage.
