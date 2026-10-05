# Stage45 frozen residual-scale correction

2026-10-05. This is a post-Stage44 development correction informed by inspected elections. Earlier-only parameter estimation does not make its design untouched validation. One structure, no mean refit, new sources, national inference or family tournament. External gauss provisional; continuous S+R preferred, S active, baseline mandatory. The original Stage44 files remain unchanged.

## Evidence and estimand

Consume Stage44's exact 321 party vectors and 257 candidate slates/1902 candidates. Party errors condition on national truth; candidate errors condition on local-party truth and frozen earlier-fit continuous mean features. Wider frame, Māori coverage-only, cancellation, 2011 no candidate fit and source evidence remain intact. Do not mix threshold means, polling misses or upstream local input errors into these scales. Means/inputs/scales and historical code are pinned by consumed hashes; all prior data bytes have separate preservation checks.

## One arithmetic aggregate/within-remainder tree

Let N,L be the unique standing/modelled major options, M=N+L and O=1-M. Coordinates, when defined:

- a=log(N/L), raw log odds; one scalar degree of freedom.
- b=log(M/O), raw log odds; one scalar degree of freedom.
- u_i=log(O_i)-mean_j log(O_j), within the remaining options; K_O-1 degrees of freedom.

Inverse: M=sigmoid(b), rho=sigmoid(a), N=M*rho, L=M*(1-rho), O_i=(1-M)*softmax(u)_i. Independent a/b disturbances give independent conditional M/rho. Adding tiny remainder categories cannot change a/b noise or its normalization. Within-remainder competition retains every minor/independent option. It does not enter major ratios or aggregate remainder mass. This is arithmetic aggregation, not CLR means of heterogeneous coordinates.

If one major is absent, omit a and use b for the existing major versus remainder. If both majors are absent, all options belong to the remainder. If remainder is absent, omit b. A single remaining option has no within allocation noise. Ambiguous/duplicate major destinations are errors. Structural absence never creates an option. Changed category/slate IDs remain election-local; shared effects use pinned ballot-group labels, not names.

Retain Stage44 epsilon=1e-6 additive resolution replacement for residual calculation only. This keeps zero observations finite; no pseudocount search. Frozen predicted zero remains locked zero in simulation. Source-zero/positive outcome is a labelled irreducible miss, not permission to alter the mean.

## Earlier-only estimation and dependence

For a/b within each earlier election, calculate the equal-record residual mean h and residual variance mean((e-h)^2). Shared second moment is h^2; do not fit a bias correction. Each election gets one weight, no sample-size illusion of extra environments. Seat moment uses population denominator: predictive second moment, not an unbiased variance estimator.

For u, regress projected residuals on centered remainder ballot-group indicators in independent Helmert coordinates, with one total remainder-df-normalized weight per seat. Shared moment=norm(group effects)^2/(G-1). Seat moment=equal-seat mean norm(leftover)^2/(K_O-1). Direct full-rank solution, relative singular threshold1e-10 and absolute1e-12, no pseudoinverse. Rank failure makes that election's shared moment unavailable; unprojected seat moment remains. One common shared SD and one seat SD for all remainder labels; no unrestricted covariance or per-seat scales. Independents share the no-group label, with separate seat errors.

Each direction/kind uses variance=(sum earlier election moments+3*prior_SD^2)/(available moments+3). Missing coordinate/election moments do not become zero. Full-panel descriptive moments are separate. No earlier evidence uses the fixed prior. Degrees of freedom are explicitly different between scalar odds balances and projected within-remainder intensities.

Fixed prior SDs (dimensionless log units), selected for interpretable conditional odds and synthetic implications, not held-out coverage:

| Layer | Coordinate | Shared | Seat | Total SD |
| --- | --- | ---: | ---: | ---: |
| party | N/L | .08 | .15 | .1700 |
| party | majors/remainder | .10 | .20 | .2236 |
| party | within remainder | .15 | .50 | .5220 per intensity |
| candidate | N/L | .15 | .35 | .3808 |
| candidate | majors/remainder | .15 | .40 | .4272 |
| candidate | within remainder | .20 | .70 | .7280 per intensity |

