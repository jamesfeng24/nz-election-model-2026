## Stage49 — MMP rules and exact allocation (2026-10-06)

- Add `src/models/mmp/allocate.ts`: exact integer Sainte-Laguë allocation with 5%/electorate qualification, independent-winner deduction, overhang, list exhaustion and explicit tie flag; 26 tests including exact replay of official 2008–2023 seat tables.
- Add oracle builder `scripts/mmp/oracle.py` and `data/processed/mmp/oracle-seat-tables.json`; update the `MmpAllocation` conventions in the data dictionary. No forecast, workflow or Stage47 change.

## Stage49 — MMP rule verification checkpoint (2026-10-06)

- Preserve the Electoral Act 1993 text (version 238.0, 1 Jan 2026) under `data/raw/legislation/` and verify ss 191–193 rules against it.
- Record sourced status of the 5% threshold, one-electorate exemption, Sainte-Laguë, overhang, 120-seat house, 71-electorate/49-list-seat 2026 structure and 2025 law changes in `docs/mmp-rules-verification.md`; list items still open (statute text, independents, ties, postponed polls).
- Propose, but do not start, the `src/models/mmp` allocation-core stage. No code, data, test or workflow change.

## Stage34 — bounded post-result diagnostic

Added provenance-pinned whole-party TV/category audit, exact saved-expert common samples, per-election scatters/complete CSV, S/R and joint paired associations, equal-election robustness/baseline-relative controls, strict/chronology/observed-input sensitivities and independent arithmetic tests. No fitting or prior data changes. D066 retains S/S+R actively and recommends separately authorized dated-input readiness before any learned blend.

## Stage29 — 2026-10-03

- Preserve gate-first asymmetric-response abstentions and all earlier outputs.
- Add separately authorized central-anchor descriptive response and fixed-anchor deletion diagnostics; all anchor failures/classification changes visible.
- Add independent arithmetic, outcome-boundary/identification tests and deterministic CI checks. No acquisition, alternative model or operational change.

## Stage28 — asymmetric-response design checkpoint (2026-10-03)

- Record post-result S development preference with baseline mandatory; preserve failed historical screens and operational nulls.
- Add preserved aggregate-input/fold/provenance inventory and proposed guarded national-parity/asymmetric contract; defer unsupported personal baseline.
- Add synthetic-only classification, anchor/regime/rank, chronology and preservation tests. No historical estimation/scoring/acquisition.

# Changelog

## Stage27 — exact-geography conditional retests — 2026-10-03

- Freeze Stage25-based samples, both chronology protocols and only registered NAT/LAB / baseline-S formulations before numerical work; commit predictions before evaluation.
- Add 20/34 exact 2014/2020 general seats, preserve explicit earliest/separated abstentions and reproduce original Stage16/22 results.
- Report share/ranking, response/status, rounding/influence and original-versus-expanded training diagnostics; all-fold screens fail and operational selections remain unchanged.
- Reuse Stage24 Decimal serialization transparently (2.22e−16 maximum share change), add full-adapter tests/independent arithmetic/CI checks and preserve all prior data/evidence artifacts.

## Stage25 post-checkpoint amendment — 2026-10-03

- Register expanding-window primary and inherited more-separated sensitivity with exact earlier ID selectors and training-only preprocessing contracts.
- Preserve 20/34 strict exact geography and all original separated sample IDs; make a 2014 conditional fitted comparison chronologically available without fitting it.
- Specify practical preserved-evidence candidate linkage as the next separately authorized task, keeping identity-free model interfaces independent.
- No raw evidence, prior numerical output, identity adjudication or operational selection changed.


## Unreleased — Stage 25 historical geography applicability — 2026-10-02

- Added one canonical 356-target geography layer, linking the original three comparable transitions and both preserved redistribution crosswalks with explicit predecessor and two-sided population bounds. The 2011→2014 one-sided 29 identity flags resolve to 20 strictly two-sided exact general targets; 2017→2020 has 34.
- Added separate source-pinned candidate/party/split/identity availability, 30 unfitted family/fold plans, ten stable exact-seat chains, a source-only composition audit and a bounded experiment register. No historical fit, prediction, score, source, identity adjudication or operational selection changed.
- Added focused certification, provenance, outcome-independence, chronology and sample tests, deterministic regeneration, migration guidance and a separately authorized exact-geography retest proposal.

