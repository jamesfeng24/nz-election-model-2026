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
- Do not start later stages unless explicitly asked. Stage 1 authorizes architecture, contracts, documentation and shell only.
- When interrupted, record incomplete work, commands, branch, blockers and next action in PROJECT_STATE.md. A fresh session must resume from files alone.
