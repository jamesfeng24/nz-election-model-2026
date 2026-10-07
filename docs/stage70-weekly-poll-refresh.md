# Stage70 — weekly national poll refresh and routine

Authorised by James (project thread, 2026-10-06); decision number D104. Internal only: the refresh updates the national party-vote input of Stage62 and nothing else. Since D106 the product is a nowcast, so the refresh produces the **latest-state input** described in `docs/nowcast-specification.md` section 2: joint draws of `lastDataSupport` (the latent national state at the latest poll week, which already integrates house effects and the industry polling error), labelled by model-state date. Election-week draws (`electionDay`, pure future drift) are not saved or summarised, and no extra polling-error draw is added. It changes no model, prior, pollster map or downstream layer, publishes nothing, produces no probability, seat or bloc output, and never merges or pushes to `main` (a routine opens a pull request; the coordinator reviews it).

## What one refresh does

Command (needs `.venv-external` built from `requirements-external.lock`, Python 3.12, four CPU devices, network to Wikipedia; about 15 to 35 minutes, almost all of it the NUTS fit):

```
python3.12 -m venv .venv-external && .venv-external/bin/pip install -r requirements-external.lock
.venv-external/bin/python -m scripts.polling.weekly_refresh.run            # date = today in Pacific/Auckland; also the poll cutoff
.venv-external/bin/python -m scripts.polling.weekly_refresh.run --date 2026-10-14 --use-existing-capture   # offline rebuild of a preserved capture
python3 -m scripts.polling.weekly_refresh.run --check                      # stdlib + numpy: verify every committed run
.venv-external/bin/python -m scripts.polling.weekly_refresh.run --rebuild-check   # re-derive panel and dataset from the raw captures
```

