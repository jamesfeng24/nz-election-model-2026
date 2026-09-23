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

## D019 — 2026-09-10 — Shared modern parser with explicit election configuration

The preserved 2020 representative controls, candidate and split tables use the same modern publication layouts as 2017. Reuse modern table/split parsing and parameterize orchestration with explicit year, election/boundary identifiers and expected coverage. Keep source-specific exceptions small and evidence-based. The legacy E9 parser and all previously committed processed outputs remain unchanged; 2020 is an independent per-election export, not a panel extension.

## D020 — 2026-09-11 — 2020 aggregate split reporting group

Retain NZ Public Party as the official candidate affiliation and local split label. Māori/national aggregate split column totals reconcile when its sole candidature (1,349 votes) is grouped under Advance NZ rather than other parties. Record this as an inferred, 2020-only aggregate reporting convention with provenance; do not treat it as party continuity. Preserve and validate supporting Te Tai Tokerau split evidence separately. The source rationale is unstated. No tolerance relaxation, raw correction or exact joint-cell reconstruction is permitted.

## D021 — 2026-09-13 — Cancelled contests and 2023 split-source discrepancies

Configure Port Waikato's general-election candidate contest as cancelled and verify official markers. Retain nominations and published zeros; derived winner/majority/share/elected outcomes are null. Preserve its substantive party vote and non-behavioural local split publication. Do not substitute the by-election. Existing 2017/2020 serialized contracts remain unchanged.

2023 aggregate denominators include Port Waikato. Exact rational rounding intervals prove Party Vote Only discrepancies; retain both official values with narrowly fingerprinted unresolved discrepancies, not increased tolerances or an inferred ballot allocation. See docs/2023-split-discrepancy.md. An unexplained source difference is not a fitted effect. Freedoms NZ constituent affiliations remain unchanged; aggregate-only joins and two abbreviated party-header joins do not establish cross-year identity. Complementary overall-summary source rows retain original blanks separately from explicitly published zeros.

## D022 — 2026-09-13 — Full processed-input panel and bounded rename aliases

Extend historical_panel.py to six elections, moving the same output family to historical/2008-2023. Preserve schema-1 source records and all additional split evidence layers. Default absent candidateContestStatus to held while preserving explicit 2023 cancellation; do not backfill fields into old observations. Pin all 18 processed input hashes and prove byte-identical 2008–2014 serialized subsets plus reconstructed legacy manifest against pre-extension hashes. Integration never reparses raw CSVs; optional final regressions are separate and in-memory.

Use only official name-change/abbreviation evidence for additional canonical aliases: New Conservative/New Conservatives to existing conservative ID; Te Pāti Māori to maoriparty; NewZeal to oneparty; NZ Outdoors & Freedom Party to nzoutdoorsparty; Social Credit to democratsforsocialcredit. References and approval dates are in DATA_SOURCES.md and panel_config.py. These six keys represent five rename relationships. Original labels and keys remain unchanged; 2014 Internet MANA, 2020 Advance grouping and 2023 Freedoms NZ grouping remain source-report-specific. No TOP/Opportunity equivalence, person linking or behavioural transfer follows from an alias.

Propagate the validated 2023 source discrepancy exactly. Known publication inconsistencies are not new integration errors; altered inputs, changed discrepancy metadata and lossy projections fail. No tolerance expansion, imputation, fitting or boundary harmonization.

## D023 — 2026-09-14 — Disclosure-bounded boundary transfers

Use official exact/historical meshblock membership joins, not geometry-derived population allocations, for 2020→2025. Published suppressed electoral populations remain null with compatible integer bounds 0–5; released base-three rounded counts retain their publication value and compatible ±2 bounds (minimum 6). Condition on the preserved same-universe Schedule C target totals. Do not impose the election turnout tables' different-vintage electoral populations as source-side controls.

For an edge with bounds [L,U] and other destination cells [A,B], the sharp controlled edge interval is [max(L,C−B), min(U,C−A)]. Source outgoing weight is edge population divided by the sum of that source's edge populations. Different destinations have independent control equations, allowing sharp ratio bounds, but different weights remain coupled. Preserve those equations: marginal lower/upper endpoints cannot be independently selected or summed into a nominal matrix. No nominal population is currently necessary or introduced. These are reconstruction/disclosure bounds, not confidence intervals or fitted coefficients.

