# Persistent project rules

- GitHub (`jamesfeng24/nz-election-model-2026`) is the canonical project state. Local conversations are not a source of truth.
- Before every scoped task, read AGENTS.md and PROJECT_STATE.md. Read DECISIONS.md, METHODOLOGY.md, DATA_SOURCES.md and docs/statistical-specification.md before a new modelling component, at integration checkpoints, for relevant methodological/provenance questions, or when PROJECT_STATE.md directs it. Routine ingestion need not reread unchanged unrelated documents. Inspect only relevant code. Inspect git status and synchronize safely before editing. Preserve other contributors' work.
- Preserve raw source data unchanged. Record provenance and checksums before processing.
- Processed datasets must be reproducible through documented scripts.
- Do not invent missing political or statistical data. Synthetic fixtures must be explicitly labelled and kept out of application results.
- Expose uncertainty rather than fake precision. Missing values are not zero.
- Avoid double-counting overlapping statistical effects. Record each effect's estimand and dependencies.
- Keep a static/client-side architecture: React, TypeScript, Vite, Vitest; no backend or database.
- Run relevant Python tests and source/data validation for ingestion changes. Run `npm run test`, `npm run typecheck` and `npm run build` when frontend/shared TypeScript changes, at major integration/model-release checkpoints, or when explicit current task instructions require them before a PR. Do not repeat unrelated frontend checks for Python-only checkpoints. Run configured formatters/linters relevant to changed code; document unavailable tooling. Fix failures or record precise blockers; never claim unrun checks passed.
- Commit and push meaningful progress. Verify the remote contains the commit; never force-push shared history.
- Update PROJECT_STATE.md at the end of every stage, including exact next task and check status. Update decisions, methodology, sources and changelog when affected.
- Do not start later stages unless explicitly asked. Current authorized scope is recorded in PROJECT_STATE.md; never infer permission for later stages.
- When interrupted, record incomplete work, commands, branch, blockers and next action in PROJECT_STATE.md. A fresh session must resume from files alone.

## Branch and stage workflow

Before major work fetch/pull latest main, confirm the remote is `jamesfeng24/nz-election-model-2026`, and inspect the working tree. Create the user-specified branch from current main before editing, or preserve and resume an existing branch when explicitly requested. Work only on that branch. Commit and push meaningful checkpoints periodically, not only at the end. Open a pull request into main at completion; never merge it yourself or publish directly to main. Preserve the historical initial foundation commit already on main; do not rewrite shared history to simulate compliance.

Update PROJECT_STATE.md **before the final commit**, recording current/last branch, important commits and PRs, material files, all check results, datasets, limitations and exact next task. Update relevant source/handoff/changelog documentation each stage; update DECISIONS.md only for substantive decisions. Preserve historical decision records. Record no-data-change checkpoints explicitly.

Python is allowed offline only. Keep dependencies reproducible and minimal; run checks appropriate to changed code under the rules above. Commit and push small coherent checkpoints promptly, including acquisition before transformation is complete. Export required website artifacts to versioned JSON/GeoJSON. Keep eventual Monte Carlo code independent of the DOM and serializable for Web Worker execution. The user and PROJECT_STATE.md define the current authorized scope. Stop at that boundary; ingestion does not authorize regressions, forecasts or later elections.
