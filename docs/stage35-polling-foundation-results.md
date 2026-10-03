# Stage35 polling foundation and implementation handoff

No national posterior, forecast score, candidate replay or live forecast is calculated.

## Foundation coverage

The owned normalized panel has **496 unique survey waves**. Raw source history is versioned, not claimed historically archived.44 distinct resources are preserved against60 ceiling (including2 empty responses);51 acquisition attempts include7 failed routes. One duplicate collapses, one invalidSeptember31 row stays excluded. Missing-marker differences are not substantive conflicts. Raw bytes, line/row IDs, checksums, repository commits, fieldwork ranges and verification supplements remain separate.

| Target cycle | Waves | Pollsters | Verified publication | Missing nominal n | Raw unknown day |
|---|---:|---:|---:|---:|---:|
|2014|136|5|0|136|0|
|2017|78|6|0|78|0|
|2020|46|4|1|5|0|
|2023|116|8|1|15|8|
|2026|120|7|1|8|1|

Latest current fieldwork end is2026-09-27. This is a current-input foundation, not a complete ongoing feed or forecast. The original2023 August release supplement corrects one broad fieldwork interval without rewriting its original label. Undecided/refused splits remain unknown when only a combined nonresponse figure is supported.

## Frozen cutoff manifests

Counts are target-cycle waves after cutoff/overlap selection, not predictions. Earlier-cycle IDs and every exclusion are saved individually in coverage.json. Primary5-day assumed release lag vs10-day timing sensitivity:

|Election|14days:5/10lag|56days:5/10lag|Verified-only total earlier+current at14/56days|
|---|---:|---:|---:|
|2014|123/121|110/108|0/0|
|2017|70/70|62/62|0/0|
|2020|41/40|37/37|1/0|
|2023|107/106|98/98|2/1|

All proposed folds are implementation-ready **under the explicit inferred timing, denominator and missing-n assumptions**. None establishes an entirely verified as-of polling archive. Verified-only early folds cannot provide polling fits. End-of-fieldwork is never relabelled publication. Earlier election results use a conservative next-January availability assumption because exact publication evidence is not preserved. Historical calendar dates agree across pinned bulk/config evidence; failed official summary retrievals provide no independent verification.2026 date has an original Electoral Commission source. No horizon changed to improve results.

## Owned build and frozen next task

Use [the audited reuse decision](stage35-reuse-audit.md): versioned Nixinova bulk data/current Wikipedia supplementation; independently implemented small adapters; simplify the inspected compositional architecture. Frozen [national model](stage35-national-model-design.md) has weekly Helmert-coordinate diffusion, centered pooled house effects, one common cycle bias, fixed sampling/design approximation and interval observation likelihood. It produces current and election-day joint shares/draws, not merely a point average. NumPyro0.19.0/JAX-JAXlib0.6.2 are pinned by preserved package metadata; runtime verification and transitive locking occur in the isolated next inference environment, without the upstream website/electorate/ensemble stack.

The transparent30-day half-life, pollster-balanced coarse average is a national point benchmark. It carries current support to election day and makes no calibration claim. The finite next implementation is **one national model, one benchmark, eight2014/2017/2020/2023 ×14/56day cases**, with10-day lag/missing-n sensitivity separately. No candidate predictions/parameter changes or interim-average candidate replay. Major-party accuracy and joint/marginal calibration are assessed independently of which candidate expert later wins.

## Limitations and dependency boundaries

Only3 verified release records;242 nominal sample sizes unknown; sparse modes/denominators/design histories and incomplete revision archives. Explicit assumptions permit estimation rather than invent facts. Few election cycles weakly identify common bias; fixed structural covariance and priors must remain visible. Conditional-independent Gaussian reporting is an approximation; rounded percentages are never pseudo-counts. Missing parties stay unobserved, threshold observations stay intervals. Other is coarse, especially around alliances/entrants. Fine local party-group allocation inside Other is unresolved, so downstream complete-vector adapter may abstain until separately designed. No target election result may split it.

Component validation, fixed-fit substitution and end-to-end replay remain distinct (D067). S/S+R active, R challenger/baseline control. Future polling misses cannot automatically overturn candidate-layer findings; isolated error cancellation cannot select an expert. End-to-end results can inform deployment only with their uncertainty/chronological limitations. National draw IDs remain shared across electorates; no duplicated national error. Mean-input forecasts differ from averages of nonlinear transformed draws.

Slate, target-boundary candidate baseline, dated direct electorate polls/Māori coverage and turnout/invalid-ballot/national-reconciliation inputs remain separate. National inference/backtest comes next; fixed candidate alternatives replay comes afterward under separate authorization. No production backend.

## Validation

22 focused tests cover rounded/missing/zero/censored observations, invalid dates, duplicates/conflicts/overlap, schema/Other, publication timezones/revisions, actual-adapter held-out-result independence, earlier anchors, source bytes and synthetic joint outputs. Deterministic data/design/independent checks pass. Independent Decimal arithmetic checks3,205 rounding cells; Fraction arithmetic40 national category ratios;16 horizon manifests and all source references. All1,461 prior tracked data files remain byte-identical, including raw sources, fits, identity/geography and operational nulls. No candidate numerical machinery rerun. The full652-test Python suite passed in141.205s; final-head CI status is recorded separately on the PR; no Python formatter/linter configured, compilation/whitespace checks used. Unrelated local frontend checks are not repeated; GitHub CI runs them.

Acquisition deviations are explicit in [the audit](stage35-reuse-audit.md): repeated discovery routes, unknown individual discovery timestamps and unavailable failure diagnostics. These do not become verified historical availability. No unresolved automatic-approval restriction is known from the preserved logs; failure causes without logs cannot be reconstructed.
