<!-- fold: changelog -->
## CI: parallel full replay, 2026-10-10

- New manual-only workflow `.github/workflows/full-replay.yml` runs every Verify `python` job command with no reuse, split into parallel jobs (`base`, `stage39`, `stage45-47`, `stage48`, `stage54`, `stage63`) plus the frontend check, with a final job requiring all of them. The Verify `python` job's 180-minute `timeout-minutes` is what made the single-job manual full dispatch fail; GitHub's own limit is 6 hours.
- `scripts/validate/ci_full_replay.py` reads the command list from `ci.yml` (no copy), partitions it, and runs one group; `scripts/tests/test_ci_full_replay.py` guards that the partition covers each command exactly once and that each registered frozen pipeline has its own group. Added to `NON_VERIFY_WORKFLOWS` in `ci_frozen.py`. `ci.yml`, the selectors, the registry and the pins are unchanged. No statistical code, output or check changed.

<!-- fold: state -->
# CI: parallel full replay — review-ready, 2026-10-10

Branch `claude/parallel-full-replay-qikw5y`. Adds the manual Full replay workflow and `ci_full_replay` partition script described in `docs/ci-validation.md` (section "Parallel full replay"). Pull-request and main-push validation are unchanged. Group timeouts are estimates from earlier recorded durations; the first manual run should be read from the per-command job summaries and the limits tightened. The pre-release gate is a single manual dispatch of Full replay on main after the last stage merges. A Full replay run is not an attestation for the frozen-pipeline discovery walk (pins and PR runs still attest). **Exact next action:** after merge, dispatch Full replay on main once when the last stage has merged, record the per-group durations, and adjust timeouts if needed.
