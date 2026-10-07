# Stage53 — website export contract and end-to-end dry run (v1, draft)

## v2 (6 October 2026, D106): nowcast semantics

The primary product is a nowcast ([nowcast-specification.md](nowcast-specification.md)). Snapshot `schemaVersion` is now **2**. Loaders reject v1, which never reached a published release; only the synthetic dry run produced it. Changes:

- `targetType`: `nowcast` (primary) or `election-day-scenario`, which may only ever be a separately labelled output.
- `modelStateAsOf` (date): the latent national state the results describe, i.e. the latest poll-midpoint week, not "today". The schema requires `modelStateAsOf` ≤ `dataCutoff` ≤ `createdAt`.
- `electionDate` (date): context only. A nowcast state may not postdate it.
- **Intervals:** every national vote share (`partyVoteShares[].share`) and party seat summary (`partySeatSummaries[].seats`) is a set of exactly three central intervals at levels 0.5, 0.8 and 0.9, in that order, sharing one median and nested (`IntervalSetSchema`, `INTERVAL_LEVELS`, `PRIMARY_INTERVAL_LEVEL = 0.8` in `src/types/domain.ts`). The 80% range is the primary display. Every range is shown as full lower–upper bounds, never as a ± half-width, and is described as a central range across simulated elections under current conditions, not a margin of error or an election-day range.
- `provenance.configVersion` is required for model snapshots.

Unchanged: the archive layout and index (`ForecastIndexSchema`, still v1), the synthetic guards, and the `Forecast*` identifiers and `forecasts/` root, which are kept as stable names. Still to add in the assembly PR ([release-checklist.md](release-checklist.md)), because they depend on Stage63 and the live layers:
- candidate-share intervals;
- Monte Carlo SE and effective sample size;
- threshold, overhang, size and bloc distributions from Stage65;
- per-seat uncertainty class;
- per-component calibration status;
- replacing the fixed-`requiredSeats` government combinations with Stage65 dynamic-majority blocs.

### v2 completion (7 October 2026, Stage74)

Added before any v2 snapshot was published, so `schemaVersion` stays 2 ([stage74-nowcast-snapshot.md](stage74-nowcast-snapshot.md)):
- `seatLayer`: `available` with the Stage65 summary over every simulated election, or `unavailable` with a reason. The summary holds:
  - party, bloc and Parliament-size 50/80/90 seat intervals;
  - seat and size distributions;
  - qualification, lifeboat, overhang, majority and exact-half probabilities, each `{p, mcse, ess}` by batch means within national MCMC chains.

  An available seat layer requires an MMP example allocation and no unavailable electorate.
- `electorateDetail`: per predicted seat, the uncertainty class (`ordinary`, `exceptional` or `maori-layer`, D107) and per-candidate `meanShare`, 50/80/90 share intervals and `winProbability {p, mcse, ess}`. A model snapshot must give it for every predicted seat.
- `directory.candidates[].partyLabel` (optional): the ballot-group key of a candidate whose party has no national group (`partyId` null).
- `governmentOutcomes` stays empty for nowcasts. Blocs live in `seatLayer.summary.blocs`, defined by James.
- `seatLayer.summary.scenarios` (Stage77): named seat-arithmetic outcomes over the configured blocs, each `{id, label, definition, probability {p, mcse, ess}}`. James's configuration (`config/nowcast-2026.json` `mmp.hungParliament`) gives three:
  - `hung`: neither NAT+ACT+NZF nor LAB+GRN+TPM has a majority;
  - `hung-opportunity-kingmaker`: hung, and TOP's seats give either side a majority;
  - `hung-opportunity-nat-act-nzf-only` and `hung-opportunity-lab-grn-tpm-only`: hung, and TOP's seats give only that side a majority.

  Hung with neither side reaching a majority even with TOP is the remainder of `hung`, not a separate output (James).

  These are scenarios of seat arithmetic, not predictions of coalition agreements.

Calibration labels were dropped by James's release-policy decision (D114, 2026-10-07): `calibrationStatus` is no longer in the v2 contract. Precision thresholds are set (MCSE ≤ 0.01).

The v1 text below is the original Stage53 record.

Authorized by the roadmap ([D082](../DECISIONS.md), item (d)). One question: can a single versioned export contract carry a forecast from polls through MMP to the website, with synthetic data kept out of real results? This fixes the boundary only. It fits nothing, changes no Python or statistical output, and produces no forecast. Everything run through it so far is invented.

## Chain and interfaces

`polls → national draws → local party shares → candidate shares → MMP allocation → aggregate → snapshot → archive → loader → site`

