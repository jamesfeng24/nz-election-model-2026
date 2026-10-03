# Reproducibility and session recovery

## Stage 22 conditional complete-share checkpoints

With Python 3.12 and pinned `requirements-boundaries.txt` installed, run the Stage22 commands **in historical checkpoint order**: `python3 -m scripts.checkpoints.stage22_prefit --check`, `python3 -m scripts.checkpoints.stage22_construction --check`, then `python3 -m scripts.checkpoints.stage22_evaluation --check`. The first verifies election-local shared-group routing, exact IDs, pre-fit gates, source registry metadata and consumed raw bytes; the second reruns all four restrictions and coherent rounding scenarios and requires byte-identical saved fits/predictions; the third checks the evaluation-only actuals/paired scores against the committed construction hash. New unrelated `data/sources.json` registrations are accepted. The independent 4,097-point κ profile makes construction checking more expensive than a routine source check; it should be run once for final validation, not repeatedly during unrelated work. The [Stage22 findings](stage22-conditional-complete-share-results.md) state conditional-only inputs, full-frame abstentions and the null operational selection. Earlier stage outputs are read, not regenerated.

## Fresh checkout

1. Clone the canonical GitHub repository and inspect branch, HEAD and `git status`.
2. Read AGENTS.md, PROJECT_STATE.md, DECISIONS.md, METHODOLOGY.md, DATA_SOURCES.md and docs/statistical-specification.md. Check the latest changelog and relevant schemas.
3. Use the Node version in .nvmrc and npm 10.9.2; run `npm ci` from the committed lockfile.
4. Use Python 3.12.2; install pinned `requirements-boundaries.txt` for numerical/model checks. Run `npm run check:all`. If results differ from PROJECT_STATE.md, investigate before major work.
5. Confirm the user's authorized stage. Do not implement the backlog automatically.

## Stage close or interrupted session

Record current stage, completed/unfinished work, branch, check results, known problems, data limitations, affected files and exact next task in PROJECT_STATE.md. Update durable decisions and source/method documentation. Review `git diff --check` and `git diff`, run checks, commit and push. Work only on the user-specified stage branch; periodically push checkpoints. Verify HEAD matches that remote stage branch. When the stage is complete, open a PR into main and record its URL before the final handoff commit; never merge it yourself. For a user-requested pause, save the partial checkpoint and state that no completion PR exists. Do not push directly to main. Do not record a self-referential commit hash inside its own commit; Git history supplies the authoritative revision.

If interrupted before checks or push, say so explicitly and record the first recovery command. Never rely on local untracked files or chat summaries for handoff.

## Future data pipeline contract

Each processed dataset must document a runnable command, input source IDs and SHA-256 values, script revision, dependency versions, configuration, output paths and checksums. Identical inputs/configuration must regenerate semantically identical outputs. Keep run timestamps in metadata where they do not destabilize data checksums; explain any byte-level nondeterminism. Validate schemas, joins, missingness and relevant totals. Fail on missing inputs rather than synthesize them.

For future random runs record seed, PRNG implementation/version, draw count, model version, configuration and input revisions. Document platform-sensitive numerical tolerances. No stochastic code exists. The deterministic historical processing pipeline below is implemented for 2008.

## Automated checks

GitHub Actions runs locked installation, Vitest, strict TypeScript and Vite build on pushes and pull requests. Local gates use the same npm scripts. Build artifacts and node_modules are ignored; package-lock.json is tracked. Dependency upgrades must be intentional, checked and documented.

## Offline research and large inputs

Python 3.12.2 is pinned in .python-version, and pyproject.toml declares no dependencies. Standard-library tests and source-integrity checking run in a separate CI job. Once third-party packages are needed, commit exact direct/transitive versions and installation instructions before using them. Keep per-run environment metadata and export JSON/GeoJSON for the client. No pip installation is required in this stage.

Source file validation reads data/sources.json and verifies unchanged local raw bytes; it fails on missing files and never retrieves data. Large or restricted inputs may be excluded from Git only with an exact reproducible download recipe, expected checksums and rights notes. Each new source release has a separate materialization path. Validation does not authorize collection.

