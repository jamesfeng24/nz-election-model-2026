<!-- fold: changelog -->
## Stage50 (part 1) — official nomination refresh pipeline, 2026-10-07

- Added `scripts/nominations_2026/`.
  - `official.py` turns the official table into Stage40 claims and complete-slate declarations.
  - `refresh.py` produces the Stage40 snapshot, then the Stage42 features, the Stage75 recentring, the reconciliation report and the config pointer.
  - Both run the unchanged Stage40/42 builders.
- The assembly's `live_slates` takes general seats only and can be called on in-memory features.
- Tested end to end on an in-memory synthetic official list.
- No official data yet. No change to frozen outputs, `data/sources.json`, models or CI.

<!-- fold: state -->
# Stage50 part 1 official nomination pipeline — review-ready, 2026-10-07

Branch `stage/50-nominations` from main `e429222`. Authorized by James on 2026-10-07: James supplies the official files (tool-rendered text as a fallback), and the official list replaces party announcements in the live roster.

**What changed.**
- New `scripts/nominations_2026/` (`official.py`, `refresh.py`) and `docs/stage50-nominations.md`, which includes the post-publication procedure.
- `scripts/tests/test_stage50_nominations.py`: 7 tests.
- Stage75 `recentre` accepts an explicit feature file.
- Assembly `live_slates` takes general seats only and accepts in-memory features.

**Checks.**
- `python3 -m unittest scripts.tests.test_stage50_nominations`: 7 pass.
- Stage72–75 tests: 21 pass.
- `python3 -m scripts.nowcast_assembly.run --check` and `python3 -m scripts.nowcast_assembly.fixture --check`: reproduced.

**Exact next action (part 2).** This happens after the official publication (nominations close 12:00 NZDT, 8 October):
1. preserve James's files and register them in the new standalone registry;
2. commit;
3. transcribe the files to the official table;
4. run `python3 -m scripts.nominations_2026.refresh --acquisition … --apply-config` and `--check`;
5. regenerate the development gate, review the reconciliation, and recheck the classification draft against Labour and the new candidates;
6. open the part-2 PR.

<!-- fold: roadmap -->
| Stage50 | Nomination snapshot, immutable raw acquisition (item 3) | part 1 (pipeline, tested on a synthetic list) review-ready; part 2 (acquisition and refresh) after the 8 October publication |
