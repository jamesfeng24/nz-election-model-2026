# Data sources and provenance standard

## Stage 17 preserved candidate-baseline evidence

No new resource was acquired. `data/source-plans/stage17-candidate-baseline-preserved-sources.json` snapshots the exact 72 official 2023 candidate-votes-by-voting-place records consumed by the target-boundary inventory. The Stage17 generator verifies each live required record and original raw SHA-256, while unrelated registry additions are allowed; deleted/changed/ambiguous required records or changed bytes fail. Its manifest separately hashes the validated 2023→2026 population crosswalk, synthetic party-vote bounds, Stage4 secondary-availability record, Stage7 2023 occurrences, Stage8 links/history and Stage13 primary occurrence evidence. The 72 raw candidate tables reparse to the 495 saved election-local occurrence names, affiliations and votes. Voting-place addresses and aggregate special-vote rows have no voter-residence meshblock join and cannot reconstruct changed-boundary candidate votes. The Stage4 party bounds are assumption-dependent 2023 synthetic geography, not 2026 party forecasts. No raw, registry or earlier processed output changed. See [the Stage17 inventory and design](docs/candidate-baseline-complete-forecast-design.md).

## Stage15 conditional ledger: preserved source dependencies only

No source was acquired or changed. `data/source-plans/stage15-conditional-ledger-sources.json` pins the exact **612** official source registry records attached to the consumed general-seat election records and 2008/2014/2020 local split matrices. Stage15 checks each required record against the live registry and each original `data/raw/` SHA-256; unrelated new registrations do not invalidate it, but changed/deleted/duplicate required IDs or changed raw bytes do. The six processed election files, three source split files, Stage5 party-continuity contract, Stage14 specification/contracts/inventory and code are separately byte-hashed in the construction manifest. The evaluation manifest separately pins the committed construction and target election outcomes. The 2023 split destination tables and 21 preserved discrepancy assertions are **not used to construct** target ledgers; they remain preserved as prior evidence. Source local split cells are rounded percentages conditional on exact valid/informal-party row counts, not exact joint counts. Candidate ballot totals and winner fields are evaluation-only. See [Stage15 findings](docs/conditional-candidate-interval-ledger.md).

## Stage 13 identity evidence — 2026-09-26

The Stage 13 source plan `data/source-plans/stage13-identity-sources.json` pins 18 unique newly acquired raw HTML resources under `data/raw/identity-stage13/`, with SHA-256, exact URL, publication date where known, and 2026 retrieval time. Nine party-authored statements/listings are primary occurrence-specific sources; eight Policy.nz candidate-submitted profiles and one Hawke's Bay Today interview are preserved ancillary sources outside the frozen primary hierarchy. The inherited National selection statement for Scott Simpson is pinned by the earlier Stage 10 source contract. `data/source-plans/stage13-identity-adjudications.json` records 32 individually checked source/occurrence claims, including alias and name conflicts. The original 96-record candidature snapshot, 17-record inherited identity snapshot and later 22-profile supplement snapshot remain separate. The Stage 13 generator validates these contracts and raw bytes, accepts unrelated source additions and rejects changed/deleted required records.


## Stage 9 bounded tenure evidence — 2026-09-23

The Stage8 Parliament former-MP index preserved only page1 of2. Stage9 preserves official page2 plus107 individual Parliament profiles selected from surname candidates for125 unchanged-boundary source-winner/recontester pairs; matching surname is a retrieval candidate, **not** an identity decision. Profiles can show explicit dated `Member for / List` rows, first-election date and publication date. A historical source winner is linked to a profile only when its electorate and election date agree with a service row; aliases are retained without rewriting source labels. Missing or ambiguous rows remain unknown. The108 new source URLs, raw paths, retrieval timestamps and SHA-256 values are registered in `data/source-plans/freshman-incumbency-tenure-sources.json`, not appended to the shared registry. All raw checksums passed. The completed parser yields101 complete dated tables and six profiles with no usable dated rows; initial acquisition notes' seven-table estimate was superseded. This is a bounded, retrospective authoritative acquisition; profile publication/retrieval dates are distinct from historical service dates. No new election votes were acquired.

The acquisition universe came from Stage8 pairs. A post-fit winner-flag counterfactual found three of125 source-winner comparable pair links depended on target/later winner anchors. One retrieved profile was only used by a removed pair, while two also supported surviving pairs. Stage9 retains all raw sources and the original inventory as audit history, but excludes the three links from final evaluation; no further profiles were acquired to compensate. The counterfactual does not establish that profile publication/completeness is independent of later career success. See `docs/freshman-incumbency.md` and the pinned Stage9 cohort audit.

## Stage 8 bounded identity evidence — 2026-09-23

