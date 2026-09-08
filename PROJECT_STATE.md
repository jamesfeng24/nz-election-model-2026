# Project state

Updated 2026-09-08. GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Objective and current stage

Build a transparent, reproducible static 2026 New Zealand election website using React/TypeScript/Vite/Vitest and offline Python preparation. No backend/database. Preserve raw evidence and uncertainty. No statistical model has been implemented.

Completed:
- 2008 ingestion: merged through PR #2 (main merge f819f48).
- 2011 ingestion: merged through PR #3 (main merge 2448ec6).
- 2014 ingestion: merged through PR #4 (main merge 7e9dd53).
- 2008–2014 integration and cross-year validation: complete on `stage/02d-historical-2008-2014-integration`, ready for PR review into main; do not merge automatically.

2017 is not started. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights.

## Branch and checkpoints

Current branch: `stage/02d-historical-2008-2014-integration`, created from clean, fetched main at 7e9dd53 after confirming all three ingestion merges.

- 6da663a: working panel, core integration tests and six combined output files; pushed.
- a276304: offline all-year regression command, control reconciliation and CI; pushed.
- Final documentation checkpoint follows; branch HEAD identifies its authoritative SHA. Publish a PR into main after pushing; leave it unmerged. If interrupted during publication, find the PR by this head branch before creating another.

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

## Verification status

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

First confirm this integration PR is merged into main. Do not begin 2017, later elections or modelling without explicit authorization.
