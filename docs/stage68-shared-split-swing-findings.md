# Stage68 findings: national swing and the shared candidate-split shift

Frozen design: [stage68-shared-split-swing-design.md](stage68-shared-split-swing-design.md) (commit `8bf4a5f`; disclosed as not blind). Output: `data/processed/shared-split-swing/summary.json`. Reproduce with `python3 -m scripts.shared_split_swing.run --check`, which takes seconds. Decision D102. **Nothing is adopted or changed.**

## Finding: `record_and_stop`

| Election | Shared shift `y` (log units) | National N/L party swing `x` | Through-origin fit (β = 0.203) | LOEO prediction | LOEO error |
|---|---:|---:|---:|---:|---:|
| 2014 | −0.303 | +0.101 | −0.020 | −0.019 | −0.284 |
| 2017 | +0.025 | −0.440 | +0.089 | +0.096 | −0.071 |
| 2020 | +0.277 | −0.879 | +0.178 | +0.120 | +0.157 |
| 2023 | −0.130 | +1.051 | −0.213 | −0.307 | +0.177 |

| Stop-rule test | Result |
|---|---|
| Signs agree (4 required) | 4 of 4: pass |
| Every LOEO β positive | 0.189 / 0.218 / 0.136 / 0.292: pass |
| LOEO RMS ≤ 0.75 × RMS(y) | 0.188 against 0.216 (ratio 0.87): **fail** |
| Leave-future-out beats predicting zero | 2020: error 0.098 against \|y\| 0.277, pass; 2023: error 0.177 against \|y\| 0.130, **fail** |

The with-intercept OLS fit (descriptive) has slope −0.206 and intercept −0.041. The shared shifts here use the corrected Stage48 control location. They differ from the Stage46-era `heterogeneity.json` election means by 0.007 to 0.021.

## Reading

The direction is real and consistent: when the national party vote swings, the candidate split moves less, in all four elections. But the size is not predictable.
- 2014 had a large shift on a small swing.
- 2023 had a small shift on a large swing; a β trained on earlier elections over-predicts it, and does worse than assuming no shift.

Using the swing would cut the shared split uncertainty by only about 13% out of sample (0.216 to 0.188), on four points. That is not enough to justify a scored stage under the frozen rule. The shared election scale (about 0.19) stays as the honest uncertainty for the shared part of the split.

## Limits

- Four elections; not blind (the author had seen the shifts).
- The swing is the actual national swing. In a live forecast it would itself be forecast, which adds error.
- With-intercept and seat-level variants were deliberately not tested.

## Recommendation

Record and stop. Do not add a swing term to the candidate mean. Revisit only if a further election (2026) adds a fifth point; the frozen rule above would then be re-applied unchanged.