The two unchanged-seat exceptions MB4018221 (Rotorua→East Cape) and MB4019214 (Te Tai Tokerau→Tāmaki Makaurau) each remain 0–5 under available controls. Their sharp outgoing-weight maxima are 5/64501 and 5/76207 respectively. The general technical-adjustment narrative does not identify either suppressed observation as zero; do not force a zero transfer or remove its meshblock. Future notional party-vote bounds must preserve joint conservation and keep uncertainty distinct from observed data.

## D024 — 2026-09-22 — Constrained 2013 electoral-population outer feasible set

Use Level B, not a resident point proxy. Public rounded Census categories constrain U=Y+N+K+R and S=Y+N+K. The separately imputed electoral descent D lies between Y and U−N; no individual imputation is recovered. Confidential categories have bounds0..U, not the later electoral release's0..5 rule. With an unknown local roll proportion0≤r≤1, retain only necessary bounds N≤G≤U and0≤M≤D. General/Māori geographic calculation universes remain separate; do not impose a common-ratio G+M=U across their distinct published control scopes or replace final Schedule C with seat-allocation totals.

Sum independent single-destination parent bounds into edge groups. Each of22 multi-destination MB2013 parents keeps one coupled population interval, allocated among its official MB2016 descendants'2014 memberships. The published resident sum is1,827. All71 final controls are simultaneous equalities. SciPy1.16.0/HiGHS dual simplex (available in the existing environment, now pinned) solves this small transport network; certified integral vertices give sharp linear flow/source bounds and exact-rational fractional objectives give sharp outgoing-weight bounds. These are extrema of the documented **necessary-constraint outer set**, not proof that every extremum reproduces Stats NZ's unpublished calculation. No local roll ratio is supplied or estimated.

Maximum general weight width is about0.160866; maximum Māori width about0.003757. Retain informative but sometimes broad intervals, not an arbitrary midpoint. Target predecessor-share intervals use global flow extrema; the current maximum-predecessor-share enclosure is explicitly conservative. Do not independently select marginal endpoints. Party diagnostic/conservation propagation follows.

MB3166710/3166711 have published zero residents but rounding bounds0..2 and change from Invercargill/Te Tai Tonga membership to officially outside both final electoral systems. Retain their evidence separately as outside-final-universe records; do not call them observed exact zero or assign them to an invented target. Eight other source inventory units have no Census row and are outside both systems. All in-universe electorates remain covered. Official changed/unchanged report audit remains outstanding at this checkpoint.

## D025 — 2026-09-22 — Notional bounds and secondary evidence limits

Party-only synthetic reconstruction assumes uniform party composition within each source electorate, conditional on the preserved population feasible set. Deterministic McCormick branch-and-bound uses64 nodes per extremum, storing feasible attainable brackets, outer numerical bounds and solver/search gaps separately from source uncertainty. It does not publish a nominal population. The maximum2011 vote gap8.745829 is retained; direct share-gap maximum0.000428 percentage points is small relative to geographic ranges, but sub-vote extrema are not claimed. Floating-point LP feasibility is checked explicitly; this is a numerical optimization enclosure, not a recovery of unpublished microdata.

Secondary candidate/split reconstruction stops at coverage metadata: source totals and candidate-local choices do not identify within-transfer distributions, and rounded split percentages do not identify exact joint counts. No forced baseline is warranted in this stage. Preserve Port Waikato missingness and21 known source discrepancies. Readiness joins2014 source code043 Rangit?¢kei to the election label Rangitīkei using the official code and Schedule C label, without rewriting raw or observed labels.

## D026 — 2026-09-23 — Frozen Stage5 comparison, unresolved default

Freeze formulas, three observed primary transitions, two bounded robustness transitions, metrics and0.5%/1% sensitivity thresholds before scoring (b919915). Existing canonical identities only; no new organizational equivalences. General/Māori evidence remains separate. Record unresolved_between_methods with additive/proportional/log-odds retained: log-odds leads generic macro-MAE and robustness, but additive has a material general-Labour advantage and Māori temporal rankings conflict. No universal default or later-stage elasticity fitted. Quantitative evidence is in selection.json and METHODOLOGY.

## D027 — 2026-09-23 — Materiality-directed research and computation