## Unreleased — Stage 24 fixed candidate input substitution — 2026-10-02

- Froze exact Stage22 baseline/S-only fits, means, source features, shared-group mappings and 2017/2023 common IDs before calculation; reproduced saved observed-input predictions exactly and committed construction before outcome evaluation.
- Substituted Stage23 complete local party vectors without candidate refitting. The paired S-versus-baseline MAE interaction is +0.314pp in 2017 and −0.099pp in 2023; share and winner diagnostics differ, and operational selections remain null.
- Added separated evaluation, category/ranking/influence/rounding diagnostics, source-pinned manifests, mutation and arithmetic tests, and deterministic CI checks. No earlier artifact, source or identity adjudication was changed.
- Corrected post-evaluation cross-platform C/D serialization after CI exposed last-bit NumPy variation. Decimal evaluation of the same frozen formula differs by at most `2.22e−16` candidate share and changes no fit or conclusion; the original checkpoint remains in history.

## Unreleased — Stage 23 conditional complete local party vectors — 2026-10-02

- Reused preserved official party ballots, Stage5 continuity, the validated 213-seat frame and Stage21 alliance overlay to inventory every source/target party category before scoring.
- Froze and implemented a parameter-free compositional proportional construction, producing coherent local vectors for all 213 party-ballot pairs conditional on supplied target national support; entrants use an explicit neutral national profile.
- Evaluated party shares separately from construction against a flat national-vector benchmark, with full-population oracle-weight national-gap diagnostics. No exact national reconciliation, as-of forecast, candidate score or operational selection is claimed.
- Added stage-specific source checks, deterministic regeneration and synthetic tests; earlier raw sources, numerical artifacts, identity evidence and operational selections remain unchanged.

## Unreleased — Stage 17 candidate-baseline design — 2026-09-30

- Verified Stage16 PR #23 merged and pinned a preserved 71-seat target-boundary candidate/party evidence inventory with 72 official candidate-file source records and exact raw checksums.
- Compared geographic candidate transport, joint ballot routing and a direct complete candidate-share composition; proposed the identity-free direct-share baseline and chronological conditional validation contract without fitting or scoring.
- Added synthetic conservation, entrant/independent, changed-boundary, denominator, shared-scenario and outcome-independence tests. Earlier numerical outputs and operational selections remain unchanged.

## Unreleased — Stage 15 conditional candidate interval ledger — 2026-09-27

- Implemented the reviewed pooled-equality ballot ledger, separate source-seat convex-hull sensitivity, party-diagonal and unrestricted comparators on 191 held general contests, preserving the 213-contest coverage frame.
- Kept construction independent of target candidate outcomes; evaluated marginal and joint observed-vector feasibility separately. The primary ledger is wholly free in 157/191 contests and rejects the observed joint vector in all 34 partly constrained contests.
- Pinned 612 consumed source records and raw bytes; deterministic regeneration, full configured tests and prior-output preservation passed. No point score or operational coefficient was selected; this remains a conditional retrospective diagnostic.

## Unreleased — Stage10 replacement-candidate effects — 2026-09-23

- Verified Stage9 PR #16 merged, then committed/pushed the same-party party-seat pre-fit inventory and frozen replacement specification separately before diagnostics.
- Preserved 1,433 candidate comparisons with boundary, identity, tenure and source-winner uncertainty. Only 39 general source-winner continuations, and no replacement, have pre-target-supported identity on unchanged boundaries.
- Audited target/later-winner flags by rebuilding identity: no primary eligibility changes. Eight distinct-person cases rely on retrospective outcome anchors and all incoming candidates won; they remain descriptive.
- Recorded zero/carry-forward arithmetic and normalization sensitivities, with the fitted chronological comparison explicitly unavailable and operational replacement effect null. Stage5–9 numerical outputs and stage-specific source protections remain unchanged.

## Unreleased — Stage8 candidate persistence — 2026-09-23

