# Project state

Updated 2026-09-08 (Australia/Sydney). GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Objective and current stage

Build a transparent, reproducible static website modelling the 2026 New Zealand election. React/TypeScript/Vite/Vitest; offline Python preparation; no backend/database. Read AGENTS.md, DECISIONS.md, METHODOLOGY.md, DATA_SOURCES.md, docs/statistical-specification.md, docs/data-dictionary.md and docs/reproducibility.md before major work.

**Stage 2A / 2008 is complete and merged via PR #2 at main f819f48fe4030a7fbe5a9aa22f7826a745f7e509. Stage 2B / 2011 is now authorized and in progress on stage/02b-historical-2011. Stage 2C / 2014 is not started.** Broader historical integration remains outstanding. Open an unmerged PR for 2011 only; do not continue to 2014.

## Branch and completed checkpoints

- Existing branch: `stage/02-historical-2008-2014`. Preserve it; do not reset/recreate it.
- Stage 1 merged through PR #1: https://github.com/jamesfeng24/nz-election-model-2026/pull/1. Verified main commit: `8cf0345dba83e3adb68630d1044e2839b2cf2037`.
- A, recovery/infrastructure, pushed: `03664153ec97fb2d60311b271735b727ad8d0d81`.
- B, complete 2008 acquisition/processing/basic validation, pushed: `49bd2356088d6a1ed44b0bab897bee4bd218709c`.
- A separate documentation handoff follows B. Its authoritative SHA is the branch head, not a self-reference in this file.
- C (2011), D (2014), E (unified integration/validation/docs) remain outstanding. Push each separately as soon as complete. Create an unmerged PR into main only when Stage 2 is genuinely complete.

## Recovery result

Initial inspection found local and remote stage branches equal to merged main, with no modified, staged, untracked or unpushed project work. One original 2008 Auckland Central split CSV survived in Downloads; it was recovered byte-for-byte, checksum-registered and committed. No partially written ingestion code survived. Synced project reference files were untouched.

## Available data and important files

- `data/sources.json`: 139 authoritative 2008 CSV resources, exact URLs, retrieval timestamps, SHA-256, raw paths, processor and limitations.
- `data/source-plans/historical-2008.json`: explicit acquisition inventory (six national/electorate summary/control tables, 70 candidate tables, 63 general-electorate split tables).
- `data/raw/elections/2008/`: all 139 source files, unchanged.
- `data/processed/elections/2008.json`: 63 general electorates, 499 candidate records, 1,197 party-vote records, winners, turnout and national controls.
- `data/processed/split-votes/2008.json`: 63 general-electorate matrices of reported percentages; exact joint counts are unavailable and null.
- `data/processed/elections/2008-validation.json`: reconciliation results, eight source-label mappings, zero unresolved discrepancies.
- `scripts/ingest/historical_sources.py`: immutable import and checksum-pinned reacquisition.
- `scripts/ingest/import_historical_downloads.py`: import files from an explicit acquisition plan, preserving browser downloads.
- `scripts/transform/historical.py`: deterministic processor and `--check` regeneration verification; implemented and verified for 2008 only. CLI year options do not imply 2011/2014 compatibility.
- `scripts/tests/`: 13 standard-library tests, including source integrity, immutable recovery/import, Unicode and explicit missingness.
- `docs/historical-ingestion.md`, `docs/data-dictionary.md`, `docs/reproducibility.md`: source peculiarities, actual output contract and commands.
- Stage 1 app and draft model contracts remain in `src/app`, `src/types` and `src/models`; historical JSON is not yet consumed by the website. No statistical models are implemented.

## Validation status

2008 processor completed with zero unresolved discrepancies: nonnegative counts, normalized party/candidate shares, official winners and majorities, turnout components/rates, general/Māori/national totals, national party and candidate-party aggregates, split row totals and rounding-bounded column comparisons. National valid party votes: 2,344,566; valid candidate votes: 2,300,266; votes cast: 2,376,480. Seven Māori candidate tables support national controls but are not primary electorate outputs.

At B, 13 Python tests passed and byte-for-byte regeneration passed. The final handoff checks are recorded below after running them. No full Stage 2 validation can be claimed while two years are absent. Existing Python CI does not yet run historical regeneration; integrating that and stronger processor regression tests remains for E.

## Known limitations and outstanding work

- No 2011 or 2014 raw/processed inputs acquired in this session. No polling, 2023 reconstruction or 2026 boundary inputs.
- Split files provide two-decimal percentages, not exact joint counts. Do not infer observed counts by rounding percentages. Denominators include informal party votes and exclude disallowed ballots; keep informal candidate and party-vote-only categories.
- Candidate occurrence IDs are election-local. `personId` is null. Full names, source labels, parties and comparison keys aid later reviewed linking but do not establish cross-election identity.
- Seven candidate display/full-name variants and a truncated party header are explicitly mapped and reported. The mappings establish local source joins, not independent biographical claims.
- Source spelling/Unicode is preserved; missing CSV macrons are not invented. Historical boundary IDs label the publication vintage, not a verified geometry/crosswalk.
- Direct archive fetches returned HTTP 403 in this environment. Normal browser downloads worked; immutable committed raw files permit offline regeneration. Do not bypass access controls.
- Historical export contract is documented separately from the Stage 1 draft Zod model schemas. Full typed consumer integration and wider tests remain for E.
- Code licence selection and Cloudflare deployment remain deferred. Data reuse terms are recorded separately.
- Local Git has no HTTPS write credentials. Publish identical trees through the GitHub connection using non-forced stage ref updates, then fetch/synchronize; do not change main or expose credentials.

## Modelling components

Completed: none. Ingestion and validation are infrastructure, not a statistical model.
Outstanding: national polling; boundary reconstruction; independent split/elasticity/premium estimators; National/Labour resilience; normalization; incumbency/replacement effects; separate Opportunity behaviour; backtesting/calibration; correlated simulation; MMP/list/overhang allocation and explanations. All remain out of scope here.

## Current sequence and next task

The revised 25-step project sequence is authoritative in docs/future-work.md. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Freeze the historical backtesting design and ensemble weights before Opportunity-specific modelling or current 2026 polling ingestion. Each later task requires explicit authorization.

Finish only 2011, pushing sequencing, ingestion, processed-data and documentation checkpoints separately. After 2011 the exact next task is **2014 ingestion only**. The older checkpoint/branch notes above are historical; the active branch is stage/02b-historical-2011.

## Final pause-handoff checks — 2026-09-08

PASS: 30 frontend tests (3 files), 13 Python tests, TypeScript type checking, production build, integrity of all 139 registered sources, byte-for-byte regeneration of all three 2008 outputs, and git diff whitespace check. These are local results for the saved checkpoint, not a claim of completed 2011/2014 coverage or remote CI execution. All meaningful files are committed and published on the stage branch; verify local/remote equality when resuming.

## Stage 2B acquisition checkpoint

Sequencing pushed in 720ceb6. Preserved initial 2011 controls, candidate files and split sample/aggregates through the existing immutable importer. Existing CSV reader handles the UTF-8 BOM and macrons. Electorate split cells are rounded percentages; the aggregate summary additionally reports exact split/non-split counts, to be preserved separately. Full 2011 acquisition, joins and reconciliation remain underway. No 2014 work.
