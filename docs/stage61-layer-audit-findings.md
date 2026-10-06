# Stage61 findings: are the other uncertainty layers calibrated?

Frozen design: [stage61-layer-audit-design.md](stage61-layer-audit-design.md) (design committed `fe221eb` before any score; one amendment A1 for the within-remainder moment definition, recorded in that file). Artifacts: `data/processed/layer-audit/` (`summary.json`, `design-contract.json`, `input-contract.json`, `manifest.json`). Reproduce: `python3 -m scripts.layer_audit.run --check` (about 2 seconds, no network, no national inference). Diagnostic only: nothing is adopted, refit or rescaled, and no scale, mean or CI file changed.

## Headline

**Candidate N/L balance is the only component that over-covers materially and is worth narrowing.** Every other layer is calibrated, immaterial for the National/Labour widths, or cannot be assessed from four or five elections. The remaining width (about 21pp of composed National 90% width with balance removed) is mostly national uncertainty and candidate mass, and the evidence does not show either is too wide.

| Question | Answer |
|---|---|
| Does candidate balance over-cover? | Yes. R = 0.79 (90% seat bootstrap 0.65 to 0.92), below 1 in all three estimated elections. Indicative cut to composed National 90% width: about 10% (29.9 to 26.9pp) at R, about 4% at the interval's upper end. |
| Next-best narrowing target after balance? | **None that matters.** The frozen rule lists candidate within-remainder second (R = 0.75), but removing that block changes the composed National width by 0.0pp. The local seat layer is worth at most 2.3% even if every local coordinate took the lowest R, and the evidence for it is mixed (below). |
| Is candidate mass (the next-largest candidate block) too wide? | No. R = 0.99 (0.82 to 1.14): calibrated. |
| Local-party layer? | Slightly conservative on balance (R 0.89) and mass (R 0.82) over the whole record, but mass is calibrated in 2020 and 2023 and the election-by-election ratios swing from 0.22 to 1.60. Within-remainder is slightly too tight (R 1.08). Not a narrowing target. |

## Seat scale by component (estimated folds, equal election weight)

R is the square root of the pooled ratio of the leftover second moment to the frozen seat variance; below 1 means the frozen scale is larger than the data support. The 2011 local and 2014 candidate folds use the fixed prior only and are shown in the per-election column but excluded from R. The per-election column lists years in order (local 2011 to 2023, candidate 2014 to 2023).

| Layer | Component | R | 90% seat bootstrap | Frozen verdict | Per-election ratio | Elections below 1 (estimated) |
|---|---|---:|---|---|---|---:|
| candidate | balance | 0.79 | [0.65, 0.92] | conservative | 0.72 / 0.81 / 0.39 / 0.68 | 3 of 3 |
| candidate | mass | 0.99 | [0.82, 1.14] | calibrated | 0.82 / 1.08 / 0.57 / 1.29 | 1 of 3 |
| candidate | within | 0.75 | [0.67, 0.82] | conservative | 0.43 / 0.55 / 0.49 / 0.63 | 3 of 3 |
| local party | balance | 0.89 | [0.79, 0.98] | conservative | 1.42 / 0.56 / 1.60 / 0.36 / 0.65 | 3 of 4 |
| local party | mass | 0.82 | [0.73, 0.89] | conservative | 0.28 / 0.22 / 0.36 / 1.15 / 0.93 | 3 of 4 |
| local party | within | 1.08 | [1.02, 1.15] | too tight | 0.77 / 1.80 / 0.79 / 1.38 / 0.73 | 2 of 4 |

Two things the verdicts hide. First, ratios move a lot between elections (candidate balance 0.39 in 2020, local mass 0.22 in 2014 against 1.15 in 2020), far more than seat sampling explains: per-election 90% intervals such as 0.26 to 0.52 (candidate balance 2020) and 1.04 to 2.16 (local balance 2017) do not overlap. That is an election-level scale shock, and three or four elections cannot separate it from a level error, so every seat-bootstrap interval here is narrower than the real uncertainty about the level. Second (post hoc, labelled in the artifact), the local mass verdict rests on 2011 to 2017 (ratios 0.28, 0.22, 0.36); the two most recent elections are about right (1.15, 0.93). Leaving each election out in turn moves candidate balance R only between 0.73 and 0.86, so the over-coverage is not one election.