The configured GitHub integration can publish an identical Git tree when local Git credentials are unavailable. Record returned commit IDs, update only the stage branch with a non-forced ref update, then fetch and synchronize the local branch. Do not expose credentials or rewrite main. Commit hashes can differ from preliminary local commits; the remote commit and identical tree are canonical.

## Reproduce checkpoint B (2008) offline

Use Python 3.12.2, Node 22.17.0 and npm 10.9.2. No Python packages need installing. After reading state and inspecting Git status, run from the repository root:

```sh
npm run check:all
python3 -m scripts.transform.historical --year 2008 --check
git diff --check
```

The processor verifies input hashes, regenerates all three outputs in memory and compares exact committed bytes with `--check`. To intentionally regenerate after a reviewed code change, omit `--check`. JSON is UTF-8 with deterministic order/formatting, no run timestamp; the command prints output SHA-256 hashes. Source IDs resolve exact input hashes in the registry; Git revision identifies the processor/configuration. This is not yet automated in CI and must be run explicitly.

If raw inputs are missing, the checksum-pinned fetch mechanism is:

```sh
python3 -m scripts.ingest.historical_sources --year 2008 --fetch-registered
```

HTTP 403 was observed here. If this recurs, use normal browser downloads of the exact registered URLs and import unchanged files:

```sh
python3 -m scripts.ingest.import_historical_downloads --year 2008 --directory /path/to/downloads
```

The explicit source plan controls filenames/URLs; `--suffix` supports an observed browser collision suffix and `--allow-partial` allows incremental imports but does not imply complete coverage. Never rename/overwrite raw inputs to fit a schema. Different bytes at a registered path fail; investigate rather than update a checksum to conceal a change.

The three committed 2008 output hashes at B are respectively:
- elections/2008.json: `15eb63c45984177b21b964c4580102a2e5b54879316143e64684f13753dd86d0`
- split-votes/2008.json: `3a9a763ef298ce894066982752bdc60627c14dd952b6a370ad196473f90bfc7a`
- elections/2008-validation.json: `389d131e4e5884aa9c29ce6960183dfa05b2c04129362a1dc79442c2920d5973`

2011 now has a complete plan and validated inputs as documented below. 2014 is now implemented as described in its section below. Resume instructions and mandatory per-year pushes are in PROJECT_STATE.md.

## Reproduce 2011 (Stage 2B)

Use the same pinned runtimes and zero Python dependencies as 2008. All 143 inputs are committed; regeneration needs no network:

```sh
python3 -m unittest discover -s scripts/tests
python3 scripts/validate/source_files.py
python3 -m scripts.transform.historical --year 2011 --check
```

Omit `--check` only to intentionally regenerate reviewed outputs. The shared processor calls the 2011-specific control extension; configuration is the year and committed source inventory, and the Git revision identifies code. The new tests regenerate 2011 deterministically and mutate only temporary copies to check rejected bad votes, winner totals, split percentages and summary counts. No authoritative raw file is edited.

The 2011 output SHA-256 hashes are:
- elections/2011.json: `8b3043edb38e072befc2508ed769836fcb6aaaa52c81626b6748f59f37729030`
- split-votes/2011.json: `3e503b3757380e63d3da795ea9506c3c3ba445b89f815f18b33343207d04514c`
- elections/2011-validation.json: `7fba25dbba5d750d0b49564f83b8ce5f95f497e2ddec1166df06169f34690ebd`

For missing raw files, use the established `historical_sources --year 2011 --fetch-registered` mechanism. If HTTP is blocked, browser-download exact registered URLs and use `import_historical_downloads --year 2011 --directory /path/to/downloads`. The plan's optional downloadFilename records observed collision names; adjust only acquisition metadata if a fresh browser names downloads differently. Do not accidentally import the older 2008 same-basename file. Retrieval timestamps derive from original browser file modification times and existing records remain idempotent.

2011 source checksums and all semantic validations passed. Since shared Python code changed, the specific 2008 `--check` regression was run and all committed 2008 output bytes matched; no broader 2008 re-audit was performed. AGENTS.md requires frontend tests/typecheck/build, and those also passed. Local Git fetch/push worked for this task. Next task: 2014 ingestion only.

