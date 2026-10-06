# Stage62 — live 2026 national poll fit: findings (internal)

Design: [stage62-live-poll-fit-design.md](stage62-live-poll-fit-design.md), frozen before any 2026 fit (decision D094). Outputs are internal: no probability, seat or bloc quantity exists in them, nothing is published or fed to another layer. Code `scripts/polling/live_fit/`, outputs `data/processed/polling/live-fit-2026-10/`.

## Result

The pinned external `gauss` model (Stage38, unchanged) fitted to every 2026-cycle poll on the Wikipedia table as of 6 October 2026 (119 polls, 496 in all with the three earlier cycles). All seven fits pass the Stage38 gates on the first attempt (below). Latent party support, percentage points, 8,000 joint draws:

| Party | Last-data mean | sd | 90% | Election-week mean | sd | 90% |
|---|---:|---:|---|---:|---:|---|
| NAT | 27.5 | 1.98 | 24.5 to 30.8 | 27.2 | 3.06 | 22.4 to 32.4 |
| LAB | 28.9 | 2.16 | 25.4 to 32.3 | 28.7 | 4.32 | 21.9 to 35.9 |
| GRN | 13.1 | 1.21 | 11.3 to 15.2 | 13.1 | 2.00 | 10.0 to 16.5 |
| ACT | 9.9 | 1.17 | 8.1 to 11.9 | 10.0 | 2.42 | 6.4 to 14.3 |
| NZF | 10.7 | 1.22 | 8.8 to 12.7 | 10.8 | 2.34 | 7.3 to 14.8 |
| TPM | 1.9 | 0.42 | 1.3 to 2.6 | 1.9 | 0.60 | 1.1 to 3.0 |
| TOP | 6.1 | 1.21 | 4.3 to 8.2 | 6.3 | 2.52 | 3.1 to 11.1 |
| OTH | 1.9 | 0.45 | 1.3 to 2.8 | 2.1 | 0.99 | 0.9 to 3.9 |

"Last data" is the week of 27 September (latest poll midpoint), latent support with no polling error. "Election week" is the Sunday week of 1 November and adds the model's common polling-error draw for the forecast term (Student-t(4) scale learned from 2014–2023), so it is wider. National minus Labour: mean -1.4 pp at the last-data week (sd 3.5, 90% -6.9 to +4.5) and -1.6 pp at election week (sd 6.0, 90% -11.4 to +8.0). Labour narrowly leads National on these draws, but the interval comfortably contains zero. The plain mean of the five latest polls (Reid 14–21 Aug, Curia 1–3 Sep, Freshwater 4–11 Sep, Verian 23–27 Sep, Reid 24 Sep–1 Oct) is NAT 27.8, LAB 29.0, GRN 13.8, ACT 9.4, NZF 10.6, TOP 5.5, TPM 2.0; the model is within 0.65 pp of it on every party (descriptive, not a gate).

## House effects (poll-share shift in pp against the equal-weight pollster mean at the last-data state; posterior sd in brackets)

| Pollster | NAT | LAB | GRN | ACT | NZF | TPM | TOP |
|---|---:|---:|---:|---:|---:|---:|---:|
| Curia | +0.5 (0.4) | -0.4 (0.4) | -0.8 (0.3) | +0.5 (0.3) | -0.1 (0.3) | +0.1 (0.1) | -0.9 (0.3) |
| Freshwater Strategy | -0.9 (0.5) | +1.4 (0.6) | -0.4 (0.5) | -0.4 (0.4) | +0.5 (0.4) | -0.3 (0.1) | +0.0 (0.5) |
| Reid Research | -0.1 (0.5) | +1.5 (0.5) | -0.4 (0.4) | -0.7 (0.4) | +0.2 (0.4) | +0.2 (0.1) | -0.4 (0.4) |
| Roy Morgan | -1.5 (0.3) | -4.2 (0.4) | +2.1 (0.4) | +1.4 (0.3) | -0.5 (0.2) | +0.2 (0.1) | +2.6 (0.6) |
| Talbot Mills | -0.1 (0.3) | +1.6 (0.4) | -0.7 (0.3) | -0.5 (0.3) | +0.6 (0.3) | +0.0 (0.1) | -0.4 (0.3) |
| Verian | +1.6 (0.4) | -0.1 (0.4) | +0.2 (0.3) | -0.4 (0.3) | -1.0 (0.3) | -0.2 (0.1) | -0.4 (0.3) |

