# Project state

Updated 2026-09-09. GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Objective and current stage

Build a transparent, reproducible static 2026 New Zealand election website using React/TypeScript/Vite/Vitest and offline Python preparation. No backend/database. Preserve raw evidence and uncertainty. No statistical model has been implemented.

Completed:
- 2008 ingestion: merged through PR #2 (main merge f819f48).
- 2011 ingestion: merged through PR #3 (main merge 2448ec6).
- 2014 ingestion: merged through PR #4 (main merge 7e9dd53).
- 2008–2014 integration and cross-year validation: complete and merged through PR #5, main merge f62790363a95823e67158200acb5b864cd2f7741.

Stage 3A / 2017 ingestion only is now authorized; acquisition has not started. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights.

## Branch and checkpoints

Current branch: `stage/03a-historical-2017`, created from clean fetched main f62790363a95823e67158200acb5b864cd2f7741. Verified PR #5 merge and ancestry of integration head f3485e9007dff2de37567df36beda5b8db702626. Checkpoint A repairs scoped handoff rules; no data/code changes yet.

Previous integration checkpoints:

- 6da663a: working panel, core integration tests and six combined output files; pushed.
- a276304: offline all-year regression command, control reconciliation and CI; pushed.
- f3485e9: integration documentation; merged in PR #5.

2017 checkpoint plan: A rules/state; B official index/resource plan and core immutable acquisition; C core transform/validation; D split evidence; E all Python tests, source integrity, deterministic 2017 and old-output compatibility, final handoff and unmerged PR. Push each checkpoint. Next action after A: inspect official 2017 statistics and split/voting-place indexes, preserve exact discovered URLs, inspect CSV layouts before choosing adapter architecture. No 2017 source/processed counts exist yet.

Local Git authentication works. Preserve local work before future synchronization. No old ingestion work was reset, reacquired or rewritten in this task. Prior 2014 recovery history remains in PR #4 and its commits.

## Data and important files

The source registry still has 427 immutable official files: 139 (2008), 143 (2011), 145 (2014). No raw files, source registry entries or existing per-year processed outputs changed during integration.

| Year | General electorates | Party records | Candidate records | Local split matrices |
| --- | ---: | ---: | ---: | ---: |
| 2008 | 63 | 1,197 | 499 | 63 |
| 2011 | 63 | 819 | 423 | 63 |
| 2014 | 64 | 960 | 451 | 64 |
| Combined | 190 | 2,976 | 1,373 | 190 |

- `data/sources.json`, `data/raw/elections/`, `data/source-plans/`: original acquisition/provenance system, unchanged.
- `data/processed/elections/{year}.json`, `{year}-validation.json`, and `data/processed/split-votes/{year}.json`: validated per-year inputs, byte-identical to main.
- `scripts/transform/historical_panel.py`: offline processed-input integration, canonical party aliases, invariants and optional raw-to-panel verification.
- `data/processed/historical/2008-2014/`: electorate, party-vote, candidate-vote, split-vote and election-control JSON plus manifest with nine input hashes, five output hashes and record counts.
- `scripts/tests/test_historical_panel.py`: deterministic committed outputs, lossless projection, party identity/source exceptions and corruption rejection.
- Existing per-year transform and source validators are unchanged. CI now also runs all-year byte comparisons and panel verification.
- `docs/data-dictionary.md`: panel contract and safe invariants. Historical exports remain separate from provisional frontend model contracts; no frontend consumer was added.

## Last completed integration verification (not rerun for documentation-only A)

PASS: all 31 Python tests; offline `python3 -m scripts.transform.historical_panel --check --verify-years`; regeneration of all nine per-year outputs with byte equality and consumed-source checksum validation; all 190 local split matrices and available aggregate controls through existing per-year validators; panel determinism; general/Māori/national control relationships; source-label and Unicode preservation; deliberate corrupt-panel rejection.

PASS: 30 frontend tests, TypeScript checking and production build, required by AGENTS.md despite no frontend/TypeScript changes. Git whitespace checks pass. Remote CI status is separate from these local results.

No unresolved numeric discrepancies. No new acquisition, browser download, source modification or fitted model work.

## Schema findings and limitations

- Same per-year normalized record shapes; differences in optional split controls are retained explicitly. 2008 aggregate split controls are **not collected in this repository**, not zero or proven unavailable at source. The 2011/2014 exact split summaries and rounded aggregate matrices are preserved separately.
- Panel `canonicalPartyId` resolves Conservative Party/Conservative and Mana/MANA Movement using the Electoral Commission's 2014 report, paragraph 187. Existing `partyKey` and official labels remain unchanged. Independent is an affiliation category with null canonical party ID. No speculative other-party equivalence is asserted.
- Internet MANA is distinct from Internet Party and MANA Movement. The 2014 split-report grouping remains in election controls and never overwrites candidate affiliations.
- All local split cells retain rounded percentages and null joint counts; aggregate exact summaries cannot reconstruct local exact cells. Split denominators differ from valid party/candidate vote denominators.
- Candidate IDs identify election-local occurrences, with personId null. Existing intra-election alternate-name mappings remain in validation metadata and source split labels. No cross-year person continuity is inferred.
- Electorate IDs and boundary versions are election-specific. This is a stacked historical panel, not a boundary-harmonized longitudinal geography.
- General electorates are the modelling records. Seven Māori electorates per year remain supporting raw inputs and aggregate controls, not new detailed panel records.
- 2011 BOM/macrons and all source spellings remain preserved. Published informal-party non-split summary conventions (424 in 2011; 337 in 2014) remain documented and should not be interpreted as substantive party behaviour.

