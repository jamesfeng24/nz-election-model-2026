# Stage72: 2026 scales, live nowcast configuration and the D107 classification schema

Decision D109 (provisional; D108 is proposed for the CI rule in #85). Approved by James on 2026-10-07. This is an engineering stage: nothing is fitted, scored or tuned, and no flag is entered.

## What it provides

1. **2026 uncertainty scales.**
   - **Produced by:** `python3 -m scripts.nowcast_config.scales` (add `--check` to verify), writing `data/processed/nowcast-config/scales-2026.json`.
   - **Rule:** the frozen Stage45 function `scripts.uncertainty_revision.estimation.fit(rows, layer, 2026)`, unchanged, on the unchanged Stage44 inventory and Stage45 priors. It must equal Stage45's own all-election `descriptive` fit exactly; the build fails otherwise.

   | Layer | Trained on | Balance seat sd | Balance shared sd |
   |---|---|---|---|
   | Candidate | 2014–2023 | 0.3010 | 0.1808 |
   | Local party | 2011–2023 | 0.1473 | 0.0613 |

   **D107 (arithmetic only, candidate seat balance scale):** ordinary seat sd 0.1806 (total balance sd 0.2556); exceptional seat sd 0.3010 (total 0.3512). The evidence for 0.60 stays development-informed and flag-selection-sensitive (D101, D107).

2. **`config/nowcast-2026.json`, the single live configuration** ([nowcast-specification.md §8](nowcast-specification.md)). It records:
   - the estimand `nowcast`;
   - national source Stage62 arm A, `stateKey: lastDataSupport` with `electionDay` forbidden, model state as of 2026-09-27, data cutoff 2026-10-06;
   - the scales file and the D107 multipliers;
   - the classification path;
   - the baseline pointer (Stage41/64 population-flat for now, Stage69 when adopted);
   - interval levels 50/80/90 with 80% primary.

   **Explicitly pending:** `roster.snapshotId` (Stage50), `simulation.draws` and `precisionPolicy` (Stage63), `mmp.rulesVersion` (no canonical identifier recorded yet), `mmp.blocs` and `maori.unpolledSeats` (James).

   **Validator:** `python3 -m scripts.nowcast_config.validate`. It accepts pending fields now and rejects them with `--require-complete`, which the assembly must use.

3. **The D107 classification schema** (`config/general-seat-classification-2026.json`, not yet written). Validated by `check_classification`. Fields per seat: `electorateId`, `class` (`ordinary`/`exceptional`), `reason`, `sources`, `author`, `recordedAt`, `extraSdOptIn`. It requires:
   - every one of the 64 general seats exactly once (Stage56's 2026 target frame), with no Māori ids;
   - a missing file or seat fails, never defaulting to 0.60;
   - exceptional seats cite a source;
   - `extraSdOptIn` only on exceptional seats;
   - every Stage56 exceptional flag is `exceptional` here.

## Not done

- No 2026 classification entered (James's decision).
- No draw count, precision rule, bloc, rules-version string or Māori fallback invented.
- No change to Stage45–71 outputs, the national fit, CI or the registry.
- No Stage50/63/69/70 work.

Tests: `scripts/tests/test_stage72_nowcast_config.py` (labelled synthetic classification fixtures in memory only).
