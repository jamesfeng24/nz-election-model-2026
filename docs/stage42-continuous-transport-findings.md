# Stage42 continuous predecessor-weighted transport findings

Frozen audit/contract66b033a preceded construction8365b92, which was pushed before scoring. No acquisition, refitting, MCMC or live forecast. Earlier numerical outputs/adjudications/operational records remain unchanged.

## Within-seat evidence and assumptions

Preserved evidence cannot identify a transferred residential fragment as more National- or Labour-leaning. Acquired voting-place files contain candidate ballots, not party-by-residence detail. Advance sites outside the home seat and aggregated special/overseas votes preclude booth catchment inference. See the [audit](stage42-within-seat-evidence-audit.md). Zero discovery queries/resources; no finer-flow implementation.

The unchanged Stage41 feasible population witness supplies `F=source party votes × source-outgoing population weight`, explicitly uniform voting within source electorates. Lambda uses every predecessor party mass, including unsupported components. S and same-person R are centered with each earlier saved training mean **before** weighting; missing evidence contributes a neutral exponent and is never renormalized away. R uses one accepted source in any genuine predecessor, not an outgoing replacement bonus. Party weighting of candidate-normalized residuals is a modelling assumption.

## Historical paired full-frame diagnostic

Only saved primary expanding-window Stage33 S+R parameters, observed target local party inputs and complete retrospective slates. All policies share identical IDs; strict changes R availability only, not fitted parameters. Errors/gains are percentage points; positive gain means lower error than the comparator.

| Election | Contests / candidates | Exact fallback MAE / RMSE | Stage41 90 MAE / RMSE | Continuous MAE / RMSE | Gain vs fallback / 90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2014 | 64 / 451 | 3.4547 / 6.0766 | 3.3243 / 5.9192 | 2.7173 / 4.8469 | +0.7374 / +0.6070 |
| 2020 | 65 / 561 | 2.5662 / 4.3309 | 2.4140 / 4.1093 | 2.1324 / 3.6215 | +0.4337 / +0.2815 |

Pooling weights each of129 contests equally (64/129 and65/129 election weights). Primary pooled MAE: exact_fallback=3.0070pp, stage41_90=2.8656pp, continuous=2.4226pp. Full-slate signed bias cancels by conservation and is accounting, not calibration. Seven Māori targets per year remain coverage-only. No held general contest is excluded.

### Exclusive overlap bands and strict sensitivity

| Election / band | Contests | Continuous gain vs fallback | Continuous gain vs Stage41 90 |
| --- | ---: | ---: | ---: |
| 2014 / exact | 20 | +0.0000 | +0.0000 |
| 2014 / approximate_95 | 8 | -0.0734 | -0.0038 |
| 2014 / approximate_90 | 9 | +0.9747 | -0.0146 |
| 2014 / below90 or ambiguous | 27 | +1.4449 | +1.4449 |
| 2020 / exact | 34 | +0.0000 | +0.0000 |
| 2020 / approximate_95 | 7 | +0.7731 | +0.0177 |
| 2020 / approximate_90 | 6 | +0.7935 | +0.0256 |
| 2020 / below90 or ambiguous | 18 | +1.0011 | +1.0011 |

These are paired effects within each band, not a comparison of different tier populations. Exact features and Stage41 predictions on original37/47 common samples reproduce within1e-12. Continuous versus90 on those original samples is −0.0044pp (2014) and +0.0059pp (2020): most gain comes from avoiding neutral fallback below90, not a dramatic reweighting improvement on already admitted seats.

| Election | Strict continuous MAE / RMSE | Gain vs strict fallback / 90 |
| --- | ---: | ---: |
| 2014 | 2.7483 / 4.9153 | +0.7002 / +0.5663 |
| 2020 | 2.1752 / 3.7007 | +0.4199 / +0.2754 |

### Feature support and unsupported mass

| Election | S / R / strict R positive-mass support | Mean unsupported S / R weight |
| --- | ---: | ---: |
| 2014 | 330 / 146 / 130 | 0.3090 / 0.7117 |
| 2020 | 318 / 113 / 94 | 0.4650 / 0.8152 |

