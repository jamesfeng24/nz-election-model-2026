# Project state

Updated 2026-09-10. GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Active Stage 3B checkpoint — 2026-09-10

2017 PR #6 is merged in main at a151441397b599ea58ce90127a66d160a889b394. Current branch: `stage/03b-historical-2020`, based on that clean main commit. Authorized scope: 2020 ingestion only. The completed 2017 handoff below is retained as historical context.

Official 2020 indexes confirm 65 general + seven Māori electorates. The explicit 147-resource plan is `data/source-plans/historical-2020.json`. 83 official files are imported unchanged and checksum-registered: all six core controls, all 72 candidate files, local split 1, three aggregate splits and exact summary. Core reconciliation passes for all 72 electorates: primary export covers 65 general electorates, 561 candidate records and 1,105 party records. Official winners, majorities, turnout, informal/valid controls and national party/candidate counts reconcile. Shared modern configuration (D019) preserves deterministic 2017 output bytes; 23 focused tests pass. Registry integrity passes for 655 total resources.

Next action: acquire only missing general split files 2–65 using the explicit plan. Then generate full 2020 outputs, add regression/mutation tests, run final validation and update documentation. Candidate/core acquisition is complete. Do not re-download preserved sources. All prior processed outputs remain untouched. No modelling, person linking or panel extension. After this stage the next task is **2023 historical election ingestion only**.

## Historical 2017 completion handoff

## Objective and current stage

Build a transparent static 2026 election website with reproducible offline historical data and later independently validated models. React/TypeScript/Vite/Vitest, no backend/database. No model has been fitted.

