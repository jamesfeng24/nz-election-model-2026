<!-- fold: changelog -->
## CI: only Stage39 and CI-policy tests force the Stage39 replay, 2026-10-07

- `scripts/validate/ci_selection.py`: a new or changed test file forces the full Stage39 reconstruction (about 3 minutes) only if it is `test_stage39_candidate_integration.py`, a `test_ci_*.py` selector test, or a registered Stage39 dependency. Every test still runs in full discovery.
- Tests in `scripts/tests/test_ci_selection.py` updated; AGENTS.md and `docs/ci-validation.md` record the rule.
- No registry, attestation, workflow, frozen-pipeline or statistical change.

<!-- fold: state -->
# CI: Stage39 owned-test rule — review-ready, 7 October 2026

Branch `claude/ci-stage39-owned-tests` from main `ce61569`, independent of the open docs PR #84 (no shared files). James chose one of four proposed CI savings: other test files no longer force the Stage39 replay. He did not adopt main-push reuse, archival test skipping or a docs-only fast path.

**Effect.** PRs that add or change ordinary tests can now reach Stage39 integrity mode. Before, the selector forced full on nearly every such PR (about 3 minutes of the roughly 15-minute Python job). Stage PRs that add new `scripts/<stage>/` or `data/processed/<stage>/` paths still go full, because those paths are outside Stage39's reviewed scopes; that is unchanged. The frozen Stage45/46/47/48/54 replays are unaffected; they were already reused.

**Checks.** `python3 -m unittest scripts.tests.test_ci_selection`: 17 run; the new and changed selector tests pass. The one local failure, `test_runtime_must_match_previously_validated_linux_environment`, is environmental: this container has an unattested package set. It passes on the attested CI runner and fails identically on main locally. This PR changes `scripts/validate/ci*` and AGENTS.md, so its own hosted run is full by design, once.

**Exact next action.** The coordinator reviews and merges.

<!-- fold: decisions -->
## D108 — 2026-10-07 — CI: only Stage39 and CI-policy tests force the Stage39 replay

James narrowed one Stage39 selector rule: a new or changed test file forces the full Stage39 reconstruction only if it is Stage39's own test, a CI-policy (`test_ci_*`) test or a registered Stage39 dependency. A test file cannot change Stage39's outputs, and every test still runs in full standard discovery. All other fail-closed rules (CI, selector, AGENTS.md, unknown paths, dependencies, main/manual events) are unchanged, as are the frozen-pipeline selector and every attestation. Main-push reuse, archival test skipping and a docs-only fast path were considered and not adopted. Decision number taken as the next free after D107; the coordinator may renumber, in which case Stage72 shifts accordingly.
