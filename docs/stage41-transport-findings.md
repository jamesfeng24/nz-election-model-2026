# Stage41: practical boundary transport

Post-Stage40 implementation under the frozen Stage41 contract. No refitting, source acquisition, MCMC or live 2026 forecast. External gauss provisional; S+R preferred, S active and baseline mandatory. Original decisions and operational records remain unchanged.

## Coherent party-input scenario

All six general/Māori scopes across 2011→2014,2017→2020 and2023→2026 construct. A lexicographically minimum integral feasible population network satisfies the full parent-group/suppression bounds and destination controls. It is a chosen scenario, not a midpoint, observed reconstruction or expected population allocation. Source party votes and their valid denominator use the same source-outgoing population weights; exact rational mass is conserved across every target. Complete categories include parties without electorate candidates.

The within-source uniform population-to-party-vote distribution is assumed. Target valid-party totals are not observed turnout forecasts. Future national support is not supplied here, and no national reconciliation to a future scenario is imposed. The complete source national denominator includes every general and Māori electorate, never the selected overlap sample.

| Transition | General / Māori target vectors | Full source valid-party denominator |
| --- | ---: | ---: |
| 2011-2014 | 64 / 7 | 2,237,464 |
| 2017-2020 | 65 / 7 | 2,591,896 |
| 2023-2026 | 64 / 7 | 2,851,211 |

## Historical fixed-fit diagnostic

S+R uses the saved Stage33 primary expanding-window parameters and training means, applied to observed target local party support. All six branches share 37/47 complete slates; strict sensitivity changes only R linkage availability, with the same primary fit. Exact features remain in both branches. Positive paired gain means fallback error minus transported error. Errors are percentage points; MAE/RMSE are contest-equal. Full-slate bias cancels by construction and is an accounting check.

| Election | View / tier on common90 sample | Contests / candidates | MAE | RMSE | MAE gain over matching fallback | Transported S / R |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2014 | fallback | 37 / 265 | 3.0083 | 5.3279 | +0.0000 | 0 / 0 |
| 2014 | fallback_strict | 37 / 265 | 2.9975 | 5.3236 | +0.0000 | 0 / 0 |
| 2014 | transport_90 | 37 / 265 | 2.7827 | 5.0119 | +0.2256 | 82 / 37 |
| 2014 | transport_90_strict | 37 / 265 | 2.7660 | 5.0024 | +0.2316 | 82 / 35 |
| 2014 | transport_95 | 37 / 265 | 3.0233 | 5.3399 | -0.0150 | 38 / 18 |
| 2014 | transport_95_strict | 37 / 265 | 3.0126 | 5.3357 | -0.0150 | 38 / 18 |
| 2020 | fallback | 47 / 409 | 2.4372 | 4.0795 | +0.0000 | 0 / 0 |
| 2020 | fallback_strict | 47 / 409 | 2.4772 | 4.1561 | +0.0000 | 0 / 0 |
| 2020 | transport_90 | 47 / 409 | 2.2266 | 3.7492 | +0.2105 | 65 / 26 |
| 2020 | transport_90_strict | 47 / 409 | 2.2773 | 3.8397 | +0.1999 | 65 / 21 |
| 2020 | transport_95 | 47 / 409 | 2.3247 | 3.8965 | +0.1125 | 37 / 15 |
| 2020 | transport_95_strict | 47 / 409 | 2.3588 | 3.9624 | +0.1184 | 37 / 12 |

### Exclusive additions and cumulative coverage

Tier-wide errors are not compared as if their populations were identical. The paired effects below compare each transport branch with its corresponding fallback on identical records.

| Election | Sample | Contests / candidates | Broad90 gain | Broad95 gain |
| --- | --- | ---: | ---: | ---: |
| 2014 | exact | 20 / 143 | +0.0000 | +0.0000 |
| 2014 | approximate95_only | 8 / 58 | -0.0696 | -0.0696 |
| 2014 | approximate90_only | 9 / 64 | +0.9893 | +0.0000 |
| 2014 | cumulative95 | 28 / 201 | -0.0199 | -0.0199 |
| 2014 | common90 | 37 / 265 | +0.2256 | -0.0150 |
| 2020 | exact | 34 / 286 | +0.0000 | +0.0000 |
| 2020 | approximate95_only | 7 / 67 | +0.7553 | +0.7553 |
| 2020 | approximate90_only | 6 / 56 | +0.7679 | +0.0000 |
| 2020 | cumulative95 | 41 / 353 | +0.1290 | +0.1290 |
| 2020 | common90 | 47 / 409 | +0.2105 | +0.1125 |

