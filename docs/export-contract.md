# Stage53 — website export contract and end-to-end dry run (v1, draft)

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
| `calibrationStatus` | `uncalibrated` or `validated`. The site states uncalibrated output as such. What the site may show, and the gate for it, is the still-open probability-release policy (roadmap); the contract only carries the status. |
| `directory` | Names for parties, electorates, candidates, so pages need no other lookup. |
| `national` | Party vote-share intervals plus a basis note. |
| `simulation` | `SimulationResult`: seed, PRNG, draws, input hashes, code revision, electorate winner frequencies, party seat intervals, government-combination probabilities, limitations. Must contain every requested draw. |
| `unavailableElectorates` | Every directory electorate has exactly one prediction or one explicit reason. Missing is never zero (for example Māori seats have no candidate model yet). |
| `mmp` | `available` (one draw's allocation, to show seat accounting, explicitly not a forecast) or `unavailable` with a reason. |
| `boundaries` | Optional reference (path, sha256) to an `ElectorateGeometrySchema` GeoJSON FeatureCollection keyed by `properties.electorateId`. |
| `limitations` | At least one. |

Cross-checks reject unknown parties/candidates, duplicate ids, election mismatches, out-of-range shares and placeholder MMP rules in model snapshots.

## Archive and loading

Layout under `<base>/forecasts/`: `index.json` and `<snapshotId>/snapshot.json` (and optionally a GeoJSON file). `ForecastIndexSchema` is append-only and ordered: each entry has the snapshot's SHA-256, `supersedes`, and `published`/`withdrawn` (withdrawal needs a reason). Snapshot files are never edited; a correction is a new entry that supersedes the old one. Files are written by `canonicalJson` (sorted keys, fixed indent) via `addToArchive`, so the same run gives identical bytes.

`src/data/loader.ts` `loadLatestSnapshot`: validate index → pick the latest published entry that is neither withdrawn nor superseded (supersession is permanent) → verify the file hash → validate the snapshot → check it agrees with its index entry. Any failure returns `unavailable` with a reason; the site then shows "No forecast published" and never renders partial data. `allowSynthetic` is `import.meta.env.DEV` only.

## Synthetic fixtures and the leak guard

`data/fixtures/synthetic/` holds invented parties, polls, electorates, candidates and unit-square geometry (README there). `src/dev/syntheticSnapshot.ts` runs the whole chain in memory; the dev site shows it under a SYNTHETIC banner, the production site never does. Guards:

1. `src/dev` is imported only behind `if (import.meta.env.DEV)`; a test checks that structure, that fixtures are imported only from `src/dev` and tests, and that `public/` has no synthetic names or markers.
2. `npm run build && npm run check:dist` (`scripts/validate/no_synthetic_in_dist.mjs`) scans the built bundle for fixture markers. It was verified to fail on a `NODE_ENV=development` build and pass on the production build.
3. Loader tests check synthetic snapshots are refused when `allowSynthetic` is false.

`check:dist` is not yet in `ci.yml` (owned by the CI-scoping stage); until it is, run it after `npm run build`.

## Not done here

A Python exporter that fills the contract from Stage41–47 artifacts; real national, local, candidate or MMP components; current-cycle polls; Māori layer; reconciliation; the probability-release policy; publication to `public/forecasts/`. Whether named-electorate winner probabilities are part of the minimum publishable product is undecided, so the contract keeps them as ordinary optional-by-explicit-unavailability data. No D-number is assigned to the contract; assign one if it should be a recorded decision.
