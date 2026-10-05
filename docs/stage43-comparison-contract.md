# Stage43 frozen continuous S versus S+R comparison

Committed before construction/scoring; post-result bounded development comparison. No fitting, acquisition, new transport or uncertainty implementation.

## Implementation plan

1. Pin Stage33 primary fits and Stage42 continuous components, exact common contest/candidate IDs and prior-data hashes.
2. Recalculate supported source features with each saved fold's own training means, then weight using all predecessor party mass. Reproduce Stage42 broad/strict joint predictions at 1e-12. Save predictions before evaluation.
3. Score independently fitted S and joint models on identical full slates. Strict R changes only the joint feature, using the same broad-trained parameters; reuse S unchanged.
4. Independently check arithmetic, exercise actual adapters, reproduce outputs, run configured checks and preserve earlier artifacts. Report and open an unmerged PR.

## Frozen equation and preprocessing

q(c) proportional to (observed target local party-group share + model's own saved kappa) times exp(thetaS zS + thetaR zR). S has its own independently fitted kappa and thetaS, and no R column. Joint uses its own kappa, thetaS and thetaR. All fits are Stage33 primary constructed-input-trained expanding-window fits; this is fixed-fit application to observed local inputs, not observed-input retraining.

z is the sum of party-mass predecessor weights times supported (raw source feature minus saved training-only mean). Unsupported mass remains in the denominator and contributes zero exponent. Use Stage42 frozen feasible uniform-within-source party-flow scenario and its continuity, cancellation and unique-person safeguards unchanged. Broad primary, strict R only sensitivity. Missing R is not known zero strength. Source S does not require identity. Exact models share fold-level training means in the saved artifact; verify against Stage42 rather than assume. Complete slates remain intact.

## Exact samples and chronology

2014:64 held general contests/451 candidates; 2020:65/561. Manifest pins IDs in order, wider frame and exclusions. Source/target years2011/2014 and2017/2020. Training targets must precede evaluation target under inherited expanding chronology. No approximate candidate votes are reconstructed. No Māori fitted extension.

## Reporting frozen before scores

Contest-equal MAE and RMSE (square root of mean contest MSE), candidate-equal sensitivity, full-slate signed bias accounting; National, Labour, other mapped parties and affirmative no-group candidates with candidate-equal group MAE/RMSE/bias and explicit counts. Joint-minus-S MAE/RMSE is positive when joint is worse; report paired contest errors and five largest gains/losses, without removing records.

Report exact, exclusive >=95%, exclusive90–95%, below90, cumulative>=95%; same records for model pairs within each stratum. Also contests with/without broad usable R, strict usable R, and supported/unsupported candidate R diagnostics, showing counts and supported mass. Normalization can affect candidates with no own R.

Reuse Stage33 winner_set tolerance1e-12: unique-correct count, predicted ties, tied-set winner inclusion. Observed-top-two margin error compares q(actual winner)-q(actual runner) with actual gap, averaging tied runners; predicted-top-two gap diagnostic separately. No result/order tie breaking. Rankings are descriptive, not win probabilities.

Pool one weight per contest (64/129,65/129); additionally equal-election mean MAE, root mean election MSE for RMSE and mean fold differences. These two reused election environments are not independent temporal confirmation; no reliable future-stability estimate from two MAEs. No new gain threshold or post-result selection rules. Retain Stage33–34/39 evidence separately, no naive pooling.

## Stopping and next decision

Recommend retaining joint preferred/S active, preferring S/joint alternative, or unchanged preference if inconclusive based on magnitudes/consistency/robustness. Preserve historical screens and operational nulls. Next task is separately authorized coherent local-party/candidate uncertainty, not another mean-model search.