- Started from verified merged Stage7 main and froze the Stage8 estimand, chronology, identity and operational gate before fitting.
- Preserved two official Parliament member indexes with source registry checksums; added auditable person links, unresolved identities and election-dated history/status without changing source occurrences.
- Built unchanged-boundary same-seat persistence pairs, chronological benchmark/fitted comparisons, scale and identity sensitivities and deterministic pinned outputs.
- Found descriptive selected-sample continuity but no stable fitted gain over the prior-residual benchmark; selected operational persistence coefficient remains null. No freshman-incumbency or replacement fit, Stage6 bonus, candidate transport or2026 input.
- Corrected Stage6/7 source provenance after CI exposed a whole-registry hash dependency: an immutable snapshot pins42 consumed supporting candidate records and raw bytes while unrelated source additions are accepted. Only provenance metadata changed; historical numerical outputs remain identical.
- Corrected Stage8 after PR audit: only directly anchored winner occurrences remain confirmed (169);46 projected links become probable (793 total). Outcome-independent source-anchored validation has39 general pairs (20/16/3), separate from39 target-win-selected retrospective diagnostics. The null operational selection remains; the original freeze and post-fit amendment are both recorded. No prior numerical output changed.

## 0.1.0 — 2026-09-07

- Established React, TypeScript, Vite and Vitest static application.
- Added seven responsive pages, navigation, unavailable states and unknown-route handling.
- Reserved modelling module boundaries without implementing statistical logic.
- Added versioned source provenance contracts, empty registry and synthetic metadata tests.
- Added persistent session handoff, methodology, decisions, source standard and reproducibility documentation.
- Added locked dependencies, Node pin and GitHub Actions validation.
- No political data collected; no forecast, allocation engine or deployment produced.

## Unreleased — Stage 1 workflow correction — 2026-09-07

- Created stage/01-foundation from the published foundation; all corrections are reviewable separately from main.
- Added intended statistical specification, explicit estimator constraints and fuller persistent workflow rules.
- Added data/script directory boundaries and offline Python / Web Worker architecture guidance.
- Added draft runtime schemas/types for all requested domain entities, candidate history, predictions, allocation accounting and serializable worker messages.
- Added Python 3.12.2 configuration with zero third-party dependencies, eight integrity tests and a Python CI job.
- Added source-integrity verification without downloading or changing data. No model or election data added.

- Submitted corrective PR #1: https://github.com/jamesfeng24/nz-election-model-2026/pull/1; left open and unmerged. All local gates pass (30 frontend tests, 8 Python tests, typecheck, build and source integrity).

## Stage 2 checkpoint A — recovery and ingestion infrastructure

Preserved recovered official split CSV; added immutable import/checksum-pinned fetch, CSV parsing and Unicode/missing-value tests. No statistical model added.

### Stage 2 checkpoint B
- Acquired and checksum-registered all 139 official 2008 inputs.
- Generated general-electorate results and percentage-only split matrices with national controls and a validation report.
- Preserved source name variants through explicit local mappings; exact unavailable joint counts remain null.

### Stage 2 pause handoff — 2026-09-08
- Checkpoint B pushed as 49bd2356088d6a1ed44b0bab897bee4bd218709c; no 2011/2014 work started.
- Replaced stale state claims; documented actual historical output fields, source limitations, offline reproduction, decisions and precise checkpoint C recovery instructions.
- Stage 2 is incomplete; no completion PR created. Historical PR #1 was subsequently merged by the user before Stage 2.
- Pause-handoff validation passed: 30 frontend tests, 13 Python tests, typecheck, build, 139 source hashes and exact 2008 regeneration.

## Stage 2B — sequencing checkpoint — 2026-09-08

- Verified the valid 2008 merge in main and created stage/02b-historical-2011.
- Recorded the revised 25-step sequence and froze the boundary between historical selection/weight fitting and later 2026 Opportunity/polling inputs.
- Documentation only; no data changes. 2014 remains out of scope.

## Stage 2B — 2011 complete for review

- Preserved 143 official raw resources; produced 63 general electorates, 423 candidate records, 819 party-vote records and 63 split matrices. Added three aggregate split controls and exact summary counts.
- Reused shared ingestion/parsing; retained Unicode/macrons and eight explicit local candidate-name mappings. Documented the informal-party aggregate summary convention.
- Passed 20 Python tests, all 282 source checksums, deterministic 2011 regeneration, targeted byte-identical 2008 regression, 30 frontend tests, typecheck and production build. Zero unresolved numeric reconciliation discrepancies.
- Stage 2A/2008 remains validly merged; 2014 and unified historical integration remain outstanding. Next: 2014 ingestion only. Current 2026 polling and Opportunity remain deferred until historical backtesting/weight freeze.

## Stage 2C — 2014 complete for review