## Reproduce 2014 (Stage 2C)

All 145 raw sources are committed. Use the existing pinned Python 3.12.2 runtime without third-party packages:

```sh
python3 -m unittest scripts.tests.test_historical scripts.tests.test_historical_2014
python3 -m scripts.transform.historical --year 2014 --check
```

The 2014 tests verify exactly 145 registered inputs and their checksums; the transform independently verifies every consumed input. Regeneration compares exact UTF-8 output bytes, with no timestamps in generated data. Source registry hashes identify inputs; Git revision identifies code/configuration. The shared aggregate implementation is now historical_split_controls.py, with the 2011 API preserved by a wrapper. Targeted 2008/2011 regeneration confirmed unchanged bytes after this extraction and the year-scoped grouping change.

Final 2014 output SHA-256:
- elections/2014.json: `f6f005d0e936230ad260fb7cd32897033d8179482d8cdd6c570712df904a638c`
- split-votes/2014.json: `0388187be992b503c861ece81f8452322b8d404fa0709360fc77c6d31101e292`
- elections/2014-validation.json: `a70bbe76e5ffc735ca7188c31f3a84046c4d57b683e502ffdd7182a3d8792261`

For missing inputs, use `python3 -m scripts.ingest.historical_sources --year 2014 --fetch-registered`. If direct access is blocked, use normal browser downloads of exact registered URLs, then `python3 -m scripts.ingest.import_historical_downloads --year 2014 --directory /path/to/downloads`. The plan records observed browser duplicate filenames; adapt acquisition metadata to actual filenames if needed, never source contents. Do not import a prior year's same-basename download. Existing source records remain immutable/idempotent.

Frontend tests/typecheck/build were run because AGENTS.md requires them, not because frontend code changed. No broad 2008/2011 re-audit or cross-year integration was performed. Next task: **2008–2014 integration and cross-year validation only**.

## Integrated 2008–2014 panel (Stage 2D)

Normal panel regeneration uses only committed per-year JSON, with no network or raw reparsing:

```sh
python3 -m scripts.transform.historical_panel
python3 -m scripts.transform.historical_panel --check
```

One offline verification command covers preserved raw inputs → all three per-year outputs → combined panel and cross-year invariants:

```sh
python3 -m scripts.transform.historical_panel --check --verify-years
python3 -m unittest discover -s scripts/tests -v
```

`--verify-years` invokes the existing per-year validators (including consumed-source checksums and rounded/exact control reconciliation), regenerates all nine input outputs **in memory**, and requires byte equality before checking the panel. It never overwrites per-year files. CI runs this command. No fetch/download is part of any command above.

For intentional full output regeneration after a reviewed processing change:

```sh
for year in 2008 2011 2014; do
  python3 -m scripts.transform.historical --year "$year" || exit 1
done
python3 -m scripts.transform.historical_panel
python3 -m scripts.transform.historical_panel --check --verify-years
python3 -m unittest discover -s scripts/tests -v
```

The manifest records every per-year input hash and panel output hash. JSON serialization uses UTF-8, preserved Unicode, deterministic input order and no wall-clock timestamps. Code and canonical-party decisions are versioned with Git. Stage 2D passed all 31 Python tests, all-year regeneration, 30 frontend tests, typecheck and build. All previous per-year hashes listed above remain unchanged. Next task: **2017 historical election ingestion only**, after review/merge and explicit authorization.

## Reproduce 2017 (Stage 3A)

All 145 official sources are committed with registry hashes; use pinned Python and its standard library, without browser/network access:

```sh
python3 -m scripts.transform.modern_election --check
python3 -m unittest discover -s scripts/tests -v
python3 scripts/validate/source_files.py
python3 -m scripts.transform.historical_panel --check --verify-years
```

Omit `--check` to deliberately regenerate the three 2017 exports. Complete validation is always required; the temporary core-only checkpoint mode has been removed. CI checks committed output equality. The 2017 adapter consumes all 145 inputs, checks hashes before parsing, and uses deterministic UTF-8 JSON without timestamps. Acquisition remains a separate immutable import process using the explicit source plan; do not redownload valid preserved files.

