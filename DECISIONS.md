# Decision log

Record date, context, decision, rationale and consequences for each material change. Supersede decisions explicitly; do not erase history.

## D001 — 2026-09-07 — Static foundation

Use React + TypeScript + Vite + Vitest, with no backend or database. Cloudflare Pages is the intended host; deployment is deferred. This meets the requested stack and keeps future analytical code independent of hosting.

## D002 — 2026-09-07 — Route and model separation

Use React Router with clean URLs, a shared shell and explicit unavailable states. Reserve pure modelling modules under src/models; React must consume outputs rather than own statistical logic. Pages' SPA fallback will support deep links; verify this on deployment.

## D003 — 2026-09-07 — Contracts before observations

Use Zod for source metadata validation and inferred TypeScript types. Keep the real source register empty. Define only infrastructure contracts now; defer political observation and forecast schemas until their evidence, units and estimands can be specified. Version contracts starting at 1; document migrations for breaking changes.

## D004 — 2026-09-07 — Reproducible handoff

Commit lockfile, Node version, CI and persistent stage documents. All future processing must be scripted; all future stochastic work must record a seed and generator version. GitHub, not chat history, owns project state.

## D005 — 2026-09-07 — No assumed licence

Do not assign a licence without an explicit choice. Repository is public with open-source-style structure; code licensing remains a documented maintainer decision. Data rights must be recorded per source.
