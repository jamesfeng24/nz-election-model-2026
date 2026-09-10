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

## Decision metadata for D001–D005

All five decisions originated in Stage 1 on 2026-09-07. D001 is a standing stack constraint; backend/database alternatives were excluded by the user. D002 is a revisitable architecture choice; hash routing and separate page modules were alternatives, but clean URLs and the small shared shell keep the foundation simple. D003's domain-contract deferral is superseded by D006. D004 is a standing reproducibility requirement; chat-only handoff and unpinned installs were rejected. D005 remains unresolved pending a maintainer licence choice; unilaterally selecting MIT or another licence was rejected. None is an empirically fitted statistical decision.

## D006 — Stage 1 correction / 2026-09-07 — Domain contracts now

Decision: add versioned domain schemas/types without observations or algorithms, superseding D003's domain-schema deferral. Rationale: a fresh session needs explicit shared contracts. Alternative: continue deferring all domain definitions; rejected by the expanded stage instructions. Status: provisional interfaces, subject to evidence-led schema revisions; statistical specifications and weights remain subject to backtesting.

## D007 — Stage 1 correction / 2026-09-07 — Offline Python, serializable browser inputs

Decision: pin Python 3.12.2, use only its standard library for foundation checks, and declare an empty dependency set. Add pinned third-party packages and a lockfile only when needed. Export JSON/GeoJSON; keep eventual TypeScript Monte Carlo inputs/outputs serializable for a module Web Worker. Rationale: reproducibility without unused scientific packages or a deployed Python service. Alternatives: installing the full research stack now or executing Python in production; rejected as unnecessary. Status: standing runtime boundary; package choices revisitable when research begins.

## D008 — Stage 1 correction / 2026-09-07 — Preserve existing module names

Decision: retain src/app, src/models and colocated tests; add src/components and src/data boundaries plus the requested data/script subdirectories. Rationale: exact names were flexible and moving working files adds no capability. Alternative: mechanically rename all directories to the example tree. Status: revisitable architecture choice, not subject to statistical backtesting.

## D009 — Stage 1 correction / 2026-09-07 — Independent estimators and evidence-led combination

Decision: preserve independent split-ticket, elasticity and normalized-premium predictions and learn final weights out of sample. Rationale: correlated bonuses can double count personal vote. Alternative: hand-tuned weights or stacked bonuses; excluded by the project instructions. Status: independence and evidence requirement are standing constraints; estimands, normalizations and fitted weights are subject to historical backtesting.

## D010 — Stage 1 correction / 2026-09-07 — Corrective PR, no history rewrite

Decision: branch from current main and submit only missing foundation work through stage/01-foundation. Rationale: initial commit 9eed984 already exists on main; the corrective PR cannot retroactively represent it as unmerged. Alternatives: reverting main or force-rewriting history; not requested. Status: permanent historical record. All new work stays on the stage branch and the PR must remain unmerged.

## D011 — 2026-09-08 — Historical evidence without inferred cell counts

Stage 2 authorizes authoritative observations, superseding D003's empty-register instruction for this stage. Store immutable raw CSVs, exact provenance and deterministic JSON. The 2008 split source publishes rounded percentages only: retain percentages and null joint counts, with rounding-bounded reconciliation. Do not manufacture exact cells. Use all 70 electorate candidate files for national controls but export the requested 63 general electorates.

## D012 — 2026-09-08 — Local occurrence identities and source variants

Use election-local candidate occurrence IDs; leave personId null. Preserve source full/display names and Unicode. Seven 2008 split/candidate name variants are explicitly joined within the same electorate using unique party candidature and independently reconciled overall vote share; record each mapping. This is not cross-election identity verification. Keep historical ingestion exports separate from provisional model schemas until consumer integration is reviewed.

## D013 — 2026-09-08 — Pause after saved 2008 checkpoint

User requested a stop for usage conservation after work already completed at B. Push B and a separate current-state documentation handoff; do not begin 2011/2014 or open a Stage 2 completion PR. Resume only when authorized. Checkpoints C/D/E and final PR remain outstanding.

## D014 — 2026-09-08 — Historical selection before 2026 inputs

Adopt the 25-step sequence in docs/future-work.md. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Freeze the historical backtesting design and ensemble weights before Opportunity-specific modelling or current 2026 polling ingestion. Each later task requires explicit authorization. This supersedes prior broad Stage 2 sequencing and D013's pause: 2008 is merged through PR #2; authorize only 2011 on stage/02b-historical-2011, followed by an unmerged PR. No data or fitted model changes in this checkpoint.

## D015 — 2026-09-08 — Preserve 2011 aggregate evidence and source conventions

Reuse the 2008 pipeline and append 2011 aggregate controls without changing 2008 output schemas/bytes. Preserve exact published aggregate split/non-split summary counts separately from rounded local and aggregate matrix percentages. Validate local-to-general intervals rather than infer exact cells. The official summary's informal-party non-split value matches Party Vote Only, not Candidate Informals; retain and flag it rather than relabel raw evidence. Eight 2011 local candidate-name variants are mapped explicitly with same-electorate party/vote evidence; cross-election identity remains deferred.

## D016 — 2026-09-08 — 2014 source grouping without affiliation replacement

The official 2014 split reports group Internet Party and MANA Movement candidatures under Internet MANA, while candidate-result tables and national candidate controls distinguish them. Preserve those original affiliations and use an explicit 2014-only mapping for split joins and aggregate checks; expose the grouping in processed metadata. Reuse the 2011 control algorithm with publication-specific electorate counts and grouping, retaining byte-identical prior-year exports. This is source-format reconciliation, not political continuity or modelling.

## D017 — 2026-09-08 — Lossless historical panel and conservative party identity

Build the 2008–2014 panel from validated per-year JSON, retaining election-specific electorate/candidate occurrence identities and existing source fields. Keep it separate from provisional model-facing TypeScript contracts. Add canonicalPartyId without overwriting partyKey or official labels: Conservative Party/Conservative and Mana/MANA Movement are documented name changes (Electoral Commission 2014 report, paragraph 187; citation in DATA_SOURCES.md). Independent remains a category with null party ID. Internet MANA remains distinct from its constituent candidate affiliations. Do not infer other organizational or cross-election person equivalences. Preserve 2008 uncollected aggregate controls as explicit null/not-collected and 2011/2014 controls unchanged. No raw/per-year data changes; no modelling or new source acquisition.

## D018 — 2026-09-09 — Source-format-specific modern election adapter

2017 descriptive statistics CSVs retain several older concepts but change candidate share units to percentages, round turnout rates to two decimals, and add publication-specific section/summary rows. Keep legacy historical.py unchanged. Use modern_tables.py for small pure table parsers, modern_election.py for 2017 orchestration/reconciliation, and modern_split.py for rounded matrices/exact summary controls. Reuse only generic Unicode/count/key/ratio/split parsing helpers. No assumption that 2020/2023 formats match until their authorized inspection. Candidate/person continuity and panel integration remain deferred.
