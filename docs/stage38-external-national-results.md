# Stage38 — bounded external joint national comparison

2026-10-05. Source protocol3d76c77/preservation47dfce8, frozen executionfa08640, accepted forecast checkpoints42d9ba6/eff424a precede scoring. No owned inference, candidate replay, parameter tuning or operational selection. Upstream gauss pin `ef76cf6562e1d028b4fff46d063f4b93945299de`.

## Coverage and information sets

All three2017/2020/2023 cases at exactly56 days are accepted. Primary common partition: National, Labour, Green, ACT, NZ First, all remaining parties. Every complete draw, mean, official outcome and average uses this partition; no subset normalization or Stage37 fine allocation. Te Pāti Māori/TOP remain in raw schemas wherever upstream models them. Aggregation is benchmark-only and does not remove TPM from eventual forecasts. No richer secondary partition was added.

| Election | Cutoff | Eligible polls | Missing published n | Earlier result anchors | External schema |
|---|---|---:|---:|---|---|
| 2017 | 2017-07-29 | 199 | 199 | 2011,2014 | National, Labour, Green, ACT, NZ First, Te Pāti Māori, New Conservative, United Future, Other |
| 2020 | 2020-08-22 | 250 | 219 | 2011,2014,2017 | National, Labour, Green, ACT, NZ First, Other |
| 2023 | 2023-08-19 | 358 | 231 | 2011,2014,2017,2020 | National, Labour, Green, ACT, NZ First, Te Pāti Māori, TOP, Other |

Five new resources (cap6): pinned official repository archive plus four bulk historical Wikipedia pages. GPL-3.0-or-later upstream code/config/notices are retained separately; Wikipedia source attribution/URLs/raw bytes/checksums/retrieval dates remain. No wider search or individual poll acquisition. Prepared snapshots are reconstructed from2026 retrievals under pinned rules, not claimed identical to inaccessible archived input fingerprints.

Inputs respect case cutoffs and exclude target/later results: adapter passes only earlier outcomes; result rows never become polls. Actual-pipeline mutations of held-out results, post-cutoff poll shares and future-only publication revisions leave dataset fingerprints unchanged. Permitted earlier results can change anchors. Earlier anchors use upstream rounded reference results; all systems are scored against the same exact preserved official national outcomes.

Retrospective limitations: fixed2.5 minor-party error factor/8% threshold explicitly developed from2011–2023 misses; its cutoff-derived scale affects all cycle industry offsets. No direct held-out fitting, but not wholly chronological prior development. Publication day is fieldwork end plus pollster-specific lag, not verified hour/timezone. Schema uses prior parliament and pre-cutoff auto-tracking. Source-specific sample defaults, missing denominators, midpoint/Sunday-week fieldwork, parser threshold midpoint and inferred rounding, residualOther differ from our Gaussian interval/censoring/daily-fieldwork model. This is a national system comparison, not a matched-input architecture experiment or certified as-of validation. No ensemble/spread calibration or extra common-error draw.

Weekly target approximation: upstream target_t is the Sunday-start election week (2017-09-17, 2020-10-11, 2023-10-08), representing support for the Saturday election rather than a separate daily election-day state. Calendar cutoffs remain exactly56 days before election day. This preserved time-resolution difference is not an extra forecast or a changed horizon; no weekly-to-daily extrapolation was added.

The source-only reported-row audit retains3/1/6 overfull observed rows in2017/2020/2023, maximum0.4/0.3/1.2pp excess. These remain unchanged Gaussian measurement observations, not an exactly normalized source simplex; every posterior draw remains coherent. Wave-level rounding precision is inferred from all cells, so minor tenths can imply tenths for whole-percent major observations. This differs from owned per-cell rounding intervals and is a measurement-approximation limitation, not a reason to silently normalize, delete rows or change the external model. See reported-row-audit.json.

## Point accuracy — percentage points

Equal election weights1/3. RMSE pools squared category errors before taking the root. Global signed share bias cancels by construction; category bias is below.

| Election | Our MAE / RMSE | Gauss MAE / RMSE | Average MAE / RMSE | Our minus gauss MAE |
|---|---:|---:|---:|---:|
| 2017 | 3.4228 / 4.8831 | 3.4914 / 4.8451 | 3.4135 / 4.7540 | -0.0686 |
| 2020 | 3.0896 / 3.7693 | 2.9804 / 3.4363 | 2.8753 / 3.2577 | 0.1092 |
| 2023 | 2.5647 / 2.8088 | 2.6585 / 3.0960 | 2.6613 / 3.0361 | -0.0938 |
| Equal-election pool | 3.0257 / 3.9133 | 3.0434 / 3.8673 | 2.9834 / 3.7608 | -0.0177 |

### National/Labour on original national-share denominator

