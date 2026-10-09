# 2026 nowcast specification (canonical current design)

**This is the single source of truth for what the 2026 product is and how its parts connect.** Other active documents point here rather than restating it. Decisions: [D106](../DECISIONS.md) (nowcast estimand) and [D107](../DECISIONS.md) (general-seat candidate-balance uncertainty policy). The remaining work and the publication gate are in [release-checklist.md](release-checklist.md). Historical stage documents are records of what each stage found, not current policy.

Status, 7 October 2026: every layer below exists and has been checked historically. Stage73 assembles the Python draw bank ([stage73-nowcast-assembly.md](stage73-nowcast-assembly.md)) and Stage74 turns a bank into a validated v2 snapshot ([stage74-nowcast-snapshot.md](stage74-nowcast-snapshot.md)); the live bank is blocked on inputs and nothing is published.

## 1. Estimand

The primary public product is a **nowcast**:

> If a New Zealand general election were held under current political conditions, what would happen?

It is **not** a forecast of how opinion will move by election day (7 November 2026). The election date is context, not the estimand.

| Belongs in the nowcast (keep) | Excluded from the primary nowcast |
|---|---|
| Uncertainty about the current latent national state, including the industry-wide polling error and house effects | National drift between the latest model state and election day (the gauss random walk and campaign multiplier) |
| Local-party and candidate translation uncertainty (Stage45 Gaussian scales, conditional on national and local truth) | Any extra polling-error draw on top of the national posterior |
| Māori electorate poll error, and movement since the poll fieldwork up to the as-of date | Campaign-period movement after the as-of date |
| Turnout, threshold, overhang and MMP allocation outcomes | |

The local-party and candidate scales were calibrated against election-day results. They therefore also absorb seat-level campaign movement after T−56, which cannot be separated out. They are kept unchanged and are treated as slightly conservative for a nowcast. A nowcast cannot be validated directly against an election result, because the result includes later movement. Any calibration statement for the nowcast is indirect.

## 2. National input and dating

- **Source:** the Stage62 live fit (Stage70 refits it as polls arrive), pinned external `gauss` model, arm A.
- **Draws used:** `lastDataSupport`, joint draws over the eight categories (`fits/A/attempt1.npz`).
  - In the pinned model `pi` is latent *true* support; polls measure `pi + house + industry(t)`.
  - `lastDataSupport` therefore already integrates the industry polling-error uncertainty. Its correlation with the election-day industry error is −0.45 to −0.68 by party, checked on the committed draws.
  - Never add a second industry-error draw.
- **Not used for the nowcast:** the key `electionDay`, which is election-week support. Its difference from `lastDataSupport` is uncorrelated with the industry error (|r| ≤ 0.03), so it is pure future drift. It may only feed an explicitly labelled `election-day-scenario` output, never the primary product.
- **Wording correction.** Stage62's findings, and the METHODOLOGY section copied from them, say the last-data draws carry "no polling error" and that election week "adds the common polling-error draw". Both statements are inaccurate, as shown above. The numbers are unchanged.
- **Dating.**
  - `lastDataSupport` is the latent state for the Sunday week of the latest poll midpoint: the week of 27 September 2026 in the Stage62 fit, with the poll cutoff on 6 October.
  - Polls whose fieldwork ends later are placed at their midpoint week and are incorporated coherently.
  - Outputs are labelled **"latent state as of the week of …, polls to …"**, never "today". `modelStateAsOf` in the export carries this date.
  - Stage70 should refit when polls arrive and save joint draws at the as-of week.
- **Precision.** The 8,000 national draws are MCMC output with bulk ESS of about 1,000 to 1,800 per coordinate. Monte Carlo errors for national-driven quantities (party seats, thresholds, blocs) must use an effective sample size, for example batch means by chain, not `sqrt(p(1-p)/n)` with n = 8,000. Production uses 4,096 national draws × 16 layer replicates (Stage63; `simulation` in the config): replicates lower the layer error, not the national floor, and batch means keep each draw's replicates together (Stage77).

## 3. Pipeline (producer → interface → consumer)

