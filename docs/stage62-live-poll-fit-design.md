# Stage62 — live 2026 national poll fit: frozen design

Frozen 2026-10-06, before any 2026 fit. Authorised by James (project thread, 2026-10-06); decision number D094. This is the one-question stage "what is the current national party-vote distribution as of the latest 2026 poll, under the project's existing pinned national model?" It is a new current-cycle estimate, not a reopening of any historical backtest (the roadmap's do-not-reopen list forbids historical national MCMC reruns, and this stage does not do them; its one environment check is described in section 9).

Outputs are **internal only**. Nothing is published, exported, put on the website or fed into the local-party, candidate, Māori or MMP layers. No seat or winner probability is produced (the probability-release policy is still open). Māori electorates are out of scope (modelled completely separately).

## 1. Model: the pinned external `gauss` variant, unchanged

The model is the Stage38 external comparison model, byte-pinned upstream commit `ef76cf6562e1d028b4fff46d063f4b93945299de` (archive `data/raw/polling/stage38/upstream.tar.gz`, SHA-256 `a949954d…db9`), variant `gauss` of `config/model.yml`: Gaussian observations (variance `deff·p(1-p)/n` plus rounding variance), `house: cycle` (persistent per-pollster-segment bias plus per-term deviation), `industry_error: true` (shared polling error moving linearly within a term, fresh Student-t(4) draw for the forecast term's election-day value), `campaign_kappa: true` (innovation multiplier in the last eight weeks), weekly random walk with LKJ(2) correlated innovations, state pinned to official results at 2011 (anchor) and each completed election by a Brownian bridge. All priors, `minor_party_factor` 2.5 / `minor_party_share` 8%, `auto_track`, pollster map, exclusions, `polling_code_only: false`, `min_polls: 2` and the config files are used exactly as pinned (SHA-256 of each `config/*.yml` is recorded in the input contract). No prior, equation, pollster mapping or threshold is changed for the primary fit. Provenance of the settings: Stage38 (D-record in `docs/stage38-execution-contract.md`); this is the model the roadmap calls "external gauss, provisional", the source of the cached national draws Stage39 already consumes.

The in-house Stage36 national model is not refitted (it needs a new current-cycle adapter, i.e. new code, and its published backtest evidence is 14- and 56-day only). It remains the development control; a 2026 fit of it is a separately authorised task.

## 2. Poll input

Primary input is unchanged pinned upstream parsing of the preserved Wikipedia tables:

- cycles 2014–2023: `data/raw/polling/stage38/{2014,2017,2020,2023}.html` (retrieved 2026-10-04; SHA-256 recorded);
- cycle 2026: `data/raw/polling/current-2026-primary/wikipedia-opinion-polling-2026.html`, the Wikipedia REST HTML (revision 1378752122, retrieved 2026-10-06T01:09Z, SHA-256 `b7d8a710…c689`), parsed by the pinned `parse_page_file`, `build_polls_table`, `build_dataset` (layout-agnostic; the 2026 page parses with no change to code).

Earlier results anchoring the latent state come only from the pinned reference CSV and the result rows of those pages (2011, 2014, 2017, 2020, 2023); the pinned `verify_results` audit must report no issue. No 2026 result exists or is used.

**Cutoff and information set.** `cutoff = 2026-10-06`, `lagged = False`: every poll on the page has already been published (the upstream config says the live forecast ignores publication lags), so a poll counts once its fieldwork has ended. The latest poll is RNZ–Reid Research (fieldwork 24 Sep–1 Oct 2026, published 6 Oct 06:27 NZDT). This is a poll-information set as of 6 October, not a verified-timestamp as-of reconstruction. Election day 2026-11-07, so the horizon is 32 days; the weekly target is the Sunday week of 2026-11-01 (the same weekly approximation as Stage38; no daily extrapolation).

**Reconciliation with the Stage59 panel (PR #68, `data/processed/polling/panel-update-2026-10/panel.json`).** The gauss pipeline cannot read the Stage35-format panel, so the panel is used as the independent check and the evidence-grade register of the same polls. Pre-registered check: every 2026-cycle wave in `panel.json` has a matching row in the parsed Wikipedia table (key: fieldwork end date plus rounded NAT/LAB/GRN/ACT/NZF shares) and vice versa, and counts are reported. Exploration before freezing (inputs only, no fit) found the key sets identical: 122 panel waves and 122 parsed rows, which the pinned de-duplication (same pollster, midpoint and party) collapses to 120 table polls. Any mismatch found when the check is rerun is reported and not repaired by editing the poll table.

**Evidence grade.** Panel waves carry `evidenceGrade` only where Stage59 changed them; the only `aggregator_only` wave is Talbot Mills 1–10 May 2024 (NAT 35, LAB 32). Stage52 verified fieldwork, sample sizes and shares for every poll since 1 June 2026 against preserved primary pages. Arm E (below) removes the one `aggregator_only` row.

**Pinned-config consequences, stated rather than repaired.** The pinned config drops pollsters with fewer than two eligible polls: the single Anacta poll (4–10 Sep 2026, n 1701; Anacta is the rebranded Talbot Mills per Stage52) is excluded from the primary fit, so the dataset holds 119 2026-cycle polls and 496 in all (exploration, no fit). Arm T tests the effect of treating Anacta as Talbot Mills. Talbot Mills rows with no reported sample size use the pinned default 1000. Publication lag and the Reid Research method segment are as pinned.

## 3. House effects and drift

Pinned structure (section 1): per pollster-segment persistent bias `house_base` (Normal(0, 0.12) on the logit scale per party), per pollster-term deviation `house_cycle` (sd HalfNormal(0.05)), shared industry error, per-pollster design effect. Older cycles inform `house_base` and the industry-error scales, which is why they are retained in every arm except where stated. Reported house effects are posterior summaries, in percentage points, of the poll-share shift of each 2026-cycle pollster relative to the equal-weight mean across the pollsters active in 2026, at the last-data state: `100·[softmax(θ_last + δ_j) − softmax(θ_last + mean_j δ_j)]` with `δ_j` the pollster's `house_base + house_cycle` offset (industry error excluded). Drift: weekly random-walk innovations with pinned `sigma_scale` 0.06, `lkj_eta` 2, campaign `kappa_sd` 0.3, `campaign_weeks` 8.

## 4. Inference settings and convergence gates (Stage38 PRIMARY, unchanged)

Four CPU chains, x64, 2000 warmup + 2000 samples per chain, `target_accept` 0.95, `max_tree_depth` 12, diagonal mass, `init_to_median(20)`, seed 2034 (the Stage38 seed, used for every arm). Acceptance, every mathematically non-fixed stochastic or derived coordinate: rank R-hat ≤ 1.01, bulk and tail ESS ≥ 400, all finite, 0 divergences, 0 tree-depth contacts, per-chain BFMI ≥ 0.3. Fixed coordinates (triangular `L_corr`, exact anchor `theta`/`pi`) are excluded exactly as in Stage38 (the diagnostic function is imported unchanged). One numerical retry per failed attempt: same data and seed, 4000 warmup, `target_accept` 0.99, `max_tree_depth` 15; the original failure is preserved. No other retries, bound, prior or data changes. A fit that fails both attempts is reported as failed and its draws are not scored or compared.

## 5. Arms (pre-registered)

| Arm | Change from the primary fit | Purpose |
|---|---|---|
| **A** (primary) | none | the reported estimate |
| A2 | seed 2035 | Monte Carlo noise floor for every comparison |
| B1 | drop 2026-cycle polls with fieldwork end before 2026-06-01 (earlier cycles kept) | James's "use only recent polls": about 18 weeks, the span Stage52 verified against primary pages |
| B2 | drop 2026-cycle polls with fieldwork end before 2026-08-11 (8 weeks, earlier cycles kept) | a harder recent window |
| E | drop the `aggregator_only` Talbot Mills May 2024 row | evidence-grade filter |
| T | relabel the Anacta poll as Talbot Mills | pinned-config consequence of section 2 |

Windows are applied to the polars table before the pinned `build_dataset`; windowed polls are neither renamed nor reweighted. Earlier cycles are kept in B1/B2 because, in this model, they are where persistent house bias and the industry-error scales are learned, and removing them would be a different model. A "history-truncated" variant (a later `anchor_election`) is not run.

## 6. Outputs (internal)

Per arm, saved before any summary: joint draws of election-week support and last-data-week support (8,000 × 8 each, with chain IDs), the house-effect and polling-error hyperparameter draws needed to reproduce the summaries, all diagnostic statistics, and exact input, config, code and environment signatures. Summaries (`summary.json`): for NAT, LAB, GRN, ACT, NZF, TPM, TOP and Other at the last-data week and at election week, mean, sd and 5/25/50/75/95% quantiles in percentage points; National minus Labour margin; weekly path mean and 90% band; house effects (section 3); sampler and polling-error hyperparameters; convergence record. No seat, bloc, government or winner probability; the draws are internal and are not wired into any other layer or the site.

## 7. How much arms move (descriptive, no adoption rule)

For each arm against A, per category and at both states: difference of means in pp and in units of A's sd; ratio of sds; ratio of 90% interval widths; the same for National minus Labour; and the A versus A2 difference as the Monte Carlo floor. A difference is flagged as material only if at election week or last-data week |Δ mean| ≥ 1.0 pp for NAT or LAB, or the NAT or LAB 90% width ratio falls outside [0.80, 1.25]. These thresholds are descriptive (about the rounding granularity of the polls and about half an election-week posterior sd) and are not tuned. Primary A is reported whatever the arms show; because no historical backtest of windowed live fits exists and historical national reruns are not reopened, a window is not adopted on these results, and the comparison only says how much the estimate and its uncertainty depend on older polls. Also reported, descriptively and not gated: A's last-data mean against the plain mean of the five most recent polls.

## 8. Environment

Isolated `.venv-external` built from `requirements-external.lock` (every pin satisfied, no substitution), Python 3.12.3, Linux x86-64, four CPU devices, x64. Stage38 ran on macOS 15.6 arm64 with Python 3.12.2. NUTS results will not bit-match the earlier Mac archives; they are compared statistically (section 9). The Stage38 runtime guard requires an exact platform match, so it is not reused; the new runner records its own `environment.json` and refuses to run if the installed packages differ from the lock. Stage38 code and outputs are untouched.

## 9. Environment check (not scoring, not a historical rerun)

To show the x86 environment reproduces the model, the Stage38 2017 dataset (`data/processed/polling/external-comparison/datasets/2017`) is refitted once under the Stage38 PRIMARY settings and compared with the committed Stage38 summary. Criterion fixed now: every category's election-week mean within 0.30 pp and sd ratio within [0.85, 1.15] of the committed fit (the Monte Carlo error of the posterior mean is about 0.1 pp). The refit is stored only under the Stage62 directory; no Stage38 file changes and no score or comparison with outcomes is made. If it fails, the cause is investigated before any 2026 number is used.

## 10. Checks

`python3 -m scripts.polling.live_fit.run --check` (committed-artifact checks: input and output hashes, draw simplexes and weights, gates, summaries recomputed from the saved draws, the absence of probability or seat fields) is numpy-only and runs inside an always-run unit test; the optional full check rebuilds the datasets in `.venv-external` and verifies their fingerprints. MCMC is never rerun in CI. Local verification also covers the panel reconciliation, a fold-fragment check and the Stage38/Stage59 frozen-hash preservation.

## 11. Not done (explicit)

No historical backtest, no model change, no new prior or threshold, no spread or horizon calibration (the roadmap records that the 56-day Stage46/47 scales are probably conservative for a 32-day forecast; this fit is a poll-model distribution, with nothing claimed about its calibration at this horizon), no ensemble, no `fund` variant, no publication, export or website use, no probability, no candidate, local-party, Māori-seat or MMP use, no edit to `data/sources.json`, Stage35 `polls.json`, Stage36–48 outputs or the Stage59 panel, no merge. Limits recorded in advance: three completed cycles of poll history from a Wikipedia table (an aggregator transcription, verified only since June 2026 for fieldwork and sample size); inferred sample sizes for Talbot Mills; the 2026 Anacta poll excluded by the pinned rule; Wikipedia polls fieldwork dates, not publication times; election-week support is latent support including the common polling-error draw, not an outcome forecast with any calibration claim.
