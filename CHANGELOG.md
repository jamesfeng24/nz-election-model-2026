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