| Election | Our NAT / LAB signed error | Gauss NAT / LAB signed error | Average NAT / LAB signed error |
|---|---:|---:|---:|
| 2017 | 0.0002 / -10.2685 | 2.7766 / -10.1079 | 1.3001 / -9.3152 |
| 2020 | 1.9140 / 7.2210 | 3.0658 / 5.8387 | 3.1101 / 5.5160 |
| 2023 | -3.9319 / 3.7708 | -4.4447 / 3.5398 | -3.8631 / 4.3112 |

Major-party pooled MAE / RMSE: ours 4.5177 / 5.6410; gauss 4.9623 / 5.5626; average 4.5693 / 5.1973. Six major-party cases; no two-party renormalization.

| Category | Our signed bias | Gauss signed bias | Average signed bias |
|---|---:|---:|---:|
| NAT | -0.6726 | 0.4659 | 0.1823 |
| LAB | 0.2411 | -0.2431 | 0.1707 |
| GRN | -0.3173 | 0.1671 | 0.9323 |
| ACT | -0.1850 | 0.3152 | 0.2177 |
| NZF | 0.9355 | 0.4577 | -0.1347 |
| REST | -0.0016 | -1.1627 | -1.3683 |

## Joint forecast distributions

Election-day joint draws,8,000 per case/model. Expected shares average transformed draws. CRPS exact empirical univariate; intervals central linear quantiles; proper interval score penalizes both width and misses. Energy uses the frozen deterministic2,000-draw subset/128-block empirical V-statistic, not invented independent party draws. Scores/widths below use pp units. The average has point forecasts only.

| Election / system | CRPS | Energy | 50% covered / 6 | 90% covered / 6 | 50% width / interval score | 90% width / interval score |
|---|---:|---:|---:|---:|---:|---:|
| 2017 / owned | 2.9396 | 9.7596 | 1 | 2 | 2.0779 / 12.8649 | 5.0861 / 39.4252 |
| 2017 / gauss | 2.6835 | 9.0742 | 2 | 4 | 2.6017 / 11.5779 | 6.7410 / 30.8858 |
| 2020 / owned | 2.2933 | 6.8014 | 2 | 3 | 2.9695 / 10.4916 | 7.2537 / 19.1415 |
| 2020 / gauss | 2.0438 | 6.0511 | 2 | 6 | 4.5060 / 8.8166 | 11.5403 / 11.5403 |
| 2023 / owned | 1.6042 | 4.5978 | 1 | 6 | 3.3077 / 7.1350 | 7.9814 / 7.9814 |
| 2023 / gauss | 1.6434 | 5.0047 | 2 | 6 | 4.6814 / 7.0551 | 11.7949 / 11.7949 |

| System, pooled | CRPS | Energy | 50% covered / 18 | 90% covered / 18 | 50% width / interval score | 90% width / interval score |
|---|---:|---:|---:|---:|---:|---:|
| owned | 2.2790 | 7.0530 | 4 | 11 | 2.7850 / 10.1638 | 6.7737 / 22.1827 |
| gauss | 2.1236 | 6.7100 | 6 | 16 | 3.9297 / 9.1499 | 10.0254 / 18.0736 |

Gauss90% misses:2017 Labour and Green. Owned90% misses:2017 Labour/Green/NZFirst/remainder,2020 Green/ACT/remainder. Both miss2017 Labour by about10pp and both cover5/6 major-party90% cases. Gauss coverage gains therefore occur mainly in minors/remainder; neither model resolves the major2017 shock. At50%,4/18 owned and6/18 gauss remain below nominal. Three elections and dependent categories cannot establish calibration. Wider intervals alone would not establish quality; lower pooled CRPS/energy/proper interval scores provide the additional evidence, with2023 favouring ours.

### Fixed-forecast election influence

| Omitted election | Our pooled MAE | Gauss pooled MAE | Average pooled MAE | Our CRPS | Gauss CRPS |
|---|---:|---:|---:|---:|---:|
| 2017 | 2.8272 | 2.8195 | 2.7683 | 1.9487 | 1.8436 |
| 2020 | 2.9938 | 3.0750 | 3.0374 | 2.2719 | 2.1634 |
| 2023 | 3.2562 | 3.2359 | 3.1444 | 2.6165 | 2.3636 |

These are fixed-prediction influence summaries, not new forecasts/refits. MAE ordering changes with the retained elections. Few environments, retrospective fixed calibration and data differences prevent strong generalization claims. Stage36/37 historical comparisons remain unchanged; their headline pools use different categories/cases and are not substituted here.

## Numerical reliability and reproducibility

| Election | Attempt | Seconds (sampling + full diagnostics) | Active audited coordinates | Maximum rank R-hat | Minimum bulk / tail ESS | Divergences / depth contacts |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 1 accepted | 146.1 | 7946 | 1.004229 | 2029.5 / 1750.7 | 0 / 0 |
| 2020 | 1 accepted | 121.5 | 7767 | 1.006115 | 1149.4 / 904.6 | 0 / 0 |
| 2023 | 1 accepted | 320.2 | 14435 | 1.004804 | 1439.0 / 2045.9 | 0 / 0 |

