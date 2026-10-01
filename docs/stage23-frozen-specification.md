# Stage 23 frozen conditional party-vector specification

**Frozen before any Stage 23 construction or historical error calculation.**
The [preserved-input inventory](stage23-input-inventory.md) fixes the 213
unchanged-boundary party-seat pairs. This specification makes one point
scenario conditional on *supplied* target national valid-party shares. The
historical exercise supplies the subsequently observed national result; it is
neither a national-support forecast nor an as-of 2026 forecast.

## Estimand, categories and construction

Let `p[e,c]` be the source electorate share among source **valid party votes**,
`P0[c]` the source national valid-party share, and `Q[c]` a supplied target
national valid-party share. Every target election registered ballot group is
included exactly once. Stage 5's supported canonical group relationship is
the sole cross-election continuity key. For a continuing group, set
`a[e,c] = p[e,c] / P0[c]`. For a genuine target entrant, set `a[e,c] = 1`.
Then `u[e,c] = Q[c] a[e,c]` and
`L[e,c] = u[e,c] / sum_{d in target groups} u[e,d]`.

Thus `L` is nonnegative and sums to one. Exited source groups are absent from
the target vector and their local mass is redistributed by the common
closure, not attributed to a named successor. An entrant's affinity of one
is a **neutral national-profile assumption**, not observed local evidence.
An observed zero for a continuing source group yields zero in that seat under
this rule; that point assumption does not assert future support is impossible.
A structurally new target group instead receives `Q[c]`, so the source zero
cannot bar its entry. Missing source evidence is never substituted by zero.
If continuity is ambiguous, a required source row is missing, `P0[c]≤0`, the
supplied `Q` is not a complete simplex, or the sum of `u` is nonpositive,
abstain on the whole electorate. No party key is inferred from a candidate's
affiliation. Internet MANA/Freedoms NZ are election-local group identities;
no constituent cross-election bridge is invented.

This is one parameter-free compositional **proportional** extension of Stage
5's party-specific proportional response. Stage 5 additive and binary
log-odds formulas have no unique all-category simplex extension with entry,
exit and zero handling; they are not silently normalized or retuned here.
The output is a coupled vector, not a collection of independent marginal
estimates. No optimizer, pseudocount or fitted parameter is used.

## Population, timing and reconciliation

The target populations are **all** 70, 71 and 72 party-ballot electorates in
2011, 2017 and 2023, including seven Māori electorates each and Port Waikato's
2023 party ballot. The fixed 191 held general candidate comparison contests
are a labelled subset, never the national reconciliation population. Their
independently validated unchanged-boundary mapping supplies source seats.
Historical source party rows are exact; no geographic interval scenario is
needed for these transitions. The 2023-on-2026 joint geographic bounds are
outside this stage. There is no candidate-vote or candidate-valid denominator
in the construction.

This rule does **not** impose national reconciliation. A valid target local
simplex need not have weighted national average `Q`. After construction,
calculate the diagnostic aggregate using the *observed target valid-party
vote totals* as oracle weights, and report its difference from `Q`. Those
weights and target local shares are evaluation-only; neither is needed by the
future party-vector interface. Exact national reconciliation would require
an additional constrained allocation rule and a complete as-of electorate
weight scenario. It is not claimed here.

## Frozen evaluation

For target 2011 use only 2008 source local/national evidence; for 2017 only
2014; for 2023 only 2020. `Q` is the explicitly supplied conditional target
national result. No target local result, candidate result, winner flag,
identity label or split destination can change eligibility or `L`.

Report each holdout and scope separately, then pooled general and Māori
descriptions. Full-vector coverage is the number of electorates with all
target ballot groups and a feasible `L`; abstentions remain in the fixed
213-row frame. The simple benchmark is the flat supplied national vector
`B[e,c]=Q[c]` in every seat; it has the same complete group set and sample.
For each electorate with `K` target groups, define contest MAE as
`100*sum_c |L[e,c]-A[e,c]|/K` and contest MSE as
`10000*sum_c (L[e,c]-A[e,c])²/K`. Fold MAE is the equal-electorate mean
of contest MAE; fold RMSE is the square root of the equal-electorate mean
contest MSE. Report candidate-layer restricted 191 held general rows
separately. An electorate-valid-party-vote weighted sensitivity uses observed
target weights *only at evaluation*. Also report party-specific signed bias
`100*mean_e(L[e,c]-A[e,c])`; whole-vector signed bias is merely a conservation
identity. Entrant, continuing, small national-share (<1%), zero-source and
alliance categories are predeclared breakdowns. National weighted aggregate
gaps, max simplex residual and abstention reasons are shown.

Compare Stage 5 marginal additive, proportional and log-odds results only on
the intersection of exact electorate ID, target group ID, observed-source
geography, units and information set. That is a separate aligned-category
diagnostic; it cannot substitute for full-vector coverage. No Stage 5
operational transform is selected.

The developmental materiality screen is a ≥0.25 percentage-point MAE gain
over the flat national vector in **both** 2017 and 2023 general folds, with
no ≥0.25-point RMSE regression and complete-vector coverage ≥95% of the
fixed 191 held general contests. 2011 is reported separately. This is not a
significance test or an operational-selection rule. No rule may be tuned
after errors are inspected. A poor result or incomplete coverage is reported
as such. These reused elections are development evidence, not independent
confirmatory replications.

## Output and stopping contract

Construction and evaluation are separate files. Construction records carry
source/target election and electorate IDs, target party-ballot group keys,
the supplied national scenario, the complete local vector, source-affinity
status, no prediction weight, applicability, source checksums and the
`conditional_observed_target_national_party_support` information label.
Evaluation-only files hold actual local shares, oracle target electorate
weights, metrics and national-gap diagnostics. A different supplied national
scenario can later call the construction function without target local data.
No point output is made on a missing or ambiguous required input. All
conservation checks use absolute tolerance `1e-12`; failures raise rather
than silently renormalizing a failed calculation. Stage 22 baseline and
S-only parameters may consume these vectors in a **separately authorized**
input-substitution test, without refitting them here.
