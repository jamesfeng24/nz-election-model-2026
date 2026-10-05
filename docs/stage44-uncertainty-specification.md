# Stage44 frozen local-party and candidate uncertainty

2026-10-05. One family, frozen before scale estimation or uncertainty scores. External gauss provisional; S+R preferred, S active/baseline mandatory. No mean refit, model selection, new source, MCMC, live slate normalization or Māori coefficient extension.

## Inventory and finite plan

1. Preserve exact references for 321 general party vectors (2011/14/17/20/23:63/64/64/65/65) and 257 earlier-fit candidate vectors (64/64/65/64; 1,902 candidates). Retain wider canonical frame, missing records, Māori and cancelled status. Port Waikato 2023 has a valid party ballot but no candidate residual. 2011 has no candidate fit.
2. Commit inventory, this specification, machine constants and input hashes before uncertainty estimation.
3. Fit pooled scales from completed earlier residual transitions, save component simulations before scoring; then one bounded composed diagnostic on cached external56-day forecasts2017/20/23 and complete general slates64/65/64. No new horizons or national inference. Save resumable deterministic caches/signatures.
4. Independently verify, test actual adapters/chronology, reproduce, configured checks, PR unmerged. Stop; poor results do not authorize a family search.

Party conditional means reuse Stage31 exact vectors; changed2014/20 source geography uses the same Stage41 feasible uniform-within-source party-flow witness plus unchanged Stage23 affinity/entry/exit closure conditional on observed national support. Candidate conditional means use Stage43 continuous joint2014/20, Stage33 primary_fixed_to_observed2017/23, each own earlier primary fit and frozen means. Exact equivalence must reproduce. Constructed-input primary candidate errors and threshold-policy errors are not candidate uncertainty evidence. Every election is repeatedly inspected development data.

## Transform, zeros and units

For an observed/predicted complete K-vector x, use fixed additive resolution replacement x*=(x+epsilon)/(1+K epsilon), epsilon=1e-6 shares (0.0001pp), for residual calculation only. CLR(x*)=log(x*)−mean(log(x*)). Residual e=CLR(actual*)−CLR(frozen prediction*), dimensionless log units, sum zero. It treats standing zero votes as finite-resolution observations, not absence; no rounded count inference. Structural absent options are absent from the election-local roster. Missing categories never become zero. Candidate κ keeps standing prediction positive.

CLR has redundant coordinates constrained to sum zero; no arbitrary reference party. The inverse is stable softmax. Noise and estimation project onto this tangent subspace; rank is assessed only in independent shared-class contrasts. Exact roster/slate IDs and group mappings support varying K. Same displayed names do not bridge categories or persons.

**Zero-mean lock:** a frozen predicted zero remains on the zero simplex face in every draw. It cannot have positive arithmetic mean or cover a positive observed vote while preserving mean0. This is not a claim of structural absence; explicitly flag such misses. Stage31 contains a source-zero/target-positive minor-party case. Do not silently add a positive mean scenario in this stage.

## Pooled dependence family and estimation

For each layer and draw, eta_e=P_e[s_shared h_class(e)+s_seat u_e], where P_e=I−11'/K, independent unit Gaussian h is shared by all seats in the same election, and u has one independent value per stable option ID/seat. Classes are National/Labour/other for parties, plus affirmative no-group for candidates. Others deliberately share one effect; no fine-party or seat covariance matrix. Shared-local effects describe conditional geography error even when national truth is supplied; shared-candidate effects describe conditional allocation error even when local truth is supplied. They are not additional national poll errors.

Estimate shared effects within each earlier election by equal-contest least squares of e on centered class indicators in G−1 orthonormal Helmert contrasts, with weight1/K per coordinate (one total weight per contest). Require finite full rank; solve directly, no pseudoinverse. Shared second moment is ||b_y||²/(G−1); do not remove historical across-election bias or apply it as a mean correction. Seat second moment is the mean across seats of ||e−P H b_y||²/(K−1). Each election contributes equally to pooled scale estimation. This low-dimensional moment procedure is an approximation; seats estimate within-election variation, not extra election environments.

Strong pooling: scale²=(sum of available election second moments+3 priorScale²)/(number of available election moments+3). Fixed log-unit prior scales: party shared0.15/seat0.35; candidate shared0.20/seat0.50. These imply modest multiplicative odds uncertainty (roughly1.16/1.42 and1.22/1.65), chosen structurally before scores, not calibrated facts. No earlier evidence uses the prior directly. A rank-deficient election's shared moment is unavailable; retain its unprojected residual seat moment and the shared prior, with explicit status. One environment can inform a development estimate without claiming reliable calibration.