Roy Morgan reads Labour about 4 pp below the pollster mean and Greens, ACT and TOP above it; this is the largest effect and it matters for the Labour estimate because Roy Morgan and Curia supply 68 of the 119 current-cycle polls. House effects are relative to the pollster mean, not to the truth: the model cannot say which pollsters are right, only how they differ and, through the shared industry error, how far the whole industry could be off.

## Sensitivity arms (shift against A, pp; last-data / election-week)

| Arm | Polls 2026 | NAT | LAB | GRN | ACT | NZF | TOP | NAT-LAB margin | NAT, LAB 90% width ratio (last / election) |
|---|---:|---|---|---|---|---|---|---|---|
| A2 (seed 2035) | 119 | -0.07 / -0.08 | +0.02 / +0.02 | +0.02 / +0.02 | +0.01 / +0.06 | +0.01 / -0.06 | +0.02 / +0.06 | -0.09 / -0.10 | 1.00, 1.01 / 1.00, 1.03 |
| B1 (from 1 Jun) | 18 | +0.62 / +0.63 | -0.72 / -0.71 | +0.24 / +0.25 | -0.07 / -0.03 | -0.01 / -0.02 | -0.10 / -0.11 | +1.34 / +1.33 | 1.07, 1.04 / 1.07, 1.04 |
| B2 (from 11 Aug) | 8 | +0.17 / +0.20 | -0.58 / -0.59 | +0.23 / +0.24 | +0.07 / +0.13 | +0.06 / +0.06 | +0.05 / +0.03 | +0.76 / +0.78 | 1.09, 1.06 / 1.08, 1.05 |
| E (drop 2 aggregator_only) | 117 | -0.02 / -0.02 | +0.01 / +0.01 | +0.05 / +0.05 | -0.02 / -0.01 | -0.02 / -0.02 | +0.01 / +0.01 | -0.03 / -0.03 | 1.01, 1.00 / 1.01, 1.02 |
| T (Anacta as Talbot Mills) | 120 | +0.12 / +0.09 | +0.11 / +0.15 | -0.01 / -0.03 | -0.03 / -0.01 | -0.15 / -0.16 | +0.09 / +0.10 | +0.00 / -0.07 | 0.97, 0.99 / 0.99, 1.01 |

