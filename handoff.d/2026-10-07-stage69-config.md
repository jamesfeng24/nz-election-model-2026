<!-- fold: changelog -->
## Config: nowcast baseline switched to the Stage69 voting-place notionals, 2026-10-07

- `config/nowcast-2026.json`: `baseline.source` now points at `data/processed/voting-place-notionals/baseline-party-vectors.json` (Stage69, D103); the status note records the previous source. Nothing else changed: no scale, Māori seat input, Stage64 output or code.

<!-- fold: state -->
# Config: Stage69 baseline adopted in the nowcast config — review-ready, 7 October 2026

Branch `stage/69-voting-place-notionals-72u6wn`, restarted from main `0160180` (merge of Stage69 PR #96, whose branch history was fully merged). One-line pointer change after James's "Stage 69 looks good" (relayed by the coordinator as approval of the result and of adopting the baseline). The Stage69 file has the same `transitions.2023-2026.scopes.general` structure the assembly reads: the 17 party categories and 64 general seats load through `scripts/nowcast_assembly/general.py` `baseline`, and `check_config` accepts the config (pending fields unchanged: `maori.unpolledSeats`, `mmp.blocs`, `mmp.rulesVersion`, `roster.snapshotId`, `simulation.draws`, `simulation.precisionPolicy`).

**Checks run.** `python3 -m unittest` on the Stage50, 69, 72, 73, 74, 75 and 76 test modules: 51 tests pass. Not run locally: full discovery (hosted CI runs it).

**Effect and limits.** Any nowcast assembled from now on uses the voting-place baseline for the 64 general seats (Māori seats are unaffected: they have no baseline here). Seat-level party means move at 8 seats by 2 to 8 points of National−Labour margin and Kapiti changes leader on the 2023 baseline (PR #96). Reverting is the same one-line change.

**Test fix.** The post-merge main run of #96 (Verify 37569089462, head `0160180`) failed one Stage69 test, `test_deterministic_regeneration_matches_saved_artifacts_apart_from_draws`, on `baseline-party-vectors.json` only; the PR run on the same content had passed. Cause: `shareExact` is `Fraction(share).limit_denominator(10**15)`, so a last-bit float difference between runner CPUs changes both integers, and `equivalent()` compared integers exactly. `scripts/voting_place_notionals/common.py` `equivalent` now compares `{numerator, denominator}` pairs by value to the same 1e-9 tolerance as floats (a unit test shows one-ulp noise changes the integers but not the value). Artifacts are byte-identical; only the manifest code hash changed.

**Exact next action.** The coordinator reviews and merges; the docs fold then folds this and the Stage69 fragment.

<!-- fold: roadmap -->
| Stage69 | Voting-place-based 2026 notional baselines (boundary reconstruction replacing the Stage64 population-flat allocation) | merged (PR #96, D103): 8 of 64 seats material, Kapiti changes leader; Māori seats excluded; adopted as the nowcast baseline by the Config PR (baseline.source pointer) |
