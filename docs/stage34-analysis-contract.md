# Stage34 — post-result S/R movement and robustness diagnostic

## Scope and implementation plan (frozen before new summaries)

Verified PR40 merge304de1fb/reviewed7fae468; clean main synchronized, branch `stage/34-s-r-error-diagnostics`. This is explicitly post-result descriptive analysis of saved Stage33 predictions, not a preregistered model validation. No fitting/prediction regeneration, bound changes, new variable/distance search, adaptive weighting, source acquisition or deployment.

1. Pin Stage33 construction/evaluation/specification and Stage32 features; Stage31 complete vectors/category relationships; Stage25 geography; official complete party tables/continuity/alias/alliance evidence. Save exact branch/fold/slate IDs and category audit before associating movement with errors.
2. Build candidate-outcome-independent movement records, then join saved complete-slate errors. Keep movement exclusions separate from original model-performance denominators.
3. Produce the finite associations, competing-explanation tables, robustness and fixed-prediction influence described below, with deterministic scatterplots. Independently recalculate arithmetic, test actual adapters/counterfactuals and preserve prior bytes.

## Movement and category contract

Only total variation: `D=0.5*sum_category(abs(target_share-source_share))`, on complete valid-party-vote vectors, including groups without a candidate. D is a fraction; display100D as percentage points of displaced share, not individual voter switching. National counts use the full official national valid-party denominator; local source and target vectors use their respective local valid-party denominators. Candidate MAE uses valid-candidate shares and never the party denominator.

Reuse Stage31's canonical ballot-group IDs/continuity and documented panel aliases (D017/D022). A renamed group keeps one canonical dimension; do not normalize over the candidate slate. Continuing groups must exist at both endpoints. Entrants have an explicit structural source absence=0; exits have explicit structural target absence=0. Missing rows, duplicate canonical/group mappings, inconsistent relationships or incomplete simplexes are diagnostic exclusions, never observed zeros. Whole Internet-MANA and Freedoms NZ groups remain indivisible distinct categories: constituent-to-alliance membership is not whole-group continuity. Entry/exit displacement includes ballot-roster reorganization and is not an identified voter transfer. No allocation to constituents, new continuity or pooled 'other' category.

Construct exactly three distances: full-national source→supplied target national; source observed local→saved Stage31 constructed target local; source observed local→observed target local (explanatory sensitivity). Inspect and record all source/target mappings and structural states before associations. Geography is the saved Stage25 two-sided exact pair; no changed-boundary approximation. National inputs are actual target results supplied conditionally; source publication timing is not thereby certified as of a historical cutoff.

## Samples and paired quantities

Primary uses Stage33 `primary` fitted2014/2017/2020/2023, exact common whole slates, all candidates. No fitted2011 is created. Sensitivities only `strict`, `separated`, `observed_retrained`, `primary_fixed_to_observed`; no Cartesian product. The latter two are respectively separately trained observed-input predictions and unchanged primary fits with observed inputs substituted. Pair IDs and candidate IDs must match all four restrictions.

`G=MAE_R-MAE_S` (positive favors S); `J=MAE_S-MAE_joint` (positive favors joint). Model improvement over baseline is baseline MAE minus model MAE. MAE averages absolute pp errors across a slate; pooled primary retains one weight per contest. RMSE is sqrt(mean_contests(mean_candidates(error_pp²))). Target candidate actuals are evaluation only. Diagnostic exclusions cannot change original model summaries.

## Finite associations and competing explanations

- Four national distance/G/J environment rows, without multiplying national observations by seats or estimating a national weighting model.
- Per-election scatter/data tables of each local distance versus G, without smoothers/bins. Descriptive OLS slope with intercept=`sum((D-meanD)(G-meanG))/sum((D-meanD)²)`; report pp gain per10pp D (slope*0.1). Spearman is Pearson correlation of average tied ranks. No p-values. Undefined variation/less than two observations returns explicit unavailable.
- Pooled within-election-centered raw D/G OLS and correlation: each election total weight1/K, each included contest1/(K*n_e); subtract each election's own means first. Fixed-prediction delete-one-election repeats this descriptive statistic on the remaining folds, not a forecast or refit. No multivariable model.
- Repeat these same associations for strict and both observed-input branches; separated remains the chronology/robustness sensitivity. Distances do not change by branch. Use both local distance definitions to distinguish movement from constructed-input error. Any unavailable distance is explicitly counted.
- Alongside every contest: broad/strict supported R fraction, S support, slate size; saved training IDs/count/environments; saved R bound flags/coefficients; complete-vector party-input MAE and separate National/Labour signed/absolute pp errors. No causal attribution or subgroup search.
- Candidate-equal paired errors for R-supported and R-unsupported groups, with candidate and present-contest denominators; supported labels use the branch's frozen broad/strict view. No linked-returnee trimming of primary scores. Normalization can change unsupported predictions.

## Robustness and influence

For primary/strict/separated, use identical available folds within each branch. Report original contest-weighted pooled MAE/RMSE; equal-election mean MAE; population SD (denominatorK), range, worst election MAE; all baseline-relative fold improvements; their equal-election mean/SD/range/minimum and worst fold. Baseline's identically zero gain/dispersion is an accounting control, not perfect forecast robustness. Equal-election summaries are an additional requested descriptive decision view, not a replacement for Stage33 weighting. Partial exact-seat elections remain selected samples.

Keep all182 primary contests. Report G/J signs and five largest joint-vs-S gains and five losses, ordered by value then stable contest ID (no threshold). No composite mean/variance score. Absolute error dispersion across four reused environments is not calibrated forecast uncertainty. Reduced across-fold dispersion is not sufficient if baseline-relative deterioration or sample composition explains it.

## Tests, provenance and decision boundary

Pin consumed-record hashes/raw provenance through inherited stage-specific contracts, accepting unrelated registry additions. Snapshot all prior tracked data against merged main separately for byte preservation. Test full-party joins/TV/renames/structural absence/missingness, paired IDs/signs/denominators, weighting/centering, candidate-outcome-independent movement, outcome-only changes to diagnostics, deterministic reproduction and corrupt-source detection. Independent arithmetic uses direct vector calculations and alternate formulas; tolerances1e-12 for distance,1e-9pp for scores/robustness,1e-9 for correlations/slopes on representative records.

Record a subsequent development decision keeping **S and S+R active alternatives**, R-only meaningful challenger, baseline mandatory, without rewriting D065 or Stage33's default recommendation. Finish with A: dated-input readiness/replay while retaining alternatives, or B: one separately authorized frozen blend only if a consequential reproducible pattern warrants it. B would require a fixed blend control, one slate-wide weight, distinct national/local hypotheses, earlier out-of-time expert predictions, scarce chronological meta-training and weighting uncertainty. No blend is implemented here. Shared national error must later be propagated once; no operational selection follows.
