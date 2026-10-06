# Exceptional-seat balance scale: development diagnostic

**Diagnostic only. Nothing is adopted.** No operational scale, mean, forecast, interface or manual adjustment changes. Reproduce: `python3 -m scripts.exceptional_scale.run` (writes `data/processed/exceptional-scale/summary.json`); `--check` recomputes and compares (about 2 minutes); test `python3 -m unittest scripts.tests.test_exceptional_scale`.

## Question

If the contests flagged as exceptional ex-ante uncertainty by the frozen 2026-10-06 historical audit are separated out, do the data support a narrower candidate N/L balance scale for ordinary seats and a wider one for exceptional seats?

## Inputs and method

- **Flags.** 38 of 257 seat-elections (2014: 8, 2017: 6, 2020: 10, 2023: 14), hard-coded in `scripts/exceptional_scale/run.py` as a temporary development input, not a data interface. They were fixed before this script existed and are not revised here.
- **Observations.** The Stage48 universe and loader, unchanged (`scripts.balance_scale.data.environments`): balance `v = log(N/L)`, frozen ratio means, frozen fold scales (seat 0.350/0.336/0.327/0.309, shared 0.150/0.192/0.172/0.190).
- **Model.** The Stage48 Gaussian balance likelihood (`scripts.balance_scale.fit.environment_value`): per election `Sigma = diag((seat * m_i)^2) + shared^2 11^T`, with the exact Gaussian-logistic location and no mean change. Seat multiplier `m_i = exp(a + b * exceptional_i)`, unpenalised, summed over the 257 seats. The shared election scale is held at its frozen value. Compared with a one-multiplier fit (`b = 0`).
- **Robustness.** Per-election fits; leave-one-election-out fits with held-out likelihood; refit without the five largest exceptional residuals; 400 within-election seat bootstraps; 400 within-election flag permutations (seed 20261006).
- **Descriptive residual.** `z = (v - l) / sqrt(shared^2 + seat^2)` under the frozen control scale. It includes the shared election effect, which is large in 2014, a prior-only fold. Bands are also given for the audit's own metric (`|balanceSeatResidual| / seat`).

## Results

| | N | RMS z | MAE z | \|z\| 90% | share \|z\|>1.645 | Fitted seat multiplier (90% bootstrap) |
|---|---:|---:|---:|---:|---:|---|
| All, one scale | 257 | 0.92 | 0.70 | 1.39 | 7.0% | 0.79 (0.68–0.90) |
| Ordinary | 219 | 0.79 | 0.64 | 1.24 | 3.2% | 0.60 (0.54–0.65) |
| Exceptional | **38** | 1.44 | 1.04 | 2.53 | 28.9% | 1.46 (1.09–1.80) |

The exceptional/ordinary seat-scale ratio is 2.41 (bootstrap 1.80–3.08). The likelihood-ratio statistic is 70.2 on 1 df, and no within-election permutation reached the observed ratio (0/400).

| Election | Exceptional N | Ordinary m | Exceptional m | Ratio | LOEO ordinary m | LOEO ratio | Held-out NLL/seat, two-group minus one-scale |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2014 | 8 | 0.60 | 1.74 | 2.92 | 0.61 | 2.26 | -0.196 |
| 2017 | 6 | 0.63 | 2.08 | 3.28 | 0.59 | 2.21 | -0.197 |
| 2020 | 10 | 0.59 | 0.72 | 1.23 | 0.61 | 2.69 | -0.024 |
| 2023 | 14 | 0.59 | 1.34 | 2.26 | 0.61 | 2.51 | -0.137 |

Without the five largest exceptional residuals (Ōhāriu 2017, Auckland Central 2023, Epsom 2014, Tāmaki 2023, Epsom 2017), the ordinary multiplier stays 0.60, the exceptional multiplier falls to 1.02 and the ratio to 1.69.

Total balance sd and the even-seat 90% width of the N/(N+L) split (pp), with the shared scale unchanged:

| Election | Frozen | One-scale fit | Ordinary | Exceptional | Ordinary vs frozen | Ordinary vs one-scale | Exceptional vs ordinary |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2014 | 31.3 | 25.9 | 21.3 | 43.7 | 0.68 | 0.82 | 2.05 |
| 2017 | 31.8 | 26.9 | 22.9 | 43.2 | 0.72 | 0.85 | 1.88 |
| 2020 | 30.4 | 25.5 | 21.5 | 41.6 | 0.71 | 0.84 | 1.93 |
| 2023 | 29.8 | 25.4 | 21.9 | 40.2 | 0.73 | 0.86 | 1.84 |

By |z| band (control residual), exceptional/ordinary counts: ≥1.5: 11/11; 1.25–<1.5: 1/10; 1.0–<1.25: 2/22; 0.75–<1.0: 4/36; 0.5–<0.75: 5/38; <0.5: 15/102. On the audit metric: 9/6, 1/4, 3/9, 2/23, 6/35, 17/142.

## Interpretation and limits

- **The ordinary scale is the robust finding.** About 0.60 of the frozen seat scale in every election, in every leave-one-out fit and with the largest exceptional cases removed. That is about 24% below a one-scale refit (0.79) and 40% below the frozen scale.
- **The exceptional scale is not robust.** Its size rests on 38 seats, with a ratio near 1.2 in 2020 and 1.7 once five cases are dropped. Treat "about 2x" as indicative only.
- **The flags were not fully blind.** The audit prompt included a residual-ranked list of cases at or above 0.5σ, and 21 of the 38 YES rows come from it. That inflates the separation; a blind replay would be the clean test.
- **This is in-sample development evidence.** The flags and the scales use the same, reused elections. It is not chronological validation, not a calibrated probability, and the shared scale and the parameter uncertainty are untouched.
- **Part of the narrowing applies to every seat.** Even the one-scale fit is below the frozen scale (0.79), consistent with Stage48's unpenalised constant (0.78–0.84). Only the step from 0.79 to 0.60 depends on the flags.
- **Recommendation (not adopted).** The evidence justifies a separately authorized, pre-registered ordinary/exceptional design, ideally scored chronologically with blind flags, in which the exceptional scale is treated as weakly identified.
