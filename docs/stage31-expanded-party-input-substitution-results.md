# Stage31 — expanded party vectors and fixed-parameter candidate input substitution

**Conditional reused development evidence; no fitting, operational selection, acquisition or forecast.** Preconstruction a91cc7d pins the samples/equations/input hashes; construction 6e7a4dd commits vectors and four-cell predictions before scoring. Earlier specifications and numerical outputs remain historical checkpoints.

## Coverage and construction

| Target | Held candidate contests | Candidate occurrences | Exact general party vectors | Primary fit | Separated fit |
| --- | --- | --- | --- | --- | --- |
| 2011 | 63 | 423 | 63 | no | no |
| 2014 | 20 | 143 | 20 | yes | no |
| 2017 | 64 | 431 | 64 | yes | yes |
| 2020 | 34 | 286 | 34 | yes | yes |
| 2023 | 64 | 459 | 65 | yes | yes |

The canonical 356-target frame retains 35 Māori coverage-only and 75 nonexact general seats. There are 246 exact general party vectors (including cancelled Port Waikato), 245 held complete candidate slates and 1,742 candidate occurrences. Party data availability does not create a fitted candidate model. Primary fitted comparison: 182 contests/1,319 candidates (2014/2017/2020/2023); more-separated: 162/1,176 (2017/2020/2023). All 21 fitted fold/scenario cases have identical four-cell IDs and no mapping abstentions; nine no-fit cases explicitly cover 2011 under both protocols and separated 2014 across three scenarios. No Māori candidate prediction or approximate-boundary transport is added.

## Complete local party vectors

All target categories appear once. Continuing-group affinity is source local valid-party share divided by source national valid-party share; entrants receive affinity one; exits are omitted. Multiply by supplied target national support and close the **whole party vector** jointly. Observed source zeros remain zero; missing continuing-group evidence abstains. No party support is re-normalized over standing candidates. The full source national denominator uses all electorates, including Māori, rather than the selected exact-seat subset.

| Year | Held seats | Party cells | Model MAE | Model RMSE | Flat MAE | Flat RMSE | NAT MAE | LAB MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2011 | 63 | 819 | 0.6242 | 1.3947 | 1.9064 | 4.6004 | 2.2666 | 2.3708 |
| 2014 | 20 | 300 | 0.3450 | 0.5947 | 1.7971 | 4.7589 | 0.9127 | 0.6187 |
| 2017 | 64 | 1024 | 0.5182 | 1.2808 | 1.4178 | 3.7656 | 2.8189 | 2.8163 |
| 2020 | 34 | 578 | 0.5835 | 1.4151 | 1.2466 | 3.1105 | 1.3374 | 2.3389 |
| 2023 | 64 | 1088 | 0.5536 | 1.0996 | 1.5943 | 3.6431 | 2.1996 | 2.2154 |

Primary party metrics average category errors within each electorate, then give each electorate equal weight; RMSE takes the root after averaging squared errors. The saved evaluation also reports observed valid-party-total-weighted sensitivity, all-category pooled results and each category separately. National/Labour errors materially exceed the all-category average in several folds; that average does not imply nearly perfect candidate inputs. Source geography improves over flat national support in both added elections and all original folds.

| Year | Group | Model MAE/RMSE/bias | Flat MAE/RMSE/bias |
| --- | --- | --- | --- |
| 2011 | national | 2.2666/3.1690/-0.2003 | 8.5494/10.8005/-1.9068 |
| 2011 | labour | 2.3708/3.4529/-0.1808 | 8.0444/11.3436/0.2208 |
| 2011 | other_categories | 0.3161/0.5496/0.0346 | 0.7445/1.6459/0.1533 |
| 2014 | national | 0.9127/1.1789/-0.4926 | 9.1918/11.7066/-0.4528 |
| 2014 | labour | 0.6187/0.7404/0.1973 | 8.9571/13.0978/-0.9390 |
| 2014 | other_categories | 0.2803/0.5090/0.0227 | 0.6775/1.5469/0.1071 |
| 2017 | national | 2.8189/3.3997/0.5573 | 8.5857/10.4591/-2.0537 |
| 2017 | labour | 2.8163/3.5079/-0.6571 | 7.6144/9.8639/0.9712 |
| 2017 | other_categories | 0.1897/0.4124/0.0071 | 0.4632/1.2009/0.0773 |
| 2020 | national | 1.3374/1.9681/0.4199 | 6.3855/7.6057/-0.9571 |
| 2020 | labour | 2.3389/3.0142/-1.4262 | 5.7136/7.8744/0.5489 |
| 2020 | other_categories | 0.4162/1.1856/0.0671 | 0.6062/1.7247/0.0272 |
| 2023 | national | 2.1996/2.6297/-0.3452 | 7.6741/9.3675/-2.0315 |
| 2023 | labour | 2.2154/2.6491/1.0961 | 6.2688/8.7724/0.6177 |
| 2023 | other_categories | 0.3331/0.6645/-0.0501 | 0.8774/2.0153/0.0943 |