The raw-basis sensitivity (no location adjustment) gives the same direction: candidate balance ratio 0.58 against 0.63, local balance 0.78 against 0.79, local mass 0.66 against 0.67. Raw seat and shared moments reproduce the saved Stage45 descriptive moments to machine precision, and so do the within seat moments after amendment A1.

## Total-law PIT coverage (balance and mass, estimated folds)

Central coverage of the full predictive law (shared plus seat). Nominal 0.50 / 0.80 / 0.90.

| Layer | Component | 50% | 80% | 90% | Shape flag |
|---|---|---|---|---|---|
| candidate | balance | 0.65 [0.60, 0.71] | 0.91 [0.88, 0.94] | 0.95 [0.92, 0.97] | centre too wide |
| candidate | mass | 0.55 [0.50, 0.61] | 0.84 [0.80, 0.89] | 0.92 [0.88, 0.95] | none |
| local party | balance | 0.61 [0.56, 0.65] | 0.86 [0.83, 0.89] | 0.94 [0.92, 0.96] | centre too wide |
| local party | mass | 0.68 [0.63, 0.72] | 0.92 [0.88, 0.94] | 0.96 [0.94, 0.98] | centre too wide |

The over-coverage is concentrated in the centre and the 90% level is near nominal or modestly over. A Gaussian rescaled to R = 0.79 would cover about 0.61 / 0.89 / 0.96, but candidate balance observes 0.65 / 0.91 / 0.95: the centre is even tighter than a Gaussian of the same spread and the tails are heavier. That is the shape question Stage46 closed (Student-t rejected) and it is not reopened here; it only means a pure scale cut will leave the 50% interval over-covered.

## Shared parts (election effects)

Statistic: squared election effect over its model variance, against the 5th to 95th percentile of chi-square(E)/E for E estimated elections (3 candidate, 4 local). Four or five elections cannot calibrate a shared scale, so the verdict is only inside or outside the band.

| Layer | Component | Pooled statistic | 90% band | Reading | Standardised election effects |
|---|---|---:|---|---|---|
| candidate | balance | 0.98 | [0.12, 2.60] | within band | 2014 -1.94, 2017 +0.13, 2020 +1.57, 2023 -0.67 |
| candidate | mass | 2.25 | [0.12, 2.60] | within band (near the top) | 2014 -0.85, 2017 -2.22, 2020 +1.15, 2023 -0.70 |
| candidate | within | ratio 3.47, descriptive | none | not assessed | 4.66 / 3.72 / 5.97 / 0.72 |
| local party | balance | 0.61 | [0.18, 2.37] | within band | +0.11, +0.26, -0.65, -0.86, +1.10 |
| local party | mass | 0.10 | [0.18, 2.37] | outside band, too wide | +0.09, +0.17, 0.00, +0.30, -0.54 |
| local party | within | ratio 1.69, descriptive | none | not assessed | 7.30 / 1.61 / 3.19 / 1.57 / 0.38 |

The shared candidate component is not shown to be too wide: balance is in band, mass sits near the top (a hint that it could be too tight), and within-remainder ratios of 3.5 mean the shared label effects are, if anything, too small. The one flag is the local shared mass scale, which looks too large, but removing all local shared noise changes the composed width by only 0.3pp (about 1%), so it is immaterial.

## Share-level coverage from the stored Stage47 intervals

Pooled over estimated-fold elections, nominal 0.50 / 0.80 / 0.90, with 90% contest bootstrap intervals. Local intervals are conditional on the true national result, candidate intervals on the true local result, composed intervals include 512 cached national scenarios (finite-bank noise).

