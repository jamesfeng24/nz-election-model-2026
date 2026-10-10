<!-- fold: changelog -->
## CI: site route folders no longer force a frozen replay; live-chain checks run in CI; stale docs corrected, 2026-10-10

- `scripts/validate/ci_frozen.py`: a string literal with no slash counts as a path dependency only when it names a top-level file or one of `config`, `data`, `docs`, `scripts`, `src`. The site PR's new top-level `electorates/` folder matched the dictionary key `'electorates'` in pipeline code, so every frozen pipeline (Stage45 to Stage63) replayed in full on each site push (python job 169.5 of 180 minutes, run 38025763723). No registered pipeline had such a literal before, so every pin and scope fingerprint is unchanged. New selector test.
- `.github/workflows/ci.yml`: a `live` job runs the live 2026 chain's own `--check` commands (Stage50 to Stage83) beside the `python` job; none of them ran in CI before. The development gate, the synthetic bank fixture and the Stage79 2026 readout stay out until the configuration pins the electorate-poll run they read.
- Stale status corrected in `docs/nowcast-specification.md`, `docs/release-checklist.md` and `scripts/README.md` (Stage69 baseline, Stage70 refresh, Stage79 seat polls, Stage86 polled Māori seats, the classification and precision threshold all done).
- Found by the 2026-10-10 repository audit, recorded in `docs/audits/2026-10-10-repository-audit.md` with the open questions for James (Māori C–P range, pinning the electorate-poll run, Te Tai Tokerau Party winners under s 191).

<!-- fold: state -->
# CI and docs: repository audit fixes — review-ready, 2026-10-10

Branch `claude/audit-fixes-jdkx6w` from main. Authorized by James on 2026-10-10 (repository audit; clear single-answer fixes). No model, statistical code, data, registry, pin or `data/sources.json` change.

**What changed.** `ci_frozen.closure` ignores bare literals that name top-level directories other than the source directories, so the site's route folders are not frozen-pipeline dependencies (test `test_a_new_top_level_directory_named_like_a_dictionary_key_is_not_a_dependency`). A `live` job in Verify runs 25 of the live chain's checks (about 10 minutes locally). `docs/ci-validation.md` records both. Stale status text corrected in the specification, release checklist and `scripts/README.md`; the audit is `docs/audits/2026-10-10-repository-audit.md`.

**Checks.** See the PR body.

**Limits.** A full replay of every frozen pipeline still takes about 170 of the `python` job's 180 minutes; splitting it is the parked parallel-replay CI work. The development gate is still checked only locally.

**Exact next action.** The coordinator reviews and merges, ideally before the site PR (#108) merges so its merge push reuses the frozen pipelines. Open for James: the audit's three questions (J1 to J3). At the final-check regeneration: correct the release rehearsal's text (audit C4), the config metadata (C6) and `pyproject.toml` (C5, forces a full replay).