All three first attempts accepted; zero numerical failures/retries. Supervisor compute 601.9sec (0.167 worker-hours), versus six-hour total/two-hour case cap.18 stochastic/derived sites including full free theta/pi,z,Lcorr,raw house/industry and hyperparameters were audited; counts are diagnostic coordinates, not independent political observations. Only mathematically fixed anchored states/triangular constants are exempt. All-chain BFMI passes. ARM64/Python3.12.2, NumPyro0.19/JAX0.6.2 with four CPU devices/x64; full transitive requirements-external.lock/environment/source signatures saved.

Execution-guard-amendment.json records a post-run cache enforcement companion: future supervisor resumes validate extracted upstream source/code/environment, reject unexpected configuration-root overrides and compare full completed-case signatures before skipping. Three focused guard tests and a full cache-only resume pass; frozen numerical runner, all forecast/archive signatures and bytes remain unchanged. No historical inference reran.

Exact compatible cache reuse verified; no finished inference rerun. Archives keep joint current-last-data/election-day draws, chain IDs, hyperparameter chains and every active diagnostic statistic. Last-data support is not claimed an exact cutoff nowcast. High-dimensional raw samples remain in isolated runtime cache for local independent audit, with checksums recorded; CI validates sealed forecasts/diagnostic dispositions and recorded audits without requiring that local cache. Upstream equations/config/code remain byte-pinned in the separate GPL archive. No statistical changes or tolerances relaxed.

Independent verification: 410 point/CRPS/quantile/interval/energy/pooling identities; 48,000 model joint vectors; all 1,621 prior data files byte-identical; five new resources verified. Separate raw-cache audit checks48 latent-to-simplex transformations and cached hyper Rhat/bulk/tail ESS. Actual preparation counterfactuals and synthetic schema/metric/cache tests pass. Final-head CI status is reported separately at completion; it does not rerun MCMC. No configured Python formatter/linter; compile/whitespace/source and deterministic checks apply.

## Ownership-neutral decision and next boundary

Retain both national systems for development. External gauss is an active distribution alternative: pooled proper scores and coverage improve materially, not just through a point-error accident. The point difference0.018pp is too small to select either, the average is slightly better on point MAE, and major-party accuracy/2023 proper scores favour ours on some metrics. Evidence does not justify automatic operational replacement or uncertainty recalibration. No ownership preference or significance/causality hurdle is imposed.

External adoption would require only a narrow national-output adapter and maintained pinned preparation/inference environment, with GPL attribution/licensing reviewed for distribution. Emit stable common draw IDs, cutoff/horizon/schema metadata, separate current/election support, explicit TPM wherever modeled, and mass-conserving conditional fine-category mapping. Do not copy upstream electorate/MMP assumptions. The external complete historical schemas differ from ours: Other allocation must respect explicit NewConservative/UnitedFuture versus TOP/MRI withinOther. No constituent allocation or live-output guarantee is inferred. Its richer covariance/campaign/cycle effects increase maintenance complexity, while these three runs were practical; prior archived reproducibility was weaker but this reconstruction now has precise fingerprints and diagnostics.

**Next separately authorized task:** fixed-candidate conditional replay through preserved complete local affinity and saved Stage33 baseline/S/R/S+R fits. Use existing owned14-day primary/56-day diagnostic archives; a matched external reference is available only for2017/2020/2023 at56 days. Freeze a minimal schema adapter under Stage37 allocation policies before applying external draws, and label this subset rather than manufacture14-day/2014 external fits. Every national draw stays shared across seats; average transformed candidate shares, retain all slates/features/fallbacks, and do not add national uncertainty twice. Model alternatives/specifications stay fixed. This stage ran no candidate predictions or scores. National results are not isolated evidence for/against S or R; component, substitution and end-to-end evidence remain distinct (D067).

### Māori electorate polls — planned, not implemented

For2026 incorporate available Māori electorate polls through a separately designed layer alongside an explicit Māori-seat baseline. National Te Pāti Māori party-vote support and local candidate-vote support are distinct. Preserve each poll question (candidate/localparty/both), denominator, fieldwork/publication/sample and uncertainty; connect slate/identity/target boundaries and shared national support without double-counting. Treat polls as noisy evidence, not exact results. Unpolled/stale seats require a documented fallback with wider uncertainty. Design its dependence and joint uncertainty before live integration. No such acquisition or implementation occurred here.

Roadmap: Stage38 review → bounded fixed-alternative candidate replay → deployment decision and fine-category/national reconciliation work → separately designed Māori/direct electorate polling and dated live inputs → coherent joint uncertainty/MMP/archive outputs. No new national variants, learned blend, candidate refit, acquisition or live2026 forecast starts automatically.