### National reconciliation limitation

No national reconciliation is imposed. The following gaps use observed target valid-party totals as **evaluation-only oracle weights over selected exact general seats**. They omit Māori and nonexact seats; comparison with national support is not a claim that this subset should reproduce national totals. The evaluation separately retains model-minus-actual-subset and actual-subset-minus-national gaps, plus Stage23’s unchanged complete-population gap context. Port Waikato contributes its valid party ballot only to the all-exact-party diagnostic, not candidate evaluation.

| Year | Exact party seats | Max |model subset − national scenario| pp |
| --- | --- | --- |
| 2011 | 63 | 2.0401 |
| 2014 | 20 | 0.8166 |
| 2017 | 64 | 3.2517 |
| 2020 | 34 | 2.1949 |
| 2023 | 65 | 2.1678 |

## Four-cell comparison

A = baseline/observed local party input; B = S/observed; C = baseline/constructed; D = S/constructed. Every fitted parameter, training-only mean, S feature, source-rounding scenario, candidate slate and ballot-group mapping stays fixed within each substitution. Intensities and candidate normalization reuse the frozen Stage24 numerical evaluator. No Stage30 residual, response, incumbency or replacement coefficient is added.

Primary **contest-equal MAE (pp)**:

| Year/sample | Contests/candidates | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| 2014 | 20/143 | 2.9987 | 2.9783 | 3.1074 | 3.0431 |
| 2017 | 64/431 | 2.4330 | 2.1822 | 2.5330 | 2.5811 |
| 2020 | 34/286 | 3.2932 | 2.2575 | 3.0890 | 1.9941 |
| 2023 | 64/459 | 3.1616 | 2.3550 | 3.3148 | 2.3924 |

Primary **contest-equal RMSE (pp)**:

| Year/sample | Contests/candidates | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| 2014 | 20/143 | 4.9008 | 4.9363 | 4.9801 | 4.9579 |
| 2017 | 64/431 | 4.7086 | 4.2071 | 4.9214 | 4.7656 |
| 2020 | 34/286 | 5.7832 | 4.0508 | 5.2898 | 3.4435 |
| 2023 | 64/459 | 5.3428 | 4.8399 | 5.4247 | 4.8332 |

Primary **candidate-equal MAE/RMSE sensitivity (pp)**:

| Year | A | B | C | D |
| --- | --- | --- | --- | --- |
| 2014 | 2.8937/4.8026 | 2.8100/4.7531 | 3.0035/4.8704 | 2.8635/4.7549 |
| 2017 | 2.4031/4.6600 | 2.1173/4.1137 | 2.5092/4.8696 | 2.5103/4.6700 |
| 2020 | 3.1794/5.7412 | 2.2307/4.1705 | 2.9669/5.1860 | 1.9553/3.4991 |
| 2023 | 2.9816/5.0354 | 2.1720/4.3141 | 3.1175/5.1096 | 2.2181/4.3344 |

Paired MAE changes (pp). Positive C−A or D−B is substitution damage; positive A−B/C−D is S advantage. I = (D−C)−(B−A), independently checked from paired contest errors; positive weakens S’s relative advantage. This is a descriptive interaction, not a causal/error decomposition or fitted coefficient.

