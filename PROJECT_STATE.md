# Project state

Updated 2026-09-14. Stage 4: **Historical boundary-transition reconstruction** on existing branch `stage/04-boundary-2023-2026`. Base `624fe1d74aa43014e0c65f534c161e22b51e250d` (PR #10 merged). Do not restart, rebase or change branches.

## Authorized scope and order

Continue 2023 results → final 2025/2026 boundaries first, then reconstruct 2011 → 2014 and 2017 → 2020 independently. Verify historic boundary regimes from official evidence. Use generic boundary-transition machinery with explicit source election/boundary, target election/boundary, population source and provenance configuration. These are separate derived baselines, never replacements for observed election data or the historical panel.

Primary weights must use contemporaneous official small-area population/electoral-population evidence, preferably meshblocks and official concordances. Whole-electorate land-area weights are prohibited. Preserve fractional party votes and party-by-party mass. Candidate/split sensitivity is secondary and only where defensible. No person linking, modelling, polling or geographic voter-residence inference from voting places.

## Saved progress

- `fa025b0`: authoritative boundary source plan and acquisition/registration tools.
- `0caa0f7`: four immutable official Stats NZ HD layer **metadata responses**, 2020 and 2025 general/Māori, registered in `data/sources.json`. Four full-resolution geometry responses and the population CSV/lookup were subsequently acquired as recorded below.
- Working tree was clean on resumption; no surviving uncommitted acquisition found.
- Source validation passed for 871 registered resources at the metadata checkpoint (867 historical + four boundary metadata).
- Historical panel deterministic check passed before branching. Historical outputs remain unchanged; no derived boundary outputs yet.

## Current acquisition and unresolved access

Four complete HD geometry responses are preserved under `data/raw/boundaries/2020-2025/*-geometry.json`. Inventory: 2020 65 general + 7 Māori; 2025 64 general + 7 Māori. EPSG:2193, unique OBJECTIDs, closed rings, no transfer-limit truncation. Original JSON response bytes unchanged; no simplification requested. All 143 polygons passed strict topological validation without repair using pinned Shapely 2.1.2 / NumPy 2.2.6. Source/target meshblock membership and change-control reconciliation remain pending. Total source registry now 878 (867 historical + 11 Stage 4, including Schedule B). Population checkpoint `c91eb24` is pushed.

`data/source-plans/boundary-2023-2026.json` holds exact reviewed URLs. Metadata identifies layer 0, native EPSG:2193, official general/Māori fields for each year. Final 2025 layers must be used, never proposed layers. Official publication confirms 2020 boundaries used for 2020/2023 and final August 2025 boundaries for 2026. Historical regime evidence remains to acquire after current geographic checkpoint.

Schedule B direct curl returned a 212-byte HTML access response, not a PDF; it was rejected and not registered. Schedule B was subsequently acquired unchanged through its normal Chrome link and is now preserved. Schedule C direct access also returned HTML; browser download was requested but no completed local file was found. Do not register the HTML as PDF. The existing Stats NZ layer 122744 browser page subsequently loaded. Its linked official CSV and lookup PDF are now preserved and registered (873 total resources). CSV has 57,553 unique meshblocks, 64 general and seven Māori membership codes. General population is suppressed (-999) in 5,697 rows, Māori in 29,990; all other counts are nonnegative multiples of three. Suppression is not zero. The source uses random rounding to base three; exact control reconciliation needs confidentiality-aware treatment. No weights have been calculated. The CSV contains target membership but no source membership; official concordances or geometry are still required. Do not re-download these two valid sources.

Exact next action: acquire deterministic full-resolution geometry queries using preserved layer metadata; obtain official schedules B/C and layer 122744 schema/population evidence through normal official access; reconcile 65+7 source and 64+7 target inventory and official changed/unchanged controls. Save this geographic checkpoint before lengthy historical acquisition. Never infer population transfer from metadata or electorate area.

## Remaining checkpoints

A. Current 2023→2026 geometry/schedules/population and change reconciliation.
B. Generic crosswalk framework and validated current transition.
C. Historical 2011→2014 and 2017→2020 geography/population sources, saved before lengthy processing.
D. Three population crosswalks with conservation and quality metrics.
E. Three separate notional party-vote baselines with per-party conservation.
F. Optional defensible candidate/split sensitivity.
G. Final determinism, substantive validation, immutable historical-byte checks, documentation and unmerged PR into main.

Every meaningful checkpoint must update this handoff and be pushed. No Stage 4 PR yet. All three transitions must be complete before final PR readiness. Preserve Port Waikato cancelled candidate/split missingness, substantive party votes and the 21 documented 2023 source discrepancies. No prior output or panel changes authorized.

Exact next stage after all three transitions are complete, only on explicit authorization: **Local party-vote transformation backtesting only.**

## Geography implementation checkpoint

`scripts/boundaries/geometry.py` decodes Esri clockwise shells and counterclockwise holes, preserves multipart islands, and rejects invalid topology without repair. `scripts/tests/test_boundary_geometry.py` includes four synthetic failure/structure tests, one real-source test covering all four layers, and a deterministic audit test. Run with `.venv/bin/python -m unittest scripts.tests.test_boundary_geometry -v`; six tests passed. `requirements-boundaries.txt` pins Shapely 2.1.2 and NumPy 2.2.6. Inherited system NumPy 1.26.4 caused a wheel runtime error; isolated pinned NumPy resolved it. Install these dependencies in a dedicated environment for subsequent boundary checks; do not alter legacy ingestion dependencies.

Layer 122744's geometry export UI was inspected: Shapefile export is approximately 160 MB, EPSG:2193, and Create Export routes to login. The public CSV attachment already preserved is available without login; polygon export requires normal Stats NZ/Datafinder login. No login bypass attempted. Next bounded access work: seek a published official meshblock concordance/public equivalent, or obtain the official export through authenticated normal access. The source CSV lacks source-boundary membership, so do not produce weights yet.

## Latest saved audit / next required access

- Important pushed acquisition SHAs: `472f43d` (all four HD geometry responses), `7f196e3` (topology decoder/tests and Schedule B).
- Geographic acquisition audit: `data/processed/boundaries/2020-2025/geography-validation.json`, regenerated by `.venv/bin/python -m scripts.boundaries.audit_geography`; `--check` passes. It is explicitly incomplete, not a vote-transfer output. All 19 officially unchanged seats have non-identical geometry across the published vintages. Symmetric-difference areas are diagnostics only, not population weights. Population movement remains null. The derived Schedule B control file preserves its source/page and the East Cape/East Coast rename.
- Full Python suite: **115 tests passed**, including six focused geometry/audit tests. All **878 registered raw-source checksums passed**. Historical panel deterministic check passed. Git comparison against base confirms every per-election processed dataset and historical panel file remains byte-identical. No frontend/shared TypeScript changed; frontend checks not run at this incomplete acquisition checkpoint. `git diff --check` passed; no Python formatter is configured.
- Minimal CI change installs `requirements-boundaries.txt` before existing Python checks. No check removed, path filter or cancellation change introduced.
- Bounded public alternative inspected: Stats NZ `Meshblock_2025/FeatureServer` describes January 2025 **57,551** meshblocks, not final version 2's **57,553**. It has not been accepted or registered as equivalent. Do not substitute it without valid official concordance evidence.
- **Exact next action:** obtain normal authenticated Stats NZ Datafinder export of layer **122744**, revision/version **418310**, EPSG:2193, preferably GeoPackage for full field names and offline SQLite/WKB inspection. The existing export dialog's Create Export link routes to login. User login is needed for this route; never bypass it. Preserve returned archive unchanged, exact export settings/URL/time/checksum, verify all 57,553 codes against the saved CSV, then establish 2020 electorate membership. Check surviving downloads first. Schedule C is now explicitly planned but remains unacquired; its direct response was HTML, and no completed browser download was found. Resume from the exact official plan URL rather than rediscovering it.
- No crosswalk weights, synthetic votes, older transition acquisition or fitted model yet. Checkpoint A remains incomplete pending membership/population/control reconciliation. No Stage 4 PR; do not create the final PR before all three transitions pass.

## Authenticated continuation — 2026-09-14

User signed in to Datafinder. On the existing layer 122744 page, started a full-layer GeoPackage export in native EPSG:2193 (UI estimate 84 MB), without a crop. Export is preparing; do not create a duplicate. Check its existing progress dialog / completed downloads before any new request. The old Schedule C download was recovered unchanged from Downloads, registered as `rc-2025-schedule-c`, and checksum-validated (879 total resources). No re-download was needed. Next: preserve/checksum the completed GeoPackage archive, inspect its metadata and 57,553 meshblock IDs against the preserved CSV, then continue source-boundary membership audit.

## Exact meshblock geometry acquired

Authenticated export **4647609** completed and was downloaded normally from `https://datafinder.stats.govt.nz/services/api/v1.x/exports/4647609/download/`. Original ZIP: **143,811,969 bytes**, SHA-256 **7d5857d44683f4f62c0309bd15c2f2bdf71f6ba0044a4a90f77ac9bec03f0da2**. ZIP CRC passes. Preserved unchanged as five ordered 32-MiB-or-smaller byte segments in `data/raw/boundaries/2020-2025/meshblock-export/`; this is reversible storage, not source transformation. Manifest `data/source-plans/meshblock-2025-export.json` records export settings, source URLs, timestamp, original/archive member/part hashes. Registry has 884 entries: 13 distinct Stage 4 official resources represented by 17 registry records because this one archive occupies five byte segments. Do not re-export/re-download it.

`python3 -m scripts.boundaries.archive data/source-plans/meshblock-2025-export.json /tmp/nz-meshblock-2025-original.zip` reconstructs and verifies identical original ZIP bytes. Focused archive reconstruction/mutation test passed; all 884 registered checksums passed. Next: inspect the GeoPackage and compare all IDs/population/target membership to the preserved CSV, then establish source-boundary memberships. Geometry and population-field reconciliation are not yet claimed.

## Recovered concordance checkpoint

Recovered the existing completed official export **4647631** (no duplicate export requested): table **120975**, Geographic Areas Table 2025, version **404495**, original CSV ZIP now `data/raw/boundaries/2020-2025/geographic-areas-table-2025.zip`. ZIP CRC passes; 57,551 unique MB2025 codes; explicit GED2020/MED2020 code/name fields. Registered source `stats-2025-geographic-areas-table`; registry now 885 records. Source geometry export remains safely pushed at `cfdbc94`.

Recovered uncommitted `scripts/boundaries/geopackage.py` and three passing focused tests. This adapter already validated all 57,553 GeoPackage geometries and their ID/population/target membership against the saved CSV in the previous uninterrupted work. No transformations or historical data rewritten. Exact next action: join final-version meshblocks to the official 2025 concordance by code, quantify unmatched units, and resolve only those using authoritative lineage/geometry evidence. Preserve all missingness; no weights yet.

## Official lineage acquisition checkpoint — 2026-09-14

Recovered concordance/GeoPackage adapter pushed at `9618f27`. Exact initial join: 57,517 final meshblocks match Geographic Areas Table 2025 directly; 36 new codes do not; 34 old-table codes are absent from the final population inventory. The deterministic `scripts.boundaries.audit_membership` records these facts and validates matched source code/name pairs against 2020 geometry metadata. Three focused membership tests pass; audit regeneration/check passes. No weights produced.

Acquired only the needed official Geographic Areas Table 2026, table 123518, export 4648225: original 2,260,265-byte CSV ZIP preserved and registered. CRC passes; 57,575 rows. Its explicit MB2026_code→MB2025_code fields provide predecessors for all 36 unmatched final-2025 codes (4019179–4019214). Next action: validate target electorate consistency and apply those explicit two-step official joins, with traceable source IDs; do not infer predecessors from numeric similarity. No geometry fallback is currently indicated. Registry now 886 entries, 15 distinct Stage 4 resources. Earlier historical data unchanged. Stage 4 remains incomplete; no PR yet.
