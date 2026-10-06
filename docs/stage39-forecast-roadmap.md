# Active roadmap after Stage47 — agreed sequence and authorization boundary — 6 October 2026

Planning amendment (docs only, [D082](../DECISIONS.md)); no model, data or artifact changes. It records the sequence Corinna agreed on 2026-10-06 after reviewing the Stage47/PR54 state, so every later thread starts from the same plan. The Stage47 findings entry (Gaussian expectation repair, width attribution, Recommendation B) sits below this section and is unchanged. Each item below is one bounded question; none starts another automatically. One question per stage, frozen pre-registered design, explicit do-not list, handoff documents updated in their existing style so either Claude or ChatGPT can resume from files alone.

**Authorized now (separate bounded threads, each its own PR):** (a) PR54 engineering repair only: no statistical output, threshold, draw count, Gaussian law or saved-artifact change, and no 40→60 minute bump; (b) CI scoping plus Node 24 action bumps, merged before PR54 merges or revalidates; (c) MMP rule verification and exact allocation, DOM-free and serialisable; (d) end-to-end skeleton and export contract on labelled synthetic fixtures; (e) this roadmap. **Waits for a fixed event:** nomination snapshot, only after final nominations close (noon 8 October 2026 NZDT). **Not authorized:** everything else below, in particular the frozen balance-scale comparison, which needs separate sign-off. Merges are never done by Claude; ask Corinna first. Election day is 7 November 2026; Corinna has stated this is not a scheduling concern, so no dated critical path or minimum-publishable-product is set here.

## Sequence

