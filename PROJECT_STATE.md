# Project state

Updated 2026-09-07. GitHub is canonical: https://github.com/jamesfeng24/nz-election-model-2026.

## Objective and current stage

Build a transparent, reproducible 2026 New Zealand election website: national support, all electorates on official 2026 boundaries, independent candidate estimators, normalized historical effects, joint uncertainty, MMP allocation and configurable government outcomes. A fresh session must resume from these files alone.

Stage 1 merged in 8cf0345dba83e3adb68630d1044e2839b2cf2037. Stage 2 historical ingestion authorized and in progress. Checkpoint A: immutable source import/re-fetch, initial split parser, tests and recovered source are working. B/C/D/E remain pending.

## Current/last branch and important commits/PRs

- Current branch: `stage/02-historical-2008-2014`; last branch: `main`.
- Base / original foundation: `9eed98405f6dca4ac86248c32cbf410887b1086f` (already on main).
- Pushed specification/workflow checkpoint: `015c96ffb3bff49219220115b0712fde26b231fd`.
- Domain/Python checkpoint: `38c38aaf8d8c23b13598064b8792700289501511`.
- Final handoff commit: consult the head of the PR/stage branch (a commit cannot contain its own SHA).
- PR #1: https://github.com/jamesfeng24/nz-election-model-2026/pull/1 — stage/01-foundation → main, merged by the user; verified before Stage 2.
- Initial direct-to-main publication cannot be retroactively corrected; shared history is preserved. All work in this correction uses the requested branch.

## Completed stages and material files

Stage 1 infrastructure only:

- React/TypeScript/Vite/Vitest static shell with seven routes, unavailable states and unknown-route handling: src/app, src/styles.css.
- Persistent rules and handoff: AGENTS.md, PROJECT_STATE.md, DECISIONS.md, METHODOLOGY.md, DATA_SOURCES.md, CHANGELOG.md.
- Detailed intended pipeline, independent estimators and explicit exclusions: docs/statistical-specification.md.
- Runtime provenance contracts: src/types/contracts.ts; draft domain contracts and serializable simulation message types: src/types/domain.ts; synthetic tests colocated with them.
- Contract meanings and limits: docs/data-dictionary.md. Architecture, reproducibility and backlog: docs/architecture.md, docs/reproducibility.md, docs/future-work.md.
- Reserved model boundaries: src/models/{polling,electorates,regressions,split-voting,candidate-effects,simulation,mmp}; src/components, src/data and src/utils reserve shared boundaries.
- Raw elections/polls/boundaries/candidates and processed elections/polls/electorates/split-votes/model directories; data/README.md; empty data/sources.json.
- scripts/ingest, transform, validate, analysis; read-only scripts/validate/source_files.py and eight standard-library tests in scripts/tests.
- Python 3.12.2 pin and empty third-party dependency set: .python-version, pyproject.toml. No scientific packages installed.
- Frontend locked dependencies, Node pin, check commands and separate frontend/Python CI jobs: package.json, package-lock.json, .nvmrc, .github/workflows/ci.yml.
- README includes local frontend/Python setup and future Cloudflare Pages instructions. public/ contains guidance only.

## Current test/build state

Local checks on 2026-09-07, Node 22.17.0 / npm 10.9.2 / Python 3.12.2:

- `npm run test`: PASS, 30 tests across 3 files.
- `npm run typecheck`: PASS.
- `npm run build`: PASS, static dist output ignored by Git.
- `npm run test:python`: PASS, 8 tests.
- `npm run validate:sources`: PASS, zero registered resources (not a data-coverage claim).
- `npm run check:all`: PASS; combines the above.
- `git diff --check`: PASS.
- Remote CI for implementation commit 38c38aa: frontend job passed; Python unit tests and source-integrity steps passed in run 34105472000. Final documentation-commit CI is tracked by the PR checks and is separate from these recorded results.
- Visual inspection was blocked in the original session because the browser tool could not verify its admin policy. This correction changes no UI rendering. Visual/mobile and hosted deep-link checks remain for later deployment review.