| Step | Producer | Interface | Consumer | Units and dependence | State |
|---|---|---|---|---|---|
| 1 | Poll sources (Stage52/59), Stage70 routine | dated poll panel | national fit | poll shares | Stage70 unpushed |
| 2 | Stage62/70 gauss fit | `lastDataSupport` draws | national adapter | 8 category shares; one draw id shared by every seat | exists |
| 3 | national adapter (`scripts/nowcast_assembly/national.py`) | category → 2026 ballot groups | local layer **and** MMP party vote | shares summing to 1; the **same** draw feeds both; Other one MMP bucket, split inside each seat by its own 2023 mix | built (Stage73) |
| 4 | local party (`local_vectors` + `invert`, `scripts/uncertainty_expectation/simulation.py`) | per-seat party affinities from the 2026 notional baseline; 2026 local-party scales | candidate layer | ballot-group shares; shared election effect + seat effect | built (Stage73) on the 2026 scales; baseline switches to Stage69 |
| 5 | candidate (`candidate_vectors` + `invert`, Stage45 Gaussian) | continuous S+R destinations/exponents (`data/processed/continuous-transport/readiness-2026.json`, recentred in `data/processed/candidate-fit-2026/features-2026.json`) + final slate; S+R means from the Stage75 all-elections fit; 2026 candidate scales × D107 multiplier | winners | candidate shares; shared + seat effects | built (Stage73); the official roster (Stage50) and the classification (2026-10-10) are in, so the live run simulates all 64 general seats |
| 6 | Stage56 manual layer | dated adjustment files | output B only | mean shifts, `extraSdPp` | exists; no 2026 entry |
| 7 | Stage66/71 Māori layer | per-draw winners (3 polled seats; 4 `unpolled`) | MMP | independent of the national draw (coupling optional) | exists; unpolled seats block MMP until the labelled fallback (D114) is defined |
| 8 | Python → TypeScript bridge | draw bank: national shares + 71 winners per draw (Stage73 `scripts/nowcast_assembly`) | Stage65 seat layer | shares → integer votes at 10^9 | bank built (Stage73); reader built (Stage74, `src/models/nowcast/drawBank.ts`) |
| 9 | Stage65 `src/models/mmp/seatLayer.ts` | seat summaries with Monte Carlo SE | exporter | seats, threshold/lifeboat, overhang, size, blocs | 80% quantiles and effective-n SE added (Stage74, `src/models/nowcast/`) |
| 10 | exporter (`src/models/nowcast/fromBank.ts`; in-browser `src/models/simulation/exporter.ts`) | snapshot v2 (`src/types/export.ts`) | archive → loader → site | 50/80/90 intervals | bank → snapshot built (Stage74); synthetic only so far |

National uncertainty enters exactly once, through step 2's draw id. The local and candidate scales condition on national truth, so they add no second national term.

**National reconciliation with turnout and denominators** is not needed for the nowcast. MMP uses the national draw's party-vote shares directly, and electorate winners use within-seat candidate shares. What remains is an internal release-gate check (never shown to users): the turnout-weighted aggregate of local party means must match the national mean within tolerance, to catch a broken affinity table.

**Superseded or inactive inputs:**
- Stage64's population-flat baseline and the Stage41 `forecast-transport/readiness-2026.json` stop being live when Stage69 is adopted.
- Stage42's `continuous-transport/readiness-2026.json` is the only live S/R source; it is rebuilt after Stage50 and Stage69.

## 4. General-seat uncertainty policy (D107)

**Candidate N/L balance seat-scale multiplier:**
- **0.60** for ordinary general seats;
- **1.00** (the frozen default) for exceptional general seats.

**What does not change.** No multiplier above 1 is fitted or applied. The multiplier changes the seat balance standard deviation only: the shared election scale, the means (the location solve preserves the frozen ratio mean), the local-party layer and the Māori layer are unchanged.

**Provenance and its limits.** The decision is James's, taken after Stage67. Stage67 itself (D101) recommended holding flagged seats at 1.00 and did **not** establish the narrower ordinary scale. The roughly 0.60 ordinary multiplier is development-informed: it was fitted on 2014–2023 with flags assigned knowing the results, and it is flag-selection-sensitive (the 17 cleaner flags gave no gain over a single scale). This limitation stays attached to the policy.

**Candidate within-remainder and major-mass multipliers (D121, Stage83):**
- **0.55** on the candidate within-remainder noise and **0.91** on the candidate major-mass noise (the National + Labour total against everyone else), seat and shared parts together, for ordinary general seats;
- **1.00** for both in exceptional general seats; the means, the balance multiplier and the local-party layer are unchanged.

The 0.55 is James's judgement (2026-10-10), not a fitted value; the 0.91 is the fitted all-election value. The frozen Stage83 rule fitted about 0.80 on earlier elections only and, because ordinary-seat minor-candidate 80% coverage stayed above the registered band, kept control. The pair was chosen with all four elections known and has no out-of-sample support. Its stated costs: National's 80% coverage in ordinary seats falls by 0.024 (guard 0.03), the tails of minor-candidate results in ordinary seats are thinner (a minor-candidate win in an ordinary seat becomes less likely than the fitted law allows), and independent candidates, already under-covered at the 80% level, are narrowed further. It shares the flag-selection sensitivity of the D107 policy. See `docs/stage83-ordinary-minor-spread-findings.md`.

**The 2026 classification.**
- One dated file classifies every 2026 general seat as `ordinary` or `exceptional`, by 2026 boundary id, with author, date, reason and sources. It is recorded in `config/general-seat-classification-2026.json` (2026-10-10; 13 exceptional, 51 ordinary; reasons in `docs/general-seat-classification-2026.md`).
- The classification is exhaustive and exclusive over the 64 general seats. A missing seat **fails the build**; it never defaults to 0.60.
- Any seat with a Stage56 entry flagged exceptional must be `exceptional` in the classification.
- A 1.00 seat may not also carry `extraSdPp` unless James explicitly opts in, because that would be the excluded widening above 1.
- The historical flag lists in `scripts/exceptional_scale` and the Stage67 contract (2014–2023, keyed by name) are development inputs and must never be read by the live build.