1. **PR54 repair and CI scoping.** Hosted `--check` for the frozen Stage47 construction must verify sealed contracts, hashes and independent verification, with full reconstruction as an explicit manual, split or case-scoped job, not one machine-speed `process_time()` gate. The CI-scoping thread owns AGENTS.md, ci.yml, docs/ci-validation.md, README and CHANGELOG; the PR54 thread owns the Stage47 files. The failure was a hosted CPU-budget abort, not a statistical disagreement; do not rerun the unchanged workflow.
2. **MMP rules and allocation (authorized, independent of the model).** Verify from official sources and record in DATA_SOURCES: 5% party-vote threshold, electorate-seat exemption (the one-seat threshold bypass), Sainte-Laguë, overhang, Parliament size and list ordering/vacancy. Implement exact allocation with independently checked examples and edge cases in `src/models/mmp`, no DOM dependence, serialisable for Web Worker execution. Inventory question for that stage: whether the candidate layer yields named ACT/Green/TPM/NZ First electorate-winner probabilities (threshold bypass); Stage44–47 report National/Labour/other only. **Status (2026-10-06): complete in Stage49 (PR #58, D083):** rules verified against the Electoral Act text; exact allocator reproduces the six official 2008–2023 seat tables; component-party mapping, cancelled-poll by-election seat, list ordering and the 2026 ballot roster remain open; named minor-party winner output for the threshold bypass does not yet exist for 2026 (needs the post-8-October slate).
3. **Nomination snapshot, after the 8 October close.** Bounded immutable acquisition of the official published candidate lists: raw checkpoint, checksums and provenance before any transformation, dated so later withdrawals and list changes become new dated refreshes. Stage40 recorded 70 of 71 seats partial or unknown and zero complete slates. No model change, no live shares from partial slates, no biography search.
4. **Composed Monte Carlo precision, as a gate (not yet authorized).** Stage47's composed 512→1024 representative comparison fails its frozen caps (max change: mean 0.5609pp, CRPS 0.2325pp, energy 0.2117, 90% width 2.2554pp). Caps stay frozen. Before any claim that a small composed score or probability difference is settled, and before final seat-win probabilities are treated as production-ready, resolve or bound this. Engineering, not a statistical family; once authorized it can run in parallel with item 2.
5. **Frozen candidate-seat N/L balance-scale comparison (NOT authorized).** Exactly the frozen contract `docs/stage47-next-gaussian-scale-contract.md` (added by PR54; not on main until it merges): corrected Gaussian control, one earlier-trained constant adjustment, one strongly pooled conditional adjustment on R-support deficit and continuous historical non-major support. Question: is the candidate balance scale globally too conservative, and is any heteroskedasticity predictable from pre-result information? Constant beats control: global overconservatism. Conditional beats constant: predictable heteroskedasticity. Constant only: simpler recalibration. Neither: do not force narrowing. Report against the item-4 precision limit. No replacement effects, manual intervention or new challenger. Needs Corinna's separate sign-off.
6. **Replacement/incumbency transition dataset (not yet authorized).** Question: is neutral R for an ordinary same-party replacement right? Current treatment: S may transfer, outgoing personal R does not, incoming candidate with no history gets neutral centred R. Stage10 supports only 5 clean primary replacements (Coromandel 2011, Manurewa 2011, Helensville 2017, Rangitīkei 2023, Rongotai 2023), 4 by-election successors (Botany, Mana, Mt Albert, Tauranga) and a Hutt South alias diagnostic; its descriptive −6.64pp shift stays undeployed and `selectedOperationalReplacementEffectPP = null` is unchanged. Stage10 also recorded 61 apparent candidate-name changes (13 in 2008→2011, 21 in 2014→2017, 27 in 2020→2023). **These are not 61 replacements**: they need identity classification (retirement, resignation/by-election, deselection, party change, boundary complication, unusual third-party environment, alias/unresolved). Then build the National/Labour incumbent→successor table (seat, party, outgoing, incoming, R_old, R_new, transition type) across all adjacent elections and test R_new = a + ρ R_old + ε: neutral on average? systematic negative mean? partial transfer? does it reduce candidate-balance variance? An ordinary Nat/Lab retirement is not automatically a manual adjustment.
7. **Historical manual-intervention replay at the voting-open cutoff (required stage, sequenced after item 6, not now; not yet authorized).** Corinna: it should be tested, but now is not the time given everything else; it is not dropped, and its start is confirmed after item 6. Replays the human judgement layer on past elections. For each historical final forecast, a dossier restricted to information available just before voting first becomes legally available (earliest ballot, including overseas voting if first), result and preferably model residual hidden; Corinna records intervene/no-intervene, direction, approximate size and rationale; decisions frozen; then reveal and score. Adjust the point forecast where possible, not merely drop the seat. This cutoff differs deliberately from the T−56 cutoff of the automated tests (for example Dunne's 2017 retirement postdates T−56 but would be known at voting open). The history is development evidence, not pristine out-of-sample, because some misses were already discussed; freeze the procedure before 2026.
8. **Later, each separately authorized:** live 2026 national poll ingestion and fit (cycle bias per the Stage35 design); electorate polls and by-elections; final rosters; Māori baseline and electorate polling; national reconciliation with turnout/denominators; MMP/coalition/overhang assembly; static publication/archive.

## Three final outputs

(A) automatic model, untouched; (B) model + James, after dated, sourced, subjective manual adjustments; (C) ordinary-seat automatic calibration set: historical automatic forecasts restricted to seats the replayed manual procedure would have left untouched, the candidate population for ordinary-seat sigma. Always preserve A beside B. A manually flagged seat does not inherit the narrower ordinary-seat sigma unless direct evidence supports it. After 2026 score A, B and A-on-untouched-seats. Persistent structure (S, R, Epsom-type tactics, stable non-major support, ordinary national/local movement, possibly ordinary replacement) belongs in the model; new current-cycle discontinuities (new major challenger, third-party incumbent retirement, new or collapsed electorate deal, scandal, prominence change, targeting, electorate polls) belong to the dated human or measurement layer. Evidence is sourced and dated; the judgement of whether, which way and how much is explicitly Corinna's. No candidate-quality score.

## Do not reopen without a specific result pointing back

Student-t, mixtures, latent regimes, arbitrary sigma shrinkage, broad predictor fishing, geography fragmentation, new covariance fitting, automatic S resets, generic candidate-quality scores, repeated reconstruction of frozen stages, and **historical-backtest national MCMC reruns**. This does not forbid the live 2026 national poll fit in item 8, which is a new current-cycle estimate when separately authorized. Do not rerun, regenerate or revalidate frozen stages whose code, consumed inputs, artifacts and hashes are unchanged.

## Recorded limitations and open decisions

- **Horizon.** Candidate and composed calibration use 56-day cases (Stages 39, 46, 47). At publication the live forecast is about 32 days out and tightens toward election day. The 56-day scales are probably conservative for a late forecast, but this is unmeasured: record it, do not adjust, and do not claim horizon-calibrated intervals.
- **Māori seats.** All seven have roster/geography records only; no baseline, poll layer or candidate model (Stage40), and MMP overhang depends on them. Required fallback if electorate polls are sparse: an explicitly labelled unpolled baseline with wide, stale-aware uncertainty. National Te Pāti Māori party support remains a distinct quantity. Not implemented or authorized here.
- **Probability-release policy: OPEN.** Every Stage44–47 record calls probabilities uncalibrated and not operational. No decision yet defines what the site may show (win probabilities, ranges, seat bands, disclaimers) or the gate that permits it. It must address calibration, sharpness, item-4 precision, omitted uncertainty and the three outputs, and be decided before any publication, not after. Corinna decides.
- **End-to-end skeleton and export contract (authorized).** One dry run polls → national draws → local party → candidate → MMP → static site, on explicitly labelled synthetic fixtures kept out of application results, to fix the versioned JSON/GeoJSON export schema, archive/snapshot format and Web Worker boundary before real components land. It produces no real forecast and fits nothing.

Earlier roadmaps remain historical records below.

---

# Active roadmap after Stage46 — 6 October 2026

The bounded central/tail comparison is complete. Retain Stage45 Gaussian development default; matched robust Gaussian remains a diagnostic, Studentnu4 is not adopted. Preserve S+R mean preference, S active/baseline mandatory and externalgauss provisional. No mean-model tournament or further uncertainty family starts automatically. [Stage46 assessment](stage46-development-assessment.md).

Before deployment, separately resolve the documented numerical conditional-mean preservation gap; passing representative simulation doubling does not certify this. Keep calibration/omitted uncertainty limits explicit. Remaining practical tasks: official nomination/slate refresh; an explicit Māori-seat baseline and noisy electorate-poll measurement layer; full-population turnout/valid-vote denominators and reconciliation; dated manual-adjustment interface; coherent MMP and static publication/archive assembly. None is implemented or authorized by this roadmap. Māori candidate polling is distinct from national Te Pāti Māori support and retains question, denominator, dates, sample and dependence. Manual evidence preserves both adjusted and unadjusted forecasts, never retrospectively cleans the residual sample.

Earlier roadmaps remain historical records below.

---

# Active Stage45 uncertainty handoff — 2026-10-05

Carry the aggregate/within residual allocation forward for development, preserving original Stage44 as control. Proper scores improve materially; numerical cap, conditional minor distortion, zero finite-bank winner miss, few reused environments and omitted components prevent a calibrated-probability claim. External gauss provisional, continuous S+R preferred/S active/baseline mandatory unchanged. No new family or mean search follows automatically.

Next separately bounded implementation: official nomination refresh from bulk publication, then Māori baseline/electorate-poll integration with candidate/local-party question, denominator, dates, sample, dependence and stale/unpolled fallback. National Te Pāti Māori support remains distinct from Māori candidate votes. All-population reconciliation/turnout and denominator decisions, adequate numerical integration, then MMP/live assembly remain explicit dependencies. No live partial slate is normalized.

Local commits now provide resumable checkpoints; do not assume unpushed work is on GitHub. Full final review-head Ubuntu validation and main verification remain required. Dependency-aware CI integrity is distinct from archived Linux reproduction. No scheduled cost-consuming workflow or automatic next-stage acquisition.

---

# Active roadmap after Stage44

One pooled coherent uncertainty implementation is complete around continuous S+R and cached externalgauss. Retain S+R preferred, S active and baseline mandatory; no mean-model search/refit. Its major-party intervals are too broad for a calibration claim; keep the versioned development scenario, the reported proper scores and finite precision rather than declaring operational probabilities. No automatic variance-family search follows.

1. **Bounded official nomination refresh** after bulk publication, preserving dated snapshots, incomplete slates, withdrawals/conflicts and source-only histories. No live shares from partial slates.
2. **Separately authorized Māori baseline/electorate-polling layer:** candidate/local-party question, denominator, boundary/candidate mapping, fieldwork/publication, sample/undecideds, age, uncertainty and dependence; explicit unpolled/stale fallback. National Te Pāti Māori party support remains distinct. General coefficients/error scales are not automatically extended.
3. **National reconciliation and denominator/turnout decisions:** complete electoral population and defensible weights, shared national error once and coherent local/candidate dependence. Explicitly decide probability readiness given Stage44 sharpness, omitted parameter/scale uncertainty, cross-layer approximation and finite draw precision; no unrequested model tournament.
4. **Final MMP/live assembly and publication archives**, only after input and probability-readiness requirements are resolved. Expected shares average transformed shared draws; scenarios/feasible bounds are not calibrated distributions.

This records remaining dependencies, not authorization to begin them. Stage44 [findings](stage44-uncertainty-findings.md) preserve component, substitution and end-to-end evidence distinctions. Earlier roadmap sections below are historical; all earlier decisions/results/operational nulls remain unchanged.

---

# Active roadmap after Stage43

The bounded continuous-transport S versus S+R comparison is complete. Retain S+R preferred, S active and baseline mandatory: joint gains in 2014 and modest pooled MAE/RMSE, but loses share accuracy in 2020. Strict linkage does not reverse that trade-off. No further mean-model experiment is automatically authorized. External gauss remains provisional; earlier screens/operational records remain unchanged.

1. Separately authorize one coherent local-party/candidate uncertainty implementation around continuous transport and the retained mean preference. Propagate shared national error once, distinguish local-party/candidate/transport/parameter/feature assumptions from calibrated uncertainty.
2. Bounded official nomination refresh, preserving dated snapshots, withdrawals/conflicts and incomplete slates.
3. Separately implement Māori candidate/local-party polling and explicit unpolled/stale baseline, preserving question, denominator, boundary/candidate mapping, dates, sample and dependence. National Te Pāti Māori party support remains a distinct quantity; no automatic general-coefficient extension.
4. National reconciliation with complete turnout/valid-vote weights, then coherent MMP simulations and dated static forecast archives.

These remain separately authorized dependencies. Component validation, input substitution and end-to-end replay remain distinct; expected shares average transformed shared draws. The Stage42 roadmap below is retained as history; this bounded comparison superseded its proposed immediate uncertainty stage.

---

# Active forecast roadmap after Stage42

Stage42 audit/continuous transport is complete: preferred continuous mean-feature scenario, frozenStage41/exact controls preserved, fragment party composition unobserved. No further mean-feature or threshold search is planned. External gauss provisional, S+Rpreferred/Sactive/baseline mandatory; earlier operational records unchanged.

1. Separately authorize coherent joint local-party/candidate uncertainty around existing national/party/candidate adapters: shared national error once; uniform population-to-vote allocation and continuous feature transport; local/candidate residual dependence, missing-history and parameter assumptions; distinguish assumed from empirically calibrated uncertainty.
2. Bounded official nomination refresh, preserving prior snapshots, withdrawals/conflicts and complete/incomplete slate distinction. Current206candidate snapshot is not final.
3. Separately design/ingest Māori candidate/local-party electorate polls with the actual question, denominator, fieldwork/publication dates, sample uncertainty, candidate/boundary mapping and dependence; explicit unpolled/stale-seat baseline. National TPM party support is a distinct quantity; general coefficients are not automatically applied.
4. National reconciliation and complete turnout/valid-denominator weights, then MMP simulations/static forecast archives with dated assumptions. Nonlinear expected shares average transformed shared draws, never duplicate national uncertainty.

This roadmap authorizes none of these subsequent implementations. Preserve component validation, input substitution and end-to-end replay as distinct evidence layers.

---

# Active roadmap after Stage41

Stage41 supplies one feasible complete source-party geography scenario for all71 current targets and graded source S/R reuse: exact, guaranteed two-sided95, broader90 and neutral fallback. It preserves Stage40's exact-only snapshot as history. The historical fixed-fit diagnostic supports retaining the broader development scenario with material seat-level losses and additional uncertainty, not calibrated transport. [Contract](stage41-transport-specification.md); [findings](stage41-transport-findings.md).

**Next bounded implementation:** coherent joint local-party/candidate uncertainty around the existing national-to-local and complete-share adapters. Shared national error enters once. Represent local-party/candidate residual dependence, fixed-fit parameter uncertainty, incomplete identity/history, fine-party allocation and source-to-target transport assumptions. Overlap is not candidate-error variance; distinguish assumed distributions from historical calibration. This is not another mean-model or threshold search.

Official bulk nomination refresh after publication and the separately planned Māori electorate-poll/unpolled-seat baseline remain bounded input tasks. National Te Pāti Māori support is distinct from Māori candidate support; retain actual poll question, denominator, fieldwork/publication, sample and dependence. Then national reconciliation with all-seat turnout/valid-vote weights, MMP shared simulations and archived static outputs. External gauss provisional; S+R preferred, S active, baseline mandatory. No subsequent implementation is authorized by Stage41.

The prior roadmap below is retained as history; Stage40's exact-only transport gap is addressed by the labelled Stage41 companion.

# Active roadmap after Stage40

Stage40 delivers the dated 2026 boundary/slate foundation, all71 seats, source-only feature readiness, conflict checks and a reproducible refresh path. The source snapshot closes5October before nominationclose8October; zero slates are complete. Refresh official bulk nominations after publication, without carrying incumbent MPs into unverified seats or reopening biography queues. [Readiness report](stage40-target-boundary-slate-readiness.md).

**Next bounded implementation:** coherent joint local-party/candidate uncertainty around the existing complete-share adapters. Keep shared national error once, make local/candidate residual dependence and parameter/identity/fallback/transport uncertainty explicit, and separate assumed uncertainty from validated calibration. This is not another mean-model tournament. General exact evidence can inform the layer; changed-boundary and Māori gaps remain explicit rather than silently transported. No implementation begins under Stage40.

Then separately design/implement the Māori electorate-poll layer with its explicit Māori baseline, candidate/local-party question and denominator, dates/age/sample/undecideds, poll error/dependence, and documented wider unpolled/stale fallback. National TPM party support is a different quantity. National reconciliation requires all electorates, supplied turnout/valid-vote weights and distinct party/candidate denominators. Finally MMP shared simulations, static versioned outputs and forecast publication/archive. Externalgauss provisional; S+Rpreferred/Sactive/baselinecontrol; prior screens/operational nulls remain.

The prior Stage39 dependency record below is retained as history; its target/slate task is now completed, with ongoing dated refresh as an input-maintenance dependency.

# Practical forecast dependencies after Stage39

Stage39 connects cached external national draws to fixed complete-share candidates; it does not supply a working live forecast or calibrated local uncertainty. External gauss provisional, ownednational cache fallback/averagecontrol; S+Rdevelopmentpreferred/Sactive/baselinecontrol. Preserve prior evidence independently of these preferences.

## Next bounded implementation:2026boundary/slate readiness adapter

Use preserved `data/processed/boundaries/2023-2026/{crosswalk,party-votes}.json` and their input/bounds contracts, original2023occurrences, accepted linkage evidence and complete-group mappings. Do not call population or synthetic party-vote geography a reconstructed candidate baseline. Build every target seat's explicit source relationships, exact-versus-bounded geography, known/unknown candidate slate and national-to-local group keys. A dated, finite official nomination/registration source plan may be separately authorized for current candidates; no broad biography search or outcome-selected replacement audit.

Deliver machine-readable readiness records and synthetic usable-slate fixtures for ordinary, shared-group, unsupportedentrant, no-group and unknown-slot cases. Unknown candidates need explicit status/scenario slots and cannot silently become absent. Never apply outgoing residuals to replacements or transfer personal residuals across unsupported geography. A candidate may have party-seatS without personalR; missing histories retain neutral contributions. Freeze any source-S/geographic portability rules before live predictions. This is a concrete adapter/source inventory deliverable, not a new model-family search.

## Ordered remaining dependencies, separately authorized

1. **2026target-boundary/slate readiness:** the bounded adapter above; latest national input readiness stays distinct from retrospectivepoll archives. No liveforecast now.
2. **Coherent local/candidate uncertainty:** design shared local/candidate errors around the complete-share family, separated from national uncertainty already propagated. Include parameter/identity/fallback and changed-boundary uncertainty where applicable. Failed means do not establish variance effects; assumed and calibrated uncertainty must be distinguished.
3. **Māori electorate polls and unpolled baseline:** nationalTPM party-vote support differs from candidate vote. Preserve question(candidate/localparty/both), denominator, fieldwork/publication, sample, age,undecideds and uncertainty. Combine noisy polls with explicit Māori-seat baseline, slate/identity and dependence; retain wider unpolled/stale fallback. No polls acquired/implemented in Stage39.
4. **National reconciliation and turnout/denominators:** the existing affinity rule is locally coherent but not nationally reconciled. Declare full general+Māori electoral population/weights, valid-party versus valid-candidate and invalid/turnout assumptions. Do not reconcile a selected exact-seat subset or duplicate common national error.
5. **MMP allocation/publication:** coherent shared simulations, dated raw/adjusted exceptional-seat evidence/rationale/uncertainty, static-client JSON and prospective forecast archive. Nonlinear expected candidate shares average transformed draws; draw winner frequencies are not calibrated without a validated full uncertainty layer.

Component evidence, fixed-fit substitution and full dated replay remain distinct. Preserve archived coefficients/screens; no adaptiveweights, broadacquisition, older-election ingestion or renewedmean-effect search starts automatically. The aim is a working reproducible forecast with explicit dependencies, not another open-ended historical cycle.