Each arrow is a TypeScript interface in `src/models/simulation/pipeline.ts` (`NationalStage`, `LocalPartyStage`, `CandidateStage`, `MmpStage`), DOM-free and JSON-serialisable. Draws use an independent seeded stream per draw index (`prng.ts`, sfc32 seeded by xmur3, name/version recorded), so results do not depend on how draws are chunked. `worker.ts` holds the message handler (request id, progress, one result or error); `simulation.worker.ts` is the thin entry; `createRunTracker` drops stale responses. The UI owns cancellation by terminating the worker.

Real components replace the synthetic stages in `syntheticStages.ts` by implementing the same interfaces. **MMP:** `src/models/mmp` belongs to the MMP-rules stage and was not touched; `MmpStage` is the interface it should satisfy (or be adapted to). Until then the placeholder allocator is labelled `UNVERIFIED-PLACEHOLDER-synthetic-only`, is not the New Zealand rules, and the contract forbids that rules version in a non-synthetic snapshot.

## Snapshot (`src/types/export.ts`, `ForecastSnapshotSchema`)

One immutable JSON file per run. It composes the existing draft types (`SimulationResult`, `SeatPrediction`, `MmpAllocation`, `Interval`) rather than redefining them.

| Field | Meaning |
|---|---|
| `schemaVersion` | `1`. A breaking change bumps it; loaders reject unknown versions. |
| `snapshotId`, `createdAt`, `dataCutoff` | Identity and dates. Ids are `synthetic-…` exactly when synthetic. |
| `provenance` | `synthetic-fixture` (with label) or `model` (model version, code revision). |
| `directory` | Names for parties, electorates, candidates, so pages need no other lookup. |
| `national` | Party vote-share intervals plus a basis note. |
| `simulation` | `SimulationResult`: seed, PRNG, draws, input hashes, code revision, electorate winner frequencies, party seat intervals, government-combination probabilities, limitations. Must contain every requested draw. |
| `unavailableElectorates` | Every directory electorate has exactly one prediction or one explicit reason. Missing is never zero (for example Māori seats have no candidate model yet). |
| `mmp` | `available` (one draw's allocation, to show seat accounting, explicitly not a forecast) or `unavailable` with a reason. |
| `boundaries` | Optional reference (path, sha256) to an `ElectorateGeometrySchema` GeoJSON FeatureCollection keyed by `properties.electorateId`. |
| `limitations` | At least one. |

Cross-checks reject unknown parties/candidates, duplicate ids, election mismatches, out-of-range shares and placeholder MMP rules in model snapshots. They also require a national vote-share interval for every party in the directory (a missing share is a failure, never a blank or zero), and reject any `synthetic-…` party, electorate, candidate or election id in a non-synthetic snapshot, whatever its snapshot id or provenance claims.

## Archive and loading

Layout under `<base>/forecasts/`: `index.json` and `<snapshotId>/snapshot.json` (and optionally a GeoJSON file). `ForecastIndexSchema` is append-only and ordered: each entry has the snapshot's SHA-256, `supersedes`, and `published`/`withdrawn` (withdrawal needs a reason). Snapshot files are never edited; a correction is a new entry that supersedes the old one. Files are written by `canonicalJson` (sorted keys, fixed indent) via `addToArchive`, so the same run gives identical bytes.

`src/data/loader.ts` `loadLatestSnapshot`: validate index → pick the latest published entry that is neither withdrawn nor superseded (supersession is permanent) → verify the file hash → validate the snapshot → check it agrees with its index entry. Any failure returns `unavailable` with a reason; the site then shows "No forecast published" and never renders partial data. `allowSynthetic` is `import.meta.env.DEV` only.

## Synthetic fixtures and the leak guard

`data/fixtures/synthetic/` holds invented parties, polls, electorates, candidates and unit-square geometry (README there). `src/dev/syntheticSnapshot.ts` runs the whole chain in memory; the dev site shows it under a SYNTHETIC banner, the production site never does. Guards:

1. `src/dev` is imported only behind `if (import.meta.env.DEV)`; a test checks that structure, that fixtures are imported only from `src/dev` and tests, and that `public/` has no synthetic names or markers.
2. `npm run build && npm run check:dist` (`scripts/validate/no_synthetic_in_dist.mjs`) scans the built bundle for fixture markers. It was verified to fail on a `NODE_ENV=development` build and pass on the production build.
3. Loader tests check synthetic snapshots are refused when `allowSynthetic` is false.

`check:dist` runs in the `check` job of `ci.yml` (the step is guarded so it is skipped only if the script is undefined). It passed in the hosted Verify run 37397768440 on main after #57 merged.

## Not done here

A Python exporter that fills the contract from Stage41–47 artifacts; real national, local, candidate or MMP components; current-cycle polls; Māori layer; reconciliation; the probability-release policy; publication to `public/forecasts/`. Whether named-electorate winner probabilities are part of the minimum publishable product is undecided, so the contract keeps them as ordinary optional-by-explicit-unavailability data. No D-number is assigned to the contract; assign one if it should be a recorded decision.
