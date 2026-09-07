# Project state

Last updated: 2026-09-07. Canonical repository: https://github.com/jamesfeng24/nz-election-model-2026. Working branch: main. Git history identifies the exact revision.

## Objective

Build a transparent, reproducible static web application for the 2026 New Zealand general election: national support, boundary-aware electorate forecasts, candidate and split-vote effects, probabilistic seats and MMP explanations. Fresh sessions must resume from this repository alone.

## Current stage

Stage 1 — application architecture and persistent handoff complete. Stop here; later stages require explicit user authorization.

## Completed stages

- Stage 1: React/TypeScript/Vite/Vitest foundation; seven navigable pages and unknown-route handling; reserved model modules; source metadata validation and empty registry; reproducibility, architecture and handoff documentation; locked dependencies and CI.

## Important files

- AGENTS.md: mandatory persistent rules.
- DECISIONS.md: architecture choices and rationale.
- METHODOLOGY.md: intended scope and safeguards; no implemented statistical methods.
- DATA_SOURCES.md: mandatory external-data provenance standard.
- docs/data-dictionary.md: current contracts and deferred domain schemas.
- docs/architecture.md, docs/reproducibility.md, docs/future-work.md: boundaries, recovery workflow and proposed sequence.
- src/app/App.tsx, src/app/pages.ts, src/styles.css: website shell.
- src/types/contracts.ts: source metadata schemas and availability type.
- data/sources.json: empty real source registry; data/raw and data/processed contain guidance only.
- src/models/*/README.md: reserved module responsibilities.
- package.json, package-lock.json, .nvmrc, vite.config.ts, tsconfig.json: reproducible tooling.
- .github/workflows/ci.yml: automated stage gates.

## Verification status

Local verification on 2026-09-07, Node 22.17.0 / npm 10.9.2:

- `npm run test`: PASS, 19 tests in 2 files (all routes, navigation, missing route and source contracts).
- `npm run typecheck`: PASS.
- `npm run build`: PASS; generated static dist/ output (not committed).
- Local dev server starts successfully.
- Visual browser inspection: NOT COMPLETED. Browser tool could not verify its admin-enforced security policy and denied localhost access. No security workaround attempted. Unit rendering tests passed; visual/mobile inspection remains a follow-up check.
- GitHub Actions configured; remote CI result is separate from the local checks above.

## Known problems and operational notes

No known test, type or build errors. This machine's npm configuration points at an unavailable local proxy; dependency installation succeeded using per-command `--proxy=null --https-proxy=null`. No user-wide configuration was changed. Normal environments should use `npm ci`; only apply the override if the same proxy issue occurs.

Cloudflare deployment is not configured or performed. Deep-link refresh must be verified when deployed. Code licence remains an explicit maintainer decision. Domain schemas are deliberately deferred, not implied by the source metadata contract.

## Data limitations

No external election data, polls, boundary files, candidate records or processed datasets exist. No electoral rules have been verified for implementation. Source metadata fixtures are synthetic and appear only in tests. No forecast can be produced from this stage.

## Modelling components completed

None. Infrastructure contracts and empty module boundaries only.

## Modelling components outstanding

Polling aggregation and pollster effects; 2023 reconstruction on 2026 boundaries; every electorate model; party/candidate/split-ticket evidence; National/Labour resilience; national-environment normalization; first-term incumbency; replacement effects; separate Opportunity treatment; regressions and diagnostics; joint probabilistic simulation; qualification, Sainte-Laguë, list MPs and overhangs; calibration and electorate explanations.

## Exact recommended next task

After explicit authorization: **Stage 2 — inventory authoritative data sources and design domain schemas. Read the required handoff documents, identify source candidates and access/licensing limitations, specify party/candidate/electorate identifiers and boundary vintages, propose poll and vote observation contracts with units, missingness and validation rules, and record decisions. Do not download election datasets, fit statistical models or implement MMP allocation unless separately authorized. Update the handoff documents, run all checks, commit and push, then stop.**

If the previous session was interrupted during publication, first inspect `git status` and compare HEAD to origin/main; push the existing stage-1 commit if needed rather than rebuilding it. No local files outside this repository are needed to resume.