Final verification passed 51 Python tests, all 572 registry hashes, exact 2017 regeneration and all historical regressions. All 21 pre-existing processed files match branch base f627903 byte-for-byte, including all nine earlier per-year outputs and six panel files. No frontend/shared TypeScript changed, so frontend checks were not rerun under the scoped AGENTS.md rule. No formatter/linter is configured; compilation and whitespace checks passed.

## Reproduce 2020 (Stage 3B)

All 148 official originals are committed. No browser or network is needed:

```sh
python3 -m scripts.transform.modern_election --year 2020 --check
python3 -m scripts.transform.modern_election --year 2017 --check
python3 scripts/validate/source_files.py
python3 -m scripts.transform.historical_panel --check --verify-years
python3 -m unittest discover -s scripts/tests
```

Omit `--check` from the first command to regenerate only the three 2020 exports. CI includes 2020 equality checking. Explicit modern_config.py settings select source plan, year/IDs/coverage and the documented aggregate-only affiliation grouping. No historical panel extension occurs. Final checks: 69 Python tests, 720 registry hashes, deterministic modern exports, prior-year regression and byte identity of all 24 processed files from base a151441. No frontend/shared TypeScript changed; those checks were not rerun. Next task: 2023 ingestion only.

## Reproduce 2023 (Stage 3C)

Use preserved sources offline; no acquisition is needed:

```sh
python3 -m scripts.transform.modern_election --year 2023 --check
python3 -m scripts.transform.modern_election --year 2020 --check
python3 -m scripts.transform.modern_election --year 2017 --check
python3 -m scripts.transform.historical_panel --check --verify-years
python3 scripts/validate/source_files.py
python3 -m unittest discover -s scripts/tests -q
```

Omit `--check` only from the 2023 command to regenerate its three exports. The reviewed rational discrepancy fingerprints in `data/source-plans/2023-split-discrepancies.json` are a versioned validation input, not a source correction. New/changed/disappearing discrepancies fail; do not regenerate that registry automatically to make tests pass. Exact source arithmetic and limitations are documented in `docs/2023-split-discrepancy.md`.

Final checks pass: 96 Python tests, 867 hashes, three modern deterministic checks, legacy regeneration and byte identity of all 27 previously processed files. The existing panel is not extended. No frontend/shared TypeScript changes; frontend checks were not required or run.

## Full-panel integration — Stage 3D (supersedes earlier panel output path)

Normal construction consumes only the 18 validated per-year processed JSON files, never CSV archives:

```sh
python3 -m scripts.transform.historical_panel
python3 -m scripts.transform.historical_panel --check
```

Outputs are the existing five content families plus manifest in `data/processed/historical/2008-2023/`. The old combined directory is replaced; old content survives exactly in the six-year panel and Git history. Every build verifies pinned per-year input hashes, lossless source projection and the old-slice hashes stored in `data/source-plans/historical-panel.json`. Do not update that contract to conceal altered inputs. The old manifest is reconstructed for an independent hash comparison. Two identical runs produce identical bytes; check mode rejects stale outputs.

Final compatibility/audit commands:

```sh
python3 -m scripts.transform.historical_panel --check --verify-years
python3 -m unittest discover -s scripts/tests -q
python3 scripts/validate/source_files.py
npm run check
```

`--verify-years` explicitly invokes legacy and modern per-election regenerators in memory for all six years; it does not write inputs or acquire sources. This is separate verification, not the panel's ingestion path. Full verification passed 109 Python tests, all 867 raw checksums and all 18 processed hashes, six per-year deterministic checks, old-slice/manifest byte compatibility, 30 frontend tests, typecheck and build. Frontend checks were run once because AGENTS.md requires them at this major integration checkpoint. Known 2023 source discrepancies remain recorded; no new discrepancy is accepted.

## Stage 4 geography checkpoint (in progress)

Observed election outputs and the full historical panel remain immutable. Stage 4 now covers three separate boundary transitions: 2011→2014, 2017→2020, and 2023→2026; acquisition/validation of the last transition is first. No crosswalk or notional vote baseline exists yet.

