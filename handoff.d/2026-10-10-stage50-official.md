<!-- fold: changelog -->
## Stage50 part 2 — official 2026 nominations applied to the live roster, 2026-10-10

- **Preserved:** the Electoral Commission's official electorate-candidate spreadsheet (469 candidates) and party-list PDF, supplied unchanged by James, under `data/raw/nominations/2026-10-10/`. Registered with checksums in the new standalone `data/processed/nominations-2026/source-registry.json`; `data/sources.json` is not touched.
- **Transcribed** by `scripts/nominations_2026/extract.py` (standard library only):
  - `official-table.json`: 469 rows, 71 electorates;
  - `party-lists.json`: the 17 party headings, exactly the registered parties.
- **Affiliations:**
  - one new alias (`Alliance Party`);
  - 11 unregistered printed affiliations (17 candidates), listed explicitly, which get no ballot group, like independents.
- **Refreshed outputs:**
  - roster snapshot `data/processed/forecast-readiness/snapshots/2026-10-10/` (71 official complete slates);
  - Stage42 features and their Stage75 recentring, plus the reconciliation, under `data/processed/nominations-2026/2026-10-10/`.
- **Config** (2026-10-10.1): the roster now points at the official list. `roster.snapshotId` is no longer pending; `apply_config` edits only those values.
- **Validator:** a non-null roster's files must exist, and a null roster must be pending.
- **Classification draft:** rechecked. Christchurch Central and Wigram are added as candidate changes, and the Epsom fact is corrected.
- **Regenerated:** the development gate and the rehearsal report (config version only).

<!-- fold: state -->
# Stage50 part 2 official nominations — review-ready, 2026-10-10

Branch `stage/50-official-nominations` from main `2287e57` (after #101). James supplied the official files on 2026-10-10 NZDT under the Stage50 authorization of 2026-10-07; this was the procedure's part 2. The acquisition checkpoint was committed before any transformation (`01948a3`).

**Results.**
- **Roster:** 469 official nominations; 71 of 71 seats are official complete slates; no conflicts and no unmatched claims; 64 general slates for the assembly.
- **Reconciliation against the 2026-10-05 announcements:**
  - 179 of 206 match exactly;
  - the other 27 are the same people under official spellings (checked pair by pair);
  - 290 candidates are new.
- **Identity links:** none lost under the official spellings, one gained (Menéndez March).
- **Development gate:** accepts the live roster. It is still unpublishable on two counts: the classification (James) and `maori.unpolledFallbackModel` (D114).
- **Not changed:**
  - any model, scale or fit;
  - the 2026-10-05 snapshot;
  - frozen Stage40/42 outputs;
  - `data/sources.json`.

**Checks.** See the PR body for exact counts.

**Limits.**
- The exact download URLs were not recorded (elections.nz blocks automated retrieval); the registry records the publishing host.
- Claims are dated by the spreadsheet's embedded modification time.
- Māori-seat candidates are not yet mapped to the Māori layer's poll-derived keys.

**Exact next action.**
1. James enters the 64-seat classification. The rechecked draft is `docs/general-seat-classification-2026-draft.md`: core 15 exceptional, a 9-seat boundary block for James, the rest ordinary.
2. A separately authorized bounded stage defines the no-poll fallback for the four unpolled Māori seats.
3. Then the first real run: `scripts.nowcast_assembly.run --require-complete`, then `npm run release:publish`.

<!-- fold: sources -->
### Official 2026 nominations (Stage50 part 2, preserved 2026-10-10)

The Electoral Commission's official 2026 electorate candidates (`Electorate-Candidates-2026.xlsx`, 469 rows) and party lists (`Party-lists-for-the-2026-General-Election.pdf`, 17 parties) were supplied unchanged by James after nominations closed (12:00 NZDT, 8 October 2026).
- Preserved under `data/raw/nominations/2026-10-10/` and registered in `data/processed/nominations-2026/source-registry.json`, with SHA-256 checksums and embedded file timestamps.
- The exact download URLs were not recorded, because elections.nz blocks automated retrieval; the registry records the publishing host and states this limitation.
- Publisher copyright; preserved for evidence; no licence assumed.

<!-- fold: roadmap -->
| Stage50 | Nomination snapshot, immutable raw acquisition (item 3) | part 1 merged; part 2 review-ready: official list preserved and applied (469 candidates, 71/71 official complete slates, config roster set) |
