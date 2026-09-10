# Data sources and provenance standard

**2008–2014 ingestion/integration are merged; 2017 ingestion is complete on its review branch.** `data/sources.json` contains 572 committed official CSV resources (139 for 2008, 143 for 2011, 145 for 2014 and 145 for 2017). Software documentation links are not election datasets.

Every future external dataset must have a SourceRecord validated by `src/types/contracts.ts`, recording:

| Field | Requirement |
| --- | --- |
| schemaVersion / id | Version 1; stable unique source identifier |
| organisation | Source organisation |
| url | Exact source URL |
| dateOrElection | Applicable date, period or election |
| resource | Exact file, table, sheet, release or resource used |
| retrievedAt | Retrieval timestamp, ISO 8601 with timezone |
| rawPath | Original file under data/raw/ |
| processingScript | Script under scripts/; null only while unprocessed |
| limitations | Nonempty list of known limitations; explicitly say if assessment is pending |
| sha256 | Lowercase SHA-256 of original bytes |
| licence | Reuse terms or explicit unresolved status |

Keep raw bytes unchanged and retain each acquired version separately. Never silently replace a release. Record redirects, manual retrieval steps, sheet/range selections and access restrictions where relevant in source-specific notes. Verify rights before redistributing restricted material. Processed outputs must trace to source IDs, exact input checksums and documented scripts. A non-null script path must point to a real script before publishing its outputs; runtime schema validation alone does not verify filesystem existence or remote authenticity.

Unknown values must stay unknown; do not infer evidence from plausible-looking values. Synthetic test metadata lives only in tests, uses example.org, and must never enter the source register or model inputs.

## Stage 1 correction — 2026-09-07

No datasets added or retrieved. For large/restricted resources, record a reproducible fetch command or script and expected checksum in source-specific notes; rawPath remains the materialization location even if bytes are excluded from Git. The source metadata contract does not imply the resource is checked in. Future validation must distinguish committed raw files from reproducibly fetched inputs and verify both before processing. Update this register and its limitations every stage.

Stage 2 checkpoint A: one recovered official 2008 Auckland Central split CSV registered in data/sources.json. Exact URLs, timestamps and hashes are recorded there; see docs/historical-ingestion.md. No complete election dataset yet.

## Current 2008 coverage — checkpoint B

Source organisation: New Zealand Electoral Commission archive (historical Chief Electoral Office publication). The exact resource URLs, retrieval dates, raw repository paths, processing script, checksums and per-resource limitations are in `data/sources.json`; the explicit inventory is `data/source-plans/historical-2008.json`.