1. **Capture.** The pinned source is the Wikipedia REST HTML of *Opinion polling for the 2026 New Zealand general election* (the Stage52 capture and the Stage62 primary input). It is fetched with curl and an honest User-Agent (retrying HTTP 429 with backoff) into `data/raw/polling/weekly-refresh/<date>/`: the table, the response headers and the fetch log. An existing raw or processed directory is never overwritten.
2. **New rows.** Rows are read with the Stage35 table adapter (as in Stage59, blank sample cells kept) and matched to the previous panel by wave id (pollster code plus fieldwork dates). The previous panel is the Stage59 panel for the first run and the previous run's `panel.json` afterwards. The April 2026 Talbot Mills pair that Stage59 collapsed is carried as known.
3. **Rules** (`scripts/polling/weekly_refresh/delta.py`):
   - *Blockers, the run refuses to publish:* a row that cannot be mapped (new pollster name, unreadable date); an already-published wave whose content changed on Wikipedia (revision); a panel wave that disappeared; fieldwork ending after the run date; published lower bounds summing above 100%; a party share outside 0–70%; and, after the panel is built, any difference between the panel's 2026 waves and the rows the pinned upstream parser reads (fieldwork end plus rounded NAT/LAB/GRN/ACT/NZF shares).
   - *Review flags, published but a human must look:* a pollster new to the cycle; odd fieldwork dates (span above 1.25 times that pollster's longest earlier span and above 14 days, a single date, an unknown day); a missing core party share (missing, not zero); shares plus Others outside 97–103%; and a last-data NAT or LAB mean that moved 1 pp or more against the previous published estimate (the Stage62 materiality threshold).
   - *Info:* blank sample cell (pinned default 1000 applies downstream), a late addition, a sponsored release (excluded by the pinned config), and, for every new row, primary-release verification pending. New rows enter the panel with `evidenceGrade: aggregator_only` and a note; nothing was verified against a primary page by the routine.
4. **Dated panel and registry.** `panel.json` is the previous panel plus the new waves (never an edit of an earlier version), with the base hash; `changes.json`, `review.json`, `source-registry.json` (the schema of the Stage40 and Stage52 registries; `data/sources.json` is frozen and untouched) and `input-contract.json` (every input hash, the numerical modules' hashes).
5. **Dataset and fit.** The dataset is built by the unchanged pinned upstream code exactly as Stage62 arm A (all four earlier cycles, the new capture, results only for completed elections, a counterfactual-result and post-cutoff check), cutoff = run date, `lagged=False`. The fit is the Stage62 inference reused unchanged (`scripts/polling/live_fit/inference.py` helpers, the Stage62 runtime guard that refuses on any package or frozen-code difference): pinned `gauss` model, Stage38 PRIMARY settings, seed 2034, full-coordinate diagnostics. Gates: rank R-hat ≤ 1.01, bulk and tail ESS ≥ 400, 0 divergences, 0 tree-depth contacts, BFMI ≥ 0.3. One numerical retry with the frozen RETRY settings; a second failure writes `blocked.json` (exit 3) and no estimate.
6. **Estimate and nowcast input.** `fit/attempt1.npz` holds `lastDataSupport` (4 chains × 2000 draws × 8 categories), the house offsets, hyperparameters and the weekly path up to the last-data week only; `fit/attempt1.json` is its record in the format `scripts/nowcast_assembly/national.py` already reads (status `accepted`, `signature.cutoff`, `npzSha256`, `parties`, `drawIds`). `estimate.json` has `targetType: nowcast`, `modelStateAsOf` (the Sunday week of the latest poll midpoint) and `dataCutoff` (the run date), the label "latent state as of the week of …, polls to …", a `nowcastInput` block with the values the configuration takes on adoption, and the same summaries as the Stage62 arm A for the last-data state only (means, sd, quantiles, NAT−LAB margin, house effects, path, convergence), the change against the previous published estimate (noise floor about 0.1 pp), the new polls, and every flag. No probability, seat, winner, bloc or government field exists (scanned). `manifest.json` hashes every file of the run; `index.json` lists published runs.
7. **Fragment.** One `handoff.d/<date>-poll-refresh.md` changelog entry; the shared documents are never edited.

**Adoption is separate.** The routine never edits `config/nowcast-2026.json`. After review, `python3 -m scripts.polling.weekly_refresh.adopt --date <date>` points `national.source`, `modelStateAsOf` and `dataCutoff` at that run, bumps `configVersion` and validates with `scripts.nowcast_config.validate` (`--check` verifies the config already carries a run's values). It is not run in this PR: setting `dataCutoff` to 2026-10-07 or later would make `scripts/tests/test_stage72_nowcast_config.py` (which mutates `modelStateAsOf` to the literal `2026-10-07` and expects a failure) pass its negative case wrongly, so that test needs a date change in the same adopting change.

If the table is unchanged (no new row, no blocker) the run removes its capture directory, prints `NO_NEW_POLLS`, exits 0 and leaves nothing to commit. Exit codes: 0 published or no new polls; 2 blocked by the new-row rules or reconciliation; 3 fit gates failed. The run refuses any date from election day (7 Nov 2026) on: the model's forecast target is the week of 1 November.

## Routine runbook (what the weekly session does)

Fires **Thursdays 06:55 Pacific/Auckland** (after the Monday–Wednesday releases of 1News–Verian, RNZ–Reid Research, Roy Morgan and Curia are on Wikipedia; the NZ morning leaves the coordinator the day to review). Routine `trig_01LB91p9NumjAUQjJB6QKdVs` ("Weekly NZ poll refresh", cron `CRON_TZ=Pacific/Auckland 55 6 * * 4`). The project is private, so the platform does not allow a fresh session per firing: the routine wakes this Stage70 thread's own session each week, with a prompt that assumes a possibly fresh container and starts from the repository. Before the Stage70 pull request is merged it replies that it is waiting and does nothing. Steps:

1. Branch `routine/poll-refresh-<NZ date>` from the latest `main`. Read AGENTS.md and this document.
2. Build `.venv-external`, run the command above, and read the log.
3. Exit 0 with `NO_NEW_POLLS`: stop; no pull request.
4. Exit 0 published: run `--check`, `python3 -m unittest scripts.tests.test_weekly_refresh`, `python3 -m scripts.fold_doc_fragments --check`; commit the run directories, raw capture, `index.json` and the fragment; push the branch; open one pull request `Polls: weekly national poll refresh <date>` with the repository's PR body sections, listing the new polls, the headline estimate and change, every review flag, and the gate results. Do not merge. Do not push to `main`.
5. Exit 2 or 3: commit the raw capture and the run directory's `blocked.json` and `review.json`, open a pull request `Polls: weekly refresh <date> blocked (<reason>)` naming each blocker, and stop. A human decides (extend the adapter, accept a revised row, rerun).
6. Never edit an earlier run, `data/sources.json`, Stage59 or Stage62 files, or the shared handoff documents; never rerun other stages.

After 5 November the routine's runs are refused by the election-day guard; disable the routine then.

## Limits

Aggregator input: Wikipedia transcribes poll tables, and the routine does not verify new rows against primary releases (Stage52-style verification is manual and is listed per new row). A Wikipedia edit to an old row blocks the run until a human decides, by design. Talbot Mills sample sizes use the pinned default 1000; Anacta is excluded by the pinned minimum-polls rule. The fit is the Stage62 poll-model distribution with no horizon or spread calibration and no probability. The weekly cadence cannot see a poll before Wikipedia lists it.

## Part C — electorate polls in general seats (one bounded search, 2026-10-07)

Preserved under `data/raw/polling/electorate-polls-2026/`, registered and transcribed in `data/processed/polling/electorate-polls-2026/` (`source-registry.json`, `polls.json`; `python3 -m scripts.polling.weekly_refresh.electorate_polls --check` re-verifies the bytes and each transcribed phrase). Listed only, not modelled:

| Seat | Pollster / commissioner | Sample, fieldwork | Candidate vote |
|---|---|---|---|
| Wellington Bays | Curia for the Taxpayers' Union (via Newsroom, 16 Sep) | 400; fieldwork not stated | Renney (LAB) 29, Genter (GRN) 29, Muthu (NAT) 15, McKee (ACT) 5, Warner (NZF) 5, Kingdon-Bebb (TOP) 3; party vote GRN 31, LAB 29, NAT 13 |
| Mt Albert | Curia for The Spinoff (The Spinoff 30 Sep, NZ Herald, Newsroom context) | 400; 21–28 Sep; margin of error 4.9 | White (LAB) 33, Lee (NAT) 32, Menéndez March (GRN) 14, Wong (TOP) 10, Eden-Whaitiri (NZF) 5, Price (ACT) 3; party vote NAT 32, LAB 32, GRN 19, TOP 6, NZF 6, ACT 3 |

Limits: both are press reports of commissioned polls with no primary Curia tables preserved (the Taxpayers' Union page returned HTTP 403); Wellington Bays is a new electorate with no result on its boundaries and Newsroom itself cautions the result ("a pinch of salt"); fieldwork dates are not published for it. The search found no Freshwater, Talbot Mills or Horizon electorate polls and no electorate table on the Wikipedia opinion-polling page; Q+A was not searched by name. Māori-seat polls (Te Tai Hauāuru, Te Tai Tonga and others, Curia for Whakaata Māori) belong to the Stage71 layer and are already preserved under `data/raw/polling/current-2026-primary/`.