Fit separately for each target using only earlier target years;2011 party and2014 candidate are assumption-based. Full-panel descriptive scales are separate and never used for earlier forecasts. No parameter jitter: coefficient uncertainty and scale-estimation uncertainty are omitted as explicit draw components; predictive residuals already reflect earlier fixed-fit estimation error. Few environments, accepted algorithmic identity and shared normalization remain warnings, not automatic exclusions.

Cross-layer noise is independent as an explicit approximation. Before interpreting scores, report National/Labour conditional residual association on matching seats, including within-election-centered correlation. Conditional definitions do not prove independence. Do not estimate a cross-layer covariance matrix.

## Arithmetic expected shares and location adjustment

For fixed conditional mean m and generated finite zero-mean Gaussian bank eta, solve a centered location offset a such that mean_d softmax(log(m)+a+eta_d)=m on m's positive face. Iterative log-ratio updates, max1,000 iterations, share tolerance1e-10; stable softmax, simplex tolerance1e-12; failure is explicit numerical abstention. No outcomes enter this adjustment. All-zero face is invalid. This finite-ensemble mean-preservation is a numerical correction, not historical bias fitting or proof of an underlying exact logistic-normal expectation.

For a varying ensemble of supplied national/local inputs, solve one offset preserving the ensemble mean of each layer's deterministic conditional vectors. Thus marginal arithmetic mean is preserved at that layer; **per-national-draw conditional preservation is not guaranteed**. Candidate means can still shift relative to the no-local-error pipeline because the candidate map is nonlinear in uncertain local support. Report frozen deterministic vectors, log-space offsets, simulated expectations, finite-bank errors and composed nonlinear shifts separately. Do not replace averaging transformed draws with transforming average inputs.

## Simulation, transport and limits

Primary512 draws with antithetic consecutive normal pairs, seed20261005; stable SHA256-derived PCG64 keys distinguish layer, shared class, seat/option and draw position. Shared IDs are reused across seats. National subset is a fixed seeded interleaved-chain selection from cached8,000 draws, chosen without outcomes; chain/draw IDs retained. Never independently redraw national support by seat or add a second national common-error draw.

Primary includes ordinary uncertainty estimated from both exact and continuously transported residuals. No extra primary transport variance. Exactly one stress scenario: multiply candidate seat variance by1.5 on nonexact seats, an assumed 50% excess beyond pooled ordinary variance, not a fitted overlap relationship or independent known boundary variance. Use the same random banks, no new threshold. Do not add it to local-party variance. Primary moment evidence already includes transported seats, so stress may duplicate some transport variation and is deliberately labelled sensitivity, not calibrated correction. No probability over feasible-flow vertices or Other policies.

Use only existing recent_report_prior Other allocation for the bounded composed diagnostic; prior_only remains a separate preserved scenario. Explicit national categories/draw dependence remain unchanged. National reconciliation is not imposed. Interface retains complete categories and can later accept an all-population weighted reconciliation operator before candidate mapping; such an operator would change the uncertainty dependence and require a separate contract. No selected-subset reconciliation claim.

Precision check uses1,024 draws on deterministic first/last seat per available component election and per composition case, with primary bank prefix retained. Report expected-share and score differences without changing sizes/scales after results. No large simulation grid. Cache deterministic draw vectors locally with hashes and committed compact summaries; CI recreates missing caches, no MCMC.

## Frozen scoring and reporting

Components: local party conditional on national truth; candidate conditional on local-party truth. Composed: external gauss→local uncertainty→fixed joint mean→candidate uncertainty on identical eligible slates, no new mean restrictions. Report by election and layer, equal-contest MAE and RMSE (root mean contest MSE), candidate/party-equal sensitivities; pooled contest-weighted and equal-election views with denominator counts. Major parties remain visible.

Marginal CRPS via empirical sorted-draw formula; central50/90% intervals, count/coverage/width and proper interval score (width+2/alpha penalties outside); energy score using first128 stable joint draws with V-statistic pair distances, same fixed approximation for all cases. Scores in pp on original unrounded shares. Complete-vector energy keeps dependence. Correlated coordinates/horizons are not calibration replications; wider intervals alone are not improvement.

Candidate probabilities: full-slate winner frequencies with explicit ties at1e-12, multiclass Brier and actual-winner negative log probability; report infinite/unresolved if zero probability, no invented probability floor. Competitive pair is the two highest **deterministic prediction-time** candidate shares (stable IDs only resolve equal predicted ranks); score pair-win Brier and predicted-pair margin intervals/CRPS. Observed-top-two margin diagnostic is separately labelled evaluation-only. Do not claim calibrated electorate win probabilities from this reused small panel.

Report missing-feature mass, identity tiers, exact/transported status, zero locks, sparse/prior warnings, substantive misses and transport stress. No automatic all-fold gate; assess proper scores, misses and mean preservation honestly. Stop after this family. Official nominations, separate Māori baseline/polls, reconciliation/turnout and MMP/live assembly remain blockers.
