# Stage68: does the national party swing predict the shared candidate-split shift? Frozen pre-registration

**Status: frozen before this stage's script was written or run.** This file and [design-contract.json](../data/processed/shared-split-swing/design-contract.json) are the frozen checkpoint. Decision number D102 (from the coordinator). James authorized this stage on 2026-10-06 as a short descriptive check with a stop rule, not a full scored stage.

**Not blind (disclosed).** The author has already seen the four shared shifts: about −0.28, +0.03, +0.26 and −0.12 log units for 2014, 2017, 2020 and 2023, quoted in the planning conversation. The author has also commented on their signs and has sketched the obvious through-origin calculations from memory of the national results. The check is therefore descriptive. Its stop rule is deliberately strict, so that a pattern spotted by eye cannot by itself start a scored stage.

## Question

> Does the change in the national National/Labour party-vote ratio since the previous election predict that election's shared candidate N/L split shift?

The hypothesis is that candidate votes lag party-vote swings: when the party vote swings towards National, the candidate split moves less, giving a negative shared shift, and vice versa.

## Quantities (frozen)

- **Shared shift `y_e`.** The equal-seat mean over the election's general-electorate candidate records of `v - l`. `v` is the Stage48 balance observation and `l` is the Stage48 control Gaussian location at the frozen fold total sd (`scripts.balance_scale.data.environments`, `scripts.balance_scale.fit.location`). The four elections are 2014, 2017, 2020 and 2023; agreement with `heterogeneity.json` is reported.
- **Swing `x_e`.** `log(N/L)` of the summed general-electorate party votes in election `e`, minus the same for the previous general election (2011, 2014, 2017, 2020). The source is `data/processed/elections/{year}.json`, party ballots of `kind == general` electorates.
- **Model.** Through the origin, `y_e = -beta * x_e`. There is no intercept: with four points an intercept is not identifiable, and a constant shared bias is not this question. The with-intercept OLS fit is reported descriptively.

## Reported

- Sign agreement: the count of elections with `sign(y) = -sign(x)`.
- Pooled `beta`, fitted on all four elections.
- Leave-one-election-out (LOEO): `beta` fitted on three elections, the fourth predicted. Each fold's `beta`, the prediction error, and the RMS of those errors.
- Baseline: the RMS of `y` itself, i.e. predicting no shift.
- Leave-future-out errors for 2020 (trained on 2014 and 2017) and 2023 (trained on 2014, 2017 and 2020), each against `|y|`.
- Implied shared-sd ratio: LOEO RMS divided by RMS(y).

## Stop rule (frozen)

`proceed_to_scored_stage_recommended` only if **all** of the following hold:

1. 4 of 4 signs agree.
2. Every LOEO `beta` is positive.
3. LOEO RMS ≤ 0.75 × RMS(y).
4. Both leave-future-out absolute errors are below the corresponding `|y|`.

Otherwise the finding is `record_and_stop`. Even `proceed` only recommends a separately authorized, pre-registered scored stage. Nothing here changes a mean, scale or forecast.

## Do not

- No scoring, simulation, fit of any model layer, mean or scale change, or adoption.
- No seat-level swing feature (that would be a mean-model change), no other predictor, transform or intercept variant beyond the descriptive one above.
- No new source or acquisition, no `data/sources.json` edit, no CI or registry edit, and no change to any frozen output.
