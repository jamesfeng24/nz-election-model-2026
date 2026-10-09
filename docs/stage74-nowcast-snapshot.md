# Stage74: draw bank to a validated v2 nowcast snapshot (TypeScript side of the assembly)

**Question.** Can a Stage73 draw bank become a validated snapshot v2 in TypeScript, refusing anything incomplete? The snapshot needs:
- the Stage65 seat layer on every bank row;
- nested 50/80/90 intervals;
- effective-sample Monte Carlo errors;
- the remaining v2 fields.

**Answer.** Yes. A complete 71-seat synthetic bank produced by the Python engine becomes a valid synthetic v2 snapshot. A bank with any unavailable seat withholds the seat layer and MMP with a reason. The live bank is still blocked upstream (Stage73); nothing is published. Pre-approved by James on 2026-10-07 to follow Stage73 as a separate PR.

## What it adds

| Piece | Where | Behaviour |
|---|---|---|
| Bank schema 2 (Python) | `scripts/nowcast_assembly/` | Each simulated seat carries `candidateParty`, per-candidate mean and 50/80/90 share intervals (`summaries.py`), and per-row winner candidates (Māori too, with poll-derived candidate keys). The bank carries the export `directory`: national groups with registered names and the `national.display` abbreviations, the 71 electorates, and the simulated seats' candidates. A candidate whose party has no national group has `partyId` null and keeps its ballot-group key in `partyLabel`, so no national share is invented for it. |
| Bank reader | `src/models/nowcast/drawBank.ts` | zod schema with these checks: one distinct draw id per row; party-vote rows are simplexes; one winner per row per simulated seat; winners are the seat's own candidates; class matches scope; unavailable seats need a reason. |
| Effective-sample MCSE | `src/models/nowcast/batchMeans.ts` | Rows are put back in national MCMC chain order and cut into about sqrt(n) non-overlapping batches of equal size. The batch-means long-run variance gives the MCSE and ESS (spec §2: never `sqrt(p(1-p)/n)` for national-driven quantities). |
| Seat layer and snapshot | `src/models/nowcast/fromBank.ts` | Runs the Stage65 `allocateDraw` (Stage49 allocator unchanged) on every row, with Other as an unlisted bucket and the bank's 64 + 7 expected electorates. It exports party, bloc and Parliament-size 50/80/90 seat intervals and probabilities with MCSE/ESS. Per seat it exports the D107 uncertainty class, candidate-share intervals and win probabilities with MCSE. The national 50/80/90 party-vote intervals are also included. |
| Export v2 completion | `src/types/export.ts` | Adds `seatLayer` (`available` with the summary, or `unavailable` with a reason) and `electorateDetail`, which a **model** snapshot must give for every predicted seat. An available seat layer requires an MMP example and no unavailable electorate. The placeholder-rules guard now also covers the seat layer. The directory gains optional `partyLabel`. |
| Stage65 summaries | `src/models/mmp/seatLayer.ts` | `SeatQuantiles` gains `q10`/`q90`, the 80% interval. |
| Synthetic contract fixture | `data/fixtures/synthetic/nowcast-draw-bank.json`, `scripts/nowcast_assembly/fixture.py` | The real Stage73 engine on the live national draws and baseline, with invented slates, classification and Māori winners (32 rows). It is labelled `synthetic-fixture` and read only by tests. |

## Rules carried into the export

- **Missing inputs:** any unavailable seat withholds `seatLayer` and `mmp` with the count, never zeros. Missing MMP rules or blocs withhold them too.
- **Synthetic data:** a synthetic bank can only produce a `synthetic-` snapshot; a live bank with synthetic ids fails.
- **Calibration label:** every probability is `uncalibrated` (spec §6 and the release policy proposal).
- **Superseded fields:** `governmentOutcomes` stays empty. Fixed-`requiredSeats` combinations are replaced by Stage65 blocs, which James defines (`mmp.blocs` pending).

## Limits and not done

- **Not done:**
  - no live snapshot;
  - no Node production runner (a published snapshot is a release decision);
  - no UI for the new fields;
  - no bloc definitions;
  - no MMP rules-version identifier;
  - no precision thresholds (Stage63).
- **MCSE batches.** Batch means need enough rows per chain. At the 32-row fixture size the errors are rough. At production sizes (thousands of rows over 4 chains) about sqrt(n) batches is standard.
- **Māori candidates** use poll-derived keys (`<electorateId>-poll-candidate-<name key>`) until Stage50 roster ids exist. (Stage80 replaced them with the official roster ids for all seven seats.)
- **Minor-party candidates** inside Other show `partyId` null with `partyLabel`. A display mapping is a UI question.

## Reproduction

```
python3 -m scripts.nowcast_assembly.fixture --check
python3 -m scripts.nowcast_assembly.run --check
python3 -m unittest scripts.tests.test_stage73_nowcast_assembly scripts.tests.test_stage74_nowcast_snapshot
npm run test && npm run typecheck && npm run build && npm run check:dist
```
