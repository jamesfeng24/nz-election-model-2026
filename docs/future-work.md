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
17. Evidence-repair/design checkpoint before model integration: freeze a predetermined historical cohort and uniform evidence protocol for winners, losers, continuations and replacements. The checkpoint itself performs no acquisition or fitting. On separate authorization, assess systematic identity coverage, distinguishing occurrence identity from complete career history and retaining unresolved cases and selection; then test whether repaired evidence improves complete historical predictions against simple benchmarks. Separately review conditional Stage 6 elasticity and establish a defensible target-boundary candidate baseline.
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

Current state: Stage7–11 are merged; Stage11 [PR #18](https://github.com/jamesfeng24/nz-election-model-2026/pull/18) merged as `6ba16fe`. Operational persistence, freshman, replacement and split-view selections remain null; those are unresolved selections, not estimated zero real-world effects. Stage5 transform and Stage6 elasticity operational choices remain unresolved. The evidence-repair/design checkpoint on `stage/12-evidence-repair-design` freezes a predetermined 30-seat-cluster, 415-occurrence identity evidence sample from 213 comparable clusters and describes two complete-forecast designs, simple benchmarks, conditional Stage6 review and the missing target-boundary candidate baseline. It performs no acquisition, identity adjudication or fitting. Stage11's specified probable-continuation carry-forward sensitivity was not implemented and is deferred transparently. **Exact next separately authorized implementation:** bounded uniform identity evidence pass on that sample, with at most 60 new authoritative resources and explicit unresolved cases; do not infer identity from names or inherit winner-selected acquisition. Review completed coverage before authorizing complete historical candidate-view validation, conditional Stage6 refitting or target-boundary candidate baseline construction. Do not integrate models or freeze ensemble weights yet. See [design checkpoint](evidence-repair-design-checkpoint.md).

Historical note: before separately authorized persistence work, canonical main had to contain the actual merged Stage7 work; the merge SHA need not equal a branch completion SHA. The shared person/history/status infrastructure was added in Stage8 and extended with dated tenure in Stage9. Replacement effects remain a later stage.
