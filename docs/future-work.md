# Future work — requires explicit authorization

Only stage 1 is implemented. The following is a proposed sequence, not permission to proceed.

1. **Data inventory and domain schema design:** identify authoritative source candidates and access/licensing constraints; specify observation schemas, identifiers, boundary versions and validation rules. Do not ingest data or implement models in this step unless separately requested.
2. **Reproducible acquisition and processing:** preserve source bytes, register provenance, implement deterministic scripts and validation.
3. **2023 reconstruction on 2026 boundaries:** specify crosswalk methods and quantify allocation uncertainty.
4. **National polling support:** define aggregation, pollster effects and uncertainty with validation.
5. **Electorate baselines and split voting:** use local party/candidate data and boundary-aware identifiers.
6. **Candidate effects and regressions:** specify National/Labour resilience, national-environment normalization, first-term incumbency and replacements; avoid overlap. Model Opportunity separately from TOP.
7. **MMP allocation:** verify rules, implement qualification, Sainte-Laguë, list MPs and overhang cases with independent examples and edge-case tests.
8. **Joint simulation:** connect validated components, propagate correlated uncertainty, seed runs and evaluate calibration.
9. **Explanations and publication:** explain every electorate, document limitations, test performance/accessibility and deploy to Cloudflare Pages.

Cross-cutting unresolved decisions: code licence; source redistribution rights; exact statistical specifications; domain units and schema migrations; offline versus browser computation. Each stage must update the persistent handoff, pass checks and push before stopping.