### Category errors and bias

Category metrics weight each member candidate equally, with its original valid-candidate denominator. They do not sum to the contest-equal whole-slate metric.

| Election | Category / candidates | Fallback MAE / bias | Broad90 MAE / bias |
| --- | --- | ---: | ---: |
| 2014 | labour / 37 | 6.4715 / -5.6166 | 5.7273 / -4.5436 |
| 2014 | national / 37 | 6.5539 / +4.3442 | 6.8274 / +6.4945 |
| 2014 | no_party_group / 24 | 0.6446 / +0.5616 | 0.6932 / +0.5828 |
| 2014 | other_mapped / 167 | 1.8064 / +0.2012 | 1.4239 / -0.5160 |
| 2020 | labour / 47 | 4.2541 / +3.0531 | 4.3607 / +2.9714 |
| 2020 | national / 47 | 8.0170 / -7.8795 | 6.8589 / -6.6540 |
| 2020 | no_party_group / 40 | 0.4647 / +0.3967 | 0.4545 / +0.3874 |
| 2020 | other_mapped / 275 | 1.3731 / +0.7672 | 1.2300 / +0.5730 |

### Material individual failures

Up to five largest losses under the broad 90% scenario, retained in every primary score:

| Election | Seat | Paired MAE gain |
| --- | --- | ---: |
| 2014 | Papakura | -3.5354 |
| 2014 | Waitaki | -2.5731 |
| 2014 | Botany | -1.0617 |
| 2014 | Tauranga | -0.7084 |
| 2020 | West Coast-Tasman | -0.3528 |

### Interpretation

The broader 90% scenario lowers mean share error in both retained election environments; strict R gives similar gains. The tight 95% scenario slightly worsens 2014 and improves 2020. This is mixed evidence for a practical transport assumption, not permission to optimize a threshold or claim geographical reconstruction. There are substantial individual losses and only two reused election environments. Keep the frozen broader 90% development scenario and tight 95% sensitivity; carry transport error to the next uncertainty layer.

Stage26's original nonexact refusals remain intact. The supplementary direct link layer removes only that geographic refusal on admitted predecessor pairs and reapplies unchanged names, context, competitors and component checks. It does not reopen exceptions, assign persons or claim documentary identity. Source R is not target-boundary residual strength; S is not a same-person effect. No outgoing residual goes to a replacement.

## 2026 readiness companion

| Scope | Exact | Approximate95 additions | Approximate90-only additions | Fallback |
| --- | ---: | ---: | ---: | ---: |
| general | 14 | 15 | 8 | 27 |
| maori | 2 | 3 | 2 | 0 |

General exact 14 includes cancelled-source PortWaikato, leaving 13 held exact plus 15 approximate95 and 8 approximate90-only (36 held general sources in cumulative90). Cancelled source candidate features remain unavailable even though valid party votes can be transported. All Māori party inputs are constructed; the general fitted candidate coefficients are not extended to Māori.

| Scenario | Known candidate S / general R / strict R | Source party-seat S rows |
| --- | ---: | ---: |
| 90 | 68 / 16 / 7 | 183 |
| 95 | 53 / 13 / 5 | 146 |

One accepted Māori source residual is evidence only, requiring its separate baseline contract. Source party-seat S availability is inventoried independently of candidate announcements. All 206 known candidates and all 71 target seats are retained; zero slates are complete. No partial slate is normalized and no 2026 candidate share is produced. Missing features remain neutral assumptions, not known zero strength. Registered-group participation/continuity and complete nominations remain conditional.

## Validation and next action

Focused synthetic and actual-adapter tests cover rational thresholds, missing directions, suppressed/ambiguous membership, names/identity/replacements, coupled feasibility/conservation, no target-outcome admission, and fixed-fit/mean reuse. Independent arithmetic checks recompute vectors, paired errors and source transport; deterministic CLI checks preserve prior artifacts. Final check counts and CI are recorded in PROJECT_STATE and the PR.

Next separately authorized implementation: coherent joint local-party/candidate uncertainty, explicitly covering population-to-vote transport, predecessor-flat S/R error, unknown histories, local/candidate residual dependence and parameter uncertainty. Shared national error must enter once; overlap is not a calibrated variance. Official nomination refresh and Māori electorate-poll/unpolled-seat baseline remain separately bounded. No new threshold, model fit, acquisition, national comparison or live forecast begins automatically.