- Recovered and checksum-verified 100 existing sources, pushed before further acquisition; acquired only missing split matrices 20–64 and pushed all 145 raw files.
- Processed 64 general electorates, 451 candidate records, 960 party-vote records, 64 local split matrices, three aggregate matrices and exact summary controls.
- Retained candidate affiliations and eight source-name variants; added explicit 2014-only Internet MANA split grouping. Documented the 337 informal-party summary convention.
- Reused/extracted aggregate validation, retaining the 2011 API and byte-identical 2008/2011 outputs. Twelve focused Python tests, 2014 checksums/regeneration, 30 frontend tests, typecheck/build and whitespace checks passed. No unresolved numeric discrepancies.
- Updated handoff for the next task: 2008–2014 integration and cross-year validation only. No integration, 2017 or statistical/2026 modelling performed.

## Unreleased — Stage 2D historical integration — 2026-09-08

- Confirmed 2008, 2011 and 2014 ingestion merged into main (latest merge 7e9dd53).
- Added six deterministic panel files covering 190 general electorate-years, 2,976 party records, 1,373 candidate records, 190 local split matrices and three election-control records.
- Preserved source labels, election-local identities, name mappings, rounded split percentages and exact aggregate controls. Added separately documented canonical party aliases; preserved 2014 candidate affiliations.
- Added focused cross-year mutation/lossless-projection tests and offline raw-to-panel byte verification in CI. All 31 Python tests and required frontend checks pass.
- All nine prior per-year outputs, 427 raw sources and source registry are unchanged; no new data acquired. Next authorized task should be 2017 historical election ingestion only.

## Unreleased — Stage 3A checkpoint A — 2026-09-09

- Verified PR #5 merged at f627903 and branched stage/03a-historical-2017 from current main.
- Scoped persistent reading/testing rules; removed obsolete Stage 2 branch instructions and repaired current-state wording while preserving historical decisions.
- No data, parser, frontend or model changes. Documentation whitespace validation passed; ingestion checks start with code/data checkpoints.

## Unreleased — Stage 3A checkpoint B — 2026-09-09

- Discovered 145 exact official CSV links, preserving electorate name/number associations from official indexes.
- Extended immutable import allowlist to 2017; saved 12 initial official sources with checksums and retrieval provenance.
- Identified modern percentage/rounding differences before parser implementation. Thirteen focused tests and source integrity pass. No prior processed outputs changed.

- Recovery checkpoint: preserved candidate files 52–71 that survived after the 62-source push; 82 official 2017 files now registered. Saved small modern table parsers and six passing focused tests. Remaining acquisition is only general split files 2–64; no validated full-election outputs yet.

## Unreleased — Stage 3A complete — 2026-09-10

- Recovered and pushed interrupted acquisition/parser/finalization work before continuing; all 145 official 2017 sources now preserved with exact provenance/checksums.
- Added separate modern-format table, election and split adapters. Exported 64 general electorates, 431 candidate records, 1,024 party records, 64 local split matrices, three aggregate matrices and exact national split summary.
- Reconciled all 71 candidate files and national totals. Preserved percentage units, Unicode, original affiliations, disclosure notes and unresolved person identities. No aliases or fabricated joint counts.
- All 51 Python tests, source integrity, deterministic regeneration and prior-year compatibility checks pass. Legacy parser and all prior processed bytes unchanged. CI now checks 2017 regeneration.
- Updated handoff, source coverage, data dictionary and reproducibility. No frontend changes, modelling, cross-year linking, panel extension or later-year acquisition. Next task: 2020 historical election ingestion only.

## Stage 3B acquisition checkpoint — 2026-09-10

- Confirmed merged 2017 PR #6 and branched from a151441 for 2020 only.
- Recorded 147 explicit official resources and preserved 13 representative source files with checksums.
- Verified representative modern table compatibility before bulk acquisition; no processed historical observations changed.

## Stage 3B completion — 2026-09-11

- Recovered all 147 planned originals already saved at cutoff and surviving regression tests; added one supporting official split source to resolve aggregate reporting differences.
- Completed deterministic 2020 outputs: 65 general electorates, 561 candidates, 1,105 party records, 65 local splits, three aggregates, exact national summary and one supporting Māori split.
- Preserved official affiliations with explicit aggregate-only NZ Public Party/Advance NZ reporting metadata.
- Passed 69 Python tests, 720 source checksums, modern deterministic checks and historical compatibility; all 24 prior processed files unchanged.
- No modelling, cross-election identity linking or panel extension. Next task: 2023 ingestion only.

