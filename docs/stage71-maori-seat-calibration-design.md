# Stage71 design (frozen before any corrected arm was scored): calibrating the Māori seat layer

Decision number D105. Internal only: nothing is adopted, published or released. The Māori seats stay modelled completely separately from the general electorates: no general-seat data, calibration, regression or output is read or changed, and neither are the national model or the MMP allocator. The Stage66 layer, its code and its outputs are read only.

**One question.** What correction, fitted only on earlier elections and scored chronologically on the 25 historical Māori electorate polls, restores calibration of the Stage66 layer, and how much does it widen or shift the 2026 seat probabilities for the three polled seats?

## Disclosure about what was known when this was frozen

Stage66's findings were read first: its leave-one-election-out backtest (mean predicted poll-leader win 0.82 against 15 of 25 observed, 2 of 7 in 2023, Brier 0.208 against 0.240 for a constant 0.6); the four election means of the Māori Party-versus-Labour error D (-0.07, -0.11, +0.34, +0.45); the minor-candidate noise ratio (4.0 times `2 sigma^2`); the 2020 and 2023 Curia-era pattern. No corrected arm, no inflation factor and no chronological score had been computed when this file was committed. Because the pattern was known, the arms below are fixed by this document and the finding classes are pre-registered; a result is a finding about the design, not a search.

## Control and arms