Support counts mean positive party mass with evidence, not linked-only scoring. Unsupported weights average over all member candidates, including undefined no-group/entrant fallbacks. Complete slates stay primary. Missing support is not observed zero strength.

### National/Labour and other-category errors

Candidate-equal subgroup metrics retain the original valid-candidate denominator. These averages do not sum to the contest-equal whole-slate metric.

| Election / category | Candidates | Fallback MAE / bias | 90 MAE / bias | Continuous MAE / bias |
| --- | ---: | ---: | ---: | ---: |
| 2014 / labour | 64 | 8.3721 / -7.6752 | 7.9418 / -7.0549 | 5.7092 / -4.8515 |
| 2014 / national | 64 | 6.1099 / +3.5069 | 6.2681 / +4.7500 | 6.4970 / +6.0809 |
| 2014 / no_party_group | 34 | 0.6507 / +0.5784 | 0.6850 / +0.5934 | 0.6431 / +0.5330 |
| 2014 / other_mapped | 289 | 2.1183 / +0.8550 | 1.8973 / +0.4406 | 1.3658 / -0.3350 |
| 2020 / labour | 65 | 4.4383 / +2.6774 | 4.5154 / +2.6183 | 4.0726 / +2.8581 |
| 2020 / national | 65 | 8.0944 / -7.9840 | 7.2570 / -7.0978 | 6.3837 / -6.0680 |
| 2020 / no_party_group | 55 | 0.5038 / +0.3789 | 0.4964 / +0.3721 | 0.4766 / +0.3402 |
| 2020 / other_mapped | 376 | 1.4367 / +0.8619 | 1.3321 / +0.7200 | 1.1984 / +0.5051 |

### Largest individual losses versus Stage41 90

| Election | Seat | Paired MAE gain |
| --- | --- | ---: |
| 2014 | East Coast Bays | -2.2648 |
| 2014 | Rodney | -1.5951 |
| 2014 | Upper Harbour | -1.1259 |
| 2014 | Whanganui | -0.8741 |
| 2014 | Bay of Plenty | -0.7594 |
| 2020 | Dunedin | -1.5543 |
| 2020 | Panmure-Ōtāhuhu | -0.1576 |
| 2020 | Mt Roskill | -0.0780 |
| 2020 | Invercargill | -0.0034 |
| 2020 | Ilam | -0.0026 |

All observations remain in scores. Largest gains and every paired error are retained in `evaluation.json`.2014 National share MAE worsens despite overall gains;2020 National/Labour improve. Do not interpret a pooled gain as universal seat/party improvement.

## 2026 readiness companion

All71 seats and206 known candidates retained;0 complete slates. No partial-slate normalization or2026candidate shares.

Known general candidates: S154, R32, strict R11; source party-seat S372 independently of announcements. Stage41 corresponding90 counts were68/16/7 and183.

Partially supported known general features: S42, R23, strict R7. Every component retains its mass, weight, source, centered value and missing reason. Latest saved2023general training means are a named readiness transformation reference, not a new fit or live forecast.

All seven Māori party-flow records remain, source S matrices unavailable and one source R relationship evidence-only. General candidate coefficients are not extended; national TPM support remains distinct from Māori candidate votes. Complete nominations/target ballot roster, national scenarios and Māori polling/unpolled baseline remain separate dependencies.

## Development decision and stopping point

Retain continuous transport as the preferred mean-feature development scenario, with Stage41 frozen90 and exact fallback preserved as reproducible controls. It improves full-frame errors in both reused environments and under strict linkage, while individual failures and fragment-composition uncertainty remain material. This is forecasting-oriented development evidence, not causal identification, as-of validation or calibrated probabilities. No coefficient/threshold/flow changed after scores.

The next separately authorized implementation is coherent local-party/candidate uncertainty, covering uniform population-to-vote allocation, feature transport, missing histories, candidate/local errors, parameter uncertainty and shared dependence. National forecast error enters once. Overlap and finite feasible bounds are not calibrated error variances. Official nominations and Māori polling remain separately bounded. Stop further mean-feature searches here.