| Year/sample | C−A | D−B | A−B | C−D | I |
| --- | --- | --- | --- | --- | --- |
| 2014 | 0.1086 | 0.0648 | 0.0204 | 0.0643 | -0.0439 |
| 2017 | 0.1001 | 0.3989 | 0.2508 | -0.0481 | 0.2989 |
| 2020 | -0.2041 | -0.2634 | 1.0357 | 1.0950 | -0.0592 |
| 2023 | 0.1532 | 0.0373 | 0.8065 | 0.9224 | -0.1159 |

### Pooled weighting and chronology

Pooling gives every evaluated contest one vote, so primary election weights are 20/182, 64/182, 34/182 and 64/182; separated weights are 64/162, 34/162 and 64/162. No absent fitted fold enters the denominator. RMSE is sqrt(mean contest mean squared error), not mean contest RMSE. Candidate-equal sensitivity gives each candidate one vote.

| Year/sample | Contests/candidates | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| expanding_window | 182/1319 | 2.9120 | 2.3445 | 2.9749 | 2.4558 |
| more_separated | 162/1176 | 2.8974 | 2.2312 | 2.9537 | 2.3635 |

| Year/sample | Contests/candidates | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| expanding_window | 182/1319 | 5.1693 | 4.4949 | 5.1786 | 4.5953 |
| more_separated | 162/1176 | 5.1997 | 4.3769 | 5.1978 | 4.5050 |

| Year/sample | C−A | D−B | A−B | C−D | I |
| --- | --- | --- | --- | --- | --- |
| expanding_window | 0.0629 | 0.1113 | 0.5675 | 0.5191 | 0.0485 |
| more_separated | 0.0563 | 0.1323 | 0.6662 | 0.5902 | 0.0760 |

More-separated printed folds (same saved fits, no refit):

| Year/sample | Contests/candidates | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| 2017 | 64/431 | 2.4326 | 2.2198 | 2.5329 | 2.6343 |
| 2020 | 34/286 | 3.2613 | 2.1435 | 3.0550 | 1.8859 |
| 2023 | 64/459 | 3.1689 | 2.2892 | 3.3208 | 2.3464 |

| Year/sample | C−A | D−B | A−B | C−D | I |
| --- | --- | --- | --- | --- | --- |
| 2017 | 0.1003 | 0.4145 | 0.2128 | -0.1014 | 0.3142 |
| 2020 | -0.2064 | -0.2577 | 1.1178 | 1.1691 | -0.0513 |
| 2023 | 0.1518 | 0.0572 | 0.8797 | 0.9743 | -0.0946 |

### Original versus added evaluation populations

Original-common and added subsets reuse these same amended/expanded-trained predictions. They are not separate fits or outcome-selected subsets. The 2017/2023 original-common sample contains 128 contests/890 candidates; the added 2014/2020 primary contains 54/429. The 2011 original frame has no candidate fit.

| Year/sample | Contests/candidates | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| 2014 new2014_2020 | 20/143 | 2.9987 | 2.9783 | 3.1074 | 3.0431 |
| 2017 originalCommon | 64/431 | 2.4330 | 2.1822 | 2.5330 | 2.5811 |
| 2020 new2014_2020 | 34/286 | 3.2932 | 2.2575 | 3.0890 | 1.9941 |
| 2023 originalCommon | 64/459 | 3.1616 | 2.3550 | 3.3148 | 2.3924 |

## Rankings and margins

Tie tolerance remains 1e−12 in share units. No ties occur in any evaluated cell/scenario. Unique-winner counts use all evaluated contests as denominator; tied-set inclusion is zero. Margin error is the absolute difference between predicted and observed **actual winner share minus the largest other-candidate share**, using the complete slate. It is an evaluation-only diagnostic, not a prediction-time choice of winner. No calibrated winner probabilities exist.

| Year | n | A wins/margin MAE | B wins/margin MAE | C wins/margin MAE | D wins/margin MAE |
| --- | --- | --- | --- | --- | --- |
| 2014 | 20 | 15/11.1006 | 16/14.6933 | 15/11.0945 | 16/14.4653 |
| 2017 | 64 | 56/9.3893 | 61/6.3930 | 56/9.8276 | 59/9.8429 |
| 2020 | 34 | 21/15.5577 | 25/11.4999 | 25/13.2387 | 29/9.2172 |
| 2023 | 64 | 54/7.6396 | 52/8.8389 | 54/8.5888 | 53/8.0427 |

