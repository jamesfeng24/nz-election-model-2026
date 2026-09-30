# Stage 18 conditional historical candidate-share baseline

**Status:** development diagnostics for independent review. PR #24 was verified merged as `ef5ac1757baaffcf9381b71e250e91a3aa3a48d5`, including reviewed Stage17 head `fb47f9b77aad38dda916d6337062425d6da2be2f`. The [mapping inventory](conditional-candidate-share-inventory.md) was committed at `565dd9c` and the [implementation rules](conditional-candidate-share-implementation-specification.md) at `7e78c5d`, both before fitting. Construction was committed at `a7df2eb` before target outcomes were evaluated; evaluation was committed at `632e1b3`. No eligibility, floor range or method was retuned after scores.

## Coverage and fitted floors

The frozen frame has **213** contests: 191 held general, 21 Māori coverage-only and cancelled 2023 Port Waikato. It contains **1,313** standing target candidates in the *held general* contests (423/431/459). Conservative election-local mapping constructs all 63 held 2011 and 64 held 2017 contests, plus 44 of 64 held 2023 contests. The other 20 held 2023 contests (**147 candidate occurrences**) abstain because Vision New Zealand candidates cannot be assigned uniquely to the report-only Freedoms NZ party-ballot group. The construction represents **171 contests and 1,166 candidates**: 1,313 − 147 = 1,166. Port Waikato's nine cancelled nominations are **outside** the 1,313 held-general denominator and retain a separate cancelled record in the 213-contest frame. All 21 Māori contests remain coverage-only. Construction never filters on observed candidate result, winner, person identity or profile availability.

| Target holdout | Earlier training elections | Complete training contests | No-group/zero-support training contests | Fitted κ, party-share units | Status |
| --- | --- | ---: | ---: | ---: | --- |
| 2011 | 2008 | 63 | 24 | 0.002934013733 | interior; independent check agrees |
| 2017 | 2008, 2011, 2014 | 164 | 54 | 0.003125035829 | interior; independent check agrees |
| 2023 | 2008–2020 | 293 | 123 | 0.003610264416 | interior; independent check agrees |

All eligible earlier held general seats enter training; only ambiguous mapping, cancellation or incompatible totals exclude an earlier seat. The 2014 Internet Party/MANA Movement report grouping excludes 26 otherwise held general seats from training. The 2023 ambiguity is not a training input for these folds. These exclusions reduce coverage and are not assumed random.

## Candidate-share results

Errors are percentage points of **valid candidate votes**, not valid party votes. MAE averages candidates within a contest, then contests equally. RMSE takes the square root after the mean of within-contest candidate squared errors. The uniform rule ties every standing candidate as a predicted winner. The fitted common floor cannot change party-support rankings, so its winner ranking would be identical under any positive floor.

| Target | Common full subset | Fitted MAE / RMSE | Uniform MAE / RMSE | Fitted unique winner correct | Uniform ties |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2011 | 63 contests / 423 candidates | 3.2644 / 5.9509 | 17.0606 / 20.6503 | 49/63 | 63/63 |
| 2017 | 64 / 431 | 2.4400 / 4.7087 | 16.4329 / 19.7282 | 56/64 | 64/64 |
| 2023 | 44 / 312 | 3.4245 / 5.8850 | 14.6717 / 17.9827 | 35/44 | 44/44 |
| Pooled trained 2017+2023 | 108 / 743 | 2.8411 / 5.2201 | 15.7154 / 19.0364 | 91/108 | 108/108 |

The uniform comparison measures the value of supplied **observed target local party support** plus a party-linked slate; it is not a gain attributable specifically to fitting κ. The restricted zero-floor party-proportional comparison isolates that addition on an identical subset with no no-group or zero-support standing candidate:

