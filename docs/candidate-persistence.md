# Stage 8 — candidate persistence

The specification in `data/processed/models/candidate-persistence/specification.json` was frozen before fitting. Its first checkpoint was `d606e0b`; the identity evidence and practical operational gate were clarified in `b062f60`, still before any model run. Stage 7's occurrence IDs, source labels, denominators and residuals are immutable. This stage estimates **conditional predictive persistence of a same-person residual**, not a causal or uniquely personal vote effect.

## Evidence and units

The 3,007 Stage 7 candidate-election occurrences remain the universe. The outcome and predictor are additive normalized overperformance in vote-share fractions, reported as percentage points: candidate share minus local party share minus the other matched contests' party/election offset. Candidate and party valid-vote denominators stay separate. The two alternative Stage 7 scales remain sensitivity outcomes.

Person identity is separate from party, electorate and election-time status. Exact full source name, affiliation and seat chains without external corroboration are `probable`; conflicts and lone appearances remain `unresolved`. The bounded official Parliament former/current MP indexes corroborate a unique surname/first-name profile only when that exact full-source-name/affiliation/seat chain includes a compatible observed winning occurrence. Profile display variants are preserved alongside source names with explicit alias evidence. This retrospective validation cannot cover losing-only challengers, list-only histories or all Māori candidacies. It is an identity aid, not a pre-election feature. No candidate biography was invented.

| Identity outcome | Occurrences |
| --- | ---: |
| Confirmed by the bounded MP evidence rule | 215 |
| Probable exact-record chains | 747 |
| Explicit unresolved | 2,045 |

The separate history/status file has one dated record for every occurrence. It records 53 continuing and 13 first-term incumbent classifications supported by an observed earlier win plus a continuous published parliamentary service interval. The other 2,941 statuses remain unknown. Before-panel tenure is left-censored unless explicit service evidence exists. Returning/former incumbent, replacement, returning challenger, genuinely new and list-only history are valid categories in the status contract but are not assigned without evidence. Leadership is a separate nullable attribute; no status effect is fitted.

## Pair construction

An adjacent pair requires the same linked person and two observed held, exact-counterpart, normalized occurrences. Primary pairs also require both links confirmed, the same electorate and type, and one of the three validated unchanged-boundary regimes. A repeated electorate name across a changed regime is not geographic evidence. No changed-boundary candidate votes are constructed. The pair inventory retains exclusions and both residuals for retrospective audit; target residuals are never predictors of their own election.

| Transition | Linked adjacent pairs | Confirmed primary general | Comparable confirmed or probable |
| --- | ---: | ---: | ---: |
| 2008→2011 | 109 | 23 | 104 |
| 2011→2014 | 125 | 0 | 0 |
| 2014→2017 | 121 | 26 | 114 |
| 2017→2020 | 94 | 0 | 0 |
| 2020→2023 | 83 | 20 | 78 |

There are 69 confirmed primary pairs, all general, and 296 comparable confirmed-or-probable pairs (281 general, 15 Māori). The 532 linked adjacent pairs have overlapping exclusion reasons: 219 changed-boundary transitions, 415 lacking two confirmed links, 28 missing exact party counterparts/normalized premiums, five seat or scope changes and one cancelled contest. The 2,045 unresolved occurrences cannot form evidenced pairs; this is substantial identity selection. Counts are conditional on a candidate returning and being observed. The model is **not** a complete pre-election candidacy forecast.

## Fit and chronological validation

The general primary model is ordinary least squares, `target residual = intercept + slope × prior residual`. An intercept is appropriate because Stage 7 leave-one-out residuals need not average zero among selected returning MPs. It is not inherited from Stage 6's zero-intercept response restriction. The full-sample fit is descriptive: 69 pairs, slope 0.850, intercept +1.423 percentage points; the zero-intercept descriptive sensitivity slope is 0.937. Neither is an operational coefficient. Single-transition slopes are 0.719, 0.870 and 0.909 for 2011, 2017 and 2023 target elections, but these are three dependent election clusters, not independent proof of a stable person effect.

The 2011 cohort has no prior pair cohort to train on, so only benchmarks are scored. For 2017, fitting uses 2011 targets only; for 2023 it uses 2011 and 2017 targets only. Candidate identity/candidacy and earlier residuals are known conditions; each target's votes, reference offset and residual are evaluation outcomes only.

| General confirmed target | Pairs | Zero MAE | Prior MAE | Fitted MAE | Zero RMSE | Prior RMSE | Fitted RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2011, benchmark only | 23 | 7.476 | 3.306 | — | 8.469 | 4.329 | — |
| 2017 | 26 | 7.590 | 2.521 | 3.479 | 10.787 | 3.552 | 4.203 |
| 2023 | 20 | 9.039 | 4.998 | 4.999 | 12.839 | 8.396 | 8.727 |

Errors are in percentage points. The equal-transition 2017/2023 MAE is 3.759 for unchanged prior residual and 4.239 for the fitted model. The fitted model fails the frozen practical gate in both trained holdouts; it worsens RMSE in both. A prior residual predicts later same-seat residuals better than zero in this selected sample, but the fitted shrinkage/intercept does not reliably improve on simply retaining the prior residual.

Proportional and log-odds scales keep positive descriptive slopes (0.858 and 0.857) but likewise fail to beat the prior benchmark in both chronological holdouts. Adding probable general links yields 281 pairs and slope 0.773; fitted MAE improves only 0.063 points over prior in 2017, then worsens by 0.217 points in 2023. The 15 probable Māori pairs are too few and unstable across three transition groups; zero confirmed Māori pairs support no separate coefficient. Full-sample and scale results are descriptive sensitivities, not model selection by attractive coefficients.

## Interpretation and operational decision

`selectedOperationalCoefficient` is **null**. The predeclared 0.25-point MAE gain over the better simple benchmark with no RMSE deterioration does not hold, and MP-only confirmation does not establish generality to returning challengers. No residual coefficient is added to Stage 6. Stage 5's party transform and Stage 6's National/Labour operational slopes remain unresolved and provisional.

The observed same-seat correlation may reflect stable electorate and party conditions, incumbency, candidate selection and shared party/election reference offsets. All primary pairs stay in the same seat and party by the conservative identity rule, so this design cannot separate personal vote retention from those conditions. Repeated people and only three election-transition clusters make candidate-pair standard errors misleading; no causal confidence interval or election-level replication claim is made. The bounded official index pass does not resolve all identities. Later replacement and freshman-incumbency effects require a separate authorized stage and may use this person/history/status layer, with fresh evidence where needed.