Two official New Zealand Parliament index pages were preserved for retrospective person and tenure corroboration: the former-MP and current-MP indexes. Their exact URLs, retrieval times, raw HTML paths, SHA-256 hashes and limitations are registered as `parliament-former-mp-index-2026-09-23` and `parliament-current-mp-index-2026-09-23` in `data/source-plans/candidate-persistence-sources.json`. Stage8 validates this bounded SourceRecord-format register and both raw checksums offline. The earlier shared `data/sources.json` is byte-identical to merged main. They cover members of Parliament rather than the full candidate population; matching a name to a page alone does not verify an occurrence. The post-fit PR audit limits confirmation to the compatible observed winning occurrence. Other exact-name/affiliation/seat chain projections to that person remain probable. Retrieval dates are known; historical profile publication dates are not. Source candidate names and election records are unchanged. No exhaustive biography search or other external acquisition was performed.

Stage6/7 provenance was subsequently narrowed after two Stage8 CI failures exposed the whole-registry pin. The old 901-record registry was audited against merged main before creating the immutable 42-record supporting-candidate snapshot at `data/source-plans/stage6-7-supporting-candidate-sources.json`. Both stages now validate exact live records and raw checksums for these consumed sources while accepting unrelated new registrations. The shared registry remains byte-identical to merged main. See `docs/audits/stage8-source-provenance.md`.

**2008–2023 ingestion is merged; full historical integration is complete for review.** `data/sources.json` contains 867 official CSV resources: 139 for 2008, 143 for 2011, 145 for 2014, 145 for 2017, 148 for 2020 and 147 for 2023.

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

## 2020 coverage — Stage 3B complete