| Layer | Group | 50% | 80% | 90% | 80% reading | 80% by election |
|---|---|---|---|---|---|---|
| local party | national | 0.62 | 0.90 | 0.97 | over covers | 0.84 / 0.97 / 0.81 / 0.95 / 0.88 |
| local party | Labour | 0.59 | 0.84 | 0.92 | over covers | 0.87 / 0.95 / 0.73 / 0.85 / 0.83 |
| local party | other options | 0.67 | 0.87 | 0.92 | over covers | 0.89 / 0.87 / 0.86 / 0.83 / 0.91 |
| candidate | National | 0.53 | 0.90 | 0.95 | over covers | 0.81 / 0.89 / 0.85 / 0.97 |
| candidate | Labour | 0.71 | 0.93 | 0.96 | over covers | 0.81 / 0.92 / 0.94 / 0.92 |
| candidate | other options | 0.64 | 0.88 | 0.94 | over covers | 0.90 / 0.83 / 0.89 / 0.92 |
| composed | National | 0.66 | 0.90 | 0.95 | over covers | 0.75 / 0.95 / 0.98 |
| composed | Labour | 0.60 | 0.83 | 0.93 | consistent | 0.61 / 0.91 / 0.97 |
| composed | other options | 0.58 | 0.86 | 0.93 | over covers | 0.85 / 0.89 / 0.85 |

Intervals are mildly over-wide at every layer, but the composed result is not uniform: **2017 under-covers** (National 80% coverage 0.75, 50% coverage 0.45; Labour 0.61 and 0.30) while 2020 and 2023 over-cover (0.95 to 0.98). Any global narrowing of the composed intervals trades against the 2017 election, which the national layer, not the candidate layer, drives. Stage60's coverage floor should be read with that in mind.

## Where the remaining width sits

From the Stage47 nine-seat ablation (composed National 90%, full 29.9pp):

| Removed block | Width (pp) | Effect | Evidence on that block |
|---|---:|---:|---|
| candidate balance | 20.8 | -9.1 | over-covers (R 0.79) |
| national uncertainty (at mean) | 25.4 | -4.5 | not scored here |
| candidate mass | 27.3 | -2.6 | calibrated (R 0.99) |
| candidate shared | 27.7 | -2.2 | not assessable, not shown too wide |
| local seat | 27.8 | -2.1 | mixed, at most 2.3% if all cut |
| local shared | 29.6 | -0.3 | too wide but immaterial |
| candidate within | 29.9 | 0.0 | over-covers but no effect on N/L |

Widths are not additive variance shares and this is nine seats. Indicative cut at R: candidate balance 10.1%, local seat 0 to 2.3% (bracket by lowest and highest local R, mixed verdicts), candidate within 0.0%, candidate mass 0.2%.

## Recommendation (report only)

1. Carry the conclusion to Stage60: balance is the one lever. The 90% interval for R (0.65 to 0.92) and the 0.79 point both fall near or below the planned grid floor of 0.80, so the grid should also include the likelihood-preferred value (as planned) and, if cheap, a 0.75 multiplier so the floor does not bind.
2. Do not build local-layer or candidate-mass narrowing. The local evidence is election-dependent and the available gain is at most a few percent; candidate mass is calibrated.
3. Treat the 2017 composed under-coverage as a constraint on any narrowing, not as a reason to widen. It comes from the national layer, which this stage does not score.
4. Cheapest ways to firm up what this stage could not isolate: more elections for shared effects (no existing frame supplies them; Stage50 and later history work could); and rerunning the existing Stage47 ablation harness over all 193 composed seats for a measured, rather than bracketed, width effect per component. Neither is done here.

## Limits

All elections were used in development, so nothing here is out-of-sample. Seats within an election share an election effect, so seat-bootstrap intervals describe seat noise only. Composed coverage carries finite-bank noise (512 national scenarios). The first within-remainder implementation used the wrong residual records (amendment A1; the corrected values replace the first attempt, which is disclosed in the design file). The national layer, Māori seats (excluded by electorate type; 35 frame rows not scored), the mean model and scale adoption are outside this stage.
