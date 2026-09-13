# Project state

Updated 2026-09-13. GitHub is canonical. Stage 3D full 2008–2023 historical-panel integration and cross-year validation is complete, ready for an unmerged review PR. Known 2023 source discrepancies remain unresolved and explicitly preserved; no new integration discrepancy exists.

## Branch and checkpoints

Branch `stage/03d-historical-2008-2023`; clean base `455d7149caddfeefe23c817533e3ffb6c35809d4`, PR #9 merge verified before work. All six ingestions are merged.

- `dbb2d43`: 18 input hashes and six previous-panel baseline hashes pinned before integration.
- `62d94e7`: six-year core/split integration, source semantics, conservative rename aliases and old-slice proof.
- `c55a727`: focused mutation/cross-year tests and complete verification checkpoint.
- `9ca104a363aac8bcc9a02876c9690aae1e6612f1`: final documentation checkpoint.
- PR #10: https://github.com/jamesfeng24/nz-election-model-2026/pull/10 — open and unmerged. This metadata-only commit records publication; exact final SHA is branch HEAD. All checkpoints pushed.

## Coverage and output files

| Year | General electorates | Party records | Candidate records | Ordinary split matrices | Cancelled split publications |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2008 | 63 | 1,197 | 499 | 63 | 0 |
| 2011 | 63 | 819 | 423 | 63 | 0 |
| 2014 | 64 | 960 | 451 | 64 | 0 |
| 2017 | 64 | 1,024 | 431 | 64 | 0 |
| 2020 | 65 | 1,105 | 561 | 65 | 0 |
| 2023 | 65 | 1,105 | 468 | 64 | 1 |
| Total | 384 | 6,210 | 2,833 | 383 | 1 |

`data/processed/historical/2008-2023/` replaces the earlier 2008-2014 output directory, using the same five content families plus manifest: electorates, party-votes, candidate-votes, split-votes, election-controls and manifest JSON. No redundant second builder. Each year retains national/supporting controls, original source IDs and per-year validation. 2008 aggregate splits remain null/not-collected; later aggregates, exact summaries, supporting 2020 matrix, source mappings and 2023 discrepancy layers are preserved without fabrication.

## Implementation and compatibility

`historical_panel.py` consumes only validated per-year processed JSON during normal panel builds. `panel_config.py` holds coverage and integration-only aliases; `panel_validation.py` audits structure, foreign keys and lossless reconstruction of processed source objects. `data/source-plans/historical-panel.json` pins 18 inputs and prior-panel hashes at base. The manifest records input/output/code/config hashes, counts, coverage and known discrepancies. `--verify-years` separately regenerates all six years in memory for compatibility; it never writes per-year files.

Schema remains 1 with additive modern source metadata. Missing candidateContestStatus on legacy/2017/2020 records means held; 2023 explicitly states held/cancelled. Keeping old records intact permits byte-identical serialized 2008–2014 subsets and an exactly reconstructed old manifest, all six hashes checked on every build. All 18 per-election JSON inputs remain byte-identical to base (20 total files including non-JSON files in those directories). No raw or per-election transformations changed.

## Identity and source semantics

Canonical IDs retain existing Conservative and Mana aliases. Six new alias keys cover five approved rename/abbreviation relationships: New Conservative/New Conservatives → conservative; Te Pāti Māori → maoriparty; NewZeal → oneparty; NZ Outdoors & Freedom Party → nzoutdoorsparty; Social Credit → democratsforsocialcredit. Official Electoral Commission name-change evidence is recorded in panel_config.py, DATA_SOURCES.md and D022. Source labels/keys are unchanged; no temporary alliance or report grouping becomes a global alias. TOP remains separate from Opportunity. No candidate-person linking, incumbent/status inference, boundary harmonization or modelling occurred; all personId values remain null and geography is election-specific as published.

Port Waikato 2023 retains 42,399 valid party votes, nine nominations/source zeros, null candidate shares/elected outcomes/winner/majority and one non-behavioural split publication. The by-election is absent. Aggregate denominators include its party votes; no destination mass is imputed or rescaled. The exact summary's published residual is not wholly behavioural evidence.

The 21 known source reconciliation failures propagate exactly into election controls and manifest. Te Pāti Māori Party Vote Only local enclosure [1937.4629,1940.3855] versus aggregate [1979.22795,1982.18865] remains unresolved. This integration did not reopen the source investigation, widen tolerances or mark it resolved. A new/altered discrepancy fails against pinned input evidence. Details remain in docs/2023-split-discrepancy.md.

## Actual final verification

- Complete Python suite: 109 tests passed.
- All 867 registered source hashes passed; all 18 processed-input hashes passed.
- Full-panel --check --verify-years passed, including six per-election deterministic regressions.
- Two complete panel builds produced identical bytes.
- Five old content subsets plus reconstructed old manifest match their baseline hashes exactly.
- All six elections' processed datasets remain byte-identical to base.
- Integration-required frontend verification: 30 tests passed, TypeScript check passed, production build passed.
- Python compilation and Git whitespace checks passed; no Python formatter/linter configured.

## Exact next task

**2023→2026 boundary reconstruction only.** Begin only after explicit authorization. The panel does not harmonize boundaries or identify voters' residence. Do not fit models or ingest current polling as part of that next task without authorization.
