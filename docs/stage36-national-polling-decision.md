# Stage36 national development assessment

## What the frozen test establishes

All eight primary election-day forecasts are numerically accepted. On seven common categories, equal-election/equal-horizon model MAE is **1.7103pp**, versus **1.9570pp** for the pollster-balanced average; RMSE is **2.5808 versus 2.6966pp**. The model improves MAE in six of eight cases. Fourteen-day MAE is1.2108 versus1.4123pp;56-day MAE is2.2098 versus2.5016pp. The average has no probabilistic distribution, so it has no comparable CRPS, interval or energy score.

The benefit is uneven. Election-average MAE gains are about+0.9571pp in2014,−0.1028pp in2017,−0.0435pp in2020 and+0.1759pp in2023. Much of the pooled gain therefore comes from the earliest, especially prior-sensitive environment. National and Labour MAEs are2.5147/3.1863pp, versus average2.7247/3.5816pp. These consequential errors are larger than the all-category average. This is development evidence for retaining the owned model and its average control, not a strong superiority or deployment finding.

## Uncertainty is present, but not established as calibrated

Common polling error survives repeated observations: National/Labour current SD ranges roughly1.59–3.62pp and election-day SD1.83–5.10pp across the eight cases. Future diffusion increases their uncertainty within each case. This supports the intended mathematical information flow; it does not prove the error distribution is correct.

Across56 coarse party/case observations,50% intervals cover20/56 and90% intervals44/56. By horizon,90% coverage is24/28 at14 days and20/28 at56 days. Major-party90% coverage is15/16; other categories29/40. All these observations are dependent within and between two horizons of four reused elections; they are not independent calibration replications. The2017/56-day Labour error is−10.2685pp and misses its90% interval. Average90% widths rise from4.6176pp at14 days to5.3381pp at56 days, but early-horizon undercoverage remains material. Prior-sensitive common-error scale means exceed their prior scale, especially in2014; these are conditional posterior parameters, not independently measured common polling-error calibration. No priors or interval widths are retuned.

## Finite sensitivities

Ten-day timing retains eight fits and pooled MAE1.7608 versus average1.9775pp. It changes2020/14 from a small advantage to a small disadvantage, and reduces2023/14 MAE advantage from0.1384 to0.0124pp. Missing-n1000 retains eight fits and MAE1.6007 versus1.9570pp;2017/14 changes from−0.2402pp to+0.2956pp improvement. That is a consequential sample-assumption sensitivity, not permission to select1000 using its scores. Missing nominal sample sizes affect every admitted2014/2017 wave. Timing is predominantly inferred; inferred fieldwork may itself reflect release-date approximations.

Verified-only forecasts exist for only2020/14 and2023/14. Their available-only model MAE2.6197 versus average2.5336pp cannot replace the full eight-case comparison. Six cases explicitly abstain for lack of usable current-cycle evidence. Primary overlap selection can keep a later inferred wave instead of an earlier verified wave; the2023 verified Roy Morgan August wave is one such case. Verified-only is a different permitted information subset, not necessarily nested after overlap selection. Earlier-result publication remains assumed and source versions retrospective even here.

## Numerical reliability and independent checks

Twenty-six accepted case records use22 distinct accepted fits. Two verified-only first attempts had14/25 divergences; their single frozen retries pass and original failures remain archived. Accepted attempts have no divergences or depth contacts, maximum all-coordinate R-hat1.009747, minimum bulkESS628.017 and minimum tailESS460.464. BFMI and every relevant latent/house/method/bias coordinate remain visible. No chains, gates or priors changed. All32 declared cases are terminal, including the six data abstentions.

Distinct attempts total6.05 worker-hours on the pinned ARM64/Python3.12.2/NumPyro0.19/JAX0.6.2 runtime; two disjoint queues overlap in wall time. The cache guard never paused a process and no fit was duplicated. `requirements-polling.lock`, `environment.json`, exact signatures, seeds, attempt archives and resume commands permit continuation without recomputing completed MCMC.

Independent arithmetic verifies485 constrained poll projections,26 benchmark averages,192 representative paired transformed draws,48 expected-share vectors,68 point/pooling checks and410 probability/interval/aggregation checks. The complete forecast archive was committed and pushed as0d07043 before evaluation. Source, numerical portability and benchmark corrections are separately documented; none used forecast errors. Routine CI verifies deterministic archives and scores, while local isolated tests cover likelihoods/gradients and synthetic inference. Their exact final status is in PROJECT_STATE/PR.

## Exact next decision

Retain the frozen national component as a development candidate and the average as its mandatory national control. Do not claim calibrated uncertainty or a definitively superior polling model. The component supplies coherent current/election-day joint draws, but **is not yet a complete candidate-replay interface**: Other does not identify fine election-local ballot groups. The smallest separately authorized next task is a bounded **Other-to-local-category replay contract**, using preserved rosters/evidence, explicit uncertainty and no outcome-derived constituent allocation. It should settle the interface and frozen replay samples before any candidate predictions. No national model tournament, score-guided prior change or additional acquisition follows automatically.

Once that dependency is explicitly resolved, the saved national component/average may feed one separately authorized end-to-end replay of fixed baseline/S/R/S+R alternatives. Polling performance does not select a candidate model or erase conditional component evidence. S/S+R remain active, R challenger, baseline control. National draws must be shared across electorates once, and downstream expected shares must average nonlinear transformed draws. All historical operational selections remain null; no candidate replay, live2026 forecast or MMP integration is performed here.
