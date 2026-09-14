# Changelog

## 0.1.0 — 2026-09-07

- Established React, TypeScript, Vite and Vitest static application.
- Added seven responsive pages, navigation, unavailable states and unknown-route handling.
- Reserved modelling module boundaries without implementing statistical logic.
- Added versioned source provenance contracts, empty registry and synthetic metadata tests.
- Added persistent session handoff, methodology, decisions, source standard and reproducibility documentation.
- Added locked dependencies, Node pin and GitHub Actions validation.
- No political data collected; no forecast, allocation engine or deployment produced.

## Unreleased — Stage 1 workflow correction — 2026-09-07

- Created stage/01-foundation from the published foundation; all corrections are reviewable separately from main.
- Added intended statistical specification, explicit estimator constraints and fuller persistent workflow rules.
- Added data/script directory boundaries and offline Python / Web Worker architecture guidance.
- Added draft runtime schemas/types for all requested domain entities, candidate history, predictions, allocation accounting and serializable worker messages.
- Added Python 3.12.2 configuration with zero third-party dependencies, eight integrity tests and a Python CI job.
- Added source-integrity verification without downloading or changing data. No model or election data added.

- Submitted corrective PR #1: https://github.com/jamesfeng24/nz-election-model-2026/pull/1; left open and unmerged. All local gates pass (30 frontend tests, 8 Python tests, typecheck, build and source integrity).

## Stage 2 checkpoint A — recovery and ingestion infrastructure

Preserved recovered official split CSV; added immutable import/checksum-pinned fetch, CSV parsing and Unicode/missing-value tests. No statistical model added.

### Stage 2 checkpoint B
- Acquired and checksum-registered all 139 official 2008 inputs.
- Generated general-electorate results and percentage-only split matrices with national controls and a validation report.
- Preserved source name variants through explicit local mappings; exact unavailable joint counts remain null.

### Stage 2 pause handoff — 2026-09-08
- Checkpoint B pushed as 49bd2356088d6a1ed44b0bab897bee4bd218709c; no 2011/2014 work started.
- Replaced stale state claims; documented actual historical output fields, source limitations, offline reproduction, decisions and precise checkpoint C recovery instructions.
- Stage 2 is incomplete; no completion PR created. Historical PR #1 was subsequently merged by the user before Stage 2.
- Pause-handoff validation passed: 30 frontend tests, 13 Python tests, typecheck, build, 139 source hashes and exact 2008 regeneration.

## Stage 2B — sequencing checkpoint — 2026-09-08

- Verified the valid 2008 merge in main and created stage/02b-historical-2011.
- Recorded the revised 25-step sequence and froze the boundary between historical selection/weight fitting and later 2026 Opportunity/polling inputs.
- Documentation only; no data changes. 2014 remains out of scope.

## Stage 2B — 2011 complete for review

- Preserved 143 official raw resources; produced 63 general electorates, 423 candidate records, 819 party-vote records and 63 split matrices. Added three aggregate split controls and exact summary counts.
- Reused shared ingestion/parsing; retained Unicode/macrons and eight explicit local candidate-name mappings. Documented the informal-party aggregate summary convention.
- Passed 20 Python tests, all 282 source checksums, deterministic 2011 regeneration, targeted byte-identical 2008 regression, 30 frontend tests, typecheck and production build. Zero unresolved numeric reconciliation discrepancies.
- Stage 2A/2008 remains validly merged; 2014 and unified historical integration remain outstanding. Next: 2014 ingestion only. Current 2026 polling and Opportunity remain deferred until historical backtesting/weight freeze.

## Stage 2C — 2014 complete for review

- Recovered and checksum-verified 100 existing sources, pushed before further acquisition; acquired only missing split matrices 20–64 and pushed all 145 raw files.
- Processed 64 general electorates, 451 candidate records, 960 party-vote records, 64 local split matrices, three aggregate matrices and exact summary controls.
- Retained candidate affiliations and eight source-name variants; added explicit 2014-only Internet MANA split grouping. Documented the 337 informal-party summary convention.
- Reused/extracted aggregate validation, retaining the 2011 API and byte-identical 2008/2011 outputs. Twelve focused Python tests, 2014 checksums/regeneration, 30 frontend tests, typecheck/build and whitespace checks passed. No unresolved numeric discrepancies.
- Updated handoff for the next task: 2008–2014 integration and cross-year validation only. No integration, 2017 or statistical/2026 modelling performed.

## Unreleased — Stage 2D historical integration — 2026-09-08

- Confirmed 2008, 2011 and 2014 ingestion merged into main (latest merge 7e9dd53).
- Added six deterministic panel files covering 190 general electorate-years, 2,976 party records, 1,373 candidate records, 190 local split matrices and three election-control records.
- Preserved source labels, election-local identities, name mappings, rounded split percentages and exact aggregate controls. Added separately documented canonical party aliases; preserved 2014 candidate affiliations.
- Added focused cross-year mutation/lossless-projection tests and offline raw-to-panel byte verification in CI. All 31 Python tests and required frontend checks pass.
- All nine prior per-year outputs, 427 raw sources and source registry are unchanged; no new data acquired. Next authorized task should be 2017 historical election ingestion only.

## Unreleased — Stage 3A checkpoint A — 2026-09-09

- Verified PR #5 merged at f627903 and branched stage/03a-historical-2017 from current main.
- Scoped persistent reading/testing rules; removed obsolete Stage 2 branch instructions and repaired current-state wording while preserving historical decisions.
- No data, parser, frontend or model changes. Documentation whitespace validation passed; ingestion checks start with code/data checkpoints.

