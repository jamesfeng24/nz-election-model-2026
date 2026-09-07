# Reproducibility and session recovery

## Fresh checkout

1. Clone the canonical GitHub repository and inspect branch, HEAD and `git status`.
2. Read AGENTS.md, PROJECT_STATE.md, DECISIONS.md, METHODOLOGY.md, DATA_SOURCES.md and docs/statistical-specification.md. Check the latest changelog and relevant schemas.
3. Use the Node version in .nvmrc and npm 10.9.2; run `npm ci` from the committed lockfile.
4. Use Python 3.12.2 (no third-party dependencies yet). Run `npm run check:all`. If results differ from PROJECT_STATE.md, investigate before major work.
5. Confirm the user's authorized stage. Do not implement the backlog automatically.

## Stage close or interrupted session

Record current stage, completed/unfinished work, branch, check results, known problems, data limitations, affected files and exact next task in PROJECT_STATE.md. Update durable decisions and source/method documentation. Review `git diff --check` and `git diff`, run checks, commit and push. Work only on the user-specified stage branch; periodically push checkpoints. Verify HEAD matches that remote stage branch. Open a PR into main and record its URL before the final handoff commit; never merge it yourself. Do not push directly to main. Do not record a self-referential commit hash inside its own commit; Git history supplies the authoritative revision.

If interrupted before checks or push, say so explicitly and record the first recovery command. Never rely on local untracked files or chat summaries for handoff.

## Future data pipeline contract

Each processed dataset must document a runnable command, input source IDs and SHA-256 values, script revision, dependency versions, configuration, output paths and checksums. Identical inputs/configuration must regenerate semantically identical outputs. Keep run timestamps in metadata where they do not destabilize data checksums; explain any byte-level nondeterminism. Validate schemas, joins, missingness and relevant totals. Fail on missing inputs rather than synthesize them.

For future random runs record seed, PRNG implementation/version, draw count, model version, configuration and input revisions. Document platform-sensitive numerical tolerances. No stochastic code or processing pipeline exists yet.

## Automated checks

GitHub Actions runs locked installation, Vitest, strict TypeScript and Vite build on pushes and pull requests. Local gates use the same npm scripts. Build artifacts and node_modules are ignored; package-lock.json is tracked. Dependency upgrades must be intentional, checked and documented.

## Offline research and large inputs

Python 3.12.2 is pinned in .python-version, and pyproject.toml declares no dependencies. Standard-library tests and source-integrity checking run in a separate CI job. Once third-party packages are needed, commit exact direct/transitive versions and installation instructions before using them. Keep per-run environment metadata and export JSON/GeoJSON for the client. No pip installation is required in this stage.

Source file validation reads data/sources.json and verifies unchanged local raw bytes; it fails on missing files and never retrieves data. Large or restricted inputs may be excluded from Git only with an exact reproducible download recipe, expected checksums and rights notes. Each new source release has a separate materialization path. Validation does not authorize collection.

The configured GitHub integration can publish an identical Git tree when local Git credentials are unavailable. Record returned commit IDs, update only the stage branch with a non-forced ref update, then fetch and synchronize the local branch. Do not expose credentials or rewrite main. Commit hashes can differ from preliminary local commits; the remote commit and identical tree are canonical.