| Year | Substitution | Changed winner sets | Correct→incorrect | Incorrect→correct |
| --- | --- | --- | --- | --- |
| 2014 | A_to_C | 0 | 0 | 0 |
| 2014 | B_to_D | 0 | 0 | 0 |
| 2017 | A_to_C | 4 | 2 | 2 |
| 2017 | B_to_D | 2 | 2 | 0 |
| 2020 | A_to_C | 4 | 0 | 4 |
| 2020 | B_to_D | 4 | 0 | 4 |
| 2023 | A_to_C | 1 | 0 | 0 |
| 2023 | B_to_D | 1 | 0 | 1 |

Share and ranking performance differ: constructed-input S has lower MAE than baseline in 2023 but 53/64 correct winners versus 54/64. In 2017 it has slightly worse share MAE but 59/64 versus 56/64 correct winners. The shared floor and no-group fallback do not model independent candidate strength.

## Candidate groups and input error

Group tables use candidate-equal weights. National/Labour combined overlaps the two individual groups and is a separate diagnostic, not an additive decomposition. Other mapped groups and affirmative no-party-group candidates remain distinct. Saved present-contest-equal group metrics average only over contests containing that group and report their denominators; they do not automatically sum to whole-slate metrics. Full-slate signed bias is approximately zero by conservation, not calibration. No-group shares can change through the shared candidate normalization denominator even though their party input remains zero.

### 2014 candidate groups


MAE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 20/20 | 5.1817 | 7.7814 | 5.4359 | 7.7678 |
| labour | 20/20 | 7.4172 | 6.9119 | 7.1789 | 6.6975 |
| national_labour | 40/20 | 6.2994 | 7.3466 | 6.3074 | 7.2327 |
| other_mapped | 94/20 | 1.7104 | 1.1031 | 1.8741 | 1.2329 |
| affirmative_no_party_group | 9/5 | 0.1156 | 0.4756 | 0.1165 | 0.4760 |

RMSE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 20/20 | 6.2107 | 8.9808 | 6.5370 | 8.9435 |
| labour | 20/20 | 9.6084 | 7.8500 | 9.3194 | 7.6338 |
| national_labour | 40/20 | 8.0900 | 8.4344 | 8.0493 | 8.3145 |
| other_mapped | 94/20 | 2.6899 | 2.0180 | 2.9177 | 2.2257 |
| affirmative_no_party_group | 9/5 | 0.1558 | 0.5008 | 0.1562 | 0.5013 |