## 2026-09-13 — Stage 3C / 2023 ingestion

- Recovered and pushed source-local joins; retained all 147 acquired official files without reacquisition.
- Added 65 general-electorate outputs (468 nominations, 1,105 party rows), supporting national controls and complete split publications.
- Represented Port Waikato cancellation explicitly; preserved Freedoms NZ constituent affiliations, source blanks and local party-label joins.
- Preserved 21 related bounded aggregate Party Vote Only reconciliation failures with exact rational intervals; no inferred allocations or widened tolerances.
- Passed 96 Python tests, source integrity and deterministic/compatibility checks; all 27 previous processed files unchanged.
- No model, person linking, boundary reconstruction or panel extension. Next: full 2008–2023 historical-panel integration and cross-year validation only, after authorization.

## 2026-09-13 — Stage 3D / full historical integration

- Extended the existing processed-input panel to six elections: 384 electorate-years, 6,210 party rows, 2,833 candidate occurrences, 383 ordinary plus one cancelled split publication.
- Replaced the 2008–2014 combined directory with 2008–2023 outputs while proving byte-identical old subsets and reconstructed manifest; all 18 per-election inputs unchanged.
- Preserved all aggregate/supporting evidence, Port Waikato cancellation, source groupings and 21 known 2023 discrepancies.
- Added six canonical alias keys for five documented name/abbreviation changes; no candidate-person or alliance linking.
- Passed 109 Python tests, source/input integrity, all-year deterministic checks, 30 frontend tests, typecheck and production build.
- No model or boundary harmonization. Next authorized task requires a new instruction: 2023→2026 boundary reconstruction only.

## Stage 4 in progress — 2026-09-14

- Expanded the existing branch scope to three independent boundary-transition baselines (2011→2014, 2017→2020, 2023→2026), with the current transition first.
- Preserved eleven official geography/population/schedule resources with checksums, including four complete HD electorate layers and 57,553 meshblock population records.
- Added strict offline polygon topology decoding, focused tests, pinned optional geometry dependencies and an explicitly incomplete deterministic acquisition audit.
- Recorded suppressed population values and geometry differences for officially unchanged seats; no population weights, synthetic votes, historical data changes or models introduced.


### Stage 4 recovered membership and population evidence

- Preserved the completed 2025 concordance and exact GeoPackage reader; acquired only the needed 2026 historical-code concordance.
- Validated all 57,553 source memberships: 57,517 direct and 36 official lineage joins; no geometry fallback.
- Added deterministic geometry/population and Schedule C disclosure-control audits, 71 passing electorate controls, and focused failure tests.
- Retained suppressed values as unavailable; documented two technical membership exceptions pending crosswalk treatment. Historical observed data and panel remain unchanged; transition weights/notional votes are still incomplete.

### Stage 4 current transition crosswalk

- Resolved both suppression exceptions as sharp feasible intervals without zero filling.
- Added 65→64 general and 7→7 Māori population crosswalk constraints, reverse composition/quality metrics, deterministic manifest and endpoint-conservation tests.
- Preserved all historical observations; older crosswalks and synthetic vote baselines remain outstanding.

## Stage4 checkpoint —2026-09-22

- Added LevelB constrained2011→2014 electoral-population reconstruction,22 coupled split parents, all71 final controls and official unchanged-seat audit.
- Added common global validation for all three transitions without modifying the two completed crosswalks or observed history.
- Added2011-on-2014 and2017-on-2020 notional party-vote enclosures with explicit numerical gaps and party-mass conservation. 2023-on-2026 party generation and finalStage4 readiness remain pending; no modelling or final PR.

- Complete 2023-on-2026 notional party-vote bounds with deterministic regeneration and party-by-party conservation; no candidate or split inference.

- Complete Stage4 three-transition crosswalks and party-vote bounds, same-boundary readiness audit, secondary availability assessment and final reproducibility checks. Preserve all observed historical outputs; no modelling.

## 2026-09-23 — Stage5

- Freeze and backtest three generic national-to-local party transformations across five historical transitions:3,773 records,53 eligible party-transition identities,25 entrants,27 exits.
- Separate primary observed evidence from conservative reconstruction robustness; retain general/Māori, party, threshold, leave-one-out, clipping and vector diagnostics.
- Preserve unresolved selection with no default; add permanent repository-first/materiality rules. No new sources, forecasts or later-stage effects.