Completed and merged: 2008 ingestion (PR #2), 2011 ingestion (PR #3), 2014 ingestion (PR #4), 2008–2014 integration (PR #5, merge f62790363a95823e67158200acb5b864cd2f7741).

Stage 3A / 2017 ingestion is complete on `stage/03a-historical-2017`, under review in unmerged PR #6: https://github.com/jamesfeng24/nz-election-model-2026/pull/6. No 2020 work or extension of the historical panel was performed.

## Branch, recovery and checkpoints

Branch base: f62790363a95823e67158200acb5b864cd2f7741, verified to contain integration head f3485e9007dff2de37567df36beda5b8db702626.

- b1367db: scoped handoff rules and authorization correction.
- b5ab375: explicit 145-source plan and first 12 official files.
- 0ce7d3b: 62 official files preserved before browser interruption.
- 81f3b36: recovered candidate downloads 52–71 and tested table parsers; 82 files.
- a55341e / 88774a1 / ff5b88b: split acquisition batches, culminating in all 145 files.
- bb9ac05: reconciled core election outputs.
- 4ef0fad: full split validation and focused regression tests.
- 24e92f3: recovered interrupted finalization changes: CI regeneration, processor provenance and removal of partial export mode.

All checkpoints above are pushed. Final validated documentation commit: b40ff3236f5ee94976a43e00543739e0c341ea10. PR #6 is open and unmerged: https://github.com/jamesfeng24/nz-election-model-2026/pull/6. This final metadata commit records publication; branch HEAD identifies its exact SHA. Do not create a duplicate PR or merge it automatically.

## Source inventory and outputs

Exactly 145 immutable official 2017 CSV files under `data/raw/elections/2017/statistics/csv/`:
- Six overall/party/winner/turnout controls.
- 71 candidate/voting-place files: 64 general and seven supporting Māori electorates.
- 64 general-electorate local split matrices.
- Three aggregate split matrices (general, Māori, national) and one exact national split summary.

`data/source-plans/historical-2017.json` records official index references and explicit URLs/name-number associations. `data/sources.json` records exact URLs, original retrieval timestamps, SHA-256, immutable paths and processor. Total registry: 572 sources, including the unchanged 427 prior-year resources. Browser-acquired original bytes are committed; normal regeneration is fully offline. No downloads remain.

| 2017 output | Coverage |
| --- | --- |
| `data/processed/elections/2017.json` | 64 general electorates; 431 candidates; 1,024 party records; separate valid denominators, turnout, winners, margins and national controls |
| `data/processed/split-votes/2017.json` | 64 local matrices; three aggregate matrices; exact national split/non-split summary |
| `data/processed/elections/2017-validation.json` | All 145 sources consumed; passed checks; zero unexplained discrepancies; zero required candidate aliases |

All 71 candidate files reconcile 453 candidatures nationally; the 22 Māori candidatures remain supporting inputs rather than detailed primary exports. National valid party votes: 2,591,896; valid candidate votes: 2,529,531; votes cast: 2,630,173.

## Architecture and important files

- `scripts/transform/modern_tables.py`: pure modern-format table parsers and strict numeric checks.
- `scripts/transform/modern_election.py`: 2017-only orchestration, checksum-verified sources, official numbering, national/geographic reconciliation, deterministic export/check CLI.
- `scripts/transform/modern_split.py`: source-preserving rounded matrices, candidate joins and exact summary validation.
- `scripts/tests/test_modern_tables.py`, `test_modern_split.py`, `test_historical_2017.py`: 20 focused tests including deliberate count/winner/checksum/split/identity mutations.
- `scripts/ingest/historical_sources.py` and `import_historical_downloads.py`: existing immutable acquisition system extended only to authorized 2017.
- D018 in DECISIONS.md records the source-format-specific adapter choice. Legacy `historical.py` is unchanged; only genuinely generic helpers are reused. Do not assume future formats match before inspecting their evidence.
- `historical_panel.py` and the 2008–2014 panel remain unchanged and exclude 2017.

## Final checks actually run

PASS on 2026-09-10:
- Entire Python unittest suite: 51 tests.
- Raw source integrity: all 572 registered sources, including all 145 official 2017 files.
- `python3 -m scripts.transform.modern_election --check`: deterministic complete 2017 outputs.
- `python3 -m scripts.transform.historical_panel --check --verify-years`: offline prior-year regeneration and frozen panel validation.
- Byte comparison of every pre-existing processed file (21 files) against branch base: unchanged. This includes all nine 2008/2011/2014 per-year outputs and all six integrated panel outputs.
- Legacy parser unchanged, Python compilation and Git whitespace checks.

No frontend/shared TypeScript changed. Frontend tests/typecheck/build were not rerun, as permitted by updated AGENTS.md for this scoped ingestion task. No formatter/linter is configured; compilation, tests and whitespace checks were run. Remote CI results are separate from these local checks.

## Source peculiarities and limitations

- Source candidate shares are 0–100 percentages: preserve `reportedPercent`; normalize `sourceShare` to a fraction, independently calculate `share`. Turnout rates are rounded to two decimals.
- Local and aggregate split matrix cells contain rounded percentages, not exact joint counts. `count` stays null; `precision` explicitly records percentage representation and two-decimal precision. Exact national summary counts are separate and cannot reconstruct local joint cells.
- The official informal-party non-split summary count is 350, corresponding to Party Vote Only rather than Candidate Informals. Preserve this convention; do not treat it as substantive party behaviour.
- Full candidate names/affiliations match across official 2017 tables, including nested TOP parentheses. No aliases were required. Source spelling/macrons are retained; normalized keys are only local join aids.
- Candidate IDs identify election-local occurrences; `personId` remains null. No cross-election person linking or uncertain party continuity assertions.
- Māori voting-place files include electorate-name section headings. Some files contain a nonnumeric disclosure note about places with fewer than six votes. Numeric rows and columns are reconciled without fabricating missing cells. No geographic remapping or residence inference.
- Seven Māori electorates support national reconciliation; primary outputs cover general electorates only. No boundary harmonization.
- Unresolved discrepancies: none. No regressions, polling models, candidate effects, simulations, MMP or forecasts implemented.

## Exact next task

**2020 historical election ingestion only.**

First confirm this PR is merged and obtain explicit authorization for that task. Later: 2023 ingestion, separate full 2008–2023 panel, boundary reconstruction and historical model development/backtesting. Freeze ensemble weights before 2026 Opportunity/candidates/polling. Do not begin those stages now.
