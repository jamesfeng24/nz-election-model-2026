<!-- fold: changelog -->
## Stage83 — ordinary-seat minor-candidate spread, 2026-10-10

- **Question:** do ordinary-seat multipliers on the candidate within-remainder noise (and separately the major-mass noise), fitted on earlier elections only, beat the D107-only control on the 257 historical candidate records, with the 38 Stage67 flagged seats held at 1.00? Frozen design `docs/stage83-ordinary-minor-spread-design.md` committed before any score; amendment 1 (a robust scale estimator and four more arms) committed after the moment fits and before any score.
- **Result:** `keep_control_mixed`. All four candidate arms improve minor CRPS by 2.4% to 3.7% pooled and in all three decision folds, pass the National/Labour guard and leave flagged seats bit-identical, but none brings ordinary-seat minor 80% coverage inside the registered band [0.74, 0.86] (control 0.924, best arm 0.871). Nothing is adopted and the nowcast configuration is unchanged.
- **Artifacts:** `data/processed/ordinary-minor-spread/` (design contract, input contract, fits, evaluation, decision); `scripts/ordinary_minor_spread/`; `docs/stage83-ordinary-minor-spread-findings.md`. New tests: `scripts/tests/test_stage83_ordinary_minor_spread.py`.
- **Guard:** `test_historical_flag_isolation.py` now lists Stage83 (and its output directory) as a third owner of the historical flags, so no module outside Stage67, its predecessor and Stage83 may read them (D107 unchanged).
- **Not touched:** the configuration, the assembly, the draw bank, the Stage73 gate and Stage74 fixture, any mean, S, R, kappa, ratio, elasticity, local-party, national, balance or Māori component, the Stage67 flags, `data/sources.json`, CI.

<!-- fold: decisions -->
## D121 — 2026-10-10 — Stage83: ordinary-seat minor-candidate spread (number from the coordinator)

Frozen rule outcome `keep_control_mixed`; no operational change.

- **Design** (James approved the principle and the design on 2026-10-10; the flag list is the Stage67 list, unchanged): earlier-trained, closed-form multipliers on the candidate within-remainder noise and on the major-mass noise, ordinary seats only, flagged seats at 1.00, no multiplier above 1. Deviations from the approved draft, recorded before scoring: penalty-free fit (the Stage67 precedent, not a ridge), within and mass as separate arms, and a candidate-only National/Labour guard in place of the composed width check. Amendment 1 added the robust estimator after the moment multipliers were seen.
- **Result:** pooled minor CRPS −2.6% (within), −3.7% (within and mass), −2.4% and −3.4% (robust versions); the paired seat-bootstrap 90% interval for within-and-mass excludes zero. Ordinary-seat minor 80% coverage 0.924 (control) to 0.871–0.894 against the registered band [0.74, 0.86], so the rule keeps control. The 17-flag versions agree in direction (−1.5% to −2.3%).
- **What it would do:** the descriptive refit (within 0.80, mass 0.91) lowers win probability of low-share minor candidates in ordinary seats by about 10 to 30 percent of their value (Tauranga ACT 3.1% to 2.2%, Banks Peninsula Green 11.9% to 10.3%). It does not remove the tail-driven oddities, which sit in the skewed within-remainder law and the local-party layer, neither of which this stage changes.
- **Limits that stay attached:** the Stage67 flags were selected with all results known; the Gaussian law over-covers the centre of the minor-candidate distribution while fitting its tails, a heavy-tail signature (Student-t and mixtures remain closed); independents are already under-covered and the arms slightly worsen them. Adoption of the descriptive refit despite the failed band would be James's decision, as a separate change.

<!-- fold: state -->
# Stage83 ordinary-seat minor-candidate spread — review-ready, no adoption, 2026-10-10

Branch `claude/project-thread-uuzsp9` from main `9d2c8f1`. Frozen design `d1fd448`, amendment 1 `192cbab` (both before any score). Authorized by James on 2026-10-10 (D121, the coordinator's brief). Not changed: the configuration, the assembly, the draw bank, the gate and fixture, `data/sources.json`, CI and the validation registry.

- **Counts.** 257 candidate records, 219 ordinary (56, 58, 55 and 50 in 2014, 2017, 2020 and 2023) and 38 flagged; decision seats 163 ordinary (58, 55, 50) in 2017, 2020 and 2023; 38 flagged seats held at control, maximum absolute difference from control 0.0. 32,768 draws, 16,384 prefix.
- **Result.** `keep_control_mixed` (see D121 and `docs/stage83-ordinary-minor-spread-findings.md`). All guards pass except the registered ordinary-seat minor 80% coverage band.
- **Open question for James.** Adopt the descriptive refit (within 0.80, mass 0.91) anyway, or keep control. If adopted it is a separate change: new config keys, `scaled()` in `scripts/nowcast_assembly/general.py`, the `check_config` pin, and a regenerated Stage73 gate and Stage74 fixture.
- **Checks.** See the PR body.
- **Exact next action.** The coordinator reviews and merges. Then wait for James's decision on adoption; nothing else follows from this stage.
- **Reproduction.** `python3 -m scripts.ordinary_minor_spread.inputs --check`, then `fit`, `evaluation` (about 10 minutes on four cores) and `decision` with `--check`, and `python3 -m unittest scripts.tests.test_stage83_ordinary_minor_spread`.

<!-- fold: roadmap -->
| Stage83 | Ordinary-seat minor-candidate within and mass spread multipliers (frozen earlier-trained design, D121) | review-ready: `keep_control_mixed`, no adoption; every guard passes, only the registered coverage band fails |
