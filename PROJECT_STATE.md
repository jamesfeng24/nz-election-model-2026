# Project state

Updated 2026-09-13. Authorized task: Stage 3D full 2008–2023 historical-panel integration and cross-year validation only.

Branch `stage/03d-historical-2008-2023`, clean base `455d7149caddfeefe23c817533e3ffb6c35809d4`. PR #9 verified merged. All six per-election inputs present; counts exactly match expectations: 384 electorate-years, 6,210 party records, 2,833 candidate records.

Checkpoint A: `data/source-plans/historical-panel.json` pins all 18 processed input hashes and all six old 2008–2014 panel-file hashes before modification. Baseline test passes. Implementation plan: extend historical_panel.py, use existing five output families plus manifest under 2008-2023, preserve source semantics and project the earlier slice back to its original serialized bytes. Do not reparse raw files to build the panel. Later-party rename evidence is being recorded at integration level; no alliance/person linking.

Next action: extend core and split integration and focused tests, preserving cancellation and known source discrepancies. Then deterministic/all-year compatibility verification and docs/PR. 2008 aggregate split evidence stays unavailable; 2023's 21 source discrepancies remain unresolved and must propagate exactly. No raw/per-year data changes, modelling, boundary harmonization or person linking.

Exact next task after this stage, only after explicit authorization: **2023→2026 boundary reconstruction only.**