Boundary topology requires the optional exact dependencies in `requirements-boundaries.txt` (NumPy 2.2.6, Shapely 2.1.2) and Python 3.12. Install in a dedicated virtual environment. Runtime source acquisition remains shell/browser-only; Python processing is offline. CI installs the same pinned dependencies before the existing Python checks. No CI path filtering or verification reduction was introduced.

```sh
.venv/bin/python -m unittest scripts.tests.test_boundary_geometry -v
.venv/bin/python -m scripts.boundaries.audit_geography
.venv/bin/python -m scripts.boundaries.audit_geography --check
python3 scripts/validate/source_files.py
```

The acquisition audit is explicitly incomplete and contains only geometry diagnostics, never transfer weights. Its area differences must not be interpreted as population flows. The original ArcGIS JSON responses are stored without quantization/simplification; all four source layers are EPSG:2193. The decoder preserves holes and islands and rejects invalid topology rather than repairing raw data.

The public population attachment has 57,553 final-version meshblocks. Suppressed `-999` values remain missing (not negative population, zero or a midpoint estimate). Other values are confidentialised by random rounding to base three. The public January 2025 ArcGIS meshblock geometry has 57,551 units and is not an established substitute. The exact Datafinder layer 122744 geometry export was subsequently acquired through normal authenticated export; source membership and Schedule C disclosure-control audits now pass. The preserved population CSV and lookup PDF must not be downloaded again.


Resume Stage 4 entirely offline for the acquired 2020→2025 inputs:

```sh
.venv/bin/python -m scripts.boundaries.audit_membership --check
.venv/bin/python -m scripts.boundaries.audit_population --check
.venv/bin/python -m unittest scripts.tests.test_boundary_membership scripts.tests.test_boundary_population scripts.tests.test_boundary_geopackage scripts.tests.test_boundary_archive -v
```

Omit `--check` to regenerate the corresponding audit. The population audit reconstructs verified raw ZIP bytes in memory and extracts the GeoPackage into a temporary directory; no network or raw-source edits occur. Original byte segments, CRC and every archived member hash are checked. Schedule C controls are a documented transcription of the preserved PDF, not regenerated from a live website. Audits are not transition weights or notional vote outputs. Source joins preserve explicit predecessor IDs and source hashes; unresolved membership fails completeness tests.

Suppression reconciliation is offline and deterministic:

```sh
.venv/bin/python -m scripts.boundaries.suppression_report --check
.venv/bin/python -m unittest scripts.tests.test_boundary_feasible -v
```

The report records sharp conditional population/weight bounds, exact rational endpoints, control availability, two source-local exception identities and input hashes. Small exhaustive fixtures verify that ratio endpoints are attainable under all destination equations. An unexpected additional unchanged-seat exception fails validation.

Current transition crosswalk and manifest:

```sh
.venv/bin/python -m scripts.boundaries.transition --transition 2023-2026
.venv/bin/python -m scripts.boundaries.transition --transition 2023-2026 --check
.venv/bin/python -m unittest scripts.tests.test_boundary_transition scripts.tests.test_boundary_composition scripts.tests.test_boundary_feasible -v
```

The transition consumes preserved memberships/population controls offline. Manifest hashes include input data, configuration, implementation and output bytes. Witness allocations exist only inside tests; they are not nominal population estimates or exported observations. Older transition adapters remain to implement after authoritative acquisition.

### Stage 4 final reconstruction checks

Use the pinned `requirements-boundaries.txt` environment (including SciPy1.16.0):

```
python -m scripts.boundaries.transition_2014 --check
python -m scripts.boundaries.contract --check
python -m scripts.boundaries.notional --transition 2011-2014 --check
python -m scripts.boundaries.notional --transition 2017-2020 --check
```

Omit `--check` only to intentionally regenerate the corresponding derived output. All three party baselines are complete. Notional outputs use64 branch-and-bound nodes per extremum by default; retain this parameter for byte-identical regeneration. The files expose numerical enclosure gaps separately from geographic identification uncertainty. They are not fitted predictions or exact local voting observations. All three crosswalks remain globally coupled; marginal endpoints cannot be combined arbitrarily. No raw source fetching occurs during these commands.

