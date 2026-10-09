# Stage78 design (frozen before any transition error or score was computed): no-poll fallback for the unpolled Māori seats

Decision number D115 (taken as the next free number on main; the coordinator may renumber). Internal only: nothing is published or released, and the nowcast configuration and assembly are not changed. The Māori seats stay modelled completely separately from the general electorates: no general-seat data, calibration, regression or output is read or changed, and neither are the national model or the MMP allocator. The Stage66 and Stage71 layers, their code and their outputs are read only.

**One question.** Can candidate shares and a winner be estimated for a Māori electorate that has no seat poll, from the previous election's official result carried forward and from what the polled seats show about the election-wide change since then, with the uncertainty calibrated on the 2014 to 2017, 2017 to 2020 and 2020 to 2023 changes in the official results, in the Stage66 per-draw form; and does borrowing the polled seats' swing help or hurt on held-out elections?

This is release-checklist item 15 and the "labelled fallback" James chose on 2026-10-07 (D114). The four seats are Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau and Te Tai Tokerau.

## Disclosure about what was known when this was frozen

- The official Māori-seat results for 2014 to 2023 and the 2026 official nomination list for the seven seats were read in full. The 2026 candidate set differs from 2023 in every unpolled seat: Waiariki (Waititi and Boynton both stand again), Ikaroa-Rāwhiti (a new Te Pāti Māori candidate; the Labour winner stands again), Tāmaki Makaurau (both main candidates are new), Te Tai Tokerau (the 2023 Te Pāti Māori winner, Kapa-Kingi, stands for the Te Tai Tokerau Party; Te Pāti Māori and Labour both have new candidates).
- It was known that Te Pāti Māori candidates gained on Labour in every seat in 2023 and that 2023 is by far the largest election-wide movement in the data. No transition error, variance, scale, shared-shift estimate, win probability or score had been computed when this file was committed. The only quantities counted beforehand are structural: how many seats qualify for the contrast in each transition (6, 6, 7), how many candidates match a previous candidate by party label, and the sizes of the two entrant pools (6 established-party and 29 other candidates over the three transitions).
- Because the 2023 movement is known, the bias question is closed by rule, not tested: no bias term (below). The shared election-level shift carries it as uncertainty.
- The three 2026 seat polls (Hauraki-Waikato, Te Tai Hauāuru, Te Tai Tonga) were read. Their MP-versus-Labour changes from 2023 were not computed.

## Inputs (no new sources)

1. Official Māori-seat candidate results 2014 to 2023: `data/processed/maori-seat-layer/historical-results.json` (Stage66, preserved from the Electoral Commission files).
2. The 2026 official nominations for the seven Māori electorates: `data/processed/nominations-2026/2026-10-10/official-table.json` (Stage50 part 2). The complete slate is used for each seat, so there is no unnamed remainder.
3. The Stage66 polled layer (control, C) and the Stage71 variance-inflated layer (P) for the three polled 2026 seats; for the backtest, the 25 historical polls through the same code (Stage66 `calibration_rows`, Stage71 `fold_fits`).
4. One small judgement file, `data/source-plans/maori-seat-fallback/inputs-2026.json`: the party-label codes for 2026 labels not seen before, and the split-incumbent record described below.

## What is carried forward

For a seat in election `e` with candidates `i` on the ballot, and the previous election's closed shares `m` (shares of all valid candidate votes in that seat):

- **Established parties** are the codes MP (Māori Party / Te Pāti Māori), LAB, GRN, NAT, NZF, ALC and MANA. A candidate is **matched** when its code is established and exactly one candidate with that code stood in the same seat in election `e - 1` and exactly one stands now. A matched candidate's baseline is `log m` of its predecessor. The carry-forward is by party label, not by person: it does not use names, and no candidate identity is inferred (the historical record shows personal votes move with the person in some cases and stay with the party in others, and the typical turnover is part of the calibrated error).
- Every other candidate is an **entrant**: independents, unlisted parties, an established party that did not stand last time, or a code that appears twice. An entrant's closed share is drawn from the empirical set of entrant shares in the training transitions, in two pools: established-party entrants (6 over the three transitions) and all other entrants (29). This is an empirical resampling, not a model. Candidates who stood last time and do not stand now simply disappear; the softmax closure below reallocates their share in proportion.
- **Split incumbent (one 2026 case).** The 2023 Te Pāti Māori winner of Te Tai Tokerau stands for a different party. A fraction `phi` of the 2023 Te Pāti Māori baseline follows her (the Te Tai Tokerau Party candidate gets `phi * m`) and the rest stays with the Te Pāti Māori label (`(1 - phi) * m`). `phi` is drawn uniformly on (0, 1) for every draw: a stated assumption of ignorance, not a fitted value. Two reference points are reported as consistency checks only: in the Te Tai Tonga 2026 poll the former incumbent (independent) holds 15 of the 32 points of the former incumbent plus the Te Pāti Māori candidate (0.47); in Ikaroa-Rāwhiti 2023 the Labour incumbent who switched to Te Pāti Māori kept much less of her old vote than her party did (the Labour label held 97% of its 2020 share). The fixed values 0.2, 0.5 and 0.8 are sensitivities.
- The Te Tai Tokerau Party candidate is in the OTH group for the election-wide shift (below): the shift is a shift of the Te Pāti Māori label.