User-authorized permanent workflow: repository/offline evidence first, then only bounded authoritative research with a precise consequential missing fact. Compare maximum downstream effect with dominant uncertainty before extending precision work. Preserve defensible bounds when further refinement is immaterial; never hide correctness failures, leakage, conservation errors or missingness. Foundational reusable statistical algorithms and validation remain worth substantial effort. Run focused checks during development and required full checks once at readiness unless failure/relevant changes justify repetition. Later elasticity should parameterize retained transforms in one pipeline, assess material sensitivity and stop when conclusions are invariant. No authorization to begin it now.

## D028 — 2026-09-23 — Party-seat elasticity, unresolved operational slopes

Freeze specification at bca87cd before coefficients: positive delta response, separate zero-intercept general-seat OLS, actual party changes, three same-boundary clusters. Candidate change is residual noise; no person linkage. Exclude cancelled/missing candidacies; Māori observations remain descriptive. One parameterized validation pipeline substitutes Stage5 predictions without changing structural fitting or Stage5 selection.

National fullβ0.736872 and Labour0.614747 are descriptive. Both fail stable chronological improvement overβ1 across holdouts/transforms; selectedBeta remains null. Preserve unresolved status rather than force bespoke coefficients. The predeclared0.25pp material-gain diagnostic is not a significance threshold. No precision refinement, bootstrap, source archaeology or later-stage effects warranted. Exact next stage: normalized candidate overperformance only.

## D029 — 2026-09-23 — Stage6 challenge audit / operational dependencies

Audit conclusion: architecture sound with minor contract changes, not numerical replacement. Stage6 is an unconditional descriptive party-seat association, not isolated causal resilience. Preserve zero-intercept results/unresolved operational slopes: common-intercept chronological diagnostics do not improve consistently, and weighting changes are immaterial. Candidate turnover may bias coefficients if correlated with party movement. Reconsider conditional response after replacement effects, before three-view integration; freeze only under later historical validation.

Elasticity is a response component requiring an explicit, defensible target-boundary candidate baseline; it is not independently deployable on2026 geography. Do not fabricate that baseline or assume dominant predecessor suffices. “Independent estimators” means separately validated complete predictive views, not statistically independent evidence or additive personal-vote bonuses. Common normalization/availability contracts and out-of-fold residual dependence are required. Stage7 can define occurrence-level normalization; one reusable person/history/status layer is a prerequisite at the start of persistence and must preserve uncertain/left-censored identities. No links/effects implemented now. See docs/audits/stage6-architecture.md and the bounded exploratory results.

## D030 — 2026-09-23 — Matched-contest leave-one-out occurrence residual

Stage7 freezes the additive descriptive scale at21dfed7: candidate share minus local party share, net of the same party/election's candidate-versus-party offset on other eligible matched contests. Separate valid-vote denominators, identical candidate/party reference seat universes and whole-contest exclusion prevent slate-coverage bias and self-normalization. Only the two-contest minimum is imposed; singleton raw premiums survive with null normalized residuals. Exact within-election affiliations only; report groupings and person identities are not inferred.

Retain additive nationally centred normalization:3/2,673 out-of-range raw references, maximum0.6583pp, no broadly systematic pathology. Preserve raw and bounded reference values separately. Proportional/log-odds sensitivity can differ materially for individual/sparse/Māori observations and remains available; do not optimize correlations or infer predictive superiority. All3,007 nominations are retained including333 excluded and one eligible singleton. References/metrics are descriptive outcomes, not candidate quality or operational bonuses. Target-election observed references/residuals must never predict that same election. Next stage is candidate persistence only, with a single reusable person/history/status layer built first when authorized. D029's target-boundary baseline and overlap constraints remain unchanged.

## D031 — 2026-09-23 — Candidate persistence unresolved operational coefficient

The Stage8 specification was frozen before fitting (`d606e0b`, pre-fit identity/selection clarification `b062f60`). Primary identity requires a unique exact source-name/affiliation/seat chain with an observed election winner corroborated by the preserved official Parliament profile; probable chains are sensitivity only and unresolved records remain explicit. Only same-seat, same-regime observed2008→2011,2014→2017,2020→2023 pairs enter primary fitting. The full-sample general slope0.850/intercept+1.423pp across69 confirmed pairs is descriptive. The prior-residual benchmark beats zero but the fitted intercept+slope worsens MAE/RMSE versus prior in2017 and2023 chronological holdouts. Alternative normalization scales and broader probable-link sensitivity do not establish a stable fitted improvement. No confirmed Māori pairs;15 probable pairs do not support a bespoke coefficient. Selected operational coefficient remains **null**. Identity confirmation is MP-selected, stable seat/party conditions can mimic person persistence, and shared references/three election clusters preclude causal or iid pair claims. Preserve Stage5/6 unresolved selections and D029's no-bonus/target-boundary requirements. Exact next stage after Stage8 review is freshman-incumbency fitting only, on separate authorization, using the shared history layer and new evidence as needed.

