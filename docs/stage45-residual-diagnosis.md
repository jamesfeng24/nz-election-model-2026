# Stage45 residual-scale allocation diagnosis

This audit precedes revised uncertainty scoring. It uses the preserved Stage44 residual inventory and actual simulation equations; no mean model is refitted and no new performance score is calculated.

## Verified allocation

| Layer | Election | Vectors | Other squared CLR fraction | NAT/LAB log-ratio RMS | Stage44 implied NAT/LAB SD |
|---|---:|---:|---:|---:|---:|
| local_party | 2011 | 63 | 98.43% | 0.1809 | 0.5385 |
| local_party | 2014 | 64 | 98.35% | 0.1217 | 0.6080 |
| local_party | 2017 | 64 | 98.06% | 0.1928 | 0.6924 |
| local_party | 2020 | 65 | 97.72% | 0.1102 | 0.7256 |
| local_party | 2023 | 65 | 97.05% | 0.1416 | 0.7650 |
| candidate | 2014 | 64 | 85.04% | 0.4036 | 0.7616 |
| candidate | 2017 | 64 | 88.06% | 0.2898 | 0.8352 |
| candidate | 2020 | 65 | 83.77% | 0.3264 | 0.8622 |
| candidate | 2023 | 64 | 87.88% | 0.2734 | 0.8832 |

All quantities above are dimensionless natural-log units, not percentage points. The implied SD is before nonlinear location adjustment. For NAT/LAB, CLR centering cancels exactly: residual = log(actual NAT / actual LAB) − log(mean NAT / mean LAB), with the frozen ε replacement.

More minor coordinates naturally contribute more squared magnitude. In the local-party layer their per-coordinate relative errors are also much larger than the major-party coordinates, while the common isotropic seat scale imposes the same variance on every option. Candidate heterogeneity is less uniform: no-group candidates have the largest coordinate RMS, and smaller mapped candidates are not worse than every major group in every election. For the NAT/LAB contrast, the actual Stage44 generator implies variance **2 σ_shared² + 2 σ_seat²**, independently of CLR subtraction.

Stage44 is correctly implemented. Its statistical allocation spreads large small-option relative errors into major-party balance uncertainty. A post-result change to the uncertainty family is justified; this is not a numerical correction to Stage44.

## Shared, seat and prior allocation

| Layer / forecast election | Earlier environments | Shared SD | Seat SD | Shared prior variance fraction | Seat prior variance fraction |
|---|---:|---:|---:|---:|---:|
| candidate / 2014 | 0 | 0.2000 | 0.5000 | 100.0% | 100.0% |
| candidate / 2017 | 1 | 0.3115 | 0.5017 | 30.9% | 74.5% |
| candidate / 2020 | 2 | 0.3313 | 0.5119 | 21.9% | 57.3% |
| candidate / 2023 | 3 | 0.3635 | 0.5078 | 15.1% | 48.5% |
| local_party / 2011 | 0 | 0.1500 | 0.3500 | 100.0% | 100.0% |
| local_party / 2014 | 1 | 0.1328 | 0.4089 | 95.7% | 54.9% |
| local_party / 2017 | 2 | 0.1290 | 0.4723 | 81.1% | 32.9% |
| local_party / 2020 | 3 | 0.1248 | 0.4977 | 72.3% | 24.7% |
| local_party / 2023 | 4 | 0.1308 | 0.5249 | 56.4% | 19.1% |

Variance contributions are exactly priorPseudoEnvironments × priorSD² / totalEnvironments and sum(historical second moments) / totalEnvironments. The candidate early seat SD 0.50 is an assumption, not an estimate. Shared effects are estimated once per election; many seats do not create many independent common-error environments.

## Other meaningful contrasts and zero handling

| Layer | Election | Major/remainder aggregate log-ratio RMS | Within-remainder pair log-ratio RMS | Zero coordinates | Zero squared magnitude fraction | Near-zero squared magnitude fraction |
|---|---:|---:|---:|---:|---:|---:|
| local_party | 2011 | 0.1072 | 0.8446 | 1 | 8.18% | 8.50% |
| local_party | 2014 | 0.0881 | 1.0164 | 4 | 27.08% | 35.29% |
| local_party | 2017 | 0.1010 | 0.9189 | 0 | 0.00% | 13.84% |
| local_party | 2020 | 0.1708 | 1.0021 | 1 | 5.70% | 23.82% |
| local_party | 2023 | 0.1561 | 0.6906 | 0 | 0.00% | 6.80% |
| candidate | 2014 | 0.3686 | 0.8580 | 0 | 0.00% | 0.00% |
| candidate | 2017 | 0.4785 | 0.9388 | 0 | 0.00% | 0.00% |
| candidate | 2020 | 0.3903 | 0.8209 | 0 | 0.00% | 0.00% |
| candidate | 2023 | 0.4320 | 0.7726 | 0 | 0.00% | 0.00% |

Major/remainder aggregates use sums of ε-replaced fine options. Within-remainder RMS averages squared pair contrasts within each slate, then weights contests equally. Fine IDs, source/outcome references, complete group counts, coordinate RMS, fitted class effects, exact prior/history decomposition and implied contrast covariance are in `data/processed/uncertainty-revision/diagnosis.json`.

The diagnostic near-zero boundary is 0.01% share and is not an eligibility or scale-estimation threshold. All options remain represented. Zero replacement remains ε=1e-6. The consumed candidate frame has no zero observations; the party frame contains zeros, including one positive observed party share with frozen mean zero. A locked zero mean cannot acquire positive mass while preserving that mean.

Large within-remainder relative misses must remain uncertainty evidence. They should be allocated to remainder directions rather than erased. The tiny fixed replacement can materially affect extreme minor-option log errors, but observed zero coordinates alone do not account for the pooled major overdispersion. The maximum NAT/LAB log-ratio replacement perturbation is 0.00000290 for local party and 0.00000790 for candidate residuals; these meaningful major contrasts are essentially unaffected.

## Independent arithmetic and preservation

Scalar `math.log`/`math.fsum` CLR residuals and independent QR class fits reproduce every saved Stage44 environment moment and class effect within 1e-10. Direct covariance contrasts verify the projected shared/seat generator. This is independent numerical verification, not documentary or predictive validation.

Reproduce with `.venv/bin/python -m scripts.uncertainty_revision.diagnosis`; verify with `--check`. Only the separate Stage45 diagnosis artifacts are written. Consumed file hashes are pinned; prior Stage44 data and implementation are unchanged.
