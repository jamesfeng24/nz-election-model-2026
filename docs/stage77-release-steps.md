# Stage77: release steps (production runner, gate completion, precision setting, rehearsal)

**Question.** Is the release path complete and proven end to end before the first real run? That means:
- a production runner from the draw bank to the public archive;
- the remaining publication-gate checks;
- the Stage63 precision setting;
- a full-size rehearsal on the live engine.

**Answer.** Yes. A production-size rehearsal took 4,096 national draws × 16 layer replicates (65,536 simulated elections), produced a bank for all 71 seats, and published it through the release gate into a non-public archive the site loader reads. Every probability's Monte Carlo SE was ≤ 0.0051, within the proposed 0.01 limit. The real release stays blocked by its gate until James's decisions and the official roster are in.

Authorized by James on 2026-10-07. The coordinator's notes are applied:
- precision from Stage63 #91 (M = 16);
- the config file is shared with Stage70, so main is merged before pushing;
- the rehearsal says which inputs are stand-ins;
- stand-ins are labelled synthetic and kept out of the public archive;
- the decision number is the next free one on main (D113).

## What it adds

| Piece | Where | Behaviour |
|---|---|---|
| Precision setting | `config/nowcast-2026.json` `simulation` | 4,096 national draws × 16 layer replicates = 65,536 rows. The precision wording is from Stage63 (#91, D095): replicates control layer error; national-driven quantities keep the national-bank floor and use effective-sample MCSE. `simulation.draws` and `precisionPolicy` are no longer pending. |
| Layer replication | `assemble(..., replicates=M)` | Row r uses national draw ⌊r/M⌋ with independent layer noise. The frozen solver's exact-row reuse solves each local-party conditional location once per national draw (the Stage63 reuse) with no code change. Māori draws are per row. |
| Grouped noise banks | `scripts/nowcast_assembly/streams.py` | Shared keys use one scrambled Sobol bank common to all seats; each seat layer's own keys use their own bank, generated on demand. Memory stays bounded at 65,536 rows instead of one roughly 1.5 GB joint bank. Seeds derive from `simulation.seedNamespace`. |
| Bank schema 3 | Python and `src/models/nowcast/drawBank.ts` | Winners are per-row candidate indices, not names, so a production bank is about 10 MB. The bank carries `nationalDraws` and `layerReplicates`, and party votes per national draw. Batch-means MCSE keeps each draw's replicates in one batch (`chainOrder(ids, M)`, batch size a multiple of M). |
| Gate completion (Python) | `assemble.gate`, `assemble.staleness` | New check `nationalReconciliation` (maximum general-seat local-vs-national gap ≤ `release.reconciliationTolerancePP`). Staleness labels (national state older than `release.staleDays.nationalState`; Māori poll fieldwork older than `release.staleDays.maoriPoll`) go into the snapshot's limitations: stale inputs are labelled, never dropped or filled. The production path needs `--as-of`. |
| Release gate (TypeScript) | `src/release/releaseGate.ts` | Model provenance only (rehearsals excepted). Also requires: a nowcast; `uncalibrated` labels; no unavailable electorate; an available seat layer and MMP; detail for every predicted seat; and every published probability's MCSE ≤ `release.probabilityMcseMax`. |
| Publisher | `src/release/publish.ts`, `src/release/cli.ts` | Bank → v2 snapshot (with the staleness labels) → gate → append-only archive (`addToArchive`). Writes nothing on any failure, refuses an id already archived, and supports `--supersedes`. A model release goes only to `public/forecasts`; a rehearsal never goes under `public/`. Built by `npm run release:build` and run by `npm run release:publish -- --bank … --options … --archive …`. Not part of the site bundle. |
| Rehearsal | `scripts/release_rehearsal/run.py` | The full live chain at production settings, labelled synthetic. Writes the bank and options to the gitignored `.release-build/rehearsal/` and a deterministic report to `data/processed/release-rehearsal/report.json`. |
| Release settings | `config/nowcast-2026.json` `release` | Reconciliation tolerance 1.0pp, staleness windows 14/60 days and MCSE limit 0.01 are proposals. They take effect only when James approves the release policy (`release.policyApprovedBy`, now in `pending`, so the gate fails closed until then). |

## Rehearsal (7 October 2026)

**Real inputs:**
- the Stage70 2026-10-07 national refresh (`lastDataSupport`, week of 27 September, polls to 7 October), applied in memory: adoption into the config is the coordinator's separate step;
- the Stage64 population-flat baseline;
- the Stage72 scales and D107 multipliers;
- the Stage75 candidate fit;
- the Stage66 Māori layer for the three polled seats;
- the 2026 frame.

**Labelled synthetic stand-ins:**
- the official candidate list: Stage50's in-memory stand-in, the announcements plus invented Labour and independent candidates;
- the classification: every eighth general seat exceptional, not a judgement;
- winners for the four unpolled Māori seats;
- the MMP rules label (placeholder) and blocs (none).

**Not available:** the Stage69 voting-place baseline (not on main).

**Results:**
- 65,536 rows; 71 of 71 seats simulated.
- Python gate: every structural check passes, including `nationalReconciliation` (maximum gap 0.373pp against 1.0pp). It fails only `configComplete` (pending: Māori unpolled seats, blocs, rules version, release-policy approval) and `provenanceLive` (synthetic), as it should. No staleness labels at 7 October.
- Bank 10.4 MB; digest `a7152860ab2b4359…`.
- TypeScript release (rehearsal mode, MCSE limit 0.01): published to `.release-build/rehearsal/archive/` and read back by the site loader. The snapshot is 0.63 MB with 378 published probabilities.
  - The largest MCSE is 0.0051: Opportunity qualifying by party vote, a national-driven quantity with ESS about 2,900, near the national-bank floor.
  - Among probabilities between 0.05 and 0.95, the minimum ESS is about 2,900 and the median is above the row count. Seat outcomes from scrambled quasi-random layer noise can be negatively correlated within a batch, so batch means can show ESS > n.
- Runtime: 31 minutes on 4 cores (about 118 CPU minutes) for the whole chain at production size, including the Stage76 speed-up; publishing takes 7 seconds.

No rehearsal figure describes 2026 seat outcomes: the candidates, classification and four Māori seats are invented.

## Limits and not done

- No real release: it waits on the official roster (Stage50 part 2), James's classification, unpolled-Māori, bloc, rules-version and release-policy decisions, and the Stage69 baseline.
- No UI for the new export fields.
- No adoption of the Stage70 refresh into the config (the coordinator's step).
- The release settings are proposals.
- `python3 -m scripts.release_rehearsal.run --check` reproduces the report but takes about 30 minutes on 4 cores, so it is run locally, not in CI.

## Reproduction

```
python3 -m scripts.release_rehearsal.run            # about 30 minutes on 4 cores
npm run release:build
npm run release:publish -- --bank .release-build/rehearsal/bank.json --options .release-build/rehearsal/options.json --archive .release-build/rehearsal/archive --rehearsal
python3 -m unittest scripts.tests.test_stage77_release
npm run test
```

Production, once the gate can pass:

```
python3 -m scripts.nowcast_assembly.run --require-complete --bank BANK.json --as-of YYYY-MM-DD
npm run release:publish -- --bank BANK.json --options OPTIONS.json --archive public/forecasts
```
