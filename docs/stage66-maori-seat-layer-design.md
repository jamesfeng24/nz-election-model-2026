# Stage66 design (frozen before any calibration error was computed): Māori electorate seat layer

Decision number D099. Internal only: no publication, no probability release, no change to Stage45 to Stage48 outputs or to any general-electorate calibration. The Māori seats are modelled completely separately from the general electorates (James, 6 October 2026); nothing here is fitted on general-seat data and nothing here feeds general-seat regressions.

**One question.** Can seven Māori electorate polls (three published for 2026 so far) be turned into a per-draw candidate-vote distribution and winner for each polled seat, with the poll error calibrated on the historical Māori electorate polls and official results, and in a form the MMP layer can consume?

## Disclosure about what was known when this was frozen

The 25 historical polls and their official results were collected and read before this document was written. The sign of the 2020 and 2023 outcomes was therefore known (Te Pāti Māori candidates beat their polls in most seats in both elections). The bias question is consequently pre-registered as a tested option with an explicit adoption rule, not as a finding. No calibration error, scale or winner probability had been computed when this file was committed.

## Inputs

1. Current-cycle seat polls: `data/source-plans/maori-seat-layer/polls-2026.json` (Whakaata Māori–Curia, n = 500 each; raw bytes preserved by Stage52). Three seats polled: Te Tai Tonga, Te Tai Hauāuru, Hauraki-Waikato. Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau and Te Tai Tokerau have no published poll.
2. Historical polls: `data/source-plans/maori-seat-layer/historical-polls.json`: 25 polls, 2014 (4 seats, Reid Research for Māori TV), 2017 (7, Reid Research), 2020 (7, Curia for Māori TV), 2023 (7, Curia for Whakaata Māori). Transcribed from the preserved Wikipedia compilation pages; all seven 2023 polls (shares and undecided), the 2020 Waiariki poll and the 2017 Waiariki and Te Tai Hauāuru polls were cross-checked against independent news reports. Sources are registered in the new dated registry `data/processed/maori-seat-layer/source-registry.json` (never `data/sources.json`). Seats and years not listed in the compilations (2014: Hauraki-Waikato, Ikaroa-Rāwhiti, Te Tai Hauāuru) were not searched for beyond this one bounded pass; 2011 and earlier were not searched.
3. Official results: candidate votes for every Māori electorate 2014–2023, read from the preserved Electoral Commission files (`data/processed/maori-seat-layer/historical-results.json`).

## What a poll means (estimand and conversion)

A poll gives the share of respondents choosing each named candidate for electorate MP, with undecided and "other" respondents unallocated. Candidate lists differ across polls and the compilations list leading candidates only, so the quantity compared with the result is closed over the **named candidates**: `q_i = p_i / sum_j p_j` over the candidates listed with a poll share, and the official comparator is the share among the same candidates, `v_i^c = v_i / sum_j v_j`. Undecided respondents are therefore allocated proportionally to the named candidates, and respondents choosing "other" are treated like undecided. This is an assumption; its consequences are part of the calibrated error.

The unnamed remainder `w` (the share of valid candidate votes going to candidates outside the named set) is drawn from its empirical distribution over the 25 historical polls (not a model), and the reported shares are `v_i = (1 - w) v_i^c`. Winners are determined among named candidates; a seat where an unnamed candidate wins is outside the model and is recorded as a limitation. Nominations close on 8 October 2026, so a polled candidate who does not stand, or a late candidate, requires a data-file edit and a rerun.

## Error model

For named candidates `i` in a seat in election `e`, on the log scale:

`log v_i^c = log q_i + 1[group(i) = MP] (b + u_e) + eps_i`, then renormalised (softmax).

