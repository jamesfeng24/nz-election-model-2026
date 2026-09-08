# Data sources and provenance standard

**2008 and 2011 are complete and merged; 2014 ingestion is complete on its review branch.** `data/sources.json` contains 427 committed official CSV resources (139 for 2008, 143 for 2011, 145 for 2014). Software documentation links are not election datasets.

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