## Unreleased — Stage 3A checkpoint B — 2026-09-09

- Discovered 145 exact official CSV links, preserving electorate name/number associations from official indexes.
- Extended immutable import allowlist to 2017; saved 12 initial official sources with checksums and retrieval provenance.
- Identified modern percentage/rounding differences before parser implementation. Thirteen focused tests and source integrity pass. No prior processed outputs changed.

- Recovery checkpoint: preserved candidate files 52–71 that survived after the 62-source push; 82 official 2017 files now registered. Saved small modern table parsers and six passing focused tests. Remaining acquisition is only general split files 2–64; no validated full-election outputs yet.

## Unreleased — Stage 3A complete — 2026-09-10

- Recovered and pushed interrupted acquisition/parser/finalization work before continuing; all 145 official 2017 sources now preserved with exact provenance/checksums.
- Added separate modern-format table, election and split adapters. Exported 64 general electorates, 431 candidate records, 1,024 party records, 64 local split matrices, three aggregate matrices and exact national split summary.
- Reconciled all 71 candidate files and national totals. Preserved percentage units, Unicode, original affiliations, disclosure notes and unresolved person identities. No aliases or fabricated joint counts.
- All 51 Python tests, source integrity, deterministic regeneration and prior-year compatibility checks pass. Legacy parser and all prior processed bytes unchanged. CI now checks 2017 regeneration.
- Updated handoff, source coverage, data dictionary and reproducibility. No frontend changes, modelling, cross-year linking, panel extension or later-year acquisition. Next task: 2020 historical election ingestion only.

## Stage 3B acquisition checkpoint — 2026-09-10

- Confirmed merged 2017 PR #6 and branched from a151441 for 2020 only.
- Recorded 147 explicit official resources and preserved 13 representative source files with checksums.
- Verified representative modern table compatibility before bulk acquisition; no processed historical observations changed.

## Stage 3B completion — 2026-09-11

- Recovered all 147 planned originals already saved at cutoff and surviving regression tests; added one supporting official split source to resolve aggregate reporting differences.
- Completed deterministic 2020 outputs: 65 general electorates, 561 candidates, 1,105 party records, 65 local splits, three aggregates, exact national summary and one supporting Māori split.
- Preserved official affiliations with explicit aggregate-only NZ Public Party/Advance NZ reporting metadata.
- Passed 69 Python tests, 720 source checksums, modern deterministic checks and historical compatibility; all 24 prior processed files unchanged.
- No modelling, cross-election identity linking or panel extension. Next task: 2023 ingestion only.

## 2026-09-13 — Stage 3C / 2023 ingestion

- Recovered and pushed source-local joins; retained all 147 acquired official files without reacquisition.
- Added 65 general-electorate outputs (468 nominations, 1,105 party rows), supporting national controls and complete split publications.
- Represented Port Waikato cancellation explicitly; preserved Freedoms NZ constituent affiliations, source blanks and local party-label joins.
- Preserved 21 related bounded aggregate Party Vote Only reconciliation failures with exact rational intervals; no inferred allocations or widened tolerances.
- Passed 96 Python tests, source integrity and deterministic/compatibility checks; all 27 previous processed files unchanged.
- No model, person linking, boundary reconstruction or panel extension. Next: full 2008–2023 historical-panel integration and cross-year validation only, after authorization.

## 2026-09-13 — Stage 3D / full historical integration

- Extended the existing processed-input panel to six elections: 384 electorate-years, 6,210 party rows, 2,833 candidate occurrences, 383 ordinary plus one cancelled split publication.
- Replaced the 2008–2014 combined directory with 2008–2023 outputs while proving byte-identical old subsets and reconstructed manifest; all 18 per-election inputs unchanged.
- Preserved all aggregate/supporting evidence, Port Waikato cancellation, source groupings and 21 known 2023 discrepancies.
- Added six canonical alias keys for five documented name/abbreviation changes; no candidate-person or alliance linking.
- Passed 109 Python tests, source/input integrity, all-year deterministic checks, 30 frontend tests, typecheck and production build.
- No model or boundary harmonization. Next authorized task requires a new instruction: 2023→2026 boundary reconstruction only.

## Stage 4 in progress — 2026-09-14

- Expanded the existing branch scope to three independent boundary-transition baselines (2011→2014, 2017→2020, 2023→2026), with the current transition first.
- Preserved eleven official geography/population/schedule resources with checksums, including four complete HD electorate layers and 57,553 meshblock population records.
- Added strict offline polygon topology decoding, focused tests, pinned optional geometry dependencies and an explicitly incomplete deterministic acquisition audit.
- Recorded suppressed population values and geometry differences for officially unchanged seats; no population weights, synthetic votes, historical data changes or models introduced.


### Stage 4 recovered membership and population evidence

- Preserved the completed 2025 concordance and exact GeoPackage reader; acquired only the needed 2026 historical-code concordance.
- Validated all 57,553 source memberships: 57,517 direct and 36 official lineage joins; no geometry fallback.
- Added deterministic geometry/population and Schedule C disclosure-control audits, 71 passing electorate controls, and focused failure tests.
- Retained suppressed values as unavailable; documented two technical membership exceptions pending crosswalk treatment. Historical observed data and panel remain unchanged; transition weights/notional votes are still incomplete.

### Stage 4 current transition crosswalk

- Resolved both suppression exceptions as sharp feasible intervals without zero filling.
- Added 65→64 general and 7→7 Māori population crosswalk constraints, reverse composition/quality metrics, deterministic manifest and endpoint-conservation tests.
- Preserved all historical observations; older crosswalks and synthetic vote baselines remain outstanding.
