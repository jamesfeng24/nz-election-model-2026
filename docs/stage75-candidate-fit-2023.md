# Stage75: the live candidate-mean fit trained on every completed election

**Question.** Stage73's assembly used the latest saved S+R joint fold. That fold targeted 2023 and was trained on the 2011–2020 contests, so the live model left out the most recent election. What is the fit when 2023 is included, and how far does it move predictions?

**Answer.** The refit converges with the design unchanged. Its coefficients move a little:

| | Previous (2011–2020 targets, 181 contests) | Live (2011–2023 targets, 245 contests) |
|---|---|---|
| S | 0.9194 | 0.8987 (−2.3%) |
| R | 2.3459 | 2.2247 (−5.2%) |
| κ (floor) | 0.00818 | 0.00930 (+13.7%) |
| Training-only means S / R | 0.58531 / 0.01143 | 0.58573 / 0.01346 |

The live config now uses the refit. Raised by James on 2026-10-07 and authorized the same day.

## How

- **Design unchanged.** The Stage33 primary design is kept: `baseline_plus_S_plus_R`, broad view, printed rounding, constructed party input. The fitter is unchanged (`scripts.models.joint_candidate_share.numerics.calculate`). Only the training set changes: the latest saved fold's 181 training contests plus its own 64 evaluation contests from 2023.
- **Reproduction checks.**
  - Before the live fit, the builder (`scripts/candidate_fit_2026/common.py`) must produce exactly the saved 2023-target fit's payload signature (`aca80252…`). This proves the arrays, the actual results and the centring are Stage33's.
  - Re-running the fitter on that payload reproduces the saved coefficients to within 1e-7.
- **Recentring.** The Stage42 2026 continuous features were centred on the previous training-only means. They are recomputed from their stored components with the Stage42 `weighted` rule and the new means (`data/processed/candidate-fit-2026/features-2026.json`). The old contributions are reproduced first, to within 1e-12. The frozen Stage42 file is untouched.
- **Assembly.** `config/nowcast-2026.json` (configVersion 2026-10-07.4) points `candidate.parameters` at `data/processed/candidate-fit-2026/fit.json`, fold `live_all_elections`/2026. The new `candidate.centredFeatures` points at the recentred file. The assembly refuses to run unless the features are centred on the configured fit (same fit id and means).
- **Unchanged.**
  - The uncertainty scales: Stage45/72 measured out-of-time error, which is the error a 2026 prediction makes.
  - The local party layer, the national input and the Māori layer.
- **Regenerated:** the Stage73 development gate (new candidate fit id) and the Stage74 synthetic bank fixture.

## How far it moves predictions (`data/processed/candidate-fit-2026/impact.json`)

This is movement only, not a score: 2023 is in-sample for the live fit.

- **2023 contests (64 contests, 459 candidates)**, each fit with its own centring and the observed constructed party input:
  - the candidate share changes by 0.17pp on average (95th percentile 0.55pp, maximum 1.94pp);
  - the National−Labour margin changes by 0.46pp on average (95th percentile 0.95pp, maximum 1.16pp);
  - no predicted winner changes.
- **2026 candidates (206):** each candidate's feature weight before the floor changes by a factor of 0.967 to 1.013 (5th–95th percentile 0.994–1.007).

The movement is small next to the seat-level uncertainty: the ordinary candidate balance sd is 0.256 on the logit scale, several points of margin. So the refit is a correctness fix rather than a change of conclusions. The decline in R across folds (3.33, 3.35, 2.94, 2.35, now 2.22) is recorded. Whether to weight recent elections more is a separate modelling question and is not opened here.

## Reproduction

```
python3 -m scripts.candidate_fit_2026.run --check   # refits (about 4 minutes on 4 cores) and compares
python3 -m scripts.nowcast_assembly.run --check
python3 -m scripts.nowcast_assembly.fixture --check
python3 -m unittest scripts.tests.test_stage75_candidate_fit
```

The unit tests check the payload signatures, the training set, the exact recentring and the assembly pointer. They do not refit, so CI stays cheap.