Electoral Commission, 17 October 2020 general election. Exact resources discovered through the official [statistics index](https://www.electionresults.govt.nz/electionresults_2020/statistics/index.html), [voting-place index](https://www.electionresults.govt.nz/electionresults_2020/statistics/votes-by-voting-place-electorate-index.html) and [split index](https://www.electionresults.govt.nz/electionresults_2020/statistics/split-votes-index.html) are recorded in `data/source-plans/historical-2020.json`. All 148 originals are preserved under `data/raw/elections/2020/statistics/csv/`, with actual browser-download timestamps, URLs, checksums and modern_election.py provenance. The original 147-file inventory was fully recovered; no reacquisition was needed. One supporting Te Tai Tokerau split file was subsequently added for discrepancy analysis.

Coverage: six core controls, 72 candidate files, 65 general split matrices, three aggregate matrices, one exact summary and one supporting Māori split. Outputs: 65 general electorates, 561 candidates, 1,105 party records. All 601 national candidatures reconcile. No source-name aliases were needed.

The aggregate Māori/national split controls include NZ Public Party's 1,349 candidate votes under Advance NZ. This is an inferred reporting grouping, supported by exact candidate-party totals and rounded column reconciliation, not an official explanation of party identity. The preserved [local Te Tai Tokerau table](https://www.electionresults.govt.nz/electionresults_2020/statistics/csv/split-votes-electorate-70.csv) and candidate file retain NZ Public Party. The transform preserves those labels and records the aggregate-only mapping; the source's rationale remains unstated. Informal-party non-split 537 matches Party Vote Only. Rounded local/aggregate joint cells remain null-count observations; exact national split/non-split counts remain separate. All source checksums and validation pass without changing earlier processed datasets.

## 2023 coverage — Stage 3C

All 147 planned official Electoral Commission CSVs are preserved under `data/raw/elections/2023/statistics/csv/`: six controls, 72 candidate files, 65 general split publications, three aggregates and one exact summary. Exact authoritative URLs, retrieval timestamps and SHA-256 are in the registry and `historical-2023.json` source plan. All acquisition survived; no sources were reacquired during final recovery. Official index publication note: informal counts for small voting places updated 2 May 2024; current bytes are retained.

Primary outputs contain 65 general electorates, 468 nominations (including nine cancelled Port Waikato nominations) and 1,105 party rows. Seven Māori electorates support national reconciliation; 495 nominations nationally. Port Waikato's party vote remains substantive; no candidate outcome is fabricated or replaced by the by-election. Split outputs retain 64 ordinary matrices, one cancelled publication, three aggregates and exact summary.

Published aggregate Party Vote Only evidence does not fully reconcile with local evidence/cancellation-adjusted controls. Twenty-one related failed assertions are retained with exact rational endpoints, original values and source IDs; see `docs/2023-split-discrepancy.md`. Denominators include Port Waikato; no missing mass is allocated. All candidate-destination joins and other checks pass. Freedoms NZ aggregate grouping does not overwrite constituent affiliations. Leighton Baker/NZ Loyal abbreviated/full party labels use explicit local joins. Exact joint split counts remain unavailable.

## Full historical integration — Stage 3D

The panel consumes all six validated processed election/split/validation sets, pinned by 18 hashes at merged base 455d7149caddfeefe23c817533e3ffb6c35809d4. No election observations, raw downloads or source registry records were added. All 867 source resources remain unchanged. Existing source-specific missingness, grouping, cancellation and unresolved 2023 discrepancy metadata propagate without re-analysis.

Bounded party-continuity references consulted 2026-09-13 (documentary citations, not acquired election datasets; no runtime network dependency):

- Conservative → New Conservative: [Electoral Commission approval, 8 August 2018](https://elections.nz/media-and-news/2018/change-to-conservative-party-name-and-logo).
- New Conservative → New Conservatives, Māori Party → Te Pāti Māori, ONE Party → NewZeal: [2023 election report, Party registrations, PDF page 113](https://elections.nz/assets/2023-General-Election/Report-on-the-2023-General-Election.pdf).
- NZ Outdoors Party → NZ Outdoors & Freedom Party: [Commission approval of 6 April 2022](https://elections.nz/media-and-news/2022/change-to-nz-outdoors-and-freedom-party-name-and-logo).
- Democrats for Social Credit → Social Credit: [application identifying both abbreviations](https://elections.nz/media-and-news/2019/application-to-substitute-a-political-party-name-abbreviation-and-register-a-substitute-party-logo), with approval dated 15 October 2019 in the [historical registration register](https://elections.nz/assets/pagecomponent-file-files/Register-of-Political-Parties-and-Logos-12-Sept-2023-v2.pdf).

These approved name/abbreviation changes support integration-only canonical IDs. They do not imply alliance equivalence, person identity or stable voting behaviour. Exact source labels remain preserved. Original Conservative/Mana decisions remain unchanged. No later election, current polling or Opportunity evidence was collected.

## Stage 4 boundary sources — acquisition checkpoint, not completed reconstruction

`data/source-plans/boundary-2023-2026.json` and `data/sources.json` initially recorded eleven preserved official resources: four Stats NZ layer metadata responses, four complete HD geometry responses, the final meshblock electoral-population CSV and its lookup PDF, and Representation Commission Schedule B. Exact URLs, retrieval timestamps and SHA-256 values are registered. Source files live in `data/raw/boundaries/2020-2025/`.

The 2020 polygons cover 65 general + seven Māori electorates; final 2025 polygons cover 64 + seven. All 143 polygons passed topology validation without repair. Schedule B lists 15 general and four Māori electorates unchanged; East Cape is the renamed unchanged East Coast seat. The published layer geometries are not exactly equal for those seats: geometric differences are preserved in the incomplete acquisition audit, with population movement still unavailable. Do not interpret these area diagnostics as population transfers.

Stats NZ Datafinder layer 122744 (version 418310, published August 2025) provides 57,553 meshblocks with final general/Māori memberships. General electoral population is suppressed as `-999` in 5,697 rows, Māori in 29,990. Other counts use random rounding to base three. CC BY 4.0 applies to that dataset. Preserve suppression and rounding, and do not assume exact totals are reconstructible from public meshblocks. The lookup PDF documents abbreviated shapefile field names; the CSV preserves full names and Unicode. The subsequent exact GeoPackage export, Schedule C and two official concordance tables are now preserved and validated as described below. No historical transition populations or synthetic vote baselines have yet been acquired/generated.


Stage 4 membership/population checkpoint: **15 distinct official resources**, represented by 19 registry entries because the 143,811,969-byte meshblock export is stored losslessly in five byte segments. `meshblock-2025-export.json` records original/part/member checksums and export 4647609. Full GeoPackage EPSG:2193 geometry matches the saved population CSV for all 57,553 meshblocks. Geographic Areas Table 2025 (120975, export 4647631) supplies 57,517 direct GED2020/MED2020 memberships; Table 2026 (123518, export 4648225) supplies explicit historical MB2025 predecessors for the remaining 36, with target code/name checks. This is official lineage, not numeric-prefix or spatial inference.

Schedule C's 64 general/seven Māori population totals are preserved in a source-linked derived control file. Its overlaid duplicate Māori table is not double-counted. All 71 totals lie within the meshblock disclosure bounds. Suppression remains unavailable, and random rounding prevents exact recovery. Two membership exceptions among Schedule B unchanged seats involve suppressed cells (4018221, 4019214); technical-adjustment treatment remains under investigation before transfer weights. No crosswalk has yet been claimed complete.

### Historical population-basis evidence, September 2026 checkpoint

The historical transition plan now registers 2013/2016/2020/2021 geographic concordances, final2020 electoral population and Schedules B/C, 2013 resident population and complete Census meshblock archive, and final2014 Schedule C. All raw URLs, retrieval metadata and checksums are in `data/sources.json` (900 total registry entries at this checkpoint). Completed2017→2020 and2023→2026 crosswalks are described in PROJECT_STATE; earlier acquisition-only paragraphs above are historical.

For2011→2014, the full Census CSV archive is Windows-1252, with separate geographic levels and independently rounded repeated national totals. Its published descent categories do not include the separate electoral imputation described on page5 of the preserved Stats NZ retrospective methodology. Confidential cells remain unavailable. The original Stats NZ Westbrooke/Ryan2000 paper, preserved from ACE's copy and visually checked at pages1–3/10–11, uses area-specific roll/descent quantities; it does not supply missing2013 local inputs. Final2014 Schedule C controls are transcribed separately from national/island seat-allocation figures. Their sums differ; no forced reconciliation or proxy has been implemented. Level A/B/C selection remains outstanding.

### Stage4 final source status

901 registry entries now pass integrity checks. The2014 Commission report is preserved as `rc-2014-boundary-report`, supplying20 unchanged general/five Māori controls. All three transitions and party-vote bounds are complete; earlier acquisition-only notes are historical. Level B is selected for2011, not an exact electoral microdataset or resident proxy. No new source was acquired during finalization. Source metadata, raw bytes and historical election outputs remain unchanged.
## Stage 10 reused source evidence — 2026-09-23

Stage10 acquired no new raw sources. It pins the already preserved Stage7 candidate occurrences, Stage8 Parliament identity links and raw indexes, Stage9 dated Parliament profile overlay with its stage-specific source plan and raw-byte contract, Stage5 party-continuity output, and processed election winner flags. The Stage9 107-profile acquisition targeted source-winner recontesters, not the universe of incoming replacements; published profiles also favour parliamentary careers. These provenance limits explain why an unknown incoming person/career cannot be filled from a name contrast. `data/processed/models/replacement-candidate/input-contract.json` and the analysis contract pin exact consumed artifact bytes; the Stage8/9 source plans and raw files are verified without pinning the entire mutable registry. No historical registry record or raw file changed. See [Stage10 findings](docs/replacement-candidate.md).

### Stage10 post-review acquisition — 2026-09-24

The preceding paragraph is the historical initial checkpoint. A predeclared 20-case bounded pass subsequently preserved 23 additional pages under `data/raw/identity-stage10/`: 14 New Zealand Parliament electorate histories and nine pre-result candidate statements authored by National, Labour or a candidate, mirrored by Scoop or supplied to Indian Newslink. Each page has a URL, source organization, publication date where established, retrieval timestamp, SHA-256 and explicit limitation in `data/source-plans/stage10-identity-sources.json`; the same 23 records were **appended** to `data/sources.json` without changing any of its preceding 901 records or their order. Five requested Parliament profile URLs failed and were not registered as data. `data/source-plans/stage10-identity-review-plan.json` preserves the 182-case universe and priority choice made before search. This priority did not inspect target residuals or direct winner flags but did use inherited identity gaps that can encode target/later outcome anchors; `postfit-selection-audit.json` records the resulting acquisition-selection limit.

The separate `data/source-plans/stage10-maori-winner-sources.json` pins 24 previously preserved official records: 21 Māori candidate tables plus the 2008, 2014 and 2020 winner summaries. Exact live required metadata and raw hashes are verified; unrelated registry additions are permitted. Unique electorate/candidate joins reconcile official winner labels, candidate votes and majorities. This source overlay does not change the original Stage7–9 election/model outputs or infer person identities. The Stage9 profile source plan continues to protect its 108 raw files and dated tenure evidence. Original source bytes remain immutable, and publication/retrieval dates are not confused with historical service or candidacy dates.

## Stage11 reused split-vote evidence — 2026-09-25

No new source was acquired. `data/source-plans/stage11-local-split-sources.json` snapshots the exact384 registered official general local split tables consumed by Stage11, with source IDs, paths and raw SHA-256. The validator compares these required records with the live registry and verifies their raw bytes; unrelated registry additions are accepted, while changed/deleted/ambiguous required records or changed raw bytes fail. Processed election/split inputs, Stage5 party continuity and the reviewed2023 discrepancy plan have separate exact input hashes and historical deterministic checks. The original924 registry entries and Stage5–10 numerical outputs are not changed.

Every general local matrix is linked election-locally to party row controls and named candidate columns. Rows are exact party-ballot group counts; cells are rounded conditional percentages with null exact joint counts. General/Māori/national aggregate matrix destinations are party groups, not person identities; they cannot fill the missing Māori named-candidate panel. The 2023 Port Waikato cancellation and21 recorded aggregate Party Vote Only reconciliation assertions retain their original official values, exact interval fingerprints and limitations. Stage11 does not rescale or impute them. The single2020 supporting Māori local table remains outside the comparable general evaluation.
