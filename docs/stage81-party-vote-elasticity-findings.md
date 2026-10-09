# Stage81 findings: how the local party vote moves with the national change (D119)

Design frozen before scoring in [stage81-party-vote-elasticity-design.md](stage81-party-vote-elasticity-design.md) (commits 2221990 and the amendment 88671e0). James approved it on 2026-10-09 and kept the choice of default for himself after the results. General seats only; the live default is unchanged (proportional).

## Result

**Frozen rule: `carry_mixture` of P, L and H, evidence `weak`.** No arm beats another on the National minus Labour margin (M1). Same-points (A) is beaten on minor-party composition (M2) by every other arm, so it drops out. The 2017 to 2020 source bounds make no difference to any comparison. The 2026 materiality override did not fire (one seat's top party differs between arms at the national mean, Tukituki), so the class stands.

| Pooled over 2014 to 2017, 2017 to 2020, 2020 to 2023 (pp) | P proportional | A same points | L log-odds | H halfway |
|---|---:|---:|---:|---:|
| M1 margin error (mean absolute) | 4.05 | 3.85 | 3.95 | 3.77 |
| M2 minor-party error (macro mean absolute) | 0.62 | 0.87 | 0.58 | 0.62 |
| M4 all-party error (macro mean absolute) | 0.79 | 0.87 | 0.73 | 0.73 |
| M5 residual scale (CLR mean square per category) | 0.100 | 2.47 | 0.098 | 0.43 |

By transition, M1: 2014 to 2017 P 5.79, A 3.70, L 4.56, H 4.34; 2017 to 2020 P 3.14, A 4.38, L 3.71, H 3.59; 2020 to 2023 P 3.21, A 3.47, L 3.57, H 3.40. The ordering flips with the election: same points is best in 2014 to 2017 (Labour's rise from 25% to 37%, which proportional scaling overstated in National's strongholds) and worst in the two large National swings, where proportional is best. The paired seat bootstrap puts H below P on the pooled M1 (0.27pp, 90% interval 0.12 to 0.43), but H is lower in only one of three elections, so by the frozen rule it does not beat P. The bootstrap ignores dependence between seats and there are three elections.

**Large movers in their strongest seats (D1, top quartile of the party's previous share, mean signed error predicted minus actual, pp).**
- National 2017 to 2020 (x0.58): P +0.2, L +2.1, H +2.3, A +3.5. Same points keeps National's strongholds too high.
- NZ First 2020 to 2023 (x2.34): P -0.9, L -1.0, H -1.7, A -2.1. Proportional is closest; no arm over-predicts NZ First's growth in its strongest seats.
- ACT 2017 to 2020 (x15): P +4.0, L +2.7, H 0.0, A -1.1. Proportional overshoots ACT's first big rise.

**2026 readout (general seats only, 256 draws, common random numbers, classification from PR #104 as a byte copy; Māori seats not run).**

| Expected general electorates | default | P | A | L | H | mixture P/L/H |
|---|---:|---:|---:|---:|---:|---:|
| National | 29.61 | 29.61 | 29.65 | 29.79 | 29.65 | 29.71 |
| Labour | 26.92 | 26.92 | 27.54 | 27.05 | 27.33 | 27.11 |
| NZ First | 1.66 | 1.66 | 1.41 | 1.54 | 1.44 | 1.52 |

- **The transform does not explain the National electorate count.** Same points gives 29.65 against 29.61 proportional (unpaired Monte Carlo error up to about 0.25 each, smaller for the paired difference). On party vote at the national mean, National leads Labour in 31 seats under P and 32 under A, L and H. The earlier local preview's contrast of about 30 against 36 to 37 therefore does not come from proportional versus same-points scaling of the party vote in this pipeline. The remaining candidate is the baseline: this layer starts from party votes, so a National electorate margin that ran ahead of its party vote in 2023 is not carried over. That is outside this stage and is not tested here.
- **Where the arms differ is the minor-party seats.** Northland (NZ First, Labour, National win probability): P 0.43 / 0.36 / 0.16; L 0.41 / 0.39 / 0.15; H 0.36 / 0.44 / 0.15; A 0.32 / 0.49 / 0.13. The most arm-sensitive seats for National's win probability (P against A): Hutt South 0.22 to 0.14, Tāmaki 0.59 to 0.67, Whanganui 0.47 to 0.39, Kapiti 0.18 to 0.11, Takanini 0.53 to 0.59.
- The national reconciliation gap is 0.40pp (P), 0.07 (A), 0.61 (L), 0.32 (H), 0.44 (mixture), all inside the 1.0pp limit.

## What the rule leaves to James

The rule's answer is a mixture because the backtest cannot separate P, L and H. Points for the decision (a recommendation, not part of the frozen rule):

- The consequential national quantity, the National electorate count, is the same under every arm to within 0.2 seats. The arms move individual minor-party-strong seats (Northland, Hutt South, Kapiti, Tāmaki), by up to about 0.1 in win probability.
- Same points (A) and the halfway arm (H) produce exact zero shares for small parties in some seats, so their residual scale (M5 2.47 and 0.43) is far from the proportional layer's 0.100 that the current noise scales (`scales-2026.json`) were calibrated on. Proportional and log-odds are equal on M5 (0.100, 0.098), so a P/L mixture would not need a noise recalibration, while anything including A or H would.
- Keeping proportional as the default is defensible: it is best on two of the three elections for the margin, best on National's large fall and on NZ First's rise in their strongest seats, and carries no refit. A P/L mixture is the cheapest way to carry the structural spread. Switching to the rule's P/L/H mixture, or to any other arm, brings the follow-up refits in the design's knock-on section (S, R, kappa and the local noise scales) and is a separate decision for James.

## What was and was not done

- Added: `scripts/party_vote_elasticity/` (transforms, backtest, rule, 2026 readout, runner), 24 tests, an optional `localParty` configuration key read by `scripts/nowcast_assembly/general.py` and `assemble.py`, and the artifacts in `data/processed/party-vote-elasticity/`.
- Unchanged: `config/nowcast-2026.json` (no `localParty` key, so the frozen layer runs; the development gate is reproduced), the Stage5 records, the candidate fit, the noise scales, the draw bank, the export and the TypeScript.
- Limits: three elections; seats within an election are dependent; the composition closes over the persistent parties only; the national shares are the realised ones (conditioning); the readout is development-size, general seats only, and uses James's classification from PR #104 as a copy because the file is not yet on main.

## Reproduction

```
python3 -m scripts.party_vote_elasticity.run --check            # backtest scores and rule (about 3 seconds)
python3 -m scripts.party_vote_elasticity.run --stage findings --check   # final findings and manifest from the saved readout
python3 -m scripts.party_vote_elasticity.run --stage readout --draws 256  # the 2026 readout (about 12 minutes on 4 cores); not run in CI
python3 -m unittest scripts.tests.test_stage81_transforms scripts.tests.test_stage81_elasticity
```