| Target | Restricted common subset | Fitted MAE / RMSE | Zero-floor MAE / RMSE | Uniform MAE / RMSE |
| --- | ---: | ---: | ---: | ---: |
| 2011 | 43 contests / 266 candidates | 3.2260 / 5.7148 | 3.1780 / 5.6847 | 17.6682 / 21.1121 |
| 2017 | 31 / 179 | 2.6475 / 5.2693 | 2.6687 / 5.3031 | 17.5321 / 20.5960 |
| 2023 | 19 / 108 | 4.1847 / 7.4141 | 4.1949 / 7.4231 | 16.2173 / 19.6349 |
| Pooled trained 2017+2023 | 50 / 287 | 3.2316 / 6.1728 | 3.2486 / 6.1948 | 17.0325 / 20.2362 |

The floor's gains over the restricted comparator are about **0.0212pp in 2017** and **0.0102pp in 2023**, far below the 0.25pp indicative materiality screen. It worsens 2011 by 0.0480pp. Restricted applicability is only 43/63, 31/64 and 19/44 otherwise constructed contests; its missing cases are visible, not dropped from full-frame coverage. The trained-fold positive MAE comparisons and RMSE checks pass numerically, but the restricted gains are immaterial and no conditional diagnostic can select an operational forecast.

Candidate-equal MAE sensitivity for the fitted model is 3.2018/2.4125/3.2408pp in 2011/2017/2023. Independent candidates on constructed contests number 16/29/22. Their fitted mean signed errors are −0.1599/−0.8565/−0.8924pp: positive floor mass does **not** represent individual independent strength. The saved diagnostics provide party/category, no-group mapping and slate-size errors and bias. Full-slate signed bias cancels to zero by construction and is only an accounting check. A person-level entrant label is **unknown** without separate identity evidence; source-local affiliation novelty does not establish first candidacy.

## Party-input and forecast limits

Every additive, proportional and log-odds Stage5 point substitution abstains: none of the 63/64/44 constructed target contests has complete category coverage from the retained transform rows. The existing eligible-party forecasts cannot be stitched into a full vector, supplemented with zeros or renormalized. These would also be conditional on observed target national support. Stage5's transform choice remains unresolved. The observed-local-party scores above are therefore **retrospective conditional development diagnostics**, not historical as-of forecasts or 2026 predictions. The 2011/2017/2023 elections already shaped Stages5–17 and are not untouched confirmation.

The floor adds the same κ to every standing candidate, so ordering never changes. All affirmative no-party-group candidates tie below any candidate with positive mapped party support. Support from party groups without a candidate is redistributed by the denominator as a modelling assumption. Unknown personal strength is neither estimated zero nor resolved; Stage7 residuals and Stage8–10 candidate effects, Stage16 source victory and split patterns are not stacked. No candidate counts, winner probabilities, joint uncertainty or changed-boundary candidate baseline have been validated. The **selected operational candidate baseline remains null**.

## Reproduction and next decision

Run `.venv/bin/python -m scripts.models.conditional_candidate_share.inventory --check`, then `.venv/bin/python -m scripts.models.conditional_candidate_share.run --check`, then `.venv/bin/python -m scripts.models.conditional_candidate_share.evaluation_run --check`, and `.venv/bin/python -m unittest scripts.tests.test_conditional_candidate_share -v`. The manifests pin the 420 consumed official source records/raw bytes, processed inputs and generator code. Construction and evaluation are separate files. An independent scalar bounded minimization reproduced all three floors within `1e-8`; independent direct arithmetic reproduced each holdout fitted MAE to saved precision. Full checks and CI are recorded in PROJECT_STATE.md.

**Recommended next decision after independent review:** whether to separately authorize a bounded **as-of input feasibility and joint-uncertainty checkpoint**: date-verified historical nomination slates, pre-result party-support and turnout scenarios, and a coherent slate-level error model on a fixed frame. Do not tune another floor or transport candidate votes across changed boundaries from this result. That next checkpoint needs its own scope and source budget; no acquisition, operational forecast or integration is authorized by Stage 18.
