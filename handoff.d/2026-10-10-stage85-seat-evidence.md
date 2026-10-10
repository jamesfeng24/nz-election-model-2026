<!-- fold: changelog -->
## Stage85 — per-seat evidence block in the export, 2026-10-10

- The draw bank and the snapshot gain an optional `seatEvidence` array: per predicted seat, the D107 class and multipliers, the 2023 party-vote baseline by national group, the 2026 polls found (used with `shareOfPoll` and `weight`, or unused with a reason) and the National/Labour poll update. Display data for the site's seat pages. Snapshot schema 2 and bank schema 3 are unchanged in version (the field is optional).
- No forecast number changes: `bank_digest` leaves the block out, the development gate reproduces, and a live bank built on main and on this branch is identical once the block is removed. The synthetic fixture was regenerated and differs only by the added key.
- `scripts/seat_polls/live.py` gains `combine()` (the `inputs()` result plus per-poll detail); new `scripts/nowcast_assembly/evidence.py`; `src/types/export.ts`, `drawBank.ts`, `fromBank.ts`. No site code, config, data or registry change.

<!-- fold: state -->
# Stage85 per-seat evidence export — review-ready, 2026-10-10

Branch `claude/stage85-seat-evidence-export-djpg5v`, from main `50cb5e8` (after #113). Authorized by James on 2026-10-10 (the coordinator's brief, "yeah go ahead"); decision number D124 (coordinator, provisional until main is checked).

**What changed.** The optional `seatEvidence` block (bank and snapshot; see `docs/stage85-seat-evidence.md` for the shape the site may rely on), `live.combine()`, `evidence.py`, the TypeScript schemas, the regenerated synthetic fixture, `docs/stage85-seat-evidence.md`, `docs/export-contract.md`, 9 Python and 3 TypeScript tests. **What did not.** Every simulated number, the configuration, the development gate, the Māori layer and its inputs (the Māori poll switch-over, Stage86, is a separate thread), `data/sources.json`, the site.

**Counts.** 71 records per bank (64 general, 7 Māori). On the current cutoff five general seats have a used poll (Hutt South, Kāpiti, Mt Albert, Waitaki, West Coast-Tasman; Mt Albert's two Curia polls merge into one source); Auckland Central and Wellington Bays list their Green-led polls as unused context; three Māori seats (Te Tai Tonga, Te Tai Hauāuru, Hauraki-Waikato) list their poll.

**Limits.** Display only; the release gate does not require the block. Per-poll `weight` is exact for the updated balance centre, not for win probabilities. The Māori poll list reads the pinned Māori poll file through `current_polls()`; when Stage86 changes that source, `evidence.maori_polls` is the one function to adapt.

**Exact next action.** The coordinator reviews and merges. Then the site (#108) can read `seatEvidence` for its "polls we used" section. Not started: any site change.

<!-- fold: decisions -->
## D124 — 2026-10-10 — Stage85: per-seat evidence is an optional export block derived after simulation, outside the bank digest

The export carries an optional `seatEvidence` array (per seat: class and multipliers, the 2023 party-vote baseline, polls with the share each took of the combined poll and the weight each had on the updated balance, and the poll update). It is display data computed after the seats are simulated; nothing reads it back, and `bank_digest` excludes it so no existing digest or committed simulated output changes. The schema versions stay (the field is optional). A block, when given, must cover every predicted seat and satisfy the weight identities; the release gate does not require it.

<!-- fold: methodology -->
## Per-seat poll weights (Stage85, D124)

For a general seat the Stage79 update is centre = mu + k (y - mu) with k = rho x w, where y is the share-weighted mean of the seat's used polls (sources combined by inverse variance with an age discount relative to the freshest source; later same-source polls at 1.5 times the variance). Poll i therefore moves the centre by `weight` = k x share_i x (y_i - mu), the weights sum to k, and the model keeps 1 - k. This is an exact decomposition of the balance centre, not of the win probability or of the posterior spread.

<!-- fold: roadmap -->
| Stage85 | Per-seat evidence block in the export (polls used and their weights, baseline, class; display data, no forecast change; D124) | review-ready |