Signed bias (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 20/20 | 2.8668 | 7.7059 | 2.6944 | 7.4987 |
| labour | 20/20 | -7.3510 | -6.1696 | -6.9986 | -5.8085 |
| national_labour | 40/20 | -2.2421 | 0.7682 | -2.1521 | 0.8451 |
| other_mapped | 94/20 | 0.9549 | -0.3724 | 0.9165 | -0.4052 |
| affirmative_no_party_group | 9/5 | -0.0085 | 0.4756 | -0.0079 | 0.4760 |

Paired group MAE differences (candidate-equal, pp; negative improves):


| Group | B−A | D−C | C−A | D−B | I |
| --- | --- | --- | --- | --- | --- |
| national | 2.5997 | 2.3319 | 0.2542 | -0.0136 | -0.2678 |
| labour | -0.5053 | -0.4814 | -0.2383 | -0.2144 | 0.0239 |
| national_labour | 1.0472 | 0.9253 | 0.0080 | -0.1140 | -0.1219 |
| other_mapped | -0.6074 | -0.6412 | 0.1636 | 0.1298 | -0.0338 |
| affirmative_no_party_group | 0.3600 | 0.3595 | 0.0009 | 0.0004 | -0.0005 |

### 2017 candidate groups


MAE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 64/64 | 4.0535 | 4.2238 | 4.8672 | 5.8400 |
| labour | 64/64 | 5.5660 | 3.5469 | 5.3310 | 4.3566 |
| national_labour | 128/64 | 4.8098 | 3.8853 | 5.0991 | 5.0983 |
| other_mapped | 258/64 | 1.5087 | 1.4538 | 1.5422 | 1.5088 |
| affirmative_no_party_group | 45/33 | 0.6858 | 0.8927 | 0.6858 | 0.8909 |

RMSE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 64/64 | 5.9608 | 5.6787 | 7.0667 | 7.5175 |
| labour | 64/64 | 7.0598 | 4.5201 | 6.9629 | 5.2639 |
| national_labour | 128/64 | 6.5335 | 5.1322 | 7.0150 | 6.4893 |
| other_mapped | 258/64 | 3.6072 | 3.6279 | 3.6210 | 3.6742 |
| affirmative_no_party_group | 45/33 | 3.4597 | 3.4201 | 3.4597 | 3.4202 |

Signed bias (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 64/64 | 1.3582 | 3.3359 | 2.1300 | 4.0617 |
| labour | 64/64 | -0.7679 | 0.6931 | -1.3191 | 0.1529 |
| national_labour | 128/64 | 0.2951 | 2.0145 | 0.4055 | 2.1073 |
| other_mapped | 258/64 | -0.0484 | -0.9636 | -0.1032 | -1.0094 |
| affirmative_no_party_group | 45/33 | -0.5623 | -0.2053 | -0.5618 | -0.2068 |

Paired group MAE differences (candidate-equal, pp; negative improves):


| Group | B−A | D−C | C−A | D−B | I |
| --- | --- | --- | --- | --- | --- |
| national | 0.1703 | 0.9727 | 0.8137 | 1.6162 | 0.8025 |
| labour | -2.0191 | -0.9745 | -0.2350 | 0.8097 | 1.0447 |
| national_labour | -0.9244 | -0.0009 | 0.2894 | 1.2129 | 0.9236 |
| other_mapped | -0.0549 | -0.0335 | 0.0336 | 0.0550 | 0.0214 |
| affirmative_no_party_group | 0.2070 | 0.2051 | 0.0001 | -0.0018 | -0.0019 |

### 2020 candidate groups


MAE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 34/34 | 9.4448 | 5.8301 | 8.4526 | 5.0256 |
| labour | 34/34 | 5.7854 | 4.6842 | 4.7096 | 3.5295 |
| national_labour | 68/34 | 7.6151 | 5.2571 | 6.5811 | 4.2775 |
| other_mapped | 187/34 | 2.0562 | 1.4220 | 2.1069 | 1.3574 |
| affirmative_no_party_group | 31/20 | 0.2254 | 0.4699 | 0.2264 | 0.4682 |

RMSE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 34/34 | 11.1090 | 7.1137 | 10.0861 | 6.0234 |
| labour | 34/34 | 7.2234 | 5.7304 | 5.9806 | 4.6194 |
| national_labour | 68/34 | 9.3698 | 6.4592 | 8.2915 | 5.3675 |
| other_mapped | 187/34 | 4.2984 | 3.3743 | 4.0153 | 2.8646 |
| affirmative_no_party_group | 31/20 | 0.2516 | 0.5171 | 0.2524 | 0.5141 |

Signed bias (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 34/34 | -8.1336 | -4.9885 | -7.4864 | -4.2113 |
| labour | 34/34 | 1.7355 | 3.1840 | 0.5980 | 1.9804 |
| national_labour | 68/34 | -3.1990 | -0.9022 | -3.4442 | -1.1155 |
| other_mapped | 187/34 | 1.1472 | 0.2526 | 1.2361 | 0.3306 |
| affirmative_no_party_group | 31/20 | 0.0972 | 0.4551 | 0.0985 | 0.4528 |

Paired group MAE differences (candidate-equal, pp; negative improves):


| Group | B−A | D−C | C−A | D−B | I |
| --- | --- | --- | --- | --- | --- |
| national | -3.6147 | -3.4270 | -0.9922 | -0.8045 | 0.1876 |
| labour | -1.1012 | -1.1801 | -1.0758 | -1.1547 | -0.0789 |
| national_labour | -2.3579 | -2.3035 | -1.0340 | -0.9796 | 0.0544 |
| other_mapped | -0.6341 | -0.7494 | 0.0507 | -0.0646 | -0.1153 |
| affirmative_no_party_group | 0.2445 | 0.2418 | 0.0010 | -0.0017 | -0.0027 |

### 2023 candidate groups


MAE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 64/64 | 5.1305 | 4.7483 | 5.4196 | 4.3704 |
| labour | 64/64 | 4.1254 | 3.2749 | 4.6377 | 3.4186 |
| national_labour | 128/64 | 4.6279 | 4.0116 | 5.0286 | 3.8945 |
| other_mapped | 281/64 | 2.6268 | 1.5602 | 2.6662 | 1.6888 |
| affirmative_no_party_group | 50/33 | 0.7614 | 0.9012 | 0.7614 | 0.9015 |

RMSE (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 64/64 | 7.3556 | 7.2003 | 7.3071 | 6.9618 |
| labour | 64/64 | 5.4328 | 4.1419 | 5.9242 | 4.4883 |
| national_labour | 128/64 | 6.4660 | 5.8737 | 6.6517 | 5.8571 |
| other_mapped | 281/64 | 4.6256 | 3.7099 | 4.6385 | 3.7594 |
| affirmative_no_party_group | 50/33 | 2.3403 | 2.2772 | 2.3428 | 2.2843 |

Signed bias (candidate-equal, pp):


| Group | Candidates/present contests | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| national | 64/64 | -2.1171 | 4.4039 | -2.5647 | 3.8245 |
| labour | 64/64 | -2.6893 | -1.2278 | -1.3134 | 0.0171 |
| national_labour | 128/64 | -2.4032 | 1.5880 | -1.9390 | 1.9208 |
| other_mapped | 281/64 | 1.1978 | -0.6808 | 0.9862 | -0.8323 |
| affirmative_no_party_group | 50/33 | -0.5793 | -0.2392 | -0.5788 | -0.2398 |

Paired group MAE differences (candidate-equal, pp; negative improves):


| Group | B−A | D−C | C−A | D−B | I |
| --- | --- | --- | --- | --- | --- |
| national | -0.3821 | -1.0491 | 0.2891 | -0.3779 | -0.6670 |
| labour | -0.8505 | -1.2190 | 0.5123 | 0.1437 | -0.3686 |
| national_labour | -0.6163 | -1.1341 | 0.4007 | -0.1171 | -0.5178 |
| other_mapped | -1.0666 | -0.9774 | 0.0394 | 0.1286 | 0.0892 |
| affirmative_no_party_group | 0.1399 | 0.1401 | 0.0000 | 0.0003 | 0.0002 |

Major-party party-input errors use valid-party shares, while candidate errors use valid-candidate shares. In 2017 National/Labour input MAE is 2.819/2.816pp; candidate-equal S substitution damage is +1.616/+0.810pp versus baseline +0.814/−0.235pp. In 2020 imperfect inputs reduce candidate errors in both models; error compensation is possible and does not imply a causal decomposition. The saved major-party candidate/error pairs and unchanged Stage24 bins (≤−5, (−5,−2], (−2,0], (0,2], (2,5], >5 pp) expose direction without new thresholds, smoothing or subgroup search.

## Fixed-fit influence and rounding sensitivity

Every observation stays in primary scores. Leave-one-contest-out score ranges reuse the fixed predictions without fitting; they are not leave-one-election-out validation. I’s sign survives deletion of any single contest within each primary printed fold. The small 2014 S advantage itself can reverse under single-contest score deletion. Complete paired records and the five largest absolute baseline/S damage and I cases are retained in evaluation.json.

| Year | I min/median/max | I leave-one-contest range | D−C leave-one-contest range |
| --- | --- | --- | --- |
| 2014 | -0.8184/-0.0126/0.7813 | -0.0873/-0.0031 | -0.1571/0.0377 |
| 2017 | -1.1765/0.1113/2.7314 | 0.2602/0.3223 | 0.0168/0.0973 |
| 2020 | -0.5400/-0.1081/0.9527 | -0.0899/-0.0447 | -1.1550/-1.0471 |
| 2023 | -2.8326/-0.0555/1.3372 | -0.1389/-0.0727 | -1.0072/-0.8775 |

| Year | Largest absolute I contest | I pp |
| --- | --- | --- |
| 2014 | Taupo (nz-general-2014-electorate-51) | -0.8184 |
| 2014 | Northcote (nz-general-2014-electorate-34) | 0.7813 |
| 2014 | Kaikoura (nz-general-2014-electorate-20) | -0.7134 |
| 2014 | Pakuranga (nz-general-2014-electorate-38) | -0.4323 |
| 2014 | Rongotai (nz-general-2014-electorate-46) | 0.3933 |
| 2017 | Selwyn (nz-general-2017-electorate-48) | 2.7314 |
| 2017 | Coromandel (nz-general-2017-electorate-07) | 2.2565 |
| 2017 | Rodney (nz-general-2017-electorate-45) | 2.1668 |
| 2017 | New Lynn (nz-general-2017-electorate-31) | 1.4223 |
| 2017 | Taranaki-King Country (nz-general-2017-electorate-50) | 1.3663 |
| 2020 | Mt Albert (nz-general-2020-electorate-24) | 0.9527 |
| 2020 | Taranaki-King Country (nz-general-2020-electorate-50) | 0.9487 |
| 2020 | Rongotai (nz-general-2020-electorate-43) | 0.6320 |
| 2020 | Tāmaki (nz-general-2020-electorate-49) | -0.5400 |
| 2020 | Epsom (nz-general-2020-electorate-11) | -0.5396 |
| 2023 | East Coast Bays (nz-general-2023-electorate-10) | -2.8326 |
| 2023 | Botany (nz-general-2023-electorate-04) | -2.5526 |
| 2023 | Pakuranga (nz-general-2023-electorate-35) | -2.3639 |
| 2023 | Mt Albert (nz-general-2023-electorate-24) | -1.6192 |
| 2023 | Selwyn (nz-general-2023-electorate-45) | -1.5159 |

All saved coupled selected-lower/selected-upper scenarios use their corresponding immutable Stage27 fits, means and feasible source-row features. These are finite rounding measurement sensitivities, not exhaustive extrema or calibrated intervals. None is chosen by performance.

| Protocol | Year | Scenario | A−B | C−D | I |
| --- | --- | --- | --- | --- | --- |
| expanding_window | 2014 | printed | 0.0204 | 0.0643 | -0.0439 |
| expanding_window | 2014 | selected_lower | 0.0204 | 0.0643 | -0.0439 |
| expanding_window | 2014 | selected_upper | 0.0204 | 0.0643 | -0.0439 |
| expanding_window | 2017 | printed | 0.2508 | -0.0481 | 0.2989 |
| expanding_window | 2017 | selected_lower | 0.2508 | -0.0481 | 0.2989 |
| expanding_window | 2017 | selected_upper | 0.2508 | -0.0481 | 0.2989 |
| expanding_window | 2020 | printed | 1.0357 | 1.0950 | -0.0592 |
| expanding_window | 2020 | selected_lower | 1.0357 | 1.0950 | -0.0592 |
| expanding_window | 2020 | selected_upper | 1.0357 | 1.0950 | -0.0592 |
| expanding_window | 2023 | printed | 0.8065 | 0.9224 | -0.1159 |
| expanding_window | 2023 | selected_lower | 0.8065 | 0.9224 | -0.1159 |
| expanding_window | 2023 | selected_upper | 0.8065 | 0.9224 | -0.1159 |
| more_separated | 2017 | printed | 0.2128 | -0.1014 | 0.3142 |
| more_separated | 2017 | selected_lower | 0.2128 | -0.1014 | 0.3142 |
| more_separated | 2017 | selected_upper | 0.2128 | -0.1014 | 0.3142 |
| more_separated | 2020 | printed | 1.1178 | 1.1691 | -0.0513 |
| more_separated | 2020 | selected_lower | 1.1178 | 1.1691 | -0.0513 |
| more_separated | 2020 | selected_upper | 1.1178 | 1.1691 | -0.0513 |
| more_separated | 2023 | printed | 0.8797 | 0.9743 | -0.0946 |
| more_separated | 2023 | selected_lower | 0.8797 | 0.9743 | -0.0946 |
| more_separated | 2023 | selected_upper | 0.8797 | 0.9743 | -0.0946 |

## Interpretation and exact next decision

Source local party geography remains useful against flat national support in the added elections. S retains a complete-share advantage under constructed inputs in 2014/2020/2023, with a 2017 reversal. Primary pooled advantage declines from 0.5675 to 0.5191pp (I +0.0485pp), masking that fold-specific damage. The 2017 I remains positive under chronology, rounding and single-contest influence checks. The sign of I remains negative in the other primary folds. No new success threshold is introduced; earlier frozen Stage27 screens stay unchanged.

Retain S as the preferred complete-share **development** candidate with mandatory baseline. This mixed substitution result does not justify discarding prior residual information or declaring their combination successful. Stage30 supports useful carry-forward information without consistently better fitted retention. Sub-one response remains a possible later joint contribution; asymmetric parity is documented and paused. Every operational selection remains null/unresolved.

These calculations supply actual target national support and retrospective complete slates. They neither verify dated input availability nor establish an as-of/live forecast. Entrants’ flat local affinity is an explicit assumption; no nationally reconciled allocation is claimed. Exact unchanged seats are selected, Māori candidate coverage and changed-boundary transfer remain unresolved, and repeated seats/overlapping transitions share only a few reused election environments. No calibrated uncertainty or winner probabilities follow.

**Recommended next separately authorized scope:** freeze one small coherent joint/regularized complete-share comparison: baseline; S; supported prior normalized residual; S plus prior residual. Define a slate-wide embedding and explicit entrant/unknown-history fallbacks, jointly estimated coefficients and refitted ablations, broad/strict linkage and observed/constructed-input interfaces before fitting. A response contribution enters the shortlist only if a specific coherent representation is justified in that contract. Do not add separately fitted bonuses, search subsets, reopen identities, introduce another party transform or begin integration. This stage implements none of that next task.

## Reproduction, independent checks and preservation

Construction reproduces all 192 matching Stage23 general vectors and all saved Stage27 A/B predictions to 1e−12. The 54 new vectors follow the same rule. Bounded Stage24 checks reproduce all four cells using matching original saved parameters/scenarios to 1e−12; the separate Stage27 original-training comparison uses its already documented 1e−7 numerical agreement, without requiring expanded fits to equal Stage24. All 36 compatibility checks pass.

Independent Fraction count ratios verify 3,826 party cells, direct exponential intensity arithmetic verifies 29,940 candidate shares, and independent sums verify 178 fold metrics and all 21 paired I values at the frozen 1e−8 check tolerance. No fit/solver call occurs. Held-out candidate/winner/identity mutations affect scoring only; held-out local-party mutations change A/B and evaluation but cannot change vectors/C/D; supplied national support can legitimately change vectors. Saved parameters/means are immutable. Required record/raw contracts and all 1,414 prior tracked data artifacts are verified.

Candidate evaluation uses explicit error multiplication e×e for the same registered MSE; this is a numerical serialization choice, not a different equation, tolerance or statistical rule. No earlier output is regenerated. New JSON is compact with sorted keys. The report rounds displayed values to four decimals; machine artifacts preserve precision.

Run each command with `--check` for byte-identical regeneration; omit it only to regenerate this new companion:

```sh
python3 -m scripts.models.expanded_party_substitution.inventory --check
python3 -m scripts.models.expanded_party_substitution.construction --check
python3 -m scripts.models.expanded_party_substitution.evaluation --check
python3 -m scripts.models.expanded_party_substitution.verification --check
python3 -m scripts.models.expanded_party_substitution.report --check
python3 -m unittest scripts.tests.test_stage31_construction scripts.tests.test_stage31_evaluation
python3 scripts/validate/source_files.py
```

Final full-suite/CI status and the PR link are recorded in PROJECT_STATE.md. No formatter/linter is configured for Python; compilation and whitespace checks apply. This Python-only checkpoint does not repeat unrelated frontend checks locally; final-head CI runs them. Stop after review handoff.
