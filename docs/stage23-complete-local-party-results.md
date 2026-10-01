# Stage 23 conditional complete local party-share results

The [frozen specification](stage23-frozen-specification.md), [inventory](stage23-input-inventory.md) and [construction artifact](../data/processed/models/complete-party-vector/construction.json) were committed before opening the target local party results. This is a parameter-free **conditional** development diagnostic: it supplies the target election's observed nationwide valid-party shares. No national forecast, candidate prediction, winner probability or operational selection follows from these scores.

## Complete-vector coverage and errors

All 213 fixed unchanged-boundary party-ballot seat pairs construct a complete target party-group simplex: 191 held general, 21 Māori and the 2023 Port Waikato party ballot whose candidate contest was cancelled. There are no mapping or numerical abstentions in this historical frame. The 191 held general records are a complete party-input interface for a separately authorized Stage 22 input-substitution test; Stage 22's candidate mapping and other candidate applicability limits remain separate. All 1,192 mapped Stage 22 candidate/group keys on its complete contest records occur exactly once in these vectors. No independent is made into a party ballot group.

Equal-electorate, equal-party-within-electorate errors (percentage points):

| Target | Scope | Seats | Compositional MAE / RMSE | Flat national MAE / RMSE |
| --- | --- | ---: | ---: | ---: |
| 2011 | General | 63 | 0.624 / 1.395 | 1.906 / 4.600 |
| 2011 | Māori | 7 | 2.316 / 4.371 | 6.733 / 12.782 |
| 2017 | General | 64 | 0.518 / 1.281 | 1.418 / 3.766 |
| 2017 | Māori | 7 | 0.519 / 1.062 | 4.842 / 11.449 |
| 2023 | General party ballots | 65 | 0.551 / 1.094 | 1.601 / 3.648 |
| 2023 | Māori | 7 | 1.506 / 3.462 | 5.546 / 11.567 |

The fixed **191 held general** subset has MAE/RMSE 0.565/1.263 versus the flat national vector's 1.638/4.022. This is the candidate-comparison *input* subset, not candidate accuracy. Observed target electorate valid-party-vote weighting yields model versus flat MAE 0.609/1.876 (2011), 0.510/1.397 (2017), 0.549/1.586 (2023) for general seats. These oracle weights enter evaluation only.

Pooled across the reused transitions, the 192 general **party ballots** (including Port Waikato) have model/flat MAE 0.564/1.640pp; the 21 Māori party ballots have 1.447/5.707pp. These pooled figures weight electorates equally, not elections equally, and do not create more independent election transitions. Maximum local-vector sum-to-one residual is 2.22×10⁻¹⁶.

The frozen 0.25pp descriptive screen passes in both 2017 and 2023 general folds: MAE improvements are 0.900 and 1.050pp, with no RMSE regression and complete coverage. This weak flat-national benchmark chiefly tests whether source local geography adds information when target national support is supplied. It cannot select an operational party-input transform. The reused elections are developmental evidence with three transition clusters, not independent confirmations.

NAT and LAB local errors remain material despite small equal-category overall MAE: 2017 general MAE is 2.819pp for National and 2.816pp for Labour; 2023 values are 2.184pp and 2.211pp. Labour's 2023 signed local bias is +1.109pp. Entrant affinity is the neutral national profile assumption; it is not locally validated entrant strength. An observed source zero remains zero for a continuing group under the point rule. The full predeclared category and source-zero breakdown is in [`scores.json`](../data/processed/models/complete-party-vector/scores.json).

On the exact Stage 5 aligned general electorate/group rows, Stage 23's category MAE is 0.590/0.674/0.827pp (2011/2017/2023). Stage 5 log-odds is 0.576/0.581/0.801pp on those **selected continuing-category cells**; additive and proportional figures are also retained in the machine report. This comparison uses the same observed national conditioning and exact geography, but Stage 5 has no entrant/exit complete-vector coverage. It cannot rank full local scenarios against marginal predictions or resolve Stage 5's operational transform choice.

## National accounting and uncertainty

The constructed local vectors are nonnegative and sum to one in every electorate. They are **not** constrained to aggregate back to the supplied national vector. Using all target party-ballot electorates and observed target valid-party totals as oracle weights, the largest party-category national gap is 0.295pp in 2011, 0.872pp in 2017 and 0.313pp in 2023. The respective half-L1 gaps are 0.467, 0.880 and 0.406pp. The 191 held general subset alone cannot establish a national accounting identity.

The rule transports exact unchanged-boundary source party shares and a neutral national profile for entrants. Its zero handling, exit redistribution and absence of exact reconciliation are **assumptions**, not estimates of future behaviour. No calibrated interval accompanies this point scenario. Source geography is exact for these three historical transitions; the coupled 2023-on-2026 geographic bounds remain unconverted to a point and no changed-boundary validation or 2026 vector is produced. The supplied national scenario, historical source geography and the full target party-category list are still required in any later use. Forecast-time national support and electorate turnout weights are not supplied by this stage.

## Next bounded decision

The complete party-group key interface removes the **structural vector coverage barrier** for a separate, explicitly conditional Stage 22 input-substitution experiment: reuse its saved earlier-trained baseline and S-only parameters without refitting, replace observed target local support with this Stage 23 vector, and compare on fixed common candidate samples. That experiment needs separate authorization and must retain retrospective slates and observed target national support labels. It must not zero-fill, stack candidate effects or claim an as-of forecast. If the national aggregate gap is unacceptable for later operational use, a separately specified, complete-population reconciliation and as-of weight/input design is needed. No candidate test or reconciliation fitting was performed here.

Reproduction: `python3 -m scripts.models.complete_party_vector.inventory --check`, then `construction --check` and `evaluation --check` with the same module prefix. The stage-specific source contract pins consumed records and raw bytes while allowing unrelated registry additions. Stage 5–22 numerical artifacts, identity records and null operational selections remain byte-identical.