- `group` is MP for the Māori Party / Te Pāti Māori only (Mana, Greens, National, independents and all others carry no group term). `eps_i ~ N(0, sigma^2)` independent. `u_e ~ N(0, tau^2)` is one election-level shift shared by every seat in the same election (this is the cross-seat dependence). `b` is a constant bias, default 0.
- Calibration contrast: for each historical poll `D = log(v_MP/v_LAB) - log(q_MP/q_LAB)` (the Māori Party versus Labour log-odds error; all 25 polls have both). Under the model `D = b + u_e + (eps_MP - eps_LAB)`, so `Var(D | e) = 2 sigma^2`.
- `sigma^2` = within-election pooled variance of `D` about the election mean divided by 2, with 25 − 4 = 21 degrees of freedom.
- `tau^2` = max(0, mean over the four elections of `(mean_e(D) - b)^2` minus mean over elections of `2 sigma^2 / n_e`), the method-of-moments estimate on four elections, so it is itself very uncertain.
- **Bias adoption rule (frozen).** `b_hat` is the equal-weight mean of the four election means of `D`. `b = b_hat` is adopted only if (a) leave-one-election-out total log predictive score of the held-out elections' `D` vectors (multivariate normal, covariance `2 sigma^2 I + tau^2 11'`, parameters re-estimated on the other three elections) improves by at least 1.0 nat over `b = 0`, and (b) the election means of `D` have the same sign as `b_hat` in at least three of the four elections. Otherwise `b = 0` and `tau^2` is computed about zero (non-centred), so an unadopted shift is carried as extra shared uncertainty rather than silently removed.
- **Parameter uncertainty** is propagated, not ignored: each Monte Carlo draw uses `sigma^2 = s^2 * 21 / chi2_21` and `tau^2 = t^2 * 4 / chi2_4` (scaled inverse chi-square on the stated degrees of freedom; a zero `tau^2` stays zero). This is parameter uncertainty on a Gaussian model, not a heavy-tailed error model.
- **No separate sampling-error term.** The historical errors already contain sampling error of polls of similar size, house effects, undecided allocation and late movement, so adding n-based sampling error would count it twice. Sample sizes (500 in 2023 and 2026; unrecorded for the others) are not used.
- **Diagnostics, never adopted:** (i) RMS of the contrasts against Labour for non-MP, non-Labour candidates compared with `2 sigma^2` (flag when the ratio exceeds 1.5); (ii) horizon sensitivity: the 2026 polls closed 37 to 44 days before the election, longer than every historical poll except the longest 2014 and 2017 ones (median historical horizon about 10 days); sigma and tau are re-estimated on polls of 21 days or more and winner probabilities reported (winner probabilities that move by more than 0.10 are flagged for James, not substituted); (iii) leave-one-election-out backtest of the model's probability that the poll leader wins against the realised outcome.

## Several polls for one seat

Calibration used one poll per seat. If a second poll for a seat is added, the latest by fieldwork end is used; earlier ones are listed in the report. Averaging polls is not part of this stage.

## National Māori party vote and Te Pāti Māori party-vote share

Candidate and party questions differ (in Hauraki-Waikato 2026 the Te Pāti Māori candidate polled 45% and the party 22%). This stage does not use any party-vote figure, national Te Pāti Māori support or the Māori-roll poll (n = 1,000, both rolls) to move seat shares; doing so would double-count evidence already in the national layer. The only cross-seat link is `u_e`. Each draw exposes its standardised shared factor `z_e = u_e / tau` so a later assembly stage can couple it to the national Te Pāti Māori draw with an explicitly chosen correlation and a stated sensitivity; the default coupling is none (independent).

## Per-draw output for the MMP seat layer

`simulate()` returns, for each draw and each polled seat, candidate vote shares and the winner (party code and name) as arrays plus the draw's `z_e`; unpolled seats are listed as `unpolled` with no values (missing is not zero, and no winner is invented). The committed artifacts are the calibration, the seat summaries (winner probabilities, share quantiles, Monte Carlo error) and a labelled 2,000-draw preview; the full bank (100,000 draws, seed 2026066) is regenerated deterministically. Per-seat random streams are keyed by seat name, so adding a poll for one seat leaves the other seats' draws unchanged. The MMP layer (Stage65) takes winners as a separate input; its shape is `draws x seats` of party codes, which this output matches.

## Adding a poll

Append one record to `polls-2026.json` (fields as the existing three; the candidate names and parties as published, the source file preserved first and registered in a new dated registry), remove the seat from `unpolledSeats`, then run `python3 -m scripts.maori_seat_layer.run`. A seat with a second poll uses the later one. The runner fails on a seat or party it does not know and on a candidate list with fewer than two candidates.

## Explicit do-not list

No fallback or baseline for unpolled seats (they stay `unpolled`); no candidate covariates (incumbency, party, age of poll as a coefficient); no Student-t, mixtures, regimes or shrinkage; no party-vote or national input; no poll averaging; no reuse of general-electorate coefficients; no change to the frozen Stage45 to Stage48 pipeline; no publication or probability release; no `data/sources.json` edit; no later stage.

## Decision for James

None blocking. The adoption of the bias term is rule-governed above; the horizon sensitivity and the unadopted-shift treatment are reported for James's judgement.