## Error model (the Stage66 structure with the previous result in place of the poll)

On the log scale, for the draw's candidates:

`log v_i = baseline_i + 1[code(i) = MP and matched or split] u + eps_i` for matched and split candidates, `log v_i = log(entrant share draw)` for entrants, then softmax over the whole slate.

- `eps_i ~ N(0, sigma^2)` independent per candidate. `u ~ N(0, tau^2)` is one election-wide shift of the Māori Party label, shared by every seat in the election (the cross-seat dependence among the four unpolled seats).
- **Calibration contrast.** For every seat with exactly one MP and exactly one LAB candidate in both `e - 1` and `e`: `D = log(v_MP / v_LAB) - log(m_MP / m_LAB)`, the change in the Māori Party-versus-Labour log-odds. Contrasts per transition: 6 (2017), 6 (2020) and 7 (2023), 19 in total. Under the model `D = u + eps_MP - eps_LAB`, so `Var(D | e) = 2 sigma^2`.
- `sigma^2` and `tau^2` use the **Stage66 estimators unchanged** (`scripts.maori_seat_layer.fit.sigma2` and `tau2`): within-election pooled variance of `D` over 2, and the method-of-moments `tau^2` about **zero**. `sigma^2` has `n_contrasts - n_elections` degrees of freedom (16 on all three transitions) and `tau^2` has `n_elections` (3).
- **No bias term and no adoption rule.** `b = 0` is fixed: with three transitions a nested leave-one-election-out adoption test cannot be run, and Stage66 already decided the analogous question. A drift in the Māori Party label (as in 2023) is therefore uncertainty, carried in `tau^2`.
- **Parameter uncertainty** is propagated as in Stage66: each draw uses `sigma^2 = s^2 * dof / chi2_dof` and `tau^2 = t^2 * n / chi2_n`. With three elections the `tau^2` draw has heavy tails; that is a reported consequence of weak identification, not a heavy-tailed error model.
- **Diagnostic, never adopted:** the second moment of log-odds errors against Labour for matched candidates outside the MP and LAB groups, compared with `2 sigma^2` (flag above 1.5), as in Stage66.

## Borrowing the polled seats' swing (arms FC and FP)

If `k` polled seats qualify (exactly one MP and one LAB candidate in the poll and in the previous election), each draw of those seats' simulated outcomes gives a realised change `x_j = log(share_MP / share_LAB) - log(m_MP / m_LAB)`. Under the model `x_j = u + eps_MP - eps_LAB`, so the mean `x̄` of `k` seats satisfies `x̄ = u + e` with `Var(e) = 2 sigma^2 / k`. The unpolled seats use the exact Gaussian posterior of the shared shift in that draw:

`kappa = tau^2 / (tau^2 + 2 sigma^2 / k)`, `u | x̄ ~ N(kappa x̄, kappa * 2 sigma^2 / k)`,

with the draw's own `sigma^2`, `tau^2`. No parameter is fitted for the transfer: it follows from the variance components already estimated, so with large `tau^2` the unpolled seats follow the polled seats closely and with small `tau^2` they ignore them. The shifted draw is shared by every unpolled seat in the same draw, so the four unpolled seats stay dependent, and each is dependent on the polled seats through `x̄`, draw by draw.

- **FC:** the polled layer is Stage66 unchanged (control). **FP:** the polled layer is Stage71's variance-inflated layer. The two arms give the labelled C-to-P range the nowcast specification requires for Māori seats (`docs/nowcast-specification.md` section 5). **F:** no polls at all (the prior from the previous result and `tau^2`): the lower-information reference.
- **Eligibility is by party label only:** a polled seat qualifies when both the poll and the previous election have exactly one MP and one LAB candidate. In 2026 that is Hauraki-Waikato, Te Tai Hauāuru and Te Tai Tonga. Te Tai Tonga's Māori Party candidate is not the 2023 incumbent (the incumbent is now an independent); a rule that treats it differently was not pre-specified, so it is included, and its exclusion is a reported sensitivity.
- **Historical qualification of the transfer:** a target seat's own poll is never used for itself. In the backtest the swing for a target seat is estimated from subsets of **exactly three** other qualifying polled seats (the 2026 number), all subsets enumerated and the contest scores averaged over them. When fewer than three others qualify, all of them are used.

## Schemes and scoring

