# Project state

Updated 2026-09-13. Authorized task: Stage 3D full 2008–2023 historical-panel integration and cross-year validation only.

Branch `stage/03d-historical-2008-2023`, clean base `455d7149caddfeefe23c817533e3ffb6c35809d4`. PR #9 verified merged. All six per-election inputs present; counts exactly match expectations: 384 electorate-years, 6,210 party records, 2,833 candidate records.

Checkpoint A: `data/source-plans/historical-panel.json` pins all 18 processed input hashes and all six old 2008–2014 panel-file hashes before modification. Baseline test passes. Implementation plan: extend historical_panel.py, use existing five output families plus manifest under 2008-2023, preserve source semantics and project the earlier slice back to its original serialized bytes. Do not reparse raw files to build the panel. Later-party rename evidence is being recorded at integration level; no alliance/person linking.

Checkpoint B/C: full core and split panel builds with exact expected counts; five focused integration/baseline tests pass. All five historical content subsets plus reconstructed legacy manifest match baseline hashes exactly. Outputs move from 2008-2014 to 2008-2023 using the same builder/families. Six additional alias keys cover five documented rename/abbreviation relationships; original source labels and alliance/grouping boundaries remain intact. All 2023 discrepancies and cancellation metadata propagate. Next action: add full cross-year/mutation tests and run final verification. Then deterministic/all-year compatibility verification and docs/PR. 2008 aggregate split evidence stays unavailable; 2023's 21 source discrepancies remain unresolved and must propagate exactly. No raw/per-year data changes, modelling, boundary harmonization or person linking.

Exact next task after this stage, only after explicit authorization: **2023→2026 boundary reconstruction only.**

Checkpoint D: full audit passes 109 Python tests; all 867 source hashes pass; full panel --check --verify-years passes (all six per-election regenerations in memory). Two panel builds are byte-identical. All 18 per-year JSON inputs (20 total files in election/split output directories) match branch base. Legacy projection matches five historical content files and reconstructed manifest byte-for-byte. Integration-required frontend verification passes 30 tests, TypeScript checking and production build; Python compilation/whitespace checks pass. Next action: final relevant documentation and unmerged PR. No new source discrepancies.