## Modelling completed/outstanding and later sequence

Completed modelling components: none. All fitted effects, backtesting, ensemble weights, simulation and seat forecasts remain outstanding.

After separately authorized 2017 ingestion: 2020 ingestion; 2023 ingestion; full 2008–2023 panel; 2023→2026 boundary reconstruction; historical model development/backtesting; freeze ensemble weights; only then 2026 Opportunity, candidates and polling. Detailed ordering remains in `docs/future-work.md`.

## Exact next task

**2017 historical election ingestion only.**

Resume the authorized 2017 task from checkpoint A. Do not begin 2020 or modelling. After 2017 is complete, the next task is 2020 historical election ingestion only, requiring separate authorization.

## Stage 3A checkpoint B — 2026-09-09

Checkpoint A b1367db is pushed. Official index discovery produced a 145-CSV plan: six core controls, 71 candidate/voting-place files (seven supporting Māori), 64 general split matrices and four aggregate split files. Twelve originals are preserved and checksum-valid: all six controls, candidate electorate 1, local split electorate 1, and all four aggregates. Remaining: candidate files 2–71 and general split files 2–64 (133 files). No 2017 processed outputs yet.

Direct curl returns 403; native Chrome downloads work to `/Users/jamesfeng/Downloads`. In-app browser clicks did not yield local files. Use exact plan URLs with normal Chrome downloads, then `python3 -m scripts.ingest.import_historical_downloads --year 2017 --directory /Users/jamesfeng/Downloads --allow-partial`. Import preserves originals/mtime and refuses changed bytes. Source processingScript is null until a functioning adapter exists.

Observed 2017 differences: candidate footer shares are 0–100 percentages; turnout percentages are rounded to two decimals; files use descriptive statistics/csv paths; local split cells remain rounded percentages, and aggregate summary has exact counts. Create a dedicated 2017 adapter; do not add format switches to historical.py. No speculative aliases or cross-election linking. Full format/semantic validation remains outstanding.

Checks at B: 13 acquisition/integrity tests pass; all 439 registered source files pass checksum validation; whitespace check passes. No formatter/linter is configured in this repository. No frontend code changed or frontend checks rerun. All old processed outputs untouched.

## Recovery checkpoint — 2026-09-09

Saved acquisition checkpoint 0ce7d3b contained 62 sources. On resumption, 20 additional original candidate downloads (52–71) survived locally, were imported without changing bytes and passed checksums. All 71 candidate files are now preserved, including seven supporting Māori electorates. Total 2017 inventory: 82/145 planned CSVs (six core, 71 candidate, four aggregate split, one local split). Only planned general split files 2–64 remain missing (63). Resume from the plan/registry, not memory; do not repeat acquired downloads.

Initial pure table parsers and six passing focused tests are preserved in scripts/transform/modern_tables.py and scripts/tests/test_modern_tables.py. Candidate table was tested on electorate 1; complete-election orchestration and all-source semantic validation remain outstanding. Preserve actual percentage units via reportedPercent and normalized sourceShare. Legacy historical.py and all old outputs are unchanged. All 509 registered raw files pass integrity validation. Browser interruption was a current-URL restriction; user subsequently left the restricted page and authorized continuation. No 2017 completion PR yet.

## Core transform checkpoint C — 2026-09-09

Acquisition complete and pushed ff5b88b: all 145 planned sources. Core adapter scripts/transform/modern_election.py now generates 64 general electorates, 431 candidate records, 1,024 party records. All 71 candidate files (453 total candidatures) reconcile with national party/candidate totals, nominations, official winners/majorities and turnout controls. Six table-parser tests and deterministic core-only generation pass. Split-specific validation is the next unit; core report explicitly marks split not-yet-validated.

Māori candidate files contain single-cell electorate-name section headings; accept only labels present in official turnout metadata. Some candidate files include a nonnumeric 'Voting places where less than 6 votes were taken' note; preserve the note and validate the remaining published numeric rows/columns without zero-filling. Source bytes unchanged. Next command: `python3 -m scripts.transform.modern_election` to integrate split validation, followed by focused tests/check mode. Core-only is a development checkpoint option, not completion.

## Split checkpoint D — 2026-09-09

Core checkpoint bb9ac05 is pushed. Complete modern_election generation now consumes all 145 sources and validates all 64 general split matrices, three aggregate matrices and exact national summary. Twenty focused tests pass, including checksum/semantic mutations, strict candidate identity, exact nested TOP parentheses, deterministic exports and all-source provenance. No candidate name mappings were necessary; exact full labels and affiliations agree. The published informal-party non-split value 350 matches Party Vote Only; preserve that convention without behavioural interpretation. Full-suite, backwards-compatibility and final documentation checks remain for E.
