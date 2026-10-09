# Stage69: voting-place notional 2023 baselines on the 2026 boundaries

One question: do notional 2023 results on the 2026 general electorates, built from where the votes were actually cast (2023 voting places located and allocated to the new seats), differ materially from the Stage64 population-weighted baseline, and which is the better-founded baseline? Decision [D103](../DECISIONS.md) (number assigned by the coordinator; recorded through the handoff fragment). Data, audit and a parallel baseline only. Stage64's outputs, every model scale and every downstream layer are unchanged; adopting this baseline as the default is a separate decision for James after the PR.

## Pre-registered design (frozen before any result is computed)

Status: written and committed before any allocation, notional or comparison was computed. Only inputs (parsing, geocoded venue locations, meshblock frame) existed at freeze time. Later changes are recorded as dated amendments at the end of this document, never edited here.

### Scope

- 65 general electorates of 2023 (2020 boundaries) allocated to the 64 general electorates of 2026 (2025 final boundaries). **Māori electorates are not allocated by voting place and are left out**: a Māori-roll elector votes at any place in the country, so a place's location says nothing about which Māori seat the votes belong to (the Māori files group places by the general electorate they sit in). Stage64's Māori baselines are retained unchanged; the Māori boundary changes are small (largest overlap change 3.6–6.6% of Ikaroa-Rāwhiti), and no claim is made about them here.
- Quantities: (1) **party vote** for every registered party in the official files, and (2) **electorate candidate vote**, aggregated by the candidate's party label (independents together), per 2026 general seat. Candidate names are not carried to 2026 (nominations are not in).

### Inputs (all preserved before use)

- Official 2023 candidate votes by voting place for all 72 electorates (already preserved, 65 general used) and, to be added from the Electoral Commission, party votes by voting place (`party-votes-by-voting-place-N.csv`, N = 1..72), preserved as raw bytes with SHA-256 before any transformation. The Commission site blocks this cloud environment, so the files are acquired on the user's device. If the layout of the party files differs from the candidate files, only the parser is adapted; the design is not changed. If the party files cannot be acquired, the party-vote half is reported as blocked and not replaced by a proxy; the candidate-vote half and the place-geography flows are still delivered.
- Place locations: OpenStreetMap Nominatim geocodes of the venue addresses, with every raw response retained (`data/raw/voting-place-notionals/2026-10-06/nominatim-responses.jsonl`). The Commission publishes addresses, not coordinates.
- Geography: 2020 and 2025 electorate polygons (preserved), and the Stage4 meshblock frame (2020 source seat, 2025 target seat, released random-rounded electoral population, centroid) rebuilt from the preserved 2025 meshblock export and membership join.
- Cross-checks only, never model inputs: the Stage64 baseline (comparator) and the preserved Tally Room notional sheet (external).

### Joins

By 2020 polygon code through the exact NFC-folded name of the 2023 file's electorate, asserted one-to-one for all 65 seats; by 2025 target code from the meshblock frame. Never by an un-normalised name and never across vintages by code. The Tally Room sheet is joined by NFC-folded new-seat name, asserted to cover all 64 general seats.

### Locating voting places

1. A venue string (unique across the 65 files) is queried in a fixed ladder: street address (the first comma component that begins with a street number) plus the Commission's locality; then venue name plus locality; then the locality alone. A result is accepted if it lies inside, or within 1,500 m of (5,000 m for the locality query), a 2020 polygon of an electorate whose file lists the venue; the first accepted result in ladder order and rank order is used. The 2020 polygon test uses only known geography, never votes.
2. Rows with no fixed address (care-home, hospital-and-care-home, mobile, pop-up, prison and defence-force "Team" rows) are not located and are treated as non-place votes.
3. Positional error for the uncertainty draws is an isotropic Gaussian per axis with standard deviation (metres): 50 if the result has a house number; 250 if it is a street (highway class) result; 100 for any other address-tier or venue-name result; 1,500 for a locality result. These are stated assumptions, not estimates.
4. A venue that cannot be accepted is unlocated and its votes are non-place votes. The share of ordinary votes at unlocated venues is reported per seat and nationally.