**Electorate polls (general seats).** No measurement interface exists. Until one does, a poll enters only through the Stage56 layer, which requires the exceptional flag (1.00). A poll may justify the flag *or* an `extraSdPp`, not both.

## 5. Māori seats

- **Layer:** Stage66 (default) and Stage71 (single variance inflation, `improves_not_restored`, not adopted).
- **Both are calibrated against election results.** Their errors therefore mix poll error with post-poll campaign movement, and four elections cannot separate the two. For the nowcast, Stage71's inflation is **not** applied silently. Before any Māori probability is shown, either both C and P are shown as a labelled range, or the probabilities are withheld.
- **Still required before a single published Māori probability:** a structure-specific minor-candidate scale. Stage71 found its single factor over-widens the Māori Party-versus-Labour contest.
- **Unpolled seats.** Four seats (Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau, Te Tai Tokerau) have no estimate. Stage65 requires all 71 winners, so they block every MMP output until the labelled fallback James chose (D114) is defined or more polls arrive.
- **Dependence.** Māori draws are independent of national Te Pāti Māori support by default; Stage66 exports a shared factor for optional coupling. Independence understates the link between electorate wins and party vote, which drives overhang. Any coupling needs a stated correlation.
- **Refresh.** Candidate lists are rechecked against the Stage50 roster, and new Whakatau polls are added through the Stage66 procedure.

## 6. Intervals and their meaning

- **Levels:** 50%, **80% (primary display)** and 90%, all central intervals around the draw median, nested.
- **Meaning:** an 80% interval is the central range across simulated elections held under the current latent state. It is **not** a margin of error, and **not** a range for where opinion may move by election day.
- **Display:** show full lower and upper bounds; never present a half-width "±" as the interval.
- **No hard-coded widths:** every displayed width comes from the live composed draws. Development figures (for example the ordinary-seat widths discussed after Stage67) are never hard-coded or promised.

## 7. Export (snapshot schema v2)

`src/types/export.ts` and `docs/export-contract.md`:
- `schemaVersion: 2`;
- `targetType` (`nowcast`, or a separately labelled `election-day-scenario`);
- `modelStateAsOf` ≤ `dataCutoff` ≤ `createdAt`;
- `electionDate` as context;
- national and party-seat intervals at exactly 50/80/90, nested;
- `configVersion` in model provenance.

The synthetic leak guards are unchanged.

Completed by Stage74 ([stage74-nowcast-snapshot.md](stage74-nowcast-snapshot.md)):
- `seatLayer`: Stage65 party, bloc and Parliament-size intervals, plus probabilities with effective-sample MCSE/ESS (batch means within chains);
- `electorateDetail`: per-seat uncertainty class, candidate-share intervals and win probabilities with MCSE.

Still open: per-component calibration status and the Stage63 precision thresholds.

Stage53's fixed `requiredSeats` government combinations are replaced by Stage65's dynamic-majority blocs (`seatLayer.summary.blocs`); `governmentOutcomes` stays empty for nowcasts.

## 8. Configuration (one canonical source: `config/nowcast-2026.json`, Stage72)

`config/nowcast-2026.json` will hold:
- the election date;
- the national source (fit, arm, `stateKey: lastDataSupport`);
- the balance multipliers `{ordinary: 0.60, exceptional: 1.00}` and the within-remainder multipliers `{ordinary: 0.55, exceptional: 1.00}` and the major-mass multipliers `{ordinary: 0.91, exceptional: 1.00}` (D121);
- the classification path;
- the baseline pointer (Stage64 now, Stage69 later);
- the roster snapshot id;
- the interval levels;
- draw counts and seeds;
- the bloc file;
- the MMP rules version;
- the model and config version.

Frozen historical scripts keep their own constants. Live code reads only this file, through `scripts/nowcast_config/validate.py`. Fields owned by other work are explicitly pending, and the assembly runs with `--require-complete`. The 2026 scales (`data/processed/nowcast-config/scales-2026.json`) are the frozen Stage45 rule with target 2026. See [stage72-nowcast-config.md](stage72-nowcast-config.md).

## 9. Decisions still James's

- ~~the probability-release policy~~ (decided 2026-10-07, D114: [release-checklist.md](release-checklist.md));
- ~~bloc definitions for any coalition output~~ (decided 2026-10-07: NAT+ACT, NAT+ACT+NZF, LAB+GRN, LAB+GRN+TPM; hung parliament with TOP as kingmaker);
- ~~the four unpolled Māori seats~~ (decided 2026-10-07, D114: a labelled fallback; the fallback model itself is not yet defined);
- ~~whether Māori probabilities are shown as a C–P range or withheld~~ (decided 2026-10-07, D114: a labelled range);
- the 2026 ordinary/exceptional classification.