- **Monte Carlo floor (A2):** every party mean moves at most 0.08 pp and every sd ratio is within 5%, so differences below about 0.1 pp are noise.
- **Recent polls only (James's idea; B1, B2):** the party estimates move less than 1 pp, and no arm trips the frozen material flag (|Δ| ≥ 1.0 pp for NAT or LAB, or a NAT/LAB 90% width ratio outside 0.80–1.25). The direction is consistent: National up (+0.6 pp for B1, +0.2 pp for B2), Labour down (about -0.7 and -0.6 pp), so the National-minus-Labour margin moves toward National by +1.3 pp (B1) and +0.8 pp (B2). That margin shift is about a third of its posterior sd (3.5) and falls outside the frozen flag, which is defined on party means only; it is reported here rather than dismissed. Intervals widen 4–9%. The mechanism is visible in the house effects: with 18 or 8 current-cycle polls the model estimates each pollster's current-cycle deviation from far less data (the Roy Morgan Labour house effect has posterior sd 0.4 pp in A, 0.8 pp in B1 and 1.2 pp in B2, and its mean moves from -4.2 to -5.4 pp in B1), while pollster biases learned in earlier cycles keep the estimate anchored. So the older polls are doing what the design said they would: pinning down house effects, at the price of weighting early-2026 polls that may be stale. This is a sensitivity, not a validation: no backtest of windowed live fits exists and historical national reruns are not reopened, so a window is not adopted, and A remains the estimate.
- **Evidence grade (E):** removing the Talbot Mills May 2024 and April 2026 `aggregator_only` waves changes nothing beyond noise.
- **Anacta (T):** including the single Anacta poll as Talbot Mills moves NZF by -0.15 pp and nothing else beyond noise. The pinned min-two-polls rule is immaterial here.

## Stage59 corrections and the panel

Primary arm A reflects #68 without an overlay: the pinned upstream parser keeps the blank-sample Talbot Mills rows (1–10 Nov 2024 and 1–10 May 2024, default n 1000) that only the Stage35 adapter dropped, and the Wikipedia table lists the April 2026 Talbot Mills poll once. `reconciliation.json` asserts all of this (the build stops otherwise) and finds the 122 parsed 2026-cycle rows identical, key for key, to the 122 panel waves. The pinned config then removes the two Labour-commissioned Talbot Mills rows (30 Apr and 22–28 Nov 2024, sponsored-release rule; the panel keeps them) and the lone Anacta poll (fewer than two polls), leaving 119.

## Numerical reliability and environment

All seven fits are first-attempt acceptances: every non-fixed coordinate (including the weekly states) has rank R-hat ≤ 1.0060, bulk and tail ESS ≥ 740, with zero divergences and zero tree-depth contacts; per-chain BFMI ≥ 0.81 (table below). No retry was needed.

| Fit | Max rank R-hat | Min bulk ESS | Min tail ESS | Divergences | Depth contacts | Min BFMI | Seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| ENV2017 (check) | 1.0050 | 1649 | 1457 | 0 | 0 | 0.87 | 268 |
| A | 1.0036 | 1014 | 1813 | 0 | 0 | 0.83 | 946 |
| A2 | 1.0059 | 861 | 1083 | 0 | 0 | 0.81 | 712 |
| B1 | 1.0044 | 1332 | 2255 | 0 | 0 | 0.84 | 615 |
| B2 | 1.0047 | 1462 | 1848 | 0 | 0 | 0.83 | 606 |
| E | 1.0041 | 899 | 1366 | 0 | 0 | 0.84 | 945 |
| T | 1.0060 | 740 | 1562 | 0 | 0 | 0.86 | 759 |

Environment: `.venv-external` built from `requirements-external.lock` with every pin satisfied, Python 3.12.3, Linux x86-64, four CPU devices, x64; Stage38 ran on macOS 15.6 arm64 with Python 3.12.2. Draws are not bit-identical to Stage38's. Environment check (design section 9): refitting the Stage38 2017 dataset under the Stage38 settings reproduces the committed election-week means within 0.015 pp (criterion 0.30 pp) and sds within [0.96, 1.05] (criterion [0.85, 1.15]), so the platform difference is statistically negligible. Nothing under Stage38 changed. One implementation bug (house-offset extraction for a pollster with a method change inside the 2017 cycle) stopped the first environment-check launch at its save step, after sampling and before any result was read; it was fixed, the stopped launch's record is kept (`batch-launch1-implementation-error.json`), and the fits were rerun from scratch.

## Limits

- Wikipedia is an aggregator transcription; fieldwork and sample sizes are primary-verified only since 1 June 2026 (Stage52). Talbot Mills sample sizes are the pinned default 1000.
- The pinned model is untouched, so its limits carry over: three completed cycles of history, a Student-t(4) industry-error prior that four elections cannot bound, and no spread calibration. At 32 days the 56-day Stage46/47 scale evidence does not apply directly (roadmap: probably conservative for a late forecast, unmeasured). Election-week intervals are the model's own, not calibrated or horizon-checked. The Labour election-week sd (4.3 pp) is dominated by the industry-error draw.
- Last-data support is latent support at the week of 27 September, not an exact nowcast of 6 October. Election-week support is a weekly-resolution quantity (Sunday week of 1 November).
- A is one realisation of the sampler; A2 shows seed noise is about 0.1 pp.
- These draws are not wired into the candidate, local-party, Māori or MMP layers, and no seat or winner probability follows from them.

## Recommendation

Use arm A as the internal national input for the next integration step, with the A2 noise floor and the B arms' direction (National slightly up, Labour slightly down, intervals slightly wider if only recent polls are used) kept in view. A recent window is not adopted: it moves the National-Labour margin by about 1 pp and widens intervals by about 5–10% without any evidence that it is better. If James wants that question settled, the only available test is a separately authorised backtest of windowed fits, which the roadmap currently forbids (historical national reruns). Probability release, calibration at 32 days and use in the candidate layer remain separate decisions.

## Reproduction

`python3.12 -m venv .venv-external && .venv-external/bin/pip install -r requirements-external.lock`; `.venv-external/bin/python -m scripts.polling.live_fit.prepare` (inputs; `--check` rebuilds and compares), `.venv-external/bin/python -m scripts.polling.live_fit.batch` (fits, about 80 minutes on four CPU cores), `python3 -m scripts.polling.live_fit.summarize` and `python3 -m scripts.polling.live_fit.check` (numpy-only; the check also runs inside `scripts/tests/test_live_fit.py`). MCMC is never rerun in CI.