## 2026-09-23 — Stage6

- Freeze and fit separate National/Labour party-seat delta elasticities:191 general observations each;21 descriptive Māori Labour pairs; cancelled/missing candidacies excluded.
- Add chronological, leave-one-transition-out andβ0/1 comparisons plus one parameterized Stage5 transform sensitivity pipeline. Both operational coefficients remain unresolved; descriptive fits retained.
- Preserve all prior data and Stage5 selection; no web/source acquisition, candidate-person linking or2026 forecasting.

## Stage7 — normalized candidate occurrences — 2026-09-23

- Added deterministic observed-only candidate normalization for all six historical elections:3,007 occurrences,2,674 exact eligible counterparts,2,673 leave-one-out residuals.
- Preserved333 excluded nominations and one eligible singleton with reasons; retained immutable historical IDs/labels, distinct denominators and source evidence.
- Added matched-contest references, raw additive primary residuals, proportional/odds sensitivities, coverage/scope diagnostics and pinned input/output hashes.
- Retained additive after bounded diagnostics; documented sparse-slate/Māori sensitivity and the ban on using target-outcome normalization as a forecast input.
- No person linking, persistence, boundary transport,2026 inputs or prior-output changes.

## 2026-09-26 — Complete candidate-baseline design checkpoint

Added a deterministic 213-contest input-availability inventory, proposed interval-valued ballot-accounting specification, machine-readable contracts and synthetic accounting tests. No source acquisition, model fit, historical prediction, operational selection or prior numerical output changed.
# Unreleased — Stage18 conditional candidate-share diagnostics — 2026-09-30

- Added pre-fit election-local party-group mapping inventory and 420-record/raw-byte source contract on the fixed 213-contest frame.
- Fitted one common support floor chronologically, constructed complete candidate-share vectors, then separately evaluated identical-sample uniform and restricted zero-floor comparisons.
- Recorded 171 constructed held general contests, 20 ambiguous held 2023 abstentions, 21 Māori coverage-only contests and cancelled Port Waikato. Stage5 point sensitivities abstain for incomplete full-party vectors; operational selection remains null. Preserved all earlier sources and numerical outputs.

## 2026-10-03 — Stage30 expanded normalized-residual persistence

- Froze broad/strict same-person-link/exact-geography cohorts and earlier-only construction before scoring; verified482/413 pairs with Māori separate.
- Added unrestricted identifiable regression, zero/carry/mean benchmarks, chronology/normalization sensitivity, strict common-sample comparisons and descriptive transition influence.
- Independently checked covariance/prediction/error arithmetic; preserved all earlier data and operational nulls. Prior residual beats zero consistently; fitted retention does not consistently beat carry. No acquisition, identity changes or candidate integration.

## Stage31 — 2026-10-03

- Extend the frozen complete party-vector rule to54 added exact general seats, preserving all historical artifacts.
- Apply immutable expanded Stage27 baseline/S fits across both chronology protocols and three saved rounding scenarios; construction committed before scoring.
- Report full party-vector/flat and paired four-cell candidate diagnostics, major-party errors, rankings, composition and fixed-fit influence; retain conditional limitations and operational nulls.
- Add actual-adapter leakage checks, source/phase integrity, deterministic CI and independent arithmetic. No acquisition, fitting, reconciliation repair or joint implementation.

## Stage32 — 2026-10-04

- Freeze exactly baseline/S/prior-residual/S+prior-residual complete-share restrictions, source-only direct broad/strict evidence and neutral missing contributions.
- Add reproducible complete-slate applicability, canonical common folds, training-only means/rank and full-frame coverage, with no fitting/prediction/scoring.
- Retain documented renamed-party links, separate Māori evidence and all prior artifacts/nulls. Add synthetic/actual-path independence and preservation tests; record the finite implementation/forecast roadmap.

## Stage33 — 2026-10-04

- Independently fit the four frozen complete-share restrictions and finite evidence/input/chronology/rounding branches using exact Stage32 IDs; save verified predictions before evaluation.
- Preserve numerical failures and document same-objective precision retries without changing bounds/tolerances; all56 final jobs pass independent checks.
- Report useful R-alone and mixed S+R incremental development evidence, full slates/groups/influence/winners, independent arithmetic and byte-preserved prior artifacts. Keep S provisionally preferred and all operational nulls unchanged; stop before later inputs, fallback or integration.

