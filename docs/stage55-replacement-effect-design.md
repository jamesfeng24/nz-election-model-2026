# Stage55: ordinary incumbent-replacement effect, frozen pre-registration

**Status: frozen before any fold-trained fit or candidate-layer score was computed.** This file and [design-contract.json](../data/processed/replacement-effect/design-contract.json) are committed as a frozen checkpoint; the code reads every threshold and rule from the JSON. Later edits are a change of design and must be recorded as a dated amendment with a reason, never a silent rewrite.

**What the author had seen before freezing (disclosed).** While reading the Stage51 table, the design author computed pooled descriptive moments of Stage7 residuals on the full ledger: general-seat retirements have mean R_old about 4.4pp and mean R_new about 0.9pp, an unfitted pooled slope near 0.4 (n about 52), and continuations have a mean R_new about 5.2pp. No fold-trained (earlier-only) fit, no candidate-layer score and no decision quantity had been computed. The design below is built from the transition vocabulary and the layer's structure, not tuned to those moments, but the pooled moments are not blind.

**Māori seats (James, 2026-10-06 11:30).** Māori electorate transitions are excluded from every Stage55 sample, fit, score and reference, because Māori seats are modelled completely separately. The filter is the electorate type (`scope = maori` in the Stage51 ledger), never the party: all 24 Māori ledger rows are Labour. The rule was already in the frozen sample definition below ("excluded by rule ... Māori-scope rows"); this note makes it an explicit requirement and the pipeline now reports the exact removal (24 ledger rows: 21 continuations and 3 candidate changes, from Hauraki-Waikato, Ikaroa-Rāwhiti, Te Tai Hauāuru, Te Tai Tokerau, Te Tai Tonga, Tāmaki Makaurau and Waiariki; the list is in `summary.json`). No arm, threshold or sample membership changed.

## The one question

> Is the neutral R assumption right for an ordinary same-party National/Labour incumbent replacement?

