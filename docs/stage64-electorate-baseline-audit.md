# Stage64: 2026 electorate set and notional 2023 baselines

One question: does the repo hold the 2026 electorate set (the Representation Commission's 2025 final boundaries) with notional 2023 results on those boundaries, and are they correct? Data and audit only. No model scale, Stage45–48 output or frozen artifact is changed, and nothing here is read by a model stage. Decision [D096](../DECISIONS.md) (number assigned by the coordinator; recorded through the handoff fragment).

## Answer

- **Electorate set: yes, correct.** 64 general (N01–N48, S01–S16) plus 7 Māori electorates, 71 in all, with 49 nominal list seats implied. Names, official codes and electoral populations equal the preserved Schedule C transcription for all 71, every population is within ±5% of its island quota, and Tally Room's independent roster has the same 71 names.
- **Notional 2023 results: no official publication was found, so the repo's own reconstruction is the baseline, and it is internally correct.** Every 2026 electorate has a complete 17-party notional party-vote baseline (a chosen coherent scenario plus sharp population-allocation bounds), built from official 2023 party votes and the official final-2025 meshblock memberships. It reconciles exactly with the official 2023 totals. There is no notional candidate-vote result anywhere in the repo (see Limits).
- **Independent cross-check: it agrees where geography is unchanged and differs where source seats were split.** One third-party notional (Tally Room) matches the repo's party-vote ranking in 70 of 71 seats; Kapiti is the exception. The difference is within-source heterogeneity, which the population-flat reconstruction cannot see and its bounds do not cover. Recommendation below.

## What already existed (audited, not rebuilt)

| Component | Path | Role |
|---|---|---|
| Official roster and populations | `data/controls/boundaries/2025-population-controls.json` (Schedule C transcription), `2025-change-controls.json` (Schedule B) | names, SNZ codes, electoral populations; unchanged-name list |
| Old-to-new crosswalk | `data/processed/boundaries/2023-2026/crosswalk.json` | 133 population edges (123 general, 10 Māori), sharp bounds under meshblock disclosure control |
| Notional party-vote bounds | `data/processed/boundaries/2023-2026/party-votes.json` | synthetic reconstruction, population-weighted within source seats |
| Coherent scenario used downstream | `data/processed/forecast-transport/party-construction.json` (Stage41) | one chosen feasible allocation; exact rational conservation |
| Target frame | `data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json` (Stage40) | stable target ids `nz-<scope>-2026-boundary-<code>` and source ids `nz-<scope>-2023-electorate-NN` |

## Official sources and the search for official notionals

The Schedules B and C and the meshblock memberships are preserved with checksums (Stage4/Stage40). One bounded search for an official notional-results publication found none: web searches and the Electoral Commission boundary-review page (which returns a bot-protection page, as in Stage40) turned up no table, and Wikipedia carries no notional results. Absence is not proved because the Electoral Commission site cannot be read directly. A second pass was not run: a table could only matter if it contradicted the repo's reconstruction, and the cross-check below already bounds that. The acquisition and the negative search are recorded in the new standalone registry `data/processed/electorate-baseline/source-registry.json`; `data/sources.json` is untouched.

Two third-party files were preserved under `data/raw/electorate-baseline/2026-10-06/`: the Tally Room public sheet of notional 2023 results on the 2025 boundaries (72 rows, SHA-256 `57a2d25c…89cb9b3aa`) and its describing article. They are **comparison only and never a model input** (a test asserts no script or source file reads them). Kiwiblog and The Progress Report publish projected or paywalled margins, a different quantity, and were not acquired.

## Audit results

All checks are in `data/processed/electorate-baseline/audit.json` and enforced by `scripts/tests/test_stage64_electorate_baseline.py`.

| Check | Result |
|---|---|
| Roster | 71 = 64 general (48 North Island, 16 South Island) + 7 Māori; matches Schedule C by scope, code and name; all within ±5% of quota |
| Ids | 71 unique stable ids; same scheme as Stage40 |
| Baseline coverage | 71 of 71 have 17 party shares; scenario shares sum to 1 (max error 1.1e-16); scenario inside bounds |
| Geography | 16 certified two-sided exact (14 general, 2 Māori); 52 changed; 3 unchanged-by-name but with a suppressed 0–5 population edge (East Cape, Tāmaki Makaurau, Te Tai Tokerau) |
| Source seats | all 72 accounted for. 10 renamed by plurality (Bay of Plenty→Mt Maunganui, East Coast→East Cape, Kelston→Glendene, Mana→Kenepuru, New Lynn→Waitākere, Panmure-Ōtāhuhu→Ōtāhuhu, Rongotai→Wellington Bays, Te Atatū→Henderson, Wellington Central→Wellington North, Ōtaki→Kapiti); **Ōhāriu has no target in which it is the plurality** (abolished). Matches the third-party mapping for all 71 seats. Kenepuru's plurality predecessor (Mana 49.4–51.4% vs Ōhāriu 48.6–50.6%) is **not identified by the bounds**; Mana is the midpoint and the third-party choice |
| National reconciliation | official valid party votes 2,851,211 = 65 general rows + 7 Māori rows = 2,659,474 + 191,737; for all 17 parties the official total, the electorate-row sum, the Electoral Commission party-list votes, the bounds sources and the scenario targets agree exactly, scenario target totals equal source totals, and the summed bounds enclose the source total |
| Lead parties | scenario party-vote leader: National 52, Labour 17, Green 2; the lead is certain across the bounds in 70 seats, not in Glendene (margin 0.0pp) |

## Old-to-new mapping

Shares are bounds on each predecessor's share of the **new seat's electoral population** (sharp under the Schedule C controls and meshblock suppression; a single value means the bounds coincide to two decimals). They are population overlaps, not vote shares. The last column is the cross-check class described below. Full machine-readable edges, joint population bounds and source-seat fates are in `mapping.json`.

| Official code (SNZ ref) | Seat | Class | 2023 predecessors and share of the new seat's electoral population | Notional party-vote lead (scenario) | Cross-check |
|---|---|---|---|---|---|
| N01 (033) | Northland | changed | Northland 100.00% | NAT +13.4pp | moderate |
| N02 (063) | Whangārei | changed | Whangārei 97.4–97.6%; Northland 2.4–2.6% | NAT +15.5pp | moderate |
| N03 (019) | Kaipara ki Mahurangi | changed | Kaipara ki Mahurangi 99.19%; Whangaparāoa 0.77% | NAT +30.8pp | moderate |
| N04 (062) | Whangaparāoa | changed | Whangaparāoa 100.00% | NAT +37.9pp | moderate |
| N05 (009) | East Coast Bays | changed | East Coast Bays 89.5–89.9%; Whangaparāoa 10.1–10.5% | NAT +42.5pp | agrees |
| N06 (031) | North Shore | changed | North Shore 96.7–96.8%; East Coast Bays 3.2–3.3% | NAT +33.5pp | agrees |
| N07 (052) | Upper Harbour | changed | Upper Harbour 78.9–80.0%; Kaipara ki Mahurangi 12.4–13.1%; East Coast Bays 7.6–8.0% | NAT +29.3pp | large |
| N08 (032) | Northcote | changed | Northcote 94.0–94.3%; Upper Harbour 5.7–6.0% | NAT +20.9pp | moderate |
| N09 (056) | Waitākere | new name | New Lynn 64.3–65.7%; Kelston 34.3–35.7% | NAT +5.2pp | large |
| N10 (014) | Henderson | new name | Te Atatū 58.8–60.2%; Upper Harbour 27.0–27.8%; Kaipara ki Mahurangi 6.9–7.1%; Kelston 6.0–6.2% | NAT +12.3pp | large |
| N11 (011) | Glendene | new name | Kelston 47.4–49.1%; Te Atatū 43.3–44.8%; New Lynn 7.5–7.8%; Mt Albert 0.00% | LAB +0.0pp (not certain) | moderate |
| N12 (027) | Mt Roskill | changed | Mt Roskill 72.2–73.2%; New Lynn 26.8–27.8%; Mt Albert 0.00% | NAT +12.5pp | large |
| N13 (025) | Mt Albert | changed | Mt Albert 71.1–72.2%; Mt Roskill 20.8–21.7%; Kelston 5.5–5.7%; Auckland Central 1.5–1.6% | NAT +6.9pp | large |
| N14 (001) | Auckland Central | changed | Auckland Central 80.7–81.6%; Mt Albert 18.4–19.3%; Tāmaki 0.00% | NAT +8.7pp | moderate |
| N15 (010) | Epsom | changed | Epsom 90.4–90.9%; Auckland Central 8.6–9.1%; Maungakiekie 0.43% | NAT +34.9pp | moderate |
| N16 (047) | Tāmaki | changed | Tāmaki 93.7–94.0%; Panmure-Ōtāhuhu 6.0–6.3%; Maungakiekie 0.02% | NAT +33.2pp | agrees |
| N17 (024) | Maungakiekie | changed | Maungakiekie 85.8–86.7%; Panmure-Ōtāhuhu 13.3–14.2% | NAT +9.9pp | large |
| N18 (035) | Pakuranga | changed | Pakuranga 92.4–92.7%; Botany 7.3–7.6% | NAT +41.5pp | moderate |
| N19 (034) | Ōtāhuhu | new name | Panmure-Ōtāhuhu 82.3–82.8%; Botany 14.5–15.0%; Takanini 2.7–2.8% | LAB +13.0pp | large |
| N20 (022) | Māngere | changed | Māngere 95.9–96.0%; Manurewa 4.0–4.1% | LAB +41.4pp | agrees |
| N21 (003) | Botany | changed | Botany 69.9–71.1%; Papakura 18.2–19.0%; Takanini 10.7–11.1% | NAT +35.8pp | large |
| N22 (046) | Takanini | changed | Takanini 92.7–92.9%; Botany 7.1–7.3% | NAT +26.0pp | moderate |
| N23 (023) | Manurewa | changed | Manurewa 91.8–92.1%; Takanini 7.9–8.2%; Māngere 0.00% | LAB +18.4pp | moderate |
| N24 (037) | Papakura | changed | Papakura 92.4–92.6%; Takanini 7.4–7.6% | NAT +30.6pp | moderate |
| N25 (006) | Coromandel | exact | Coromandel 100.00% | NAT +23.4pp | agrees |
| N26 (038) | Port Waikato | exact | Port Waikato 100.00% | NAT +31.5pp | agrees |
| N27 (053) | Waikato | exact | Waikato 100.00% | NAT +32.8pp | agrees |
| N28 (013) | Hamilton West | exact | Hamilton West 100.00% | NAT +14.9pp | agrees |
| N29 (012) | Hamilton East | exact | Hamilton East 100.00% | NAT +18.0pp | agrees |
| N30 (050) | Tauranga | changed | Tauranga 84.3–84.9%; Bay of Plenty 15.1–15.7% | NAT +28.1pp | moderate |
| N31 (026) | Mt Maunganui | new name | Bay of Plenty 87.7–88.5%; Tauranga 11.5–12.3% | NAT +29.6pp | moderate |
| N32 (042) | Rotorua | changed | Rotorua 96.9–97.0%; Bay of Plenty 3.0–3.1% | NAT +17.8pp | moderate |
| N33 (048) | Taranaki-King Country | changed | Taranaki-King Country 94.7–95.3%; Rangitīkei 4.7–5.3% | NAT +29.5pp | moderate |
| N34 (008) | East Cape | unchanged name, edge uncertain | East Coast 99.99%; Rotorua 0.00% | NAT +7.1pp | agrees |
| N35 (049) | Taupō | changed | Taupō 100.00% | NAT +23.4pp | agrees |
| N36 (028) | Napier | changed | Napier 96.4–96.6%; Tukituki 3.4–3.6% | NAT +14.5pp | moderate |
| N37 (030) | New Plymouth | changed | New Plymouth 99.75%; Taranaki-King Country 0.23% | NAT +18.0pp | agrees |
| N38 (061) | Whanganui | changed | Whanganui 92.0–93.3%; Rangitīkei 6.7–7.9%; Taupō 0.00% | NAT +9.8pp | agrees |
| N39 (040) | Rangitīkei | changed | Rangitīkei 60.0–62.4%; Ōtaki 37.6–40.0% | NAT +14.3pp | moderate |
| N40 (051) | Tukituki | changed | Tukituki 100.00% | NAT +16.1pp | moderate |
| N41 (036) | Palmerston North | changed | Palmerston North 85.0–85.8%; Rangitīkei 14.2–15.0% | NAT +5.2pp | moderate |
| N42 (055) | Wairarapa | changed | Wairarapa 95.4–95.6%; Rangitīkei 4.4–4.6% | NAT +11.9pp | moderate |
| N43 (020) | Kapiti | new name | Ōtaki 53.3–55.6%; Mana 44.4–46.7% | LAB +0.5pp | large |
| N44 (021) | Kenepuru | new name (plurality not identified) | Mana 49.4–51.4%; Ōhāriu 48.6–50.6% | LAB +1.6pp | large |
| N45 (041) | Remutaka | changed | Remutaka 95.5–95.7%; Hutt South 4.3–4.5% | LAB +7.4pp | agrees |
| N46 (015) | Hutt South | changed | Hutt South 89.0–89.5%; Ōhāriu 10.5–11.0% | NAT +2.0pp | agrees |
| N47 (059) | Wellington North | new name | Wellington Central 69.7–71.2%; Ōhāriu 28.8–30.3% | GRN +7.0pp | moderate |
| N48 (058) | Wellington Bays | new name | Rongotai 84.2–85.0%; Wellington Central 15.0–15.8% | GRN +2.7pp | moderate |
| S01 (029) | Nelson | exact | Nelson 100.00% | NAT +3.1pp | agrees |
| S02 (060) | West Coast-Tasman | exact | West Coast-Tasman 100.00% | NAT +9.7pp | agrees |
| S03 (018) | Kaikōura | exact | Kaikōura 100.00% | NAT +20.4pp | agrees |
| S04 (054) | Waimakariri | exact | Waimakariri 100.00% | NAT +18.5pp | agrees |
| S05 (005) | Christchurch East | changed | Christchurch East 91.1–91.5%; Christchurch Central 8.5–8.9% | LAB +5.0pp | moderate |
| S06 (004) | Christchurch Central | changed | Christchurch Central 86.1–86.7%; Wigram 13.3–13.9% | NAT +3.0pp | moderate |
| S07 (016) | Ilam | changed | Ilam 97.3–97.4%; Christchurch Central 2.6–2.7% | NAT +20.8pp | moderate |
| S08 (002) | Banks Peninsula | exact | Banks Peninsula 100.00% | NAT +5.3pp | agrees |
| S09 (064) | Wigram | changed | Wigram 84.0–84.8%; Selwyn 15.2–16.0% | NAT +10.1pp | moderate |
| S10 (043) | Selwyn | changed | Selwyn 100.00% | NAT +31.2pp | moderate |
| S11 (039) | Rangitata | exact | Rangitata 100.00% | NAT +18.6pp | agrees |
| S12 (057) | Waitaki | exact | Waitaki 100.00% | NAT +21.9pp | agrees |
| S13 (007) | Dunedin | exact | Dunedin 100.00% | LAB +4.0pp | agrees |
| S14 (045) | Taieri | exact | Taieri 100.00% | LAB +0.7pp | agrees |
| S15 (044) | Southland | changed | Southland 100.00% | NAT +31.9pp | moderate |
| S16 (017) | Invercargill | changed | Invercargill 98.6–98.7%; Southland 1.3–1.4% | NAT +17.4pp | moderate |
| M01 (5) | Te Tai Tokerau | unchanged name, edge uncertain | Te Tai Tokerau 100.00% | LAB +17.4pp | agrees |
| M02 (3) | Tāmaki Makaurau | unchanged name, edge uncertain | Tāmaki Makaurau 99.99%; Te Tai Tokerau 0.00% | LAB +13.2pp | agrees |
| M03 (1) | Hauraki-Waikato | exact | Hauraki-Waikato 100.00% | LAB +11.7pp | agrees |
| M04 (7) | Waiariki | exact | Waiariki 100.00% | LAB +5.4pp | agrees |
| M05 (4) | Te Tai Hauāuru | changed | Te Tai Hauāuru 100.00% | LAB +6.0pp | agrees |
| M06 (2) | Ikaroa-Rāwhiti | changed | Ikaroa-Rāwhiti 93.4–96.4%; Te Tai Tonga 3.6–6.6% | LAB +29.4pp | moderate |
| M07 (6) | Te Tai Tonga | changed | Te Tai Tonga 99.99%; Te Tai Hauāuru 0.00% | LAB +14.0pp | moderate |

## Independent cross-check

The Tally Room sheet gives the first and second party by party vote for each new seat. Its percentages are about 1–6% larger than official shares even at seats whose boundaries did not change (probably ordinary votes only), so shares are not comparable but **the log ratio of its first to second party is** (the denominator cancels): at the 16 certified-exact seats it agrees with the repo to a maximum of 0.0027, rounding level. At the 55 other seats the log-ratio difference has RMSE 0.106 and a maximum 0.451. By bands set in the audit script after seeing the exact-seat noise (`<=0.01` agrees, `<=0.10` moderate, larger is large): exact 16 agree; changed 13 agree, 32 moderate, 10 large. The ten large seats are Botany (0.451), Ōtāhuhu (0.398), Kapiti (0.245), Henderson (−0.204), Kenepuru (0.186), Upper Harbour (0.173), Mt Albert (−0.110), Maungakiekie (0.109), Mt Roskill (0.101) and Waitākere (0.101).

The mechanism is within-source heterogeneity. The reconstruction assumes each source seat votes uniformly across its population, but a part that moves is rarely average. Kapiti takes Raumati, Paekākāriki, Camborne, Plimmerton, Paremata and Whitby from Mana (per Wikipedia's Kapiti article), plausibly more National-leaning than Mana's Porirua core, which goes to Kenepuru; the repo gives Labour +0.5pp where the third party has National +7.6pp. Botany loses its Ōtāhuhu-side edge. The bounds describe uncertainty in the population allocation only and are far narrower than this gap.

The cross-check was also read for the sheet's own headline: its 71 first-place candidates are National 45, Labour 16, Te Pāti Māori 6, Green 2, ACT 2, as the article states. That is candidate-vote information, which the repo does not hold.

## Join keys

- 2026 targets are joined by `nz-<scope>-2026-boundary-<SNZ code>`, 2023 sources by their election-local `nz-<scope>-2023-electorate-NN` id. **Boundary codes are vintage-specific**: 58 general codes mean a different seat in the 2020 and 2025 layers (for example 003 is Bay of Plenty in 2020 and Botany in 2025), and 48 names carry a different code. Never join across vintages by code.
- Name-keyed joins found (none changed here, all but the last fail closed): `scripts/boundaries/party_inputs.py` (crosswalk source name to 2023 CSV row, within one vintage, raises on missing or ambiguous); `scripts/boundaries/current_inputs.py` (joins by code and asserts the name); `scripts/readiness/geography.py:source_electorate` (exact 2023 name to election-local id, raises unless exactly one); `scripts/checkpoints/*`, `scripts/models/replacement_candidate/inventory.py`, `identity_evidence.py`, `scripts/models/nat_lab_elasticity/records.py` and `scripts/replacement_effect/sample.py` key candidate or seat records by electorate name across elections. The Stage10 silent drop of 8 of 63 seats (names without macrons in 2008) is of that last kind and is handled separately. This stage's own third-party join normalises names to NFC and asserts all 71 seats join.

## Limits and recommendation

- No notional **candidate** results exist: official ones were not found, exact seats keep their source local results, changed seats use the neutral fallback (Stage39/40). Māori electorates carry party-vote baselines only; no candidate-layer quantity is computed (Stage66).
- The party-vote baseline is a synthetic reconstruction, not observed votes. Population-flat transport is wrong by a material amount in about ten changed seats against the one independent comparator, whose method is undisclosed; it is evidence of sensitivity, not ground truth.
- Whether historical changed-seat residuals (2014, 2020 transitions, also reconstructed population-flat) already absorb this heterogeneity in the fitted spreads is not assessed here. The consequence for the party-vote lead is one seat in 71 (Kapiti), plus Glendene undecided either way.
- **Recommendation:** make no baseline change now. If James wants the heterogeneity removed rather than carried as uncertainty, the bounded next question is whether re-weighting by 2023 voting-place party votes and meshblock-linked voting places would change any seat lead or the ten large seats' composed intervals. That needs one new acquisition (2023 party votes by voting place, not preserved here) and is a separate authorized stage; do not start it from this one. Flag Botany, Ōtāhuhu, Kapiti, Henderson, Kenepuru and Upper Harbour as heterogeneity-sensitive in any seat-level display until then.

## Reproduction

`python3 -m scripts.electorate_baseline.build` regenerates `data/processed/electorate-baseline/` (register, mapping, reconciliation, audit, input contract, manifest); `--check` regenerates in memory and compares. Test: `python3 -m unittest scripts.tests.test_stage64_electorate_baseline`.
