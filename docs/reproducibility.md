# Reproducibility and session recovery

## Fresh checkout

1. Clone the canonical GitHub repository and inspect branch, HEAD and `git status`.
2. Read AGENTS.md, PROJECT_STATE.md, DECISIONS.md, METHODOLOGY.md, DATA_SOURCES.md and docs/statistical-specification.md. Check the latest changelog and relevant schemas.
3. Use the Node version in .nvmrc and npm 10.9.2; run `npm ci` from the committed lockfile.
4. Use Python 3.12.2 (no third-party dependencies yet). Run `npm run check:all`. If results differ from PROJECT_STATE.md, investigate before major work.
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
