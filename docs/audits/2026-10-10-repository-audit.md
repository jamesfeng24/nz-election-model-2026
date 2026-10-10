# Repository audit (2026-10-10)

Internal record. The same file is kept in the project files as `audit/findings.md`. Items marked "fixed in the audit PR" are in the PR that adds this file; the James items are open questions.

Audited `main` at `59edb70` (after #115 Stage86). Open PRs left alone: #116 (Stage85), #117 (Stage87), #114 (poll refresh 2026-10-10), #108 (site, out of scope). Out of scope by brief: the site, the do-not-reopen list, D107, the Sobol fix (#117) and the Māori candidates (#115).

Severity: **High** = wrong output, broken release path or multi-hour CI cost. **Medium** = reproducibility or validation gap, misleading record. **Low** = stale text, tidy-up.

**How it was checked.**
- Full Python suite on main: 1,641 tests pass, 9 skipped by design (jax/polars inference environments; ungenerated optional caches). Frontend: 141 Vitest tests, typecheck, build and `check:dist` pass.
- Every `--check` of the live 2026 chain that CI never runs (29 commands, Stage50 to Stage83) on the pinned CI packages (numpy 2.2.6, scipy 1.16.0). Table at the end.
- The frozen-pipeline selector on #108's head, and on #108 merged with the fix.
- Code read: `scripts/nowcast_assembly/*`, `scripts/seat_polls/{apply,model,live,readout}.py`, `scripts/maori_seat_layer/live.py`, `scripts/maori_seat_fallback/{draws,model}.py`, `scripts/nowcast_config/validate.py`, `scripts/release_rehearsal/run.py`, `scripts/polling/weekly_refresh/adopt.py`, `scripts/validate/ci_frozen.py`, `src/release/*`, `src/models/nowcast/*`, `src/models/mmp/seatLayer.ts`, both workflows, `config/nowcast-2026.json`, the nowcast specification and release checklist.

No numerical bug was found in the live assembly path itself: the seat-poll update keeps the D107 multiplier exactly once (`seat_polls/apply.py:37` divides by it before `general.scaled` multiplies again), national uncertainty enters once per row, Māori winners are drawn only from named candidates, and batch-means MCSE keeps each national draw's replicates together.

---

## Clear single-answer fixes

### C1 (High, CI cost) The site's `electorates/` folder forces every frozen pipeline to replay — fixed in the audit PR
- **Where:** `scripts/validate/ci_frozen.py:119-120` on main (`closure`: a bare string literal equal to any top-level name becomes a path dependency).
- **Evidence:** #108 adds a top-level `electorates/` folder. Pipeline code has the dictionary key `'electorates'`, so on #108 the selector reports `referenced path changed: electorates/index.html` for Stage45, 46, 47, 48 and 54 (reproduced locally). #108's Verify run 38025763723 took 169.5 minutes in the `python` job, against the 180-minute cap. Every further #108 push and its merge push would pay the same.
- **Fix:** bare literals count only for top-level files and the source directories `config`, `data`, `docs`, `scripts`, `src`. On main every pipeline's literal set, pin and scope fingerprint are unchanged; with #108 merged on top, Stage45 to Stage54 reuse their pins again. New test; it fails before the fix.

### C2 (Medium, validation gap) None of the live 2026 chain's checks run in CI — fixed in the audit PR
- **Where:** `.github/workflows/ci.yml` lists checks up to Stage63 only. AGENTS.md: "Every new stage registers its expensive checks the same way".
- **Evidence:** 29 `--check` commands of Stage50 to Stage83 (config, scales, nominations, notionals, Māori layer, seat polls, elasticity, minor spread, development gate, candidate fit) appear in no workflow. Unit tests read some of their outputs but never regenerate them. All pass today (table below), so nothing is stale yet, but nothing would catch it.
- **Fix:** a parallel `live` job (40-minute limit) runs the stable ones. Not added: the development gate and the Stage79 readout (see J2).

### C3 (Low, docs) Stale status text — fixed in the audit PR
- `docs/nowcast-specification.md:5` "the live bank is blocked on inputs"; `:44` "Stage70 unpushed"; `:47` "baseline switches to Stage69"; `:50` "3 polled seats; 4 unpolled"; `:86` general-seat polls "No measurement interface exists" (Stage79 built one, D117, D123); `:93` "Four seats ... have no estimate ... block every MMP output"; `:120` "Still open: ... precision thresholds"; `:126` "will hold"; `:131` "Stage64 now, Stage69 later"; `:147` classification still listed as James's open decision.
- `docs/release-checklist.md:3` "Status as of 7 October"; `:28` Stage70 joint draws (done); `:30` general-seat polls via Stage56 (done by Stage79).
- `scripts/README.md:3` "No ingestion or modelling scripts implemented in stage 1".

### C4 (Medium, false record) The release rehearsal says it uses the Stage64 baseline — apply at the next rehearsal regeneration
- **Where:** `scripts/release_rehearsal/run.py:5-10, 28-31` and `data/processed/release-rehearsal/report.json` (`realInputsNotYetAvailable`, `syntheticStandIns`).
- **Evidence:** the report says "the configured Stage64 population-flat baseline is used" and "Stage69 ... not adopted", but `config/nowcast-2026.json` `baseline.source` is the Stage69 notionals (adopted 2026-10-07), which the rehearsal reads. The stand-in list also says the classification and roster do not exist. Separately, `run.py:47-48` stops with `SystemExit` once the config adopts any refresh other than 2026-10-07.
- **Fix:** correct the text and read the national input from the config. Not done in this PR because the report must be regenerated with it (about 35 minutes), and #117 makes the report stale anyway; it belongs in the planned final-check regeneration.

### C5 (Low) `pyproject.toml` says "no model implemented" and "Standard library only" — deferred
- **Where:** `pyproject.toml:4, 11`. Editing this file forces every frozen pipeline to replay in full (it is a Python environment file in `ci_frozen.ENVIRONMENT`), about 170 minutes. Fold it into the next planned full replay.

### C6 (Low) Config metadata is behind — apply at the next config adoption
- `config/nowcast-2026.json:4` `decisions` lists D106, D107, D114, D115, D117 and D118 but not D116, D119, D121, D123 or D125. `:80-81` the Māori `decidedBy` text still says "the four unpolled seats" (three since Stage86). Edit at the next `weekly_refresh.adopt` (which bumps `configVersion`), not alone.

### C7 (Low) Stage79 readout ignores the D121 multipliers
- `scripts/seat_polls/readout.py` calls `simulate_with_poll` with the D107 multiplier only, so `readout-2026.json` win probabilities for ordinary seats are not the live model's (within ×0.55 and mass ×0.91 are missing). Internal file, not exported. Fix when the readout is next regenerated (after #117).

---

## Needs James's decision

### J1 (High) Māori seats: D114 says "labelled range", the build shows one number
- **Where:** `config/nowcast-2026.json:80` `maori.presentation: "labelled-range"`; nothing reads it. `scripts/nowcast_assembly/maori.py` simulates only the Stage66 default (C); Stage71's inflation (P) is never run. Spec `§5` and D114 say the probabilities are shown as a C–P range or withheld.
- **Why it matters:** Stage71 found C over-predicts leaders (C 0.88 / 0.78 / 0.85 against P roughly 0.6 to 0.75; Te Tai Tonga about 0.5 to 0.75), and P beat C on every pre-registered score. The site would show C's single number.
- **Options:** **Range** (recommended): seat pages show the C–P range; MMP keeps one law per draw (C) and says so. **C only**: show C and correct D114 and the spec. **P only**: use P for seats and MMP.

### J2 (Medium) Pin the electorate-poll run in the config
- **Where:** `scripts/seat_polls/live.py:32` and `scripts/maori_seat_layer/live.py:27` read the *newest* `data/processed/polling/electorate-live/` run, not one named in the config; the bank's `inputs` (`assemble.py:107-109`) do not record which run. General-seat polls are cut at `national.dataCutoff`; Māori polls are not.
- **Why it matters:** merging a refresh PR changes the forecast and makes the development gate stale before anyone adopts it, so the gate cannot sit in CI (C2), and a published snapshot cannot say which poll file it used.
- **Options:** **Pin** (recommended): `seatPolls.electorateRun` (date and hash) set by `weekly_refresh.adopt` together with the national fit, recorded in the bank inputs, with the same cutoff for both seat types. **Leave**: keep reading the newest run.

### J3 (Medium, electoral rule) A Te Tai Tokerau Party win is counted as an independent
- **Where:** `src/models/mmp/seatLayer.ts:170-173` counts any winner whose party is not a listed national group as an s 191(8) independent (seat inside the 120). `docs/stage65-seat-layer-design.md:49` records the same.
- **Evidence:** Te Tai Tokerau Party is on the 2026 party list (`data/processed/nominations-2026/2026-10-10/party-lists.json`), so under the Act it qualifies by its electorate win and its seat is overhang unless its party vote earns a Sainte-Laguë seat (about 0.4%). Its vote sits inside "Other" (about 1.6% in total), so zero entitlement is far more likely. Kapa-Kingi wins in 13.2% of draws (8,192 Māori draws, fallback arm F). The current rule is equivalent to assuming the party earns exactly one list-entitled seat: the other parties share 119 seats instead of 120, and Parliament is 120 instead of 121, in those draws. An independent win in Te Tai Tonga (1.7% of draws) is correctly s 191(8).
- **Options:** **Overhang** (recommended): count a listed party inside Other as qualified with zero party votes, so its seat is overhang. **Keep**: document the current rule as an approximation.

### J4 (Info, timing) The open refresh PR #114 blocks Monday's scheduled refresh
- `.github/workflows/poll-refresh.yml` refuses to run while any `routine/poll-refresh-*` PR is open. #114 (2026-10-10) is green and open; the next scheduled run is Sunday 11:00 UTC (Monday 00:00 NZDT). Merge or close #114 before then. Adopting it into the config is a separate step that regenerates the development gate (and the rehearsal report).

---

## Optimisations and other notes (no action proposed now)

- **CI headroom (High, already planned):** a full replay of all frozen pipelines takes 169.5 of the `python` job's 180 minutes (run 38025763723: Stage46 construction 27 min, Stage47 construction 34 min plus attribution 9 min, Stage48 evaluation 18 min, Stage54 evaluation 41 min, Stage63 about 13 min, unit tests 8 min). Any change that legitimately replays everything (an environment file, a shared helper) risks the cap. The parked parallel-replay work covers manual dispatch; it should also split the ordinary `python` job's full mode, keeping each job well under 180 minutes. C1 removes the avoidable trigger.
- **Synthetic fixture forces a Stage63 replay:** any edit to `data/fixtures/synthetic/nowcast-draw-bank.json` (#108, #116 and Stage83 all change it) hits the "existing data file changed" rule and replays Stage63 (about 13 minutes), although no frozen pipeline reads it. Exempting `data/fixtures/synthetic/` would loosen a fail-closed rule, so it is James's call; low value.
- **Fork with threads:** `run_seats` forks a pool after NumPy has started BLAS threads (Python warns "multi-threaded, use of fork() may lead to deadlocks"). It has not hung in any run; worth knowing if a production run ever stalls.
- **Release gate is all-or-nothing on precision:** any probability above MCSE 0.01 refuses the whole release, where the policy says such a quantity is withheld. Stage77's rehearsal maximum was 0.0051, so it is unlikely to bite.
- **`ci.yml:26-32`:** the `check:dist` step still guards for a script that now exists. Harmless.
- **Stage36/38 inference tests** never run in CI (no jax/polars there); by design.

---

## Live-chain check results (main `59edb70`, local, pinned packages)

| Command | Result | Time | In the new `live` job |
|---|---|---|---|
| `python3 -m scripts.nowcast_config.validate --require-complete` | pass | 1s | yes |
| `python3 -m scripts.nowcast_config.scales --check` | pass | 0s | yes |
| `python3 -m scripts.polling.weekly_refresh.adopt --date 2026-10-07 --check` | pass | 0s | no |
| `python3 -m scripts.polling.weekly_refresh.run --check` | pass | 1s | yes |
| `python3 -m scripts.polling.weekly_refresh.electorate_polls --check` | pass | 0s | yes |
| `python3 -m scripts.polling.electorate_refresh.run --check` | pass | 0s | yes |
| `python3 -m scripts.nominations_2026.refresh --acquisition data/processed/nominations-2026/2026-10-10/acquisition.json --check` | pass | 3s | yes |
| `python3 -m scripts.voting_place_notionals.run --check` | pass | 65s | yes |
| `python3 -m scripts.electorate_baseline.build --check` | pass | 0s | yes |
| `python3 -m scripts.exceptional_scale.run --check` | pass | 143s | yes |
| `python3 -m scripts.maori_seat_layer.run --check` | pass | 3s | yes |
| `python3 -m scripts.maori_seat_layer.results --check` | pass | 0s | yes |
| `python3 -m scripts.maori_seat_calibration.run --check` | pass | 14s | yes |
| `python3 -m scripts.maori_seat_fallback.run --check` | pass | 19s | yes |
| `python3 -m scripts.shared_split_swing.run --check` | pass | 1s | yes |
| `python3 -m scripts.party_vote_elasticity.run --check` | pass | 2s | yes |
| `python3 -m scripts.party_vote_elasticity.run --stage findings --check` | pass | 2s | yes |
| `python3 -m scripts.seat_polls.run --check` | pass | 2s | yes |
| `python3 -m scripts.seat_polls.readout --draws 2048 --check` | pass | 450s | no |
| `python3 -m scripts.ordinary_minor_spread.inputs --check` | pass | 0s | yes |
| `python3 -m scripts.ordinary_minor_spread.fit --check` | pass | 1s | yes |
| `python3 -m scripts.ordinary_minor_spread.decision --check` | pass | 1s | yes |
| `python3 -m scripts.exceptional_balance_scale.inputs --check` | pass | 0s | yes |
| `python3 -m scripts.exceptional_balance_scale.fit --check` | pass | 16s | yes |
| `python3 -m scripts.exceptional_balance_scale.decision --check` | pass | 0s | yes |
| `python3 -m scripts.manual_adjustment.run build-template --check` | pass | 0s | yes |
| `python3 -m scripts.nowcast_assembly.fixture --check` | pass | 12s | no |
| `python3 -m scripts.nowcast_assembly.run --check` | pass | 12s | no |
| `python3 -m scripts.candidate_fit_2026.run --check` | pass | 298s | yes |

All 29 pass on main. On #117's head `a26aedf`, `scripts.nowcast_assembly.fixture --check` fails ("Stale data/fixtures/synthetic/nowcast-draw-bank.json"): the stream change moves the fixture and #117 does not regenerate it (reported to the coordinator). The elasticity and Stage79 checks still pass there.
