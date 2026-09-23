# Stage 8 — candidate persistence, audit-corrected

The original specification was frozen at `d606e0b` and clarified at `b062f60`, both before fitting. The correction in this document follows the PR #15 correctness audit **after** the original fit. `specification.json.auditAmendment` records the change without rewriting that history. Stage 7's 3,007 occurrences, IDs, source labels, denominators and residuals remain immutable. The estimand is conditional predictive association between earlier and later same-person normalized residuals, not a causal or uniquely personal vote effect.

## Audit findings and identity evidence

The original rule treated an official Parliament profile plus one compatible winning occurrence as confirmation of *every* occurrence in the same full-source-name/affiliation/seat chain. The profile establishes a person and the winner anchors that occurrence; it does not independently document the other nominations. The audit found 46 of 215 formerly confirmed occurrences were not qualifying anchors, including two old primary pairs where neither occurrence was a winner. Those 46 links now remain **probable** projections to the anchored person. A direct official-profile/observed-winner occurrence is **confirmed**. Exact chains without an official anchor are probable; conflicts and insufficient evidence remain unresolved. Profile names, source names and aliases remain separate.

| Occurrence identity | Before audit | Corrected |
| --- | ---: | ---: |
| Confirmed direct anchors | 215 | 169 |
| Probable projected or exact-chain links | 747 | 793 |
| Unresolved | 2,045 | 2,045 |
| Total | 3,007 | 3,007 |

The person record reports whether an official profile corroborates the person's existence. Each occurrence link separately reports its confidence, method, anchor occurrence IDs and election dates, profile URL, retrieval time, and unknown publication time. A profile retrieved in 2026 is retrospective evidence about an earlier historical fact; it is not asserted to have been published by the target election. The separate history/status record makes career-history evidence confidence explicit. Only directly anchored occurrences retain supported incumbent classifications: 49 continuing, 11 first-term, 2,947 unknown. Unknown or pre-panel history is not converted to never served. Leadership remains orthogonal. No status effect is fitted.

## Cohorts and outcome timing

Evaluation cohorts require two linked held, exact-counterpart, normalized occurrences in the same electorate/type and a validated unchanged-boundary transition (2008→2011, 2014→2017 or 2020→2023). Changed-boundary same-name seats, missing premiums, missing counterparts and cancelled contests remain in the pair inventory with exclusion reasons. The 532 adjacent linked pairs and 296 comparable linked pairs (281 general, 15 Māori) are unchanged.

The **outcome-independent validation cohort** requires a directly anchored *source* winner and an exact full-name/affiliation/seat target candidacy linked to that person. Target link confidence may be probable. Eligibility uses the source result and known target candidacy, never the target win or a later winner. This is conditional on prior-winner selection, a returning candidate and retrospectively adjudicated identity. It is not a prospective all-returnee forecast: the 2026 profile acquisition and unknown publication timing cannot establish what identity evidence was available before each election. No adequate outcome-independent cohort with both occurrences independently confirmed exists under the preserved evidence.

The **retrospective confirmed diagnostic** requires two direct winner anchors. It is selected on the target win and cannot determine the operational coefficient. The broad comparable-linked sensitivity keeps probable identities visibly uncertain. Pair records include each link's evidence and confidence, anchor dates, outcome-dependency roles, and a separate inclusion reason for each cohort.

| Transition | Linked adjacent | Before-audit confirmed primary | Corrected validation general | Retrospective confirmed general | Comparable linked |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2008→2011 | 109 | 23 | 20 | 20 | 104 |
| 2011→2014 | 125 | 0 | 0 | 0 | 0 |
| 2014→2017 | 121 | 26 | 16 | 18 | 114 |
| 2017→2020 | 94 | 0 | 0 | 0 | 0 |
| 2020→2023 | 83 | 20 | 3 | 1 | 78 |
| Total | 532 | 69 | 39 | 39 | 296 |

There are zero Māori pairs in either the corrected validation or retrospective confirmed cohort. The old 2023 cohort had 17 of 20 pairs whose sole qualifying identity anchor was the target win, and 18 of 20 targets won. Those old scores are superseded. Direct confirmation in the corrected retrospective cohort remains an outcome-selected diagnostic, even though its total happens also to be 39.

## Chronological diagnostics

Residuals remain vote-share fractions internally and reported errors are percentage points. The predictor is the source election's Stage 7 normalized residual. The target's observed votes, offset and residual enter only evaluation. Training uses earlier target elections: 2011 has benchmarks only; 2017 trains on 2011; 2023 trains on 2011 and 2017. Intercept plus slope remains appropriate because selected returnees' residual mean need not be zero. Zero and unchanged-prior benchmarks use the identical evaluated pairs and equal pair weighting. Full-sample fits are descriptive.

| Validation target | Pairs | Zero MAE | Prior MAE | Fitted MAE | Zero RMSE | Prior RMSE | Fitted RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2011, benchmark only | 20 | 7.805 | 3.311 | — | 8.846 | 4.433 | — |
| 2017 | 16 | 6.886 | 2.776 | 3.697 | 7.978 | 4.082 | 4.369 |
| 2023 | 3 | 10.362 | 14.438 | 16.401 | 15.018 | 19.181 | 20.427 |

The validation cohort's descriptive full-sample slope is 0.640 with intercept +2.355 points across 39 pairs. Proportional/log-odds descriptive slopes are 0.731/0.676; they do not repair the weak temporal evidence. The broad 281-pair general probable-link sensitivity retains slope 0.773, but identity uncertainty is greater. Fifteen comparable Māori probable pairs are too few for a coefficient. The separate winner-selected retrospective cohort has 39 general pairs and descriptive slope 0.619; its scores are not operational evidence.

The fitted model fails to beat the simple benchmarks in the two trained validation holdouts. The 2023 validation cohort has only three pairs and cannot establish stable generalization. The predeclared 0.25-point/no-worse-RMSE practical gate was originally applied to an outcome-selected cohort; under this post-fit amendment only the corrected validation cohort contributes diagnostic gate values. There is no adequate outcome-independent *confirmed-target* cohort or broad challenger coverage. `selectedOperationalCoefficient` therefore remains **null**, now explicitly for insufficient defensible validation as well as poor fitted performance. No Stage 6 bonus is created; Stage 5/6 operational choices remain unresolved.

Stable electorate/party conditions, incumbency, returnee selection, 2026 profile survival, and shared party/election reference offsets can all resemble person persistence. There are only three transition clusters and repeated people, so pair-level standard errors would overstate independent information. No causal retention, general-returnee forecast, or uniquely personal effect is claimed. Later freshman-incumbency work needs separate dated electorate and list-tenure evidence; replacement fitting is later still. Neither is started here.
