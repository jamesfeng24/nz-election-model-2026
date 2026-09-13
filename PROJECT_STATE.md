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