All arms use the 25 historical polls and the Stage66 estimation code unchanged (`scripts.maori_seat_layer.fit`: sigma^2 by within-election pooled variance of D over 2, tau^2 by method of moments about the arm's bias, scaled inverse chi-square draws for each, closure over named candidates, unnamed remainder not scored). The control reproduces Stage66's stored leave-one-election-out backtest exactly (same seeds, same draw order; tested).

- **C (control).** Stage66 unchanged: `b = 0`, no inflation.
- **P (primary).** One variance inflation `lambda` multiplying both `sigma^2` and `tau^2` of every draw (an error-scale correction, `kappa = sqrt(lambda)`), fitted **penalty-free** (maximum likelihood, no prior, no shrinkage, not constrained to be at least 1) on the training elections only.
- **PB (secondary).** P plus a pollster-era bias `b` for the Māori Party candidates. The era is the pollster: Reid Research (2014, 2017) or Curia (2020, 2023, 2026). `b` for an election is the equal-weight mean of the election means of D over the training elections **of the same pollster** (zero if there is none). Training elections' own `tau^2` is estimated about their leave-self-out same-pollster `b`, so the residual variance includes the error of `b`-hat. This arm is weakly identified (see the cap below) and is reported, not recommended.

## The inflation, exactly

For a poll with candidates `i = 1..K` and reference candidate 1, the observed error contrasts are `x = A d` with `d_i = log v_i^c - log q_i` (closed result minus closed poll, log scale) and `A = [-1 | I]`. Under the Stage66 model `d = eps + (b + u_e) m + const`, `m` the Māori Party indicator, so `x` has mean `b A m` and covariance `sigma^2 A A' + tau^2 (A m)(A m)'` for one poll, and the election-level `u_e` couples the polls of an election through `tau^2 a a'` with `a` the stacked `A m`. With `Sigma_e` the stacked covariance at the arm's own (sigma^2, tau^2) estimated from the training contrasts and `S = sum_e r_e' Sigma_e^{-1} r_e` (`r_e` the stacked residuals `x - b A m`), `N = sum_polls (K - 1)`, the maximum-likelihood multiplier is `lambda_hat = S / N`. It uses **every** named candidate (not only the Māori Party and Labour contrast the estimates of sigma and tau use), so it measures the excess error variance the contrast fit misses. The likelihood is invariant to the choice of reference candidate.

**Uncertainty of the correction itself.** A two-stage bootstrap of the training set (1,000 replicates: resample the training elections with replacement, then each resampled election's polls with replacement; sigma^2, tau^2, `b` and `lambda_hat` re-estimated in each replicate; a replicate with no contrast polls, fewer than one degree of freedom for sigma^2, or a zero sigma^2 (a singular covariance; added as a clarification when the code first ran, before any score or interval was displayed) is skipped and the skip count reported; more than 5% skipped means the arm is reported without an interval and the `insufficient_data` class applies). The 5th to 95th percentiles of the replicate `lambda_hat` are the reported interval, and every Monte Carlo draw of arm P or PB multiplies that draw's sigma^2 and tau^2 by a `lambda_hat` drawn at random from the replicates, so the correction's own uncertainty is carried into the probabilities. With four elections this bootstrap is crude and will be wide; that is reported, not hidden. Leave-one-election-out values of `lambda_hat` (four) are reported beside it.

## Schemes and scoring

- **Chronological (primary).** Training on strictly earlier elections only: score 2017 (trained on 2014), 2020 (2014, 2017), 2023 (2014, 2017, 2020): 21 polls. The 2017 fold trains on one election, so its tau^2 and bias are barely identified; it is scored and reported, and the decision is also repeated on 2020 plus 2023 alone (14 polls).
- **Leave-one-election-out (secondary).** The Stage66 scheme, training on the three other elections, 25 polls. It uses later elections to predict earlier ones, so it is a comparability and robustness check, not out-of-sample in time.
- Monte Carlo: 100,000 draws per fold, one random stream per (scheme, election), the same base draws for every arm so differences are not simulation noise, a separate stream for the `lambda` selection. Seed 2026071.
- **Metrics per arm, per fold and pooled (equal weight per poll):** (1) calibration of the probability that the poll leader wins: mean predicted against observed, calibration z `= sum(y - p) / sqrt(sum p(1-p))`, and a table by predicted-probability band (below 0.7, 0.7 to 0.9, above 0.9); (2) Brier score of the leader-win probability and the multi-candidate Brier score of the winner probabilities; (3) log score of the actual winner's probability (floored at 1e-4 as in Stage66); (4) interval coverage: central 50, 80 and 90% predictive intervals of the closed candidate shares (all candidates in all polls) and of the Māori Party-versus-Labour log-odds error D (24 polls). Candidate-level coverage is descriptive: shares in a poll sum to one and polls in an election share a shift, so the effective sample is smaller than the count.
- A paired poll-level bootstrap (5,000 resamples) of the pooled Brier and log-score differences is reported with every comparison; it ignores the within-election dependence and therefore understates the uncertainty.

## Decision rule (frozen), P against C on the chronological scheme

Applied in this order; the first that holds is the finding.

1. `insufficient_data`: in neither the 2020 nor the 2023 fold (the folds with at least two training elections) does the 90% bootstrap interval of `lambda_hat` exclude 1, or more than 5% of replicates are skipped. The training data available at the time cannot distinguish the correction from the control.
2. `mixed_report_to_james`: pooled Brier and pooled log score disagree in sign (one improves, one worsens).
3. `not_helpful`: pooled Brier of P is not below C's and the pooled log score of P is not above C's. An inflation fitted on earlier elections does not repair the overconfidence; the shortfall is not a scale problem.
4. `restored`: pooled Brier and pooled log score both improve, P is better on Brier in at least two of the three chronological folds, `|z|` of the pooled leader-win calibration of P is at most 1.645, and the coverage guard holds (P's mean absolute deviation of the closed-share 50/80/90% coverage from nominal is no larger than C's). The evidence qualifier is `clear` if the 90% paired bootstrap interval of the pooled Brier difference excludes zero, otherwise `weak`.
5. `improves_not_restored`: pooled Brier and log score both improve, but a condition of `restored` fails.

The same rule is evaluated on the 2020 plus 2023 subset and on the leave-one-election-out scheme. The headline finding is the chronological one; if either robustness repeat reaches a different class from the headline, the report says so and the finding is not stated without that qualifier.

**PB against P** (chronological scheme). The same-pollster transitions available to a chronological scheme are 2014 to 2017 (Reid) and 2020 to 2023 (Curia): two, one of them with a bias of about -0.1 that is almost zero. Whatever the scores, PB is therefore capped at `suggestive_not_adopted` (pooled Brier and log score both improve over P and neither worsens in the 2017 and 2023 folds) or `not_supported`. No result here can support adoption of an era term; that rests on whether James believes a Curia-era shift persists into 2026, which two Curia elections cannot establish.

## The 2026 readout

The three published Whakaata Māori–Curia polls (`polls-2026.json`, unchanged, latest per seat) go through arms C, P and PB trained on all four elections (100,000 draws, same seed and stream layout as the Stage66 forecast, unnamed remainder as Stage66). For PB the 2026 `b` is the mean of the 2020 and 2023 election means of D (Curia, the 2026 pollster). Reported per candidate: win probability, change from C, share 5th to 95th percentile and its width; P additionally at the 5th and 95th percentile of the `lambda_hat` replicates held fixed, the Māori Party win-count distribution across the three seats, and the Te Tai Tonga sensitivity. A shift in a leading candidate's win probability above 0.10 is flagged. Unpolled seats stay `unpolled`; new 2026 polls are not part of this stage.

## Explicit do-not list

No Student-t, mixtures, regimes or shrinkage; no per-candidate-type noise model (the Stage66 minor-candidate arm stays a diagnostic); no covariates, incumbency or party-vote inputs; no Māori-roll or national Te Pāti Māori input; no poll averaging; no general-electorate data, calibration, national model or MMP allocator; no change to Stage66's code, data, outputs or contract; no new sources and no `data/sources.json` edit; no adoption, probability release or publication; no CI registry edit; no fallback for unpolled seats; no later stage.

## Decision for James

None blocking. Adoption of any correction, the pollster-era question and probability release are his, after the PR.