Current treatment (D082, Stage47 audit): the incoming candidate has no R history, so the candidate layer gives them neutral centred R (`zR = 0`, i.e. `R = mu_f`, the fold's training mean of supported R); the outgoing candidate's personal R does not transfer; S (the seat-party split) may transfer and does. Using the Stage51 National/Labour incumbent-to-successor table (2008 to 2023), test `R_new = a + rho R_old + eps`:

1. Is it neutral on average (is mean R_new close to `mu_f`)?
2. Is there a negative mean shift?
3. Is there partial transfer (`0 < rho < 1`)?
4. Does modelling it reduce candidate-balance error on the candidate layer?

Only the candidate layer is scored. There is no composed scoring, no new national fit and no acquisition.

## Sample (rules fixed before the table is joined to R)

R is the Stage7 `additive_national_centered` `normalizedPremium` (candidate share minus local-party share minus the national party-election offset). `R_old` is that residual for the outgoing source winner; `R_new` is that residual for the Stage51 primary target candidate. Rows come from the Stage51 ledger (`relation = candidate_change`), joined by occurrence ID, never by name.

- **Primary ("ordinary"):** general-scope `retirement` rows, excluding rows tagged `scandal_context` or `boundary_change_successor_seat` (a scandal exit is not ordinary, and a boundary-change successor seat compares different geographies). Retirements are the core of the question.
- **Flagged, not excluded:** other tags (`list_only`, `dismissed_as_minister`, `dropped_from_cabinet`, `late_withdrawal`, and so on) are carried for stratified description only.
- **Excluded by rule, counted and listed:** `by_election_succession` and `by_election_party_change` (the successor already held the seat), `party_change`, `boundary_complication`, Māori-scope rows (there is no Māori candidate layer; never fitted or scored), tagged primary-type rows, and rows without a finite `R_old` or `R_new`.
- **Sensitivities (pre-registered, reported beside the primary, never decisive):** (E) all general-scope election-time exits (`retirement`, `resignation_before_election`, `deselection`, `death_or_illness_withdrawal`) with no tag exclusion; (L) the primary sample minus `list_only`, `list_only_then_retirement` and `withdrew_from_selection` rows.
- **Continuation reference:** general-scope continuation pairs give the persistence slope for context only; they are never an arm.

Chronology: a fold trains only on replacements whose **target year** is earlier than the fold's year (2017 fold: targets 2011 and 2014; 2020: 2011, 2014, 2017; 2023: 2011, 2014, 2017, 2020). The held-out target's R_new is never used for fitting. The pair 2008 to 2011 is training-only (no candidate layer exists for 2011), which is why training can start earlier than the layer's folds.

## Arms (exactly four; K and P are fitted, C is the control, T is a reference)

| Arm | Predicted R of the incoming candidate | Fit |
|---|---|---|
| C | `mu_f` (neutral centred R, as deployed) | none |
| K | constant `a-hat` | equal-seat mean of training R_new |
| P | `a-hat + rho-hat R_old` | equal-seat least squares on training pairs, `rho` constrained to `[0, 1]`, `a` re-solved at a bound |
| T | `R_old` (full transfer, the continuation treatment) | none; reference only, never a candidate for adoption |

No other functional form, interaction, tag-specific shift, ridge search or seat-level covariate is fitted. The Stage10 shift of -6.64pp is not an arm: it was estimated on a different sample, includes the held-out years, and stays undeployed.

## Scoring on the candidate layer

The Stage44 candidate-layer records give, for each held general seat, the candidate shares `q` (a softmax over `log(p+kappa) + theta_S zS + theta_R zR`, earlier fit, local-party shares observed) and the record's own `theta_R` and `mu_f`. For an arm, only the replaced National or Labour candidate changes: its log weight shifts by `delta = theta_R (R-hat_new - mu_f)` and the slate is renormalised exactly. The balance mean is `p' = q'_N / (q'_N + q'_L)`, the location is the Stage48 Gaussian logistic location for `p'` under the **unchanged** Stage45 fold scales, and the observation is the unchanged Stage45 balance coordinate `v = log((y_N + eps)/(y_L + eps))`. A replaced candidate is scored only if the control already has `zR = 0` and `supportedMass.R = 0` for them (a successor with their own R history keeps it and is counted and excluded). Seats where neither N nor L candidate is replaced are bit-identical across arms and are not in the scored population, for the same reason Stage48 scored the seats its scale could move.

Because S already carries the outgoing seat-party split, any R transfer added by arm P could double count; scoring inside the live layer, whose control already contains the S transfer, is what exposes that. This is why the pooled R regression is descriptive and the layer score decides.

## Decision rule (frozen; thresholds in the JSON)

Population: affected seats (primary sample, 2017, 2020, 2023, in the layer, equal seat weight; equal-election view also reported). Decision quantity: `relative delta_CRPS` = mean over affected seats of the Gaussian CRPS of `v` under `N(location, total_sd^2)`, arm X minus arm Y, divided by the control's mean CRPS on the same seats. The 0.3% threshold mirrors Stage48's 0.01pp of about 3.7pp.

- **IMPROVES:** relative `delta_CRPS <= -0.3%`, and `delta MSE <= 0`, and `delta_CRPS < 0` in at least 2 of the 3 elections, and the upper end of a 90% seat bootstrap interval (2,000 draws, seed 55, seats resampled within election) is below 0.
- **WORSE:** relative `delta_CRPS >= +0.3%`. **NEGLIGIBLE:** `|relative delta_CRPS| < 0.3%`. **MIXED:** anything else. **INSUFFICIENT:** fewer than 20 affected seats (estimates only, no finding).
- Comparisons: K vs C, P vs K, P vs C decide; T vs C is reported as a reference.

| Result | Finding |
|---|---|
| P vs C IMPROVES and P vs K IMPROVES | `partial_transfer`: some outgoing R carries to the successor |
| K vs C IMPROVES and P vs K not IMPROVES | `constant_shift_only`: a mean shift, no transfer |
| K vs C and P vs C both NEGLIGIBLE or WORSE | `neutral_adequate`: keep neutral R |
| anything else, or any MIXED among K vs C, P vs C | `mixed_report_to_james`: stop, no recommendation |

Supporting, never decisive: delta mean squared balance error, delta negative log predictive density, replaced-candidate share MAE and N-L margin MAE (pp), out-of-fold R-unit squared error, mean squared standardised balance residual, and a materiality statement giving the balance-location size of a 1pp R shift (`theta_R x 0.01`) against the total scale.

**Descriptive inference (reported, not decisive):** mean `R_new - mu_f` per scored target year and pooled (Questions 1 and 2); pooled and per-pair OLS `rho` with a seat bootstrap interval (Question 3); the continuation slope; and the slope of R_new on R_old with and without the outgoing seat-party split `zS` as a control (S overlap).

**No adoption under any outcome.** The finding is a recommendation to James. `selectedOperationalReplacementEffectPP` stays `null`; Stage10's -6.64pp stays undeployed.

## Stage10 inventory gap (3 of 75 changes)

A fixed audit item, not a modelling choice: why Te Atatu, Rangitikei and Tamaki (2008 to 2011 pair) are absent from the Stage10 inventory, and how they are handled here. Results are in the findings document.

## Do not

- Do not fit or score any arm beyond C, K, P and T; no tag-specific, seat-level or interaction extension; no threshold change after seeing a score.
- Do not adopt, deploy or import any shift; do not edit Stage10, Stage44 to Stage48 or any frozen output; do not edit `data/sources.json`; add no source and no acquisition.
- Do not reopen Student-t, mixtures, regimes, sigma shrinkage, geography fragmentation, candidate-quality scores, S reset, covariance fitting or national MCMC reruns.
- No composed scoring, no scale change, no manual-adjustment interface, no Māori model.
- Do not relax the 20-seat floor or the bootstrap condition to reach a finding.