## Available datasets and data limitations

None. No election, poll, boundary, candidate or processed data collected. The real source register is empty. Synthetic metadata/count fixtures exist only in tests and are not website inputs. Electoral rules and the requested 71-electorate coverage target need official verification before implementation. No coefficients, predictions or simulation outputs exist.

## Modelling components completed

None. Draft data contracts, intended specification and validation infrastructure are not statistical models. No worker, ingestion pipeline, fitted estimator or MMP engine is implemented.

## Outstanding modelling components

2023-on-2026 reconstruction; multi-pollster national support; local party movement; independent split-ticket, elasticity and normalized-premium estimators; National/Labour resilience; personal-vote persistence; national normalization; freshman and replacement effects; separate Opportunity model; historical backtesting and learned weights; correlated uncertainty; seeded all-electorate simulation; verified qualification and exact Sainte-Laguë; list MPs, overhangs and Parliament size; configurable government combinations; calibration and transparent electorate explanations.

## Known issues and design limits

- Domain schemas are draft v1. They validate structure, not external authenticity or whole-dataset joins. Review source compatibility, fractional reconstructed counts, dynamic majority thresholds and list-order schemas before implementing those components; see the dictionary.
- No code licence selected. Data rights must be reviewed source by source.
- No Cloudflare deployment performed. Python remains offline; future website inputs must be JSON/GeoJSON. Worker messages are contracts only.
- This machine's npm proxy is unavailable; prior installation succeeded with per-command `--proxy=null --https-proxy=null`, without changing global settings.
- Local Git lacks HTTPS write credentials; checkpoints are published through the GitHub connection with identical Git trees and non-forced stage ref updates, then synchronized locally. Never expose credentials or change main to work around this.

## Exact recommended next task

After the user reviews/merges this PR and explicitly authorizes Stage 2: **Inventory authoritative data sources and review the draft domain contracts against documented source formats. Read all five mandatory documents, fetch latest main, create the user-specified Stage 2 branch, identify source candidates and access/licensing limitations, verify planned electorate/boundary coverage and electoral rule sources, and record contract amendments and validation requirements. Do not download election datasets or implement statistical/MMP models unless separately authorized. Update all stage documents, run checks, push checkpoints and open an unmerged PR.**

If publication is interrupted, first inspect git status, fetch origin, and compare the stage branch to origin/stage/01-foundation. Resume publication/PR handoff, not Stage 2. No temporary files or previous conversation are needed.

## Stage 2 recovery checkpoint A

Recovered clean local and remote stage branch, both equal current main. No modified/staged/untracked files or unpushed commits survived. Recovered one raw CSV in Downloads: 2008 Auckland Central split-vote table, imported byte-for-byte with checksum. New files: scripts/ingest/historical_sources.py, scripts/transform/historical.py, scripts/tests/test_historical.py, docs/historical-ingestion.md. Python tests: 13 pass. Next: acquire 2008 official summary/control and general-electorate CSVs, normalize and validate, then immediately push checkpoint B. Repeat 2011 (C), 2014 (D), then unified validation/docs (E) and an unmerged PR. Prior Stage 1 dataset/status text above is historical until final reconciliation.

## Stage 2 checkpoint B — 2008 complete

139 immutable official CSV resources acquired. Processed outputs contain 63 general electorates, 499 candidate records, 1,197 party-vote records and 63 percentage-only split matrices. Seven Māori electorate candidate files support national reconciliation. All totals/winners/shares and rounding-bounded split checks pass, with zero unresolved discrepancies. Seven local candidate display/full-name mappings and one truncated party header are recorded in the validation report; no cross-election identities are asserted. Next: acquire, process and validate 2011, then immediately commit/push checkpoint C; repeat for 2014 before final integration. Stage 2 remains incomplete; no PR yet.