## D032 — 2026-09-23 — Pin consumed source records, not the mutable registry

Stage8's first source acquisition appended two unrelated records to the shared registry and exposed Stage6/7 whole-registry hash coupling. Audit confirmed the original901 records and raw bytes were unchanged; the two additions alone caused the old hash mismatch. Stage6/7 now pin an immutable snapshot of the42 supporting Māori candidate records they consume, compare each live required record exactly and verify its raw SHA-256. Valid unrelated additions pass; altered/deleted required records or raw bytes fail. The shared registry itself is restored to merged-main bytes. Only Stage6/7 provenance contracts/manifests and Stage6 `records.json.inputHashes` changed; all numerical/model outputs are preserved. See `docs/audits/stage8-source-provenance.md`. This does not change D028/D030 estimands, conclusions or operational selections.

## D033 — 2026-09-23 — Post-fit Stage8 identity and validation correction

PR #15's bounded audit found D031's pre-fit identity rule overconfirmed every occurrence in an official-profile/winner-anchored exact chain. A winner anchors only that occurrence:46 of the original215 confirmed links were not qualifying anchors, and two old primary pairs had neither occurrence a winner. Keep those46 person projections with probable occurrence identity and explicit profile/anchor provenance; confirmed169, probable793, unresolved2,045. Person existence, occurrence identity and career-history evidence are separate; six formerly assigned status rows return to unknown. This is a **post-fit correction**, not a claim that the corrected rule was frozen at `d606e0b` or `b062f60`.

The original69-pair primary holdout admitted pairs using target wins (17 of20 in2023 had the target win as sole qualifying anchor). Corrected outcome-independent validation requires a directly corroborated source winner and exact-chain target candidacy, regardless of target or later wins:39 general pairs (20/16/3), zero Māori. Target occurrence identity may remain probable; retrieval of the2026 Parliament profile is retrospective, and earlier publication timing is unknown. A separate39-pair two-direct-winner diagnostic is target-outcome-selected and cannot govern operational selection. The corrected validation cohort has descriptive slope0.640/intercept+2.355pp; fitted MAE worsens against the better simple benchmark in2017 and in the three-pair2023 holdout. No adequate outcome-independent confirmed-target or general-returnee cohort exists. Selected operational coefficient remains **null** for insufficient validation and poor fitted performance. Stage5–7 numerical outputs, Stage6/7 provenance correction, geography/normalization rules and no-bonus constraint remain unchanged. Freshman-incumbency tenure evidence and fitting require separate authorization.

## D034 — 2026-09-23 — Pre-fit freshman tenure cohort and diagnostic specification

After Stage8 merged, Stage9 acquired a bounded set of107 official Parliament profiles plus the missing former-index page and pinned each raw file in a stage-specific plan. Dated electorate/list rows from101 complete profiles and six without usable rows form a separate tenure overlay; Stage8 links and historical outputs stay frozen. Among125 comparable source-winner general recontesters,122 have unique official source-seat/date corroboration. The **pre-fit** primary cohort is32 first-ever electorate-win freshmen and61 continuous experienced incumbents, with32 explicit exclusions:10 seat switches, six interrupted/former careers, nine prior-list freshmen, four off-cycle entrants and three unresolved source-service matches. No Māori source-winner pair is linkable in the comparable set. These categories are conditional on recontesting and retrospectively available profile evidence; target winner flags and target premiums do not determine inclusion. See the committed inventory and `docs/freshman-incumbency.md`.

Freeze the Stage9 incremental-association diagnostic **after** that inventory and **before** effect fitting: equal-pair OLS `target residual = α + β×source residual + γ×first-term`, with an intercept, compared with the same fitted model without γ on identical chronological holdouts. β is internal to this Stage9 diagnostic, not a Stage8 operational coefficient. Use additive percentage-point residuals primarily; change contrast, proportional/log-odds, prior-list and off-cycle groups are sensitivities. Both-confirmed target identity is winner-selected retrospective diagnostics only. Predeclared operational gates and null-on-failure are in `specification.json`; no effect estimate had been examined when freezing this decision. Do not add γ as an independent bonus or claim causal personal-vote retention.
