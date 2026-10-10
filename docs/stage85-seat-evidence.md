# Stage85: per-seat evidence block in the export

**Question.** Can the export say, for each seat, which polls went into it, how much each counted, where the seat started and which uncertainty class it is in, without changing any forecast number?

**Answer.** Yes. The draw bank and the snapshot gain an optional `seatEvidence` array (display data for the site's seat pages). Authorized by James on 2026-10-10 (the coordinator's brief; decision D124). Snapshot `schemaVersion` stays 2 and bank `schemaVersion` stays 3: the field is optional, so earlier banks and snapshots still load.

## No forecast number changes

- Evidence is computed after the seats are simulated, from inputs the simulation already used. Nothing reads it back.
- `assemble.bank_digest` leaves `seatEvidence` out (as it does `diagnostics`), so every existing bank digest, including the one in `data/processed/nowcast-assembly/development-gate.json`, is unchanged.
- Proof: a live bank at 64 national draws x 2 layer replicates built on main `50cb5e8` and on this branch is byte-identical once `seatEvidence` is removed; `python3 -m scripts.nowcast_assembly.run --check` reproduces the committed development gate; the regenerated synthetic fixture differs from the committed one only by the added key (`scripts/tests/test_stage85_seat_evidence.py` pins the digest rule).

## Shape (what the site may rely on)

`seatEvidence[]`, one record per predicted seat, covering exactly the predicted electorates once each (the snapshot schema enforces it; a bank or snapshot may omit the whole array):

| Field | Meaning |
|---|---|
| `electorateId`, `uncertaintyClass` | The seat and its D107 class (`ordinary`, `exceptional`, `maori-layer`); equals `electorateDetail`'s class. |
| `multipliers` | General seats: `{balance, within, mass}`, the class multipliers actually applied (D107, D121). `null` for Māori seats. |
| `baseline` | General seats: `{basis, partyVote: [{partyId, share}]}`, the 2023 party vote on the 2026 boundaries (Stage69 voting-place notionals) by national group, summing to 1; groups outside the core parties are in `other`. `null` for Māori seats. |
| `pollUpdate` | General seats with a used poll, else `null`. Balances are log(National / Labour): `modelBalance` before the poll, `pollBalance` the combined poll, `updatedBalance` after. `ageWeeks`, `ageFactor` (rho), `pollWeight` (w, capped), `effectiveWeight` (k = rho x w), `modelWeight` (1 - k), `modelSD`, `posteriorSD`. |
| `polls[]` | Every 2026 poll found for the seat. `pollId`, `pollster`, `sponsorGroup`, `fieldworkStart`/`End`, `sampleSize` (+ `sampleSizeAssumed`), `candidateVotePct` (`[{party, pct, name?}]`, the poll's own labels), `approximate` (parties whose figure was published as approximate), `evidenceGrade`, `status` (`used` or `not-used`), `reason` (exactly the unused ones), `shareOfPoll`, `weight`. |

**What `weight` means.** The Stage79 update is linear in the combined poll: updated = model + k (poll - model). The combined poll is the share-weighted mean of the polls (sources by inverse variance, an age discount relative to the freshest source, later same-source polls at 1.5 times the variance), so poll i contributes `weight` = k x `shareOfPoll`, the weights sum to `effectiveWeight`, and the model keeps `modelWeight`. The schema checks these identities. A seat page can say "this poll moved the National/Labour balance by `weight` x (its value - the model's)".

**Unused polls** are listed as context with a plain reason: excluded, not a National-versus-Labour poll (for example Green-led Auckland Central and Wellington Bays), fieldwork after the data cutoff, superseded by a newer poll of the same pollster, or the seat has no National or no Labour candidate.

**Māori seats** (as they stand): the latest poll of the seat is the Stage66 layer's input (`status: used`, no `shareOfPoll`, no `weight`, no `pollUpdate`); earlier polls of the seat are `not-used` ("superseded"). Unpolled seats and the synthetic fixture have `polls: []`. The fallback model draws no poll.

## Where it lives

- `scripts/seat_polls/live.py`: `combine()` returns the unchanged `inputs()` result and the per-poll detail; `live_rows()` rows also carry `approximate` and `evidenceGrade` (extra keys, read by nothing else).
- `scripts/nowcast_assembly/evidence.py`, wired in `assemble.py`; the Māori part reads `current_polls()` and checks that the record's poll is the latest.
- `src/types/export.ts` (`SeatEvidenceSchema`, optional `seatEvidence` on the snapshot), `src/models/nowcast/drawBank.ts`, `src/models/nowcast/fromBank.ts` (copied through unchanged). No site code.
- `data/fixtures/synthetic/nowcast-draw-bank.json` regenerated: synthetic slates and classification, real 2026 polls, as before.

## Limits and not done

- Display data only; the release gate does not require it (a block, if given, must be complete).
- A Māori seat's poll list reads the pinned Māori poll file; the separate Māori poll switch-over (Stage86) will change that source, and `evidence.maori_polls` is the one place to adapt.
- No site change; the seat-page text is the site's.

## Reproduction

```
python3 -m scripts.nowcast_assembly.fixture --check
python3 -m scripts.nowcast_assembly.run --check
python3 -m unittest scripts.tests.test_stage85_seat_evidence scripts.tests.test_stage79_seat_polls scripts.tests.test_stage73_nowcast_assembly scripts.tests.test_stage74_nowcast_snapshot
npm run test && npm run typecheck && npm run build
```
