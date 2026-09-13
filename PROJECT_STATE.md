# Project state

Updated 2026-09-14. Stage 4: **Historical boundary-transition reconstruction** on existing branch `stage/04-boundary-2023-2026`. Base `624fe1d74aa43014e0c65f534c161e22b51e250d` (PR #10 merged). Do not restart, rebase or change branches.

## Authorized scope and order

Continue 2023 results → final 2025/2026 boundaries first, then reconstruct 2011 → 2014 and 2017 → 2020 independently. Verify historic boundary regimes from official evidence. Use generic boundary-transition machinery with explicit source election/boundary, target election/boundary, population source and provenance configuration. These are separate derived baselines, never replacements for observed election data or the historical panel.

Primary weights must use contemporaneous official small-area population/electoral-population evidence, preferably meshblocks and official concordances. Whole-electorate land-area weights are prohibited. Preserve fractional party votes and party-by-party mass. Candidate/split sensitivity is secondary and only where defensible. No person linking, modelling, polling or geographic voter-residence inference from voting places.

## Saved progress

- `fa025b0`: authoritative boundary source plan and acquisition/registration tools.
- `0caa0f7`: four immutable official Stats NZ HD layer **metadata responses**, 2020 and 2025 general/Māori, registered in `data/sources.json`. Actual polygon geometry and population records have NOT yet been acquired.
- Working tree was clean on resumption; no surviving uncommitted acquisition found.
- Source validation passed for 871 registered resources at the metadata checkpoint (867 historical + four boundary metadata).
- Historical panel deterministic check passed before branching. Historical outputs remain unchanged; no derived boundary outputs yet.

## Current acquisition and unresolved access

`data/source-plans/boundary-2023-2026.json` holds exact reviewed URLs. Metadata identifies layer 0, native EPSG:2193, official general/Māori fields for each year. Final 2025 layers must be used, never proposed layers. Official publication confirms 2020 boundaries used for 2020/2023 and final August 2025 boundaries for 2026. Historical regime evidence remains to acquire after current geographic checkpoint.

Schedule B direct curl returned a 212-byte HTML access response, not a PDF; it was rejected and not registered. No schedule PDF is preserved yet. The existing Stats NZ layer 122744 browser page subsequently loaded. Its linked official CSV and lookup PDF are now preserved and registered (873 total resources). CSV has 57,553 unique meshblocks, 64 general and seven Māori membership codes. General population is suppressed (-999) in 5,697 rows, Māori in 29,990; all other counts are nonnegative multiples of three. Suppression is not zero. The source uses random rounding to base three; exact control reconciliation needs confidentiality-aware treatment. No weights have been calculated. The CSV contains target membership but no source membership; official concordances or geometry are still required. Do not re-download these two valid sources.

Exact next action: acquire deterministic full-resolution geometry queries using preserved layer metadata; obtain official schedules B/C and layer 122744 schema/population evidence through normal official access; reconcile 65+7 source and 64+7 target inventory and official changed/unchanged controls. Save this geographic checkpoint before lengthy historical acquisition. Never infer population transfer from metadata or electorate area.

## Remaining checkpoints

A. Current 2023→2026 geometry/schedules/population and change reconciliation.
B. Generic crosswalk framework and validated current transition.
C. Historical 2011→2014 and 2017→2020 geography/population sources, saved before lengthy processing.
D. Three population crosswalks with conservation and quality metrics.
E. Three separate notional party-vote baselines with per-party conservation.
F. Optional defensible candidate/split sensitivity.
G. Final determinism, substantive validation, immutable historical-byte checks, documentation and unmerged PR into main.

Every meaningful checkpoint must update this handoff and be pushed. No Stage 4 PR yet. All three transitions must be complete before final PR readiness. Preserve Port Waikato cancelled candidate/split missingness, substantive party votes and the 21 documented 2023 source discrepancies. No prior output or panel changes authorized.

Exact next stage after all three transitions are complete, only on explicit authorization: **Local party-vote transformation backtesting only.**