### Allocation (primary arm V)

For each 2023 general seat *i* separately (so every old-seat total is conserved exactly):

- Places of *i* are the located unique locations in its file, advance and election-day places at the same venue pooled. Each meshblock of *i* (centroid, released electoral population, 2025 target seat *j*) is assigned to the nearest located place of *i* by Euclidean distance in NZTM. The place's flow to *j* is the population of its meshblocks in *j* divided by the population of its meshblocks (a place with an empty catchment is treated as unlocated).
- Votes at a located place go to new seats by those flows, party by party and candidate by candidate, using that place's own counts.
- **Non-place votes** of *i* (overseas, special before and on polling day, the "fewer than six votes" row, unlocated and roving rows) are allocated to new seats by a convex mixture of **A**, the population flows of *i* (meshblock population in *i*∩*j* over population of *i*), and **B**, the vote-weighted place flows of *i* (the primary-arm flows weighted by each place's valid votes). The primary point uses A alone (weight λ = 0): the specials are enrolments with unknown residence, and A is the assumption that adds the least geography; B is the arm in which they vote like the ordinary voters near the places.
- The notional for seat *j* is the sum of its allocations from every *i*; it reconciles to the official old-seat totals by construction, and a test asserts it.

### Arms and uncertainty

- **V** (primary): as above, no perturbation.
- **P**: point-in-polygon, each located place is assigned wholly to the 2025 seat containing its coordinates (snapped to the nearest target seat with a positive population overlap from *i* if outside all of them; counted). Non-place votes as in V.
- **S**: V with non-place votes allocated by B (λ = 1).
- **O**: ordinary-place votes only (non-place votes dropped), used solely to test the hypothesis that the Tally Room sheet is ordinary-votes-only (its published percentages exceed official shares at unchanged seats).
- **W** (comparator): the Stage64 population-weighted baseline (scenario shares).
- **T** (external): the Tally Room sheet.
- **Draws**: 1,000 seeded draws (numpy default generator, seed 20261006). Each draw perturbs located places by the positional error above, draws λ uniformly on [0, 1], and draws each meshblock population uniformly inside its disclosure interval (released *v*: [max(6, *v*−2), *v*+2]; suppressed: [0, 5]). Reported per seat: 5th, 50th and 95th percentile of each major-party share and of the National−Labour party-vote margin, and the probability that National leads Labour. The draws describe geocoding, special-vote and disclosure uncertainty only; they say nothing about catchment misspecification (that is the V-versus-P difference) or about the unknown party-by-place composition of non-place votes.

### Checks that must pass (a failure is recorded, not tuned away)

1. All 72 candidate files and (when received) all 72 party files reconcile exactly: places + special rows + the fewer-than-six row = the file's total row, column by column; party and candidate totals reconcile to the preserved electorate-level files.
2. Σ over new seats of every party's V notional = the official 2023 general-electorate total, exactly; per old seat exactly.
3. At every 2025 seat whose boundary is unchanged from a 2020 seat (every meshblock of the new seat from one old seat and every meshblock of that old seat in the new seat; Stage64 lists 14 general), V, P, S and W reproduce the official 2023 seat result exactly.
4. At least 95% of national ordinary-place votes at located venues, with every located venue inside its 2020 listing seat's polygon buffer by construction; the located share per seat is reported.
5. The Tally Room ordinary-only hypothesis: at the exact seats, O shares equal the sheet's party percentages within 0.1 percentage point. If this fails the sheet is compared by log ratios only, as Stage64 did.

### Decision rules (fixed before results)

- A **material difference** at a seat is: V and W name a different party-vote leader, or the National−Labour party-vote margin differs by at least 2.0 percentage points, or the top-two log ratio differs by at least 0.10 (Stage64's "large" band). The headline is the count of material seats and the list of changed leaders.
- V is called **better founded** only if all of the following hold: checks 1–4 pass; V's RMSE of the top-two party-vote log ratio against T at the 50 changed seats outside the exact set is lower than W's (Stage64: 0.106); and V's leader agrees with T's in at least as many seats as W's. If the first two hold but the RMSE is not lower, V is reported as a documented alternative with its uncertainty and no baseline recommendation is made. The external agreement is evidence about method fit to a third party whose method is undisclosed, not ground truth, and the recommendation says so.
- The recommendation about adopting V as the default baseline is James's decision, whatever the result.

### Explicitly not done

No change to Stage64 outputs, `data/sources.json`, any model scale, Stage45–48 output or frozen artifact; no candidate-vote model, forecast, regression or later stage; no Māori allocation; no 2026 candidate names; no use of the Tally Room as a model input; no re-weighting of the national totals.

## Dated amendments (2026-10-07)

None of these changes the decision rules or any threshold above. All were made before the allocation results were looked at, except the last two, which add outputs.

1. **Party-file layout.** The party-vote files list one column per registered party rather than the candidate layout. Only the parser was adapted, as the design allowed. All 72 party files and all 72 candidate files reconcile exactly (137 tables are checked in total: 72 candidate and 65 general-seat party tables, because the 7 Māori party tables are not used).
2. **Geocoding ladder.** An address-only query (no locality) was added between the address-plus-locality and the venue-name tiers, because some Commission localities are not OpenStreetMap place names. The acceptance rule (inside, or within 1,500 m of, a listing seat's 2020 polygon; 5,000 m for locality results) is unchanged. Located venues by tier: address 2,249, venue name 63, locality 214. 5 non-roving venues are unlocated.
3. **Random stream.** Draws use `numpy.random.RandomState` (MT19937), seed 20261006, not the default generator named above, because its stream is frozen across numpy versions. Positional jitter is drawn per venue (a venue shared by several seats' files moves once), which is the intended meaning of the design.
4. **Arm A added.** All votes allocated by the population flows (no place information). It is a validation arm only: it reproduces the Stage64 population-weighted baseline W to within 0.1 percentage point of the National−Labour margin, which checks the meshblock frame and the join. It is not used in a decision rule.
5. **Drop-in file.** `baseline-party-vectors.json` carries the V party-vote shares in the same structure the nowcast assembly reads (`transitions.2023-2026.scopes.general`).

## Results

Run: `python3 -m scripts.voting_place_notionals.run` (about 1 minute locally with 1,000 draws; `--check` regenerates everything, draws included, and compares). The deterministic part (everything except the draw summaries) regenerates in about 4 seconds and a unit test compares it with the saved files.

### Pre-registered checks

| Check | Result |
| --- | --- |
| 1. All tables reconcile exactly; party files match the electorate-level party controls for all 65 general seats | **Pass** (137 of 137) |
| 2. Σ new seats = official 2023 total, nationally and per old seat | **Pass** (national difference 0.0; per old seat at most 7e-12, floating-point) |
| 3. The 14 unchanged seats reproduce 2023 exactly | **Pass** (party: 14 pairs, maximum difference 0.0 votes; candidate: 13, Port Waikato has no 2023 candidate result) |
| 4. At least 95% of ordinary votes at located venues | **Pass**: 98.79% nationally; lowest seat 95.4% (Tukituki) |
| 5. Tally Room sheet is ordinary-votes-only (O within 0.1 pp at the exact seats) | **Fail**: largest difference 6.1 pp (Port Waikato: O 56.3% against Tally 50.2%). On all votes the largest difference is 1.5 pp, so the sheet is not ordinary-only. Compared by log ratios only, as Stage64 did. Recorded as a failure; nothing was tuned. |

Other facts: 1,162 sites have an empty catchment and are pooled into the non-place votes of their seat; 981 sites were snapped to a target seat under the point-in-polygon arm P. A diagnostic only: across the 64 seats with at least 8 sites, a site's votes and its catchment population have a median Spearman correlation of 0.61 (range 0.30 to 0.78), so catchment population is a useful but far from complete predictor of where people voted.

### Party vote: V against the Stage64 baseline W

**8 of the 64 seats are material, and 1 changes leader.** The other 56 are unchanged under every material criterion, including the 14 exact seats.

| Seat | W: National−Labour (pp) | V: National−Labour (pp) | Margin difference (pp) | Top-two log-ratio difference |
| --- | --- | --- | --- | --- |
| Botany | +35.8 | +43.5 | 7.7 | 0.27 |
| Ōtāhuhu | −13.0 | −20.9 | 7.9 | 0.20 |
| Henderson | +12.3 | +6.7 | 5.6 | 0.16 |
| Kapiti | −0.5 (Labour leads) | +3.9 (National leads) | 4.4 | 0.13 |
| Mt Roskill | +12.5 | +15.5 | 3.0 | 0.08 |
| Upper Harbour | +29.3 | +32.3 | 3.0 | 0.10 |
| Papakura | +30.6 | +27.9 | 2.7 | 0.09 |
| Kenepuru | −1.6 | −4.0 | 2.4 | 0.07 |

At the 50 changed seats the mean absolute difference in the National−Labour margin is 1.03 pp (median 0.35, maximum 7.9). Kapiti is the only seat where the leader changes: arms P and S give National +5.0 and +3.8, and the draws (5th, 50th, 95th percentile) are +4.8, +5.0, +5.8 with P(National ahead of Labour) = 1.00.

### Uncertainty

The draws cover geocode position, the non-place vote rule and meshblock disclosure only. The median 90% width of the National−Labour margin at changed seats is 0.48 pp (maximum 4.74); at the exact seats it is 0. Only two seats have a National-ahead probability strictly between 0.02 and 0.98: Glendene (0.08) and Hutt South (0.93). The draw median differs a little from the unperturbed point V (mean absolute 0.19 pp, maximum 2.1 pp), and V lies outside the draw 5–95% interval at 14 of 50 changed seats: the Voronoi catchments are a nonlinear function of site position, so jitter moves the central tendency, not just the spread. Catchment misspecification (V against P: mean absolute margin difference 0.71 pp, maximum 5.0) and the unknown party composition of non-place votes (V against S: 0.16 pp, maximum 1.5) are larger than the draw width at several seats and are reported separately, not folded into the draws.

### External cross-check (not a model input, not ground truth)

At the 50 changed seats the RMSE of the top-two log ratio against the Tally Room sheet is **0.054 for V and 0.111 for W** (Stage64 reported 0.106 for W over its own set of seats). V names the same leader as Tally in 50 of 50 seats, W in 49 of 50. Tally's method is undisclosed, so this is evidence that V is closer to an independent method that appears to use place data, not that either is right.

### Candidate vote

V leaders: National 44, Labour 14, Green 3, ACT 2 (63 seats). **Port Waikato has no candidate notional**: its 2023 candidate poll was cancelled after a candidate's death and the published table holds no votes, so the seat is reported missing rather than zero-filled (its party vote is allocated normally). RMSE of the top-two log ratio against Tally is 0.051 at 50 changed seats, with 49 of 50 leaders agreeing (Wellington North: V Green, Tally Labour).

### Recommendation

Under the pre-registered rule V is **better founded** than W: checks 1–4 pass, V's RMSE against Tally is lower (0.054 against 0.111) and V's leader agreement is not lower (50 against 49). The difference matters at 8 seats and changes one leader (Kapiti). Two limits are stated with it. First, check 5 failed, so the external sheet is used only through log ratios, and its agreement is evidence about method fit, not truth. Second, V rests on nearest-site catchments and a stated rule for non-place votes (19.8% of candidate valid votes nationally); the distance from V to P and S is larger than the draw intervals at some seats. The Māori seats are not covered (Stage64 baselines retained; Stage71 owns their calibration).

**Adoption is James's decision.** To adopt V for the nowcast, point `baseline.source` in `config/nowcast-2026.json` at `data/processed/voting-place-notionals/baseline-party-vectors.json`, which has the structure the assembly reads. Nothing in Stage64, the model scales or any downstream layer was changed by this stage, and the candidate notionals are supplied as data but not consumed by anything.
