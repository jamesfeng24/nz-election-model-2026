# Project state

Updated 2026-09-08. GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Objective and current stage

Build a transparent, reproducible static 2026 New Zealand election website. React/TypeScript/Vite/Vitest; offline Python preparation; no backend/database. Preserve raw evidence and uncertainty. No statistical model has been implemented.

- 2008 ingestion: complete and merged through PR #2 (main merge f819f48).
- 2011 ingestion: complete and merged through PR #3 (main merge 2448ec6).
- 2014 ingestion: complete on `stage/02c-historical-2014`, ready for an unmerged PR into main.
- 2008–2014 integration/cross-year validation: not started in this task.
- 2017: not started.
- 2026 polling and Opportunity modelling remain intentionally deferred until historical model backtesting and ensemble-weight freeze. They must not influence historical model selection or weights. The established sequence remains in docs/future-work.md.

## Branch, recovery and checkpoints

Current branch: stage/02c-historical-2014, based on confirmed main merge 2448ec6. Initial branch creation happened before the user merged PR #3; the clean branch was then fast-forwarded to that merge. Main and prior-year raw/processed data were not altered.

- e061f30: first 27 official files and explicit 2014 split-party grouping pushed.
- 73f68dc: recovered 100 checksum-valid sources, including all 71 candidate files and split matrices 1–19; committed/pushed before further acquisition.
- 08940e0: all 145 planned raw files acquired and pushed. Only missing matrices 20–64 were downloaded during recovery.
- 8b2a257: complete processed outputs and core/aggregate reconciliation pushed immediately.
- Final tests/documentation handoff follows these commits; branch HEAD is its authoritative SHA. Create the 2014 PR only after push, leave unmerged and stop. If interrupted during publication, look up the PR by head branch before creating one.

Local Git authentication now works. Preserve any new local changes before future fetch/synchronization; never reset/recreate a branch to discard interrupted work. The earlier interrupted 2008 session recovered one original Auckland Central split CSV, now safely merged.

## Data and important files

- data/sources.json: 427 registered resources, comprising 139 (2008), 143 (2011), 145 (2014). Exact URLs, retrieval times, checksums and processing paths are recorded per file.
- data/source-plans/historical-2014.json: exact acquisition inventory and observed browser download filenames; authoritative index URLs included.
- data/raw/elections/2014/: six E9 controls (1/4/5/6/9_1/9_2), 71 candidate files, 64 general-electorate split matrices, three aggregate split matrices and one exact aggregate summary. All original bytes unchanged.
- data/processed/elections/2014.json: 64 general electorates, 451 candidate records, 960 party-vote records, denominators, winners/margins, turnout, national/general/Māori controls and source IDs.
- data/processed/split-votes/2014.json: all 64 local matrices, aggregate percentage matrices, exact published split/non-split summary counts and explicit partyGrouping metadata.
- data/processed/elections/2014-validation.json: coverage, reconciliations, eight local name mappings, source peculiarities and zero unresolved numeric discrepancies.
- scripts/ingest/historical_sources.py and import_historical_downloads.py: existing immutable import/checksum-pinned fetch system, reused unchanged during this 2014 task.
- scripts/transform/historical.py: shared pipeline, explicit 2014 split-party grouping and local name aliases.
- scripts/transform/historical_split_controls.py: extracted existing 2011 aggregate validator, parameterized for the 2014 electorate count and source grouping; no cross-year panel/integration performed.
- scripts/transform/historical_2011.py: compatibility wrapper retaining the original 2011 entry point.
- scripts/tests/test_historical_2014.py: deterministic exports, 2014 inventory/checksums, source affiliations, Unicode/aliases, missingness and mutation rejection.
- Existing 2008/2011 artifacts remain unchanged. The website does not yet consume historical exports; model-facing TypeScript contracts remain provisional.

## Final local checks

PASS: 12 focused Python tests (shared infrastructure plus 2014), all 145 official 2014 input checksums, deterministic 2014 regeneration, targeted 2008 and 2011 byte-for-byte regeneration because shared Python code changed, 30 frontend tests, TypeScript checking and production build (required by AGENTS.md), and Git whitespace checks. No frontend/shared TypeScript changes. No broad prior-year re-audit. Remote CI results are separate from local validation.

2014 validates expected and unique electorate/candidate coverage; nonnegative votes; party/candidate denominators and shares; official winners/margins; turnout; general/Māori/national totals and national party/candidate-party totals; all local split rows/columns within source rounding; aggregate controls; and local-to-general aggregate intervals. National valid party votes: 2,405,622; valid candidate votes: 2,347,607; votes cast: 2,446,297. All numeric checks pass with no unresolved discrepancies.

## 2014 source differences and limits

- 64 general electorates plus seven supporting Māori electorates, versus 63+7 in 2011. Historical publication IDs are not geometry or boundary crosswalks. Do not join electorate numbers across elections.
- Candidate source index is e9_part8_cand_index.html. UTF-8 BOMs/macrons are retained as in 2011; shared CSV structures otherwise remain compatible.
- Internet Party and MANA Movement are separate candidate affiliations in official candidate tables. Only 2014 split reports group them as Internet MANA. The transform preserves source candidate parties and their national totals; split joins and aggregate grouping use the explicit year-scoped mapping. This is not party continuity or a behavioural assumption.
- Eight explicit local candidate-label variants are preserved and joined using party/grouping, name evidence and independently reconciling vote share. Kaikōura has TOMLINSON versus TOMLINSOM. Wellington Central has two independent candidates; the explicit KARENA mapping is checked against the 52-vote candidate, not the other independent with 90 votes. No person identity across elections is asserted; personId remains null.
- Local and aggregate split cells provide two-decimal percentages, not exact joint counts; count stays null and countAvailability is explicit. Exact aggregate summary split/non-split counts are preserved separately and cannot recover local exact cells.
- The source summary labels 337 informal-party votes non-split, matching Party Vote Only rather than Candidate Informals. Preserve this published convention and exclude that category from party-behaviour estimation.
- Split denominators include informal party votes, exclude disallowed ballots and differ from valid-vote share denominators. Supporting Māori files allow national reconciliation; primary outputs are general electorates only.
- Browser-acquired originals are committed and regeneration is offline. Never overwrite a source merely because a later download differs; investigate versions/checksums.
- No 2017, integration, statistical modelling, 2026 polling, Opportunity, deployment or licence-selection work was performed.

## Modelling completed/outstanding

Completed: none; ingestion and validation are infrastructure.
Outstanding: all fitted historical estimators, boundary reconstruction, backtesting/weight freeze and later 2026-specific modelling, Monte Carlo/MMP and website outputs. Follow the recorded sequence only when explicitly authorized.

## Exact next task

**2008–2014 integration and cross-year validation only.**

2008 ingestion is complete and merged; 2011 ingestion is complete and merged; 2014 ingestion is complete for review. Confirm the 2014 PR is merged before starting the next authorized branch. 2017 is not started. 2026 polling and Opportunity modelling remain intentionally deferred until historical model backtesting and ensemble-weight freeze.
