# Stage80: wiring the chosen Māori fallback into the nowcast assembly

Internal development record, not published. Decision D118 (provisional; the coordinator may renumber). Authorized as the planned next step after Stage78 (release-checklist item 15), which James had set up on 2026-10-09 ("happy for you to push the 2023 baseline").

## What changed

- **Configuration.** `maori.unpolledFallbackModel = "stage78-f"` (Stage78 arm F: the 2023 official result carried forward by party label, no polled-seat swing; James's choice on 2026-10-09). The pending list is now empty; `configVersion` is `2026-10-10.2`; decisions D115 and D118 are recorded. The validator accepts only `null` (and then requires the field to be listed as pending) or `stage78-f` (which requires `maori.unpolledSeats = labelled-fallback`).
- **Draws** (`scripts/maori_seat_fallback/draws.py`). Stage78's own `fallback_parameters` and `simulate_seat`, unchanged, for any set of seats. The assembly seeds them from the configured seed namespace (`namespace_seed(ns, 'maori-fallback')`), so they are independent of the polled layer's stream. With the Stage78 contract seed and 100,000 draws they reproduce the stored arm F win probabilities exactly (tested).
- **Assembly** (`scripts/nowcast_assembly/maori.py`). The four unpolled seats are simulated from the fallback; the three polled seats are still the Stage66 default layer re-run at the assembly's draw count. All seven seats now carry the official roster candidate ids (`targetOccurrenceId`), names and ballot groups from `config.candidate.features`. A poll's candidates are matched to the roster by surname and party (exactly one match, else the build fails); the fallback's slate is matched by name and checked against the roster's ballot group. A pending roster, an unregistered model or any non-matching candidate fails closed.
- **Export label.** Fallback seats carry `source = "Stage78 no-poll fallback: 2023 result carried forward, no seat poll (D115)"`, which the snapshot exporter already carries as the seat's `sourceIds`. Polled seats keep `Stage66 default; poll <id>`. No TypeScript or schema change.
- **Rehearsal.** The Stage77 rehearsal no longer invents winners for the unpolled seats (its coin-flip stand-in is removed); three stand-ins remain (the general-seat candidate list, the classification and the MMP rules-version label). The rehearsal report is regenerated at full size.

## Result

With the live inputs the development gate now has one blocker left: the 64 general seats are unavailable until James's D107 classification exists (`config/general-seat-classification-2026.json`). All seven Māori seats are simulated. The development gate, the synthetic fixture and the rehearsal report change only in `configVersion`, the Māori seat statuses and the digests.

Fallback win probabilities at the assembly's 4,096 draws match Stage78 within Monte Carlo error: Waiariki Waititi 0.96, Ikaroa-Rāwhiti Tangaere-Manuel 0.65 (Maxwell 0.35), Tāmaki Makaurau Kaipara and Leoni 0.50 each, Te Tai Tokerau Prime 0.66, Edwards 0.20, Kapa-Kingi 0.13.

## Limits

- The fallback block (four seats) is independent of the polled block (three seats), as the polled layer is independent of the national draw. In reality an election-wide shift would move both; independence understates the spread of the number of Māori Party seats. Any coupling needs a stated correlation.
- The Stage78 limits stand: three transitions, a calibrated class that is `overconfident` on the 2023 wave in the chronological check, carry-forward by party label only, and the Te Tai Tokerau split fraction is an assumption.
- Polled-seat shares leave the unnamed remainder out of the named candidates (Stage66), so the polled seats' mean shares sum to about 0.96 while the fallback seats close over the whole slate.
- The Waiariki poll of 7 October is recorded but not adopted: Waiariki stays on the fallback until one combined update adopts the new seat polls (James, 2026-10-09).

## Not done

No new model, no change to Stage66, Stage71 or Stage78, no poll adopted, no classification, no TypeScript, no snapshot or release, no `data/sources.json` edit.

## Reproduction

```
python3 -m unittest scripts.tests.test_stage80_maori_wiring scripts.tests.test_stage72_nowcast_config scripts.tests.test_stage73_nowcast_assembly scripts.tests.test_stage77_release
python3 -m scripts.nowcast_assembly.run --check
python3 -m scripts.nowcast_assembly.fixture --check
python3 -m scripts.release_rehearsal.run --check   # full size, about 35 minutes on 4 cores
```