Party prior N/L odds roughly 1.32x up/down at90%; candidate about1.87x, intentionally larger for conditional allocation misses. Aggregate-major priors allow broader combined-share error; sparse minor relative errors retain larger within-remainder variation. These are substantive assumptions, not calibrated facts. Do not inherit Stage44's .50 candidate seat SD as a raw log-odds scale. Synthetic competitive, multipartite, tiny-option and missing-major fixtures are frozen in prior-implications.json; no calibration claim.

Two scalar shared Gaussian effects per election/layer are common across all seats. Within-remainder shared label Gaussians are exchangeable with one pooled scale; seat/option Gaussians are separate. National draw IDs remain shared once across seats. Cross-layer independence remains an explicit approximation. Parameter/scale uncertainty, fine Other allocation and fragment composition are omitted/scenario limitations. No extra transport variance in the revised primary: ordinary residuals already include transported seats.

## Outcome-free mean treatment and dependence audit

For each input vector, a/b use deterministic Gauss-Hermite41 integration and monotone location solving so their conditional arithmetic probabilities equal the frozen conditional mass and ratio; tolerance1e-12. Independent a/b then preserve conditional expected N and L. Extreme zeros/ones stay on their faces. Verify with higher-order81 integration, not outcomes.

Within remainder uses the unchanged type of finite-bank weighted marginal location adjustment, tolerance1e-10 shares/max1000 iterations, preserving marginal remainder allocation conditional on the sampled aggregate remainder mass. It does not preserve each national draw's conditional minor allocation. The top-level national response cannot be changed by this remainder adjustment. Report any finite-bank mean drift, theoretical conditional means, remainder conditional distortion and nonlinear local-to-candidate shifts. Synthetic and representative historical conditional audit uses an independent fixed2048 integration bank; it is numerical evidence, not historical bias fitting. Stage44's original marginal adjustment receives the same audit, preserving its equations.

Mean preservation cannot fix nonlinear upstream changes: average candidate shares after local uncertainty can differ from the national-only mean pipeline. No target outcome enters a location adjustment. Narrowness must not come from deleting shared dependence; record shared/seat covariance contributions and cross-seat draw associations.

## Integration and finite computation

Revised and unchanged Stage44 companion use the same cases, cached national draws and numerical standard. Seed20261005; stable SHA256/PCG64 component streams, antithetic noise; national indices keep Stage44's balanced chain-prefix selection. No MCMC. Unchanged companion reuses Stage44 equations and earlier fitted scales, with no transport stress, only larger numerical banks. Point control is the identical frozen component mean or national-only transformed mean.

Draw counts1024→2048→4096→8000 (full cached national archive). Representative first/middle/last sorted seat IDs in every component and composed election, both uncertainty policies. Stop doubling only if all monitored changes between successive counts are <=.05pp expected shares, <=.05pp CRPS, <=.5pp90% marginal widths. Choose one common count for every case/policy. Cap8000; if any gate remains unmet, use the cap with explicit numerical nonconvergence, no tolerance/count change and no fine model-superiority claims. Save each numerical checkpoint/cache; no expensive restart. Fixed energy approximation uses first128 joint draws for all policies, with an independent representative256 check reported separately.

Completed composed cases are only 2017/2020/2023 cached gauss56-day, recent_report_prior fine allocation and complete64/65/64 general slates. No candidate replay branch grid or new horizons. Priors/zero replacement/mean family do not change after scores. Expected shares average transformed draws.

## Evaluation and stop

Seal full draws before evaluation. Reuse Stage44 original-share pp metric definitions, equal-contest CRPS/MAE/RMSE, 50/90 coverage/counts/width/proper interval scores, complete-vector energy, group bias/major/remainder/no-group diagnostics and prediction-time top-two margins. Winner Brier/logloss remain diagnostics, not calibration. Point control has a genuine degenerate distribution; no invented intervals for unrelated systems. Pair all methods on identical IDs; report substantive minor/unusual misses, not just majors. Pooled contest and equal-election views distinct; dependent seats/parties are not independent calibration environments.

The new design may improve sharper proper scores without every fold winning; do not add pass thresholds after results. Keep Stage44 original as reproducible development record. Stop after one correction. Nomination refresh, Māori baseline/polls, all-population reconciliation/turnout and MMP remain separately bounded.