Final offline checks also include:

```sh
.venv/bin/python -m scripts.boundaries.transition --transition 2017-2020 --check
.venv/bin/python -m scripts.boundaries.transition --transition 2023-2026 --check
.venv/bin/python -m scripts.boundaries.notional --transition 2023-2026 --check
.venv/bin/python -m scripts.boundaries.readiness --check
.venv/bin/python -m scripts.boundaries.secondary --check
.venv/bin/python -m scripts.validate.source_files
.venv/bin/python -m unittest discover -s scripts/tests -q
```

The final Stage4 outputs supersede earlier acquisition-only notes. Secondary reconstruction is deliberately limited to availability/coverage metadata, with null unidentified vote baselines. Historical inputs remain untouched.

### Stage5 offline backtests

`.venv/bin/python -m scripts.models.party_vote_transform.run --check` validates pinned historical/boundary hashes, regenerates records/scores/selection in memory and compares committed bytes. Omit --check only for an intentional reviewed regeneration. No source fetching or expensive boundary optimization occurs. Run `.venv/bin/python -m unittest scripts.tests.test_party_transform -q` for focused formulas, identity, uncertainty, score, anti-leakage and input-corruption tests. Specification was committed before scoring; output and implementation hashes are recorded in manifest.json. All pre-Stage5 data must remain byte-identical.

### Stage6 offline elasticity

Run `.venv/bin/python -m scripts.models.nat_lab_elasticity.run --check` to verify pinned historical/Stage5 hashes and deterministic outputs. Omit --check only for intentional regeneration. Focused tests: `.venv/bin/python -m unittest scripts.tests.test_nat_lab_elasticity -q`. No source retrieval or boundary recomputation. Primary scores use raw linear predictions and flag out-of-range values; chronology and training years are explicit.

## Stage7 observed candidate normalization

Run `.venv/bin/python -m scripts.models.candidate_overperformance.run` to regenerate, or append `--check` to verify committed bytes without writing. Focused tests: `.venv/bin/python -m unittest scripts.tests.test_candidate_overperformance -v`. The pipeline uses standard-library arithmetic and existing validated source parsers; no new dependency or network access. It consumes all six observed election files and already-preserved supporting Māori candidate/party evidence, checks pinned hashes and candidate/party scope controls, then computes matched references and whole-contest leave-one-out residuals. It does not run boundary reconstruction or person linking.

The manifest pins input/specification/implementation hashes and serialized output hashes. Repeated builds must be byte-identical. A changed input or stale output fails the check; do not repin to hide unexplained changes. Preserve every pre-Stage7 data file against base `a28044a795e18a1ebc07bc3ea7c16fd23d6c8c14`, including Stage4/5/6 outputs and source registry. Keep the original Stage6 audit unchanged. Full configured verification is required at final model-release readiness, not after every small edit.

## Stage8 candidate persistence

Run `.venv/bin/python -m scripts.models.candidate_persistence.run --check` to verify pinned input hashes and all committed output bytes without writing. Omit `--check` only for intentional regeneration from the pinned inputs. The original pre-fit specification is preserved with an explicitly post-fit audit amendment; do not treat the corrected cohort as originally frozen. Focused tests: `.venv/bin/python -m unittest scripts.tests.test_candidate_persistence_identity scripts.tests.test_candidate_persistence -v`. The pipeline reads Stage7 occurrence outcomes, six preserved election files for winning evidence, two local Parliament HTML indexes and their Stage8 source plan. It performs no network request or boundary reconstruction. The official indexes were acquired once, registered in SourceRecord format at `data/source-plans/candidate-persistence-sources.json` and validated with exact checksums; the shared legacy registry remains unchanged. No runtime biography lookup is used.