## Stage35 — national polling foundation/design

Added versioned496-wave polling foundation, bounded raw/reference provenance, publication-cutoff/revision/duplicate/rounding infrastructure, audited reuse decision, one frozen national joint model/benchmark and eight-case chronological evaluation contract. D067 corrects active replay interpretation without altering historical decisions/numerical outputs. No fitting, forecast score, candidate replay or operational change.

## Stage36 — isolated national polling inference/backtest

Implemented the frozen compositional national model, explicit observation/schema operators, isolated transitive dependency lock, exact-signature resumable inference, all-coordinate numerical diagnostics, paired joint support draws and pollster-balanced benchmark. Forecast archival precedes separate national evaluation. Added synthetic gradient/likelihood/cutoff tests and independent deterministic arithmetic/preservation checks. No political acquisition, candidate change/replay, fine Other allocation or operational choice. Completed findings and final check status are recorded in the Stage36 report/handoff.

Completed Stage36:26 accepted forecast cases/six data abstentions, archived before scoring; independent national score/interval checks, branch-specific output manifest, mixed benchmark findings and uncertainty/availability limitations. D069 retains national development with the average control; fine Other interface remains a separately authorized prerequisite. Final CI/PR handoff is recorded in PROJECT_STATE and GitHub.

## Stage37 — 2026-10-04

- Freeze and construct two explicit Other-allocation scenarios for eight primary national cases and independent average benchmarks; conserve every draw/explicit category.
- Preserve20 bounded official external resources; audit exact56-day ensemble/gauss references, score only supported2017/2023 point subsets and abstain for2020 missing MRI.
- Add ownership-neutral adoption criterion, independent arithmetic/provenance, focused actual-adapter tests and conditional replay handoff.
- No inference, candidate predictions/scores, prior-data changes, recalibration or operational selection.

## Stage38 — bounded external national distributions, 2026-10-05

- Freeze/reconstruct three pinned gauss56-day cases, isolated locked environment and one numerical retry budget; all first attempts accepted, no retry.
- Preserve joint draws and full-coordinate diagnostics before six-category point/proper distribution scoring; independently verify arithmetic and1,621 prior datafiles.
- Record mixed ownership-neutral development decision and separate Māori electorate polling/replay requirements, without candidate work or operational changes.

## Stage39

- Connected three cached external gauss56-day forecasts to fixed baseline/S/S+R candidates on162 complete exact-general contests, through two mass-conservingOther policies.
- Added reusable raw-national adapter, deterministic shared-draw propagation, conditional intervals, paired/context metrics, independent checks and bounded forecast-readiness roadmap.
- Recorded provisional external/S+R development preferences without rewriting any prior screen, fit, identity, numerical artifact or operational selection. No inference/acquisition/liveforecast.

## Stage40

- Added dated2026 target-frame/slate/source/identity/party/S/R readiness for all71seats, with206party assertions and explicit incomplete slates.
- Preserved finite24-resource/12-query acquisition, official dates/current roster verification, conflict/withdrawal/cutoff safeguards and reversible practical links.
- Added offline refresh/change/invalidation, readable review table, deterministic checks and independent source/geography/rounding/residual preservation audits. No fits, predictions, MCMC or operational changes.

## Stage41

- Added a pre-scoring two-sided exact/95/90 candidate-feature transport contract and fixed Stage33 S+R historical diagnostic, retaining identical complete slates and neutral fallback controls.
- Constructed coherent complete source-party vectors from one integral coupled population scenario, preserving category/source mass without imposing future national reconciliation.
- Added a separate all71-seat/206-candidate2026 readiness companion, source party-seat S inventory, focused tests, independent arithmetic and preservation checks. No new fitting, acquisition or live forecast.

## Stage42 — continuous predecessor feature transport

- Audited preserved within-seat evidence; no residential fragment party composition identified or acquired.
- Frozen unchanged Stage41 party flows and all129 complete historical general slates before fixed-fit S+R scoring.
- Implemented centered, all-predecessor party-mass S/R weighting, neutral unsupported mass and genuine-predecessor practical identity safeguards; preserved three-policy controls and strict sensitivity.
- Added separate2026 readiness, independent arithmetic, provenance/preservation, tests and bounded next-stage uncertainty handoff. No refitting/MCMC/live forecast or historical output rewrite.