Official indexes: [E9 statistics](https://www.electionresults.govt.nz/electionresults_2008/e9/html/statistics.html), [candidate results](https://www.electionresults.govt.nz/electionresults_2008/e9/html/e9_part8.html), [split voting](https://www.electionresults.govt.nz/electionresults_2008/splitvote_index.html). Inputs are six summary/control CSVs (parts 1, 4, 5, 6, 9_1, 9_2), 70 candidate CSVs and 63 general-electorate split CSVs. All raw bytes are committed under `data/raw/elections/2008/`; no large-file exclusions are needed.

Normal browser downloads were used after direct HTTP requests returned 403. Import records browser-file timestamps as retrieval metadata; the recovered Auckland Central file retains its earlier timestamp. Output reproduction is offline. [Crown copyright/reuse terms](https://www.electionresults.govt.nz/about.html) permit accurate reproduction with source/copyright acknowledgement; no endorsement is implied.

Limitations: rounded split percentages only; no observed joint counts. Source-specific name variants and truncated headers are recorded in the validation report. CSV spelling is preserved, including missing macrons. Māori candidate records support national totals but only general electorates are exported as primary records. Cross-election candidate identity and boundary reconstruction are deferred. Historical Stage 1/A notes above describe earlier checkpoints, not current coverage.

## 2011 coverage — Stage 2B

New Zealand Electoral Commission, 26 November 2011 general election. [E9 statistics](https://www.electionresults.govt.nz/electionresults_2011/e9/html/statistics.html), [candidate source index](https://www.electionresults.govt.nz/electionresults_2011/e9/html/e9_part8.html), [split-vote source index](https://www.electionresults.govt.nz/electionresults_2011/splitvote_index.html). Exact resources, retrieval timestamps, unchanged raw paths, processing script and checksums are recorded individually in `data/sources.json`; the 143-resource inventory is `data/source-plans/historical-2011.json`. Browser-acquired originals are committed under `data/raw/elections/2011/`.

Coverage: six E9 control tables (parts 1/4/5/6/9_1/9_2), 70 candidate result tables, 63 general split matrices, General/Maori/Overall aggregate split matrices and the split summary. Seven Māori candidate files support national controls. Reuse terms remain the Electoral Commission archive's Crown copyright/source-acknowledgement terms already recorded above.

2011 differs from inspected 2008 CSVs in UTF-8 BOM/macron spelling and eight local candidate name aliases. Electorate split cells still contain rounded percentages only. Aggregate summary split/non-split counts are exact and preserved separately. The informal-party summary row labels 424 votes non-split, matching Party Vote Only rather than Candidate Informals in the overall matrix; retained as published and excluded from substantive party-behaviour interpretation. No unexplained reconciliation discrepancies remain. No 2014 sources acquired.

## 2014 coverage — Stage 2C

New Zealand Electoral Commission, 20 September 2014 general election. Source indexes: [statistics](https://www.electionresults.govt.nz/electionresults_2014/e9/html/statistics.html), [candidate files](https://www.electionresults.govt.nz/electionresults_2014/e9/html/e9_part8_cand_index.html), [split reports](https://www.electionresults.govt.nz/electionresults_2014/splitvote_index.html). Each of the 145 resources has its exact URL, retrieval timestamp, raw path, checksum, processor and limitations in data/sources.json. The explicit plan is data/source-plans/historical-2014.json. All originals are committed unchanged under data/raw/elections/2014/. Existing Crown copyright/source-acknowledgement terms apply.

Coverage: six E9 controls, 71 candidate files (64 general and seven supporting Māori), 64 general split files, three aggregate split matrices and one exact aggregate split summary. Browser file timestamps record acquisition; recovery verified and pushed 100 existing resources before downloading only 45 missing matrices.

Source limitations: rounded joint percentages only; candidate identities are election-local. Internet Party/MANA Movement remain original candidate affiliations, while split tables group them as Internet MANA. Eight explicit source-name variants are retained, including TOMLINSON/TOMLINSOM. The summary's informal-party non-split count of 337 corresponds to Party Vote Only in the overall matrix, not Candidate Informals; retained as published, with no substantive party-behaviour interpretation. All numeric reconciliations pass. No integration or later-year acquisition was performed.

## 2008–2014 integration — Stage 2D

All three ingestion PRs are merged into main. Integration adds no election observations, raw files or source-registry entries: the same 427 preserved official inputs support the panel. `scripts/transform/historical_panel.py` reads validated per-year JSON and writes `data/processed/historical/2008-2014/`; its manifest records nine exact input hashes. Existing per-year source IDs, source-name mappings, aggregate controls and limitations are retained.

Canonical-party evidence: New Zealand Electoral Commission, *Report on the 2014 General Election*, March 2015, paragraph 187 (printed page 23; PDF page 31), [official report](https://elections.nz/assets/2014-general-election/report-of-the-electoral-commission-on-the-2014-general-election.pdf), consulted 2026-09-08. It confirms the Conservative abbreviated-name change and Mana → MANA Movement. This is a documentary citation supporting the two versioned alias rules, not a newly ingested numerical dataset; no raw copy is registered and offline regeneration does not fetch the report. Preserve Conservative Party/Conservative and Mana/MANA Movement source labels separately. No additional organizational equivalences are inferred.

2008 aggregate split controls remain not collected in this repository. Local rounded percentages and 2011/2014 exact aggregate summaries retain their distinct precision. No prior-year source or processed bytes changed. No 2017 or later-election data acquired.

## 2017 coverage — Stage 3A complete

New Zealand Electoral Commission, 23 September 2017 general election. [Statistics index](https://www.electionresults.govt.nz/electionresults_2017/statistics/index.html), [candidate/voting-place index](https://www.electionresults.govt.nz/electionresults_2017/statistics/votes-by-voting-place-electorate-index.html), [split index](https://www.electionresults.govt.nz/electionresults_2017/statistics/split-votes-index.html). Exact discovered URLs and electorate name/number associations are in data/source-plans/historical-2017.json; no IDs were inferred from names.

All 145 planned originals are committed: six controls, 71 candidate files, 64 local split files, three aggregate matrices and one exact summary. Registry entries record actual retrieval timestamps, unchanged raw paths, SHA-256, source terms and scripts/transform/modern_election.py. Normal Chrome downloads were used after direct HTTP 403; interrupted candidate downloads were recovered and saved before further acquisition. Subsequent processing requires no network.

Outputs cover 64 general electorates, 431 candidate records and 1,024 party records. Seven Māori electorates support national reconciliation of 453 candidatures. All 64 local split matrices and general/Māori/national controls reconcile within published precision. No candidate aliases were needed; exact affiliations and Unicode labels remain preserved.

Candidate source shares and turnout are two-decimal percentages. Local and aggregate split cells are rounded percentages with null joint counts; exact national summary counts are retained separately. The informal-party non-split count 350 matches Party Vote Only, not Candidate Informals, and must not be interpreted as party behaviour. Voting-place disclosure notes and supporting geographic section headings are not missing counts to zero-fill. No unexplained discrepancy remains. Existing 2008–2014 outputs and raw evidence are unchanged; no later-election data acquired.