The manifest contains input, implementation and serialized output hashes. Candidate occurrences, earlier numerical model outputs, historical elections and boundary products remain byte-identical to merged main `fa1dda369f1cccbb9b2494c7ebac0db72f4177d9`. The Stage6/7 provenance contracts/manifests and Stage6 record input-hash metadata were deliberately updated under D032; see `docs/audits/stage8-source-provenance.md` for exact changed fields and byte comparisons. Rebuilding Stage7 with `--check`, checking source integrity and comparing numerical prior files against main provide that guard. A changed identity source or Stage7 outcome must fail rather than be silently repinned.

Stage6/7 now read the live `data/sources.json` but pin `data/source-plans/stage6-7-supporting-candidate-sources.json`, an immutable snapshot of the42 consumed records. The validator compares required live records exactly and hashes their raw files. Unrelated registry additions are accepted. `.venv/bin/python -m unittest scripts.tests.test_source_provenance -v` covers additions, required record alteration/deletion and required raw-byte alteration, including both stage builds.

## Stage9 freshman incumbency

From a clean checkout with the configured Python environment, run:

```sh
.venv/bin/python -m scripts.models.freshman_incumbency.run inventory --check
.venv/bin/python -m scripts.models.freshman_incumbency.analysis_run --check
.venv/bin/python -m unittest scripts.tests.test_freshman_inventory scripts.tests.test_freshman_analysis -v
```

The first command verifies the committed **pre-fit** inventory, all108 stage-specific raw profile/index checksums, source-plan metadata, Stage7/8 inputs and deterministic bytes. The second verifies the original specification, explicit **post-fit** cohort amendment, reconstructed target/later-winner counterfactual, corrected analysis contracts and output bytes. Neither command fetches sources, reruns boundary reconstruction or rewrites earlier outputs. Omit `--check` only when intentionally regenerating Stage9 outputs from pinned inputs and reviewing the resulting diff. Stage9's plan is independent of `data/sources.json`; Stage6/7 continue to guard their42 consumed source records and raw bytes. Do not repin contracts to conceal a changed source or prior output.

The committed pre-fit inventory at `6ddec50` and specification at `fb0f491`/pre-fit clarification `c5560f7` precede any effect fitting. `postfit-audit-amendment.json` is later: the first93-pair result had three inherited target/later-winner-dependent links. Reproduction keeps that history and evaluates90 counterfactually stable pairs. `analysis.json.supersededPreAuditOutcomeDependentCohort` is retained for audit, not validation. Stage5–8 deterministic checks and `npm run check:all` remain final validation gates; no historical numerical output should change in Stage9.
## Reproduce Stage10 replacement inventory and diagnostic

From the repository root on the Stage10 branch, with Python 3.12 and preserved raw sources:

```sh
python3 -m scripts.models.replacement_candidate.run inventory --check
python3 -m scripts.models.replacement_candidate.analysis_run --check
python3 -m unittest scripts.tests.test_replacement_candidate -v
```

The inventory command rebuilds all party-seat comparisons from pinned Stage7 occurrences, Stage8 links, Stage5 party continuity, Stage9 dated profile evidence and processed elections. It verifies the 23 new Stage10 identity pages, exact required Māori source records and raw bytes, and 21 official winner joins; unrelated registry additions are accepted. It checks the revised inventory, identity review, Māori winner overlay, input contract and manifest against exact saved bytes. The analysis command verifies the original frozen specification and explicitly **post-review** inventory amendment, plus the separately recorded **post-fit** acquisition-selection audit. It rebuilds identity after removing target/later winner flags with the acquired historical evidence fixed, independently fits replacement and no-replacement models using only earlier elections, scores identical holdout rows and checks all saved analysis bytes. Neither command downloads inputs, reruns boundary reconstruction or rewrites Stage5–9 outputs. The original pre-review inventory/specification checkpoints remain in Git history; `post-review-amendment.json` is not claimed to have been frozen before the original fitting. `analysis-input-contract.json` and `analysis-manifest.json` identify exact consumed bytes/code and output hashes. Run `npm run check:all` and the CI historical deterministic commands before PR handoff.

## Reproduce Stage11 split evidence and conditional diagnostics

From the repository root in the pinned Python environment:

```sh
.venv/bin/python -m scripts.models.historical_split_ticket.run --check
.venv/bin/python -m scripts.models.historical_split_ticket.analysis_run --check
.venv/bin/python -m unittest scripts.tests.test_historical_split_ticket -v
```

The first command verifies the committed pre-fit source/coverage inventory, all384 consumed local split source records and raw SHA-256, processed election/split input hashes and the reviewed2023 discrepancy plan. It tolerates unrelated registry additions but rejects changed/deleted/duplicate required source records or changed raw bytes. The second rechecks the evidence bytes and frozen specification, rebuilds the candidate inventory after flipping historical winner flags, then recomputes conditional local, source-year pooled and party-only split predictions, exact rounding intervals, Stage5 party-input sensitivity, identity diagnostics, selection and manifests. Target split percentages and candidate totals are evaluation inputs only. It performs no network request, raw source acquisition or boundary reconstruction and does not rewrite Stage5–10 outputs. Omit `--check` only for intentional Stage11 output regeneration after reviewing inputs/code. Run `npm run check:all` in `.venv` plus CI historical and 2017/2020 modern-election deterministic checks for final validation.

# Evidence-repair/design checkpoint (Stage 12; no external acquisition)

From the repository root, run `python3 -m scripts.checkpoints.identity_cohort --check` and `python3 -m unittest scripts.tests.test_identity_cohort_checkpoint -v`. The first command rebuilds the frozen 213-seat frame and 30-seat/415-occurrence fixed sample from the exact saved Stage 7 occurrence and validated boundary-readiness bytes, comparing every output byte and both input hashes. It reads no winner, residual or inherited identity fields to select cases. The focused tests verify the selected whole-seat frame, winner/residual-field invariance, duplicate occurrence detection and boundary mismatch rejection. Omitting `--check` intentionally rewrites **only** `data/processed/checkpoints/evidence-repair/cohort-inventory.json`; review the input hashes and diff before committing. No raw source is fetched and no Stage 5–11 numerical output is regenerated.

## Stage 13 fixed-cohort evidence pass

Run `python3 -m scripts.checkpoints.identity_evidence_pass --check`, `python3 -m scripts.checkpoints.profile_supplement --check`, `python3 -m scripts.checkpoints.search_identity --check`, `python3 -m scripts.checkpoints.acquired_sources --check`, and `python3 -m scripts.checkpoints.adjudicate_identity --check` from the repository root. The last check reproduces `data/processed/checkpoints/identity-evidence-pass/final/` from the committed fixed cohort, preserved audits, 11 search batches, 32 explicit source claims and pinned raw sources. Rebuilding without `--check` writes only that final Stage 13 output directory. It does not regenerate earlier model results. Run `python3 -m unittest scripts.tests.test_stage13_adjudication -v` for focused evidence contracts.

## Complete candidate-baseline specification checkpoint

Run `python3 -m scripts.checkpoints.complete_candidate_baseline --check` to verify the deterministic 213-contest availability inventory and pinned source-artifact hashes. Run `python3 -m unittest scripts.tests.test_complete_candidate_baseline_checkpoint -v` for synthetic mass-conservation, missing-destination, denominator and target-outcome-invariance contracts. The unmodified input files are Stage 12's full frame and the six preserved election/split files. This command creates no historical candidate predictions or scores; its synthetic fixtures remain tests only.


## Stage26 practical linkage

Run `python3 -m scripts.evidence.practical_candidate_linkage.run --construct-only` to reproduce outcome-free proposals and component/research views; full generation additionally reproduces the committed manual-review application, post-acceptance coverage/readiness and prior-data verification. `python3 -m scripts.evidence.practical_candidate_linkage.run --check` verifies all bytes without overwriting them. The manual ledger is a preserved inspection checkpoint, not generated documentary validation. Focused checks: `python3 -m unittest scripts.tests.test_practical_candidate_linkage -v`. Consumed source/raw records are stage-specific; unrelated registry additions do not break them. The prior-data snapshot supports clean/shallow checkouts. Use the committed finite aliases and contract; do not regenerate earlier effect cohorts or use outcomes to adjust linkage. No acquisition, fitting or prediction command is part of this stage.
