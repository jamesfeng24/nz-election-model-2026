# Project state

Updated 2026-09-11. Current authorized scope: Stage 3C / 2023 historical ingestion only.

Branch `stage/03c-historical-2023`, base `8d85200d2c810b28d0ed2d7c0d5820fcb863a2cc`; verified completed 2020 PR #8 merged. Clean start. Prior completed handoff retained below as historical context.

Recovery checkpoint 2026-09-13: all 147 planned 2023 CSV sources are preserved and registered; all 867 repository source checksums pass. Recovered source-local Leighton Baker/NZ Loyal joins; nine focused 2023 tests pass. No new acquisition is needed. Core processing and split reconciliation remain under development. Next action: investigate the Te Pāti Māori general aggregate/local split interval discrepancy from preserved sources, then complete outputs and final verification. Existing historical outputs remain untouched.

Verified 2023 differences: Port Waikato candidate/split labels contain `(Poll Cancelled)`, nine nomination rows publish zeros, winner table omits it (71 winners). Candidate turnout records zero valid/informal and804 special-disallowed/votes-cast. Party vote proceeds normally (42,399 valid +258 informal). Published national split denominator is2,867,478 including Port Waikato; percentage destinations leave its42,657 votes unallocated, rather than excluding it. Preserve this non-behavioural missing mass explicitly. Freedoms NZ overall source separates party/candidate rows and constituent affiliations with blank, not zero, fields. Statistics index notes2May2024 informal-voting-place update; preserve current bytes.

Next action: resolve the preserved-source split interval discrepancy; complete core/split outputs and tests. No modelling, person linking, boundaries or panel extension. After completion, exact next task: **Full 2008–2023 historical-panel integration and cross-year validation only.**

## Historical 2020 handoff (superseded current status)

# Project state

Updated 2026-09-11. GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Objective and current stage

Build a transparent static 2026 election website with reproducible historical evidence and later independently validated models. React/TypeScript/Vite/Vitest; no backend/database. No model has been fitted.

Completed and merged: 2008 (PR #2), 2011 (#3), 2014 (#4), 2008–2014 integration (#5), 2017 (#6). Stage 3B / 2020 ingestion and validation is complete on `stage/03b-historical-2020`; completion PR #8 is open and unmerged: https://github.com/jamesfeng24/nz-election-model-2026/pull/8. Do not repeat acquisition.

## Branch and checkpoints

Original clean main base: `a151441397b599ea58ce90127a66d160a889b394` (2017 merge). During the interruption, the user merged the acquisition checkpoint through PR #7 at `afff44b` on main; it was not reverted or rewritten by this task. The completion PR contains the remaining validation/evidence/documentation changes on the same branch.

- `d362a0d`: explicit official source plan and 13 representative originals.
- `0b3a68f`, `696f00b`, `2b2143d`: candidate acquisition batches; shared modern configuration at 696f00b.
- `ea2fe31`: all 72 candidate files and validated core export.
- `959996c`, `faefea1`: split batches through 41 (123 sources).
- `f26a68e`: all 147 originally planned sources preserved; already pushed before interruption.
- `0b660fe`: recovered surviving regression tests, ten core tests passing.
- `04b3a07`: one additional supporting Te Tai Tokerau split file to investigate aggregate grouping.
- `f18bdb0`: complete split validation, outputs and tests.

All checkpoints are pushed. Final validated documentation commit: `42d26e17366fd21ffca04ef0cbdd7d3e67ef0745`. PR #8 records the completion against main afff44bcbe74de11cae6b171e13764fb7b42eeb4. This metadata-only commit records publication; Git branch HEAD identifies its exact SHA. Leave PR #8 unmerged.

## Inventory and deterministic outputs

148 immutable official Electoral Commission CSV files: six core controls, 72 candidate/voting-place files, 65 general local split matrices, three aggregate matrices, one exact national summary, and one supporting Māori local split matrix (Te Tai Tokerau, number 70). All explicit URLs/name-number associations are in `data/source-plans/historical-2020.json`. All original bytes, retrieval timestamps, SHA-256 hashes and processor provenance are registered in `data/sources.json`; total registry 720 resources. No files are missing.

- `data/processed/elections/2020.json`: 65 general electorates, 561 candidates, 1,105 party records; separate valid denominators, original labels/affiliations, winner/majority, turnout and national controls.
- `data/processed/split-votes/2020.json`: 65 general matrices, one separately identified supporting Māori matrix, three aggregate matrices and exact national summary.
- `data/processed/elections/2020-validation.json`: all 148 consumed sources and passed checks; no unexplained numeric discrepancies; no candidate-name aliases.

Seven Māori electorates support national reconciliation; all 72 files contain 601 candidatures (40 supporting Māori). National valid party votes 2,886,420; valid candidate votes 2,824,198; informal party votes 21,372; informal candidate votes 57,138; votes cast 2,919,073. Split summary denominator is valid plus informal party votes, 2,907,792: 1,981,491 non-split and 926,301 split, including the published informal-party convention.

## Architecture, source differences and limitations

`modern_config.py` defines explicit 2017/2020 settings. `modern_election.py`, `modern_tables.py`, and `modern_split.py` share modern-format parsing/validation; default CLI remains 2017 and `--year 2020` selects this export. Legacy `historical.py` is unchanged. D019 records this architecture. No separate duplicated 2020 parser.

2020 has 65 rather than 64 general electorates and 17 registered party-vote columns. Modern candidate shares and turnout remain percentages rounded to two decimals. Local and aggregate split cells remain rounded percentages with null exact joint counts; national exact summary counts cannot identify local cells. Source disclosure rows are metadata, not zero observations. Candidate labels reconcile strictly without aliases; Unicode and election-local IDs survive; personId is null.

One explicit aggregate-only convention is inferred from the official evidence: NZ Public Party's 1,349 candidate votes are included under Advance NZ in Māori/national split reports. Without this grouping the Advance NZ and other-party column controls fail; with it both exact candidate controls and rounded weighted columns reconcile. Candidate results, national candidate-party totals and the supporting local split label remain NZ Public Party. `aggregateAffiliationMappings` records the scope, inference and source IDs. This does not establish organizational continuity or change any candidate affiliation. The source does not explain the reporting rationale.

The informal-party non-split summary count 537 matches Party Vote Only, not Candidate Informals. Preserve and flag it; do not use it as ordinary party behaviour. Detailed Māori candidatures remain supporting inputs; the one supporting split matrix is separate from general modelling coverage. No geographic harmonization, panel extension, cross-election person linking or modelling occurred.

## Checks actually run — 2026-09-11

- Entire Python unittest suite: 69 tests passed, including 15 focused 2020 tests and prior-year regressions.
- All 720 raw-source checksums passed, including 148 for 2020.
- Deterministic 2020 generation and `--check` passed.
- Deterministic 2017 `--check` passed after shared changes.
- `historical_panel --check --verify-years` passed for 2008/2011/2014 and the frozen panel.
- All 24 processed files present at original base a151441 are byte-identical, covering all earlier per-year outputs and all integrated files. Legacy parser bytes unchanged.
- Python compilation and Git whitespace checks passed. No Python formatter/linter is configured.
- Frontend tests/typecheck/build were not rerun: no frontend/shared TypeScript changes and scoped AGENTS.md does not require them here.

## Exact next task

**2023 historical election ingestion only.** Requires its own explicitly authorized task after review/merge. Do not extend the panel until the separate full 2008–2023 integration stage. Boundary reconstruction and historical model development/backtesting follow later; freeze ensemble weights before current 2026 Opportunity/candidate/polling inputs.
