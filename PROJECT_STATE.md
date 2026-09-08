# Project state

Updated 2026-09-08. GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Objective and current stage

Build a transparent, reproducible static 2026 New Zealand election website. React/TypeScript/Vite/Vitest; offline Python data preparation; no backend/database. Preserve raw evidence and uncertainty. No statistical models have been implemented.

- Stage 1: application architecture and permanent handoff complete and merged.
- Stage 2A / 2008: complete and merged through PR #2; valid main merge `f819f48fe4030a7fbe5a9aa22f7826a745f7e509`. Never revert this merge.
- Stage 2B / 2011: complete and merged via PR #3 at main 2448ec6.
- Stage 2C / 2014: in progress on stage/02c-historical-2014; raw acquisition checkpoint underway.
- 2008–2014 integration/unified validation: still outstanding after 2014. The broader historical stage is not complete.

## Permanent sequence and modelling constraint

The revised 25-step sequence is in docs/future-work.md. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Both are intentionally deferred until historical backtesting and ensemble-weight freeze. This task does not authorize any later work.

## Branch and checkpoints

The branch was created from current main after a successful fetch and clean working-tree inspection. Local Git fetch/push now works; no separate credential change is needed. Main was not modified by this task.

- `720ceb6`: sequencing documentation pushed before ingestion.
- `a1bda19`: initial 2011 acquisition/shared importer checkpoint pushed.
- `418b30c`: complete raw acquisition, primary outputs and core reconciliation pushed immediately.
- Final handoff follows these checkpoints; use branch HEAD for its SHA. PR is to be created after this commit is pushed; locate it by head branch in GitHub if resuming during publication. Do not create a duplicate or merge it.

## Available data and important files

- `data/sources.json`: 282 registered raw resources (139 for 2008; 143 for 2011), exact URLs, acquisition timestamps, SHA-256 and processor paths.
- `data/raw/elections/2011/`: six E9 summary/control CSVs, 70 candidate CSVs, 63 general-electorate split CSVs, three aggregate split matrices and one exact split summary. Originals are unchanged.
- `data/source-plans/historical-2011.json`: explicit URL inventory and observed browser download filenames; no dependency on chat history.
- `data/processed/elections/2011.json`: 63 general electorates, 423 candidate records, 819 party-vote records, winners, margins, valid denominators, turnout, national/general/Māori controls and source IDs.
- `data/processed/split-votes/2011.json`: 63 local matrices, three aggregate percentage matrices and exact published split/non-split summary counts.
- `data/processed/elections/2011-validation.json`: checks, counts, eight explicit local name mappings, source peculiarity and zero unresolved reconciliation discrepancies.
- `scripts/ingest/historical_sources.py` and `import_historical_downloads.py`: shared immutable import/reacquisition; year-correct provenance organisation and optional explicit download filenames.
- `scripts/transform/historical.py`: shared deterministic processor, 2011 local name mappings, optional 2011 control extension.
- `scripts/transform/historical_2011.py`: 2011-specific coverage and aggregate controls, not a separate ingestion pipeline.
- `scripts/tests/test_historical_2011.py`: deterministic export, Unicode/missingness, exact aggregate summary and semantic mutation tests.
- Existing 2008 raw/processed files are unchanged. Existing app/model interfaces remain in src; historical data is not yet loaded into the UI.

## Final validation status

PASS locally: 20 Python tests; 282 source-file checksums; deterministic 2011 output regeneration; targeted byte-for-byte 2008 regeneration because shared Python code changed; 30 frontend tests, TypeScript checking and production build as required by AGENTS.md; git diff whitespace check. No frontend or shared TypeScript files changed. Remote CI status is separate from these local results.

2011 reconciliation passes for expected/unique electorate coverage, nonnegative counts, party/candidate denominators and normalized shares, official winners/margins, turnout components, general/Māori/national totals, national party and candidate-party totals, all local split rows/columns within published precision, aggregate split controls and local-to-general aggregate intervals. National valid party votes: 2,237,464; valid candidate votes: 2,172,434; votes cast: 2,278,989. No unexplained numeric discrepancies remain.

## Source differences and limitations

- 2011 CSVs contain UTF-8 BOMs and macrons; source spelling is preserved. Original/full and split display names remain in their respective records. Eight explicit local aliases are documented; candidate occurrence IDs are reliable only within the election. personId remains null; no candidate-continuity model.
- Electorate split cells publish two-decimal percentages only, with count:null. Three party-destination aggregate matrices likewise publish percentages. The separate summary supplies exact aggregate split/non-split counts, not exact electorate joint cells.
- The summary's Informal Party Votes non-split count (424) corresponds to Party Vote Only in the overall table, not Candidate Informals. This source convention is retained and flagged; exclude it from party-behaviour estimates. No raw correction was made.
- Split denominators include informal party votes, exclude disallowed ballots and differ from valid-vote share denominators. Māori candidate files support national controls; primary modelling outputs cover general electorates only.
- 2011 needs no structural rewrite of the shared 2008 CSV reader; adaptations are provenance, explicit aliases and additional control validation. Aggregate controls were not collected for 2008 in this task; harmonizing them belongs to later integration.
- Browser acquisition was reused from 2008 after earlier direct-download blocking. All raw files are committed, so regeneration is offline. Fetch scripts remain checksum-pinned; do not replace raw data if a remote release changes.
- Historical JSON contracts remain separate from draft model-facing TypeScript schemas. Party keys are normalized source-name keys, not assertions of political continuity. Boundary labels identify historical publication vintage, not geometry or a crosswalk.
- No 2014, later election, 2026 polling, Opportunity, statistical model, deployment or code-licence choice was attempted.

## Recovery history

The interrupted 2008 session yielded one recoverable Auckland Central split CSV, preserved unchanged; no partial code survived. That work is now merged. This 2011 task began from a clean checkout of that merged state and pushed its own checkpoints. Preserve any new local work before future synchronization.

## Modelling components outstanding

All fitted components remain outstanding. Follow the sequence in docs/future-work.md: finish historical ingestion/integration, then boundary reconstruction, historical estimators and backtesting/weight freeze before later 2026-specific work.

## Exact next recommended task

**2014 ingestion only**

When explicitly authorized, fetch current main, inspect status and confirm the 2011 PR's review/merge status before selecting the next branch. Read AGENTS.md and this file plus relevant code/documentation. Reuse the shared pipeline, preserve source differences, push checkpoints and stop after an unmerged PR. Do not infer permission for integration or statistical modelling.

## Active 2014 checkpoint

Existing branch fast-forwarded to the confirmed 2011 merge. 2014 has 64 general plus seven Māori electorates. Initial controls/candidate/split files parse with the shared reader. Split destinations group Internet Party and MANA Movement as Internet MANA; actual candidate affiliations are retained. Complete acquisition, adapt source-specific joins/controls, validate and push data immediately; then final docs/checks and unmerged PR. Do not begin integration. Next after this task: **2008–2014 integration and cross-year validation only**.

## 2014 recovery and complete acquisition

Recovered and checksum-verified 100 files, including all 71 candidates and split matrices 1–19; pushed as 73f68dc before further downloads. Acquired only missing split matrices 20–64. All 145 planned 2014 raw resources are now preserved: 71 candidate files, 64 local split files, six E9 controls and four split aggregate/summary controls. Processing remains in progress; no claim of completed validation yet. Next within this task: resolve documented source-name joins, reuse aggregate validation with 2014 grouping, push processed outputs, then final tests/docs and unmerged PR.
