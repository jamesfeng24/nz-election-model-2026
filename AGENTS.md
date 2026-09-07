# Persistent project rules

- GitHub (`jamesfeng24/nz-election-model-2026`) is the canonical project state. Local conversations are not a source of truth.
- Before major work, read PROJECT_STATE.md, DECISIONS.md, METHODOLOGY.md and DATA_SOURCES.md; then relevant docs and code. Inspect git status and synchronize safely before editing. Preserve other contributors' work.
- Preserve raw source data unchanged. Record provenance and checksums before processing.
- Processed datasets must be reproducible through documented scripts.
- Do not invent missing political or statistical data. Synthetic fixtures must be explicitly labelled and kept out of application results.
- Expose uncertainty rather than fake precision. Missing values are not zero.
- Avoid double-counting overlapping statistical effects. Record each effect's estimand and dependencies.
- Keep a static/client-side architecture: React, TypeScript, Vite, Vitest; no backend or database.
- Run `npm run test`, `npm run typecheck` and `npm run build` before completing a stage. Fix failures or record precise blockers; never claim unrun checks passed.
- Commit and push meaningful progress. Verify the remote contains the commit; never force-push shared history.
- Update PROJECT_STATE.md at the end of every stage, including exact next task and check status. Update decisions, methodology, sources and changelog when affected.
- Do not start later stages unless explicitly asked. Current authorized scope is recorded in PROJECT_STATE.md; never infer permission for later stages.
- When interrupted, record incomplete work, commands, branch, blockers and next action in PROJECT_STATE.md. A fresh session must resume from files alone.

## Branch and stage workflow

Before major work fetch/pull latest main, confirm the remote is `jamesfeng24/nz-election-model-2026`, and inspect the working tree. Create the user-specified stage branch before editing; Stage 2 uses existing `stage/02-historical-2008-2014`. Work only on that branch. Commit and push meaningful checkpoints periodically, not only at the end. Open a pull request into main at completion; never merge it yourself or publish directly to main. Preserve the historical initial foundation commit already on main; do not rewrite shared history to simulate compliance.

Read `docs/statistical-specification.md` as a fifth mandatory document before major work. Update PROJECT_STATE.md **before the final commit**, recording current/last branch, important commits and PRs, material files, all check results, datasets, limitations and exact next task. Update DATA_SOURCES.md, DECISIONS.md and CHANGELOG.md each stage, including an explicit no-data-change note where applicable.

Python is allowed offline only. Keep dependencies reproducible and minimal; run relevant Python tests as well as frontend tests, typecheck and build. Export required website artifacts to versioned JSON/GeoJSON. Keep eventual Monte Carlo code independent of the DOM and serializable for Web Worker execution. Stage 2 authorizes only 2008/2011/2014 historical ingestion, normalization and validation, not regressions or forecasts.