## Stage43 — 2026-10-05

- Frozen, independently saved S versus S+R comparison under continuous transport; all 129 complete general slates retained.
- Reproduced Stage42 joint predictions, strict sensitivity, paired groups/rankings/margins and two declared pooling views.
- Retained joint preference with active S alternative; next remains coherent local/candidate uncertainty. No fitting, acquisition or live predictions.

## Stage44 — coherent local/candidate uncertainty, 2026-10-05

- Frozen residual inventory, earlier-only pooled projected log-ratio uncertainty and arithmetic-mean preservation around continuous S+R, without mean refitting.
- Shared national scenarios once; resumable component/composed draws and one labelled transport stress; proper scores, finite precision and independent arithmetic audit.
- Records poor major-party sharpness, dependence/parameter/reconciliation/Māori/slate limits; no calibrated probabilities, acquisition, MCMC, live forecasts or operational changes.

## Stage45 — residual-scale allocation correction

- Verified major/minor contrast heterogeneity and froze one aggregate/within uncertainty structure before scoring.
- Added earlier-only scales, interpretable synthetic priors, conditional major mean adjustment, shared dependence, resumable8000draw companions and independent arithmetic.
- Reported improved proper scores with small-group losses, conditional minor distortions, zero winner-frequency miss and unmet numerical cap; no calibrated deployment claim or mean refit.
- Preserved all previous data, coefficients, identities and operational nulls. Bounded CI cost controls remain separately identified and fully validated on the final review head.

## Stage45 bounded CI cost control — 2026-10-05

- Replace routine checkpoint pushes with local resumable commits; final review heads remain unskipped.
- Remove duplicate standalone feature-push runs; retain PR/main/manual events and cancellation of superseded same workflow/event/ref runs.
- Add one conservative Stage39 integrity path tied to actual prior full Linux evidence and complete reviewed dependency/runtime fingerprints; preserve unchanged full reconstruction commands.
- Keep every behavioural/default discovery test and all other historical gates. First revised PR and all main/manual runs are full. Semantic archival classification does not omit tests.
- Measured original Linux Stage39 construction about143s; new integrity1.697s on different local hardware, not a matched savings benchmark. No hosted measurement run or inference/cache changes.

## Stage46 — residual-tail diagnosis, 2026-10-06

- Diagnosed concentrated candidate National/Labour seat residuals and frozen one earlier-only pooled MAD Student(nu4) seat-balance correction, a matched robust Gaussian and the untouched Stage45 control, retaining every case and all other directions.
- Corrected Sobol endpoints and shared-ballot-label conditional covariance before scoring; sealed all 12 corrected 32,768-draw banks; retained original failed caches and the attempt ledger. Conditional mean quadrature misses its separate .05pp gate (maximum .73893pp); no tolerance relaxation or target-based adjustment.
- Student is not adopted (worse CRPS/energy than matched Gaussian in all 7 candidate/composed cases); retain the Stage45 Gaussian as development default (D080). No sources, national MCMC, mean refit or historical override.

## Frozen Stage45/46 CI reuse and Node 24 actions — 2026-10-06

- Add `.github/validation/frozen-pipelines.json` (seed: the successful full main run `d0fa5a66`; thereafter the newest green reachable PR or main run via the Actions API) and `scripts/validate/ci_frozen.py`: pull requests and main pushes skip only the expensive Stage45/46 construction/evaluation/verification (and Stage45 mean-audit) `--check` commands while Git proves the pipeline's import closure, referenced paths, outputs, environment and existing data unchanged; a modification runs them in full once, on its PR, and that successful PR run (like a main run) is the reference, so the merge does not replay again. Manual dispatch is always full. New sources must not be appended to `data/sources.json` (about 25 historical contracts hash it whole); use a standalone dated registry.
- Behavioural tests, other pipelines and cheap Stage45/46 checks always run. A later stage that reads a registered pipeline's cache (Stage47 reads the Stage46 bank) keeps it full until reviewed.
- Add job `timeout-minutes` (20/150), `actions: read`, and prohibit CPU/wall-time gates inside `--check`. Bump `actions/checkout` v5, `actions/setup-node` v5, `actions/setup-python` v6 (Node 24). No statistical code, output, threshold or artifact change. D081, AGENTS.md handoff section and README refresh.
- Add a guarded frontend step for `npm run check:dist` (skipped until the script exists on main).