- **Leave-one-election-out (headline).** For each of the three transitions in turn, train the fallback on the other two, train the polled layer on the polls of the three other elections (the Stage71 leave-one-election-out training sets), and score all seven seats' official results: 21 contests, every candidate. The nearer-in-time training is not strictly out of sample for earlier transitions, and the 2023 wave sits in the training set of the other two folds; this is stated, not hidden.
- **Chronological check (2023 only).** The fallback is trained on the 2017 and 2020 transitions and the polled layer on 2014 to 2020; 7 contests. The 2017 and 2020 folds have one or no earlier transition and are not scored chronologically.
- Monte Carlo: 20,000 draws per fold, common random numbers for every arm (the same `eps`, `chi2` and shared-normal streams), seed 2026078, entrant pools from the training transitions only, one stream per (scheme, election, seat).
- **Metrics per arm, per fold and pooled (equal weight per contest):** (1) the predicted probability of the actual winner, its log (floored at 1e-4) and the multi-candidate Brier score of the winner probabilities; (2) calibration of the pre-election favourite (highest predicted win probability): mean predicted against observed, `z = sum(y - p) / sqrt(sum p(1-p))`; (3) coverage of the closed shares of **all** candidates by the 50, 80 and 90% central predictive intervals (and of `D` for contests that have it); (4) a paired contest-level bootstrap (5,000 resamples) of the pooled log-score and Brier differences, which ignores the within-election dependence and so understates uncertainty.

## Frozen finding rules

**Rule 1: does the swing help? (FC and FP each against F, leave-one-election-out, pooled).** Applied in this order; the first that holds is the class.

1. `swing_helps`: pooled mean log score and pooled Brier both improve over F, and the log score is better in at least two of the three held-out elections.
2. `swing_hurts`: pooled mean log score and pooled Brier are both worse than F's.
3. `mixed_report_to_james`: anything else (the two pooled scores disagree, or they improve but fewer than two folds agree).

The evidence qualifier is `clear` if the 90% paired bootstrap interval of the pooled log-score difference excludes zero, otherwise `weak`.

**Registration.** If neither FC nor FP is `swing_hurts` or `mixed_report_to_james`, the registered fallback is the FC-to-FP range (the default is used unless the swing demonstrably hurts). If either is `swing_hurts`, the registered fallback is F alone, and the polled-seat coupling is not used. If the two arms land in different classes, or either is `mixed_report_to_james`, no registration is stated: the result is reported to James before anything is registered.

**Rule 2: calibration class of the registered fallback (leave-one-election-out).** `calibrated` if `|z| <= 1.645` and the mean absolute deviation of the 50/80/90% share coverage from nominal is at most 0.10; `overconfident` if `z < -1.645` or the mean coverage is below nominal by more than 0.10; otherwise `underconfident`. The same classes are reported for the chronological 2023 check. The class decides the label wording only; no correction is fitted or applied here.

If the chronological 2023 check lands in a different calibration class from the headline, the report says so and the headline is not stated without that qualifier.

## The 2026 readout

For each of the four unpolled seats under F, FC and FP (100,000 draws, fallback seed 2026078, polled layers re-simulated with the Stage66 seed and stream layout, the Stage71 bootstrap for P): the candidates and parties, win probability and its Monte Carlo error, closed-share quantiles (5, 25, 50, 75, 95%), and the count of Māori Party-label wins across the four seats and, for FC and FP, across all seven seats, with the draw-by-draw dependence kept. Reported sensitivities, never adopted: `phi` fixed at 0.2, 0.5 and 0.8 (Te Tai Tokerau only); the swing without Te Tai Tonga; and the share of draws in which a candidate outside the two main groups wins. A shift of more than 0.10 in any win probability between the registered fallback and a sensitivity is flagged for James. The per-draw output has the Stage66 shape (`share`, `winner` index and the candidate list per seat, plus the shared draws) so that the assembly can consume it; wiring it into the assembly and registering the model in the configuration are separate (below).

## Explicit do-not list

No Student-t, mixtures, regimes or shrinkage of `sigma`; no geography fragmentation; no candidate-quality scores, incumbency terms, candidate-identity matching or mean-reversion term; no bias adoption or era term; no inflation of the fallback's own variance (the calibration class reports it); no national party-vote, national Te Pāti Māori or Māori-roll poll input and no coupling with the national draw; no poll averaging; no use of general-seat data or coefficients; no rerun of national MCMC backtests; no change to Stage66 or Stage71 code, data, outputs or contracts; no change to the configuration, the assembly, the draw bank, the TypeScript or the export; no new sources and no `data/sources.json` edit; no publication or probability release; no later stage.

## Decision for James

None blocking if the rules give a clean class. The default for `phi` (uniform), the inclusion of Te Tai Tonga in the swing and the wording of the label are judgements recorded above with sensitivities. If the two finding rules disagree between FC and FP, or the swing result is `mixed_report_to_james`, the thread stops and asks before registering anything. Wiring the registered fallback into the assembly, setting `maori.unpolledFallbackModel` and the export label are the next separately authorized small stage.
