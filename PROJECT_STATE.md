# Project state

Updated 2026-09-13. GitHub is canonical. Stage 3C / 2023 ingestion is complete with explicitly bounded, unresolved official split-source discrepancies; PR readiness checks pass. Leave the completion PR unmerged. No integration is authorized in this task.

## Branch and recovery

- Branch: `stage/03c-historical-2023`.
- Base: `8d85200d2c810b28d0ed2d7c0d5820fcb863a2cc`; completed 2020 PR #8 was merged before this branch started.
- `fe9a6da`: acquisition state preceding instruction cleanup; all 147 planned files already preserved. No reacquisition was performed during this recovery.
- `a9772f4`: approved repository-only workflow cleanup.
- `b796228`: recovered uncommitted source-local Leighton Baker/NZ Loyal joins, nine focused tests and handoff.
- `8253387`: rational interval investigation, bounded source-discrepancy registry and focused tests.
- `1b5aba5`: complete outputs and real-source regression tests.
- `495a5d73ff30b91d91c80ec5afe25bc3fefb6d33`: final documentation and validated output checkpoint.
- Completion PR #9: https://github.com/jamesfeng24/nz-election-model-2026/pull/9 — open, unmerged. This metadata-only commit records publication; exact final SHA is branch HEAD.

All listed checkpoints are pushed. No local-only ingestion work remains. Prior interrupted work was recovered, checked and pushed before further implementation.

## Inventory and outputs

147 immutable official Electoral Commission CSVs: six core tables, 72 candidate/voting-place files, 65 general local split files, three aggregate split matrices and one exact national split summary. Registry contains 867 resources overall. Explicit URLs, acquisition timestamps, SHA-256 and processing provenance are in `data/sources.json`; `data/source-plans/historical-2023.json` defines the acquired inventory. No source is missing.

- `data/processed/elections/2023.json`: 65 general electorates; 468 candidate records including nine cancelled nominations; 1,105 party records.
- Seven Māori electorates support national controls: 495 total nominations across 72 electorates. Candidate contests: 71 held nationally (64 general + seven Māori), one cancelled general contest.
- `data/processed/split-votes/2023.json`: 64 normal local matrices, one cancelled Port Waikato publication, general/Māori/national aggregates, exact national summary and explicit source discrepancies.
- `data/processed/elections/2023-validation.json`: coverage, checks, limitations, source IDs and 21 related failed reconciliation assertions. Status `validated-with-source-discrepancies` does not claim full numeric reconciliation.

National valid party votes 2,851,211; informal party votes 16,267. Exact split summary denominator 2,867,478 = 1,849,366 non-split + 1,018,112 split. National valid candidate votes 2,742,677; informal candidate votes 40,353.

## Architecture and source semantics

Shared `modern_config.py`, `modern_tables.py`, `modern_election.py` and `modern_split.py` support 2017/2020/2023 through explicit configuration. Legacy `historical.py` is untouched. New `split_intervals.py` computes exact rational rounding envelopes and fails closed unless an impossible comparison matches the reviewed fingerprint in `data/source-plans/2023-split-discrepancies.json`.

Port Waikato: valid party vote 42,399 plus 258 informal is substantive. Its candidate poll is cancelled; nine source nominations/zero vote fields are retained, with null winner, majority, candidate shares and elected status. Its zero-percentage local split publication is non-behavioural, with no inferred joint counts. Official aggregate denominators include its 42,657 party votes. Missing destination mass is not rescaled or allocated. The national exact split residual includes cancellation-related ballots and is not wholly behavioural evidence. The by-election is excluded.

Unresolved publication discrepancy: Te Pāti Māori general Party Vote Only local rounding enclosure [1937.4629,1940.3855] versus aggregate [1979.22795,1982.18865], disjoint by at least 38.84245 votes. Fifteen Party Vote Only local/general comparisons, two general row sums and four aggregate column controls are impossible within the original two-decimal precision. Candidate destination joins, aggregate geographic scope checks and exact-summary comparisons otherwise reconcile. See `docs/2023-split-discrepancy.md` for arithmetic and cause analysis. Port Waikato's candidate/party disallowed difference of 619 is consistent with total excess intervals but is not a proven party-level allocation or explanation. Preserve both official publications; no correction, imputation or tolerance expansion.

Freedoms NZ: preserve complementary source rows and blank fields. Explicit published zeros are distinct from blanks; constituent candidate affiliations remain NZ Outdoors & Freedom Party, Rock the Vote NZ and Vision New Zealand. Their grouping under Freedoms NZ is limited to aggregate split destinations. Leighton Baker → Leighton Baker Party and NZ Loyal → New Zealand Loyal are source-local party-table joins. Candidate split whitespace normalization is recorded locally where needed; no person identity joins.

The official index notes a 2 May 2024 update to informal counts at small voting places. Current published bytes are preserved, not pre-update reconstructions. Local/aggregate percentages remain rounded, all exact joint counts null. No candidate-person linking, model fitting, boundary reconstruction or panel extension occurred. Historical TOP is not mapped to 2026 Opportunity.

## Verification actually run

- Complete Python suite: 96 tests passed, including 2023 coverage/cancellation/source mutation, exact interval and fail-closed discrepancy tests.
- Source integrity: all 867 registry hashes pass, including all 147 for 2023.
- Deterministic 2023 generation/check and 2017/2020 checks pass.
- `historical_panel --check --verify-years` passes for 2008/2011/2014 and the existing panel.
- All 27 processed files present at branch base remain byte-identical, including 2008/2011/2014/2017/2020 and the integrated 2008–2014 outputs. Legacy parser bytes also match base.
- Python compilation and Git whitespace checks pass. No Python formatter/linter is configured.
- Frontend tests/typecheck/build were not run: no frontend/shared TypeScript changes; scoped AGENTS.md does not require them for this ingestion stage.

## Exact next task

**Full 2008–2023 historical-panel integration and cross-year validation only.** Start only after explicit authorization. Carry forward cancellation semantics and bounded split-source discrepancies; do not treat them as fabricated reconciled evidence. No modelling is authorized by this handoff.
