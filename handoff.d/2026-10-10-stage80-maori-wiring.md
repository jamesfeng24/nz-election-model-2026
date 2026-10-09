<!-- fold: changelog -->
## Stage80 — Māori fallback wired into the nowcast assembly, 2026-10-10

- **What:** `maori.unpolledFallbackModel = stage78-f` (Stage78 arm F, James's choice of 2026-10-09) is registered in `config/nowcast-2026.json` (`configVersion` 2026-10-10.2, pending list empty, decisions D115 and D118). The assembly (`scripts/nowcast_assembly/maori.py`) simulates the four unpolled seats with Stage78's own draws (`scripts/maori_seat_fallback/draws.py`, seeded from the configured namespace) and gives all seven Māori seats the official roster candidate ids, names and ballot groups; fallback seats carry the export label `Stage78 no-poll fallback: 2023 result carried forward, no seat poll (D115)`.
- **Result:** the live development gate now has one blocker, the 64 general seats awaiting James's D107 classification; all seven Māori seats are simulated. The Stage77 rehearsal no longer uses invented winners for the unpolled seats.
- **Not touched:** Stage66/71/78 code and outputs, the pinned seat-poll file (the Waiariki poll stays recorded, not adopted), TypeScript, `data/sources.json`. 17 new tests plus updated Stage72/73/77 assertions.

<!-- fold: state -->
# Stage80 Māori fallback wiring — review-ready, 2026-10-10

Branch `claude/project-thread-0lxx4d` restarted from main `b0fc604` (PR #103 merged). Authorized by the coordinator as the planned next step after Stage78 (release-checklist item 15).

**State.** All seven Māori seats are simulated in the live development gate; the only remaining blocker is the D107 classification of the 64 general seats (`config/general-seat-classification-2026.json`, James). Fallback win probabilities at 4,096 draws match Stage78 arm F within Monte Carlo error (Waiariki Waititi 0.96; Ikaroa-Rāwhiti Tangaere-Manuel 0.65; Tāmaki Makaurau 0.50 / 0.50; Te Tai Tokerau Prime 0.66, Edwards 0.20, Kapa-Kingi 0.13). With the Stage78 seed and 100,000 draws the stored arm F is reproduced exactly (tested).

**Limits.** The fallback block is independent of the polled block; the Stage78 limits stand; the new Waiariki poll is recorded but not adopted (one later combined update, James 2026-10-09).

**Exact next action.**
1. James enters the D107 classification (PR for the draft); then the first real run (`npm run release:build`).
2. Separately authorized: one update that adopts the new Māori seat polls (Waiariki and any others) into the pinned seat-poll file and regenerates Stage66, Stage71, Stage78 and the assembly outputs.

<!-- fold: decisions -->
## D118 — 2026-10-10 — register and wire the Stage78 fallback (Stage80)

- **Decision.** `maori.unpolledFallbackModel` is `stage78-f`: the four seats without a seat poll use Stage78 arm F (2023 result carried forward by party label, no polled-seat swing; James, 2026-10-09). The validator accepts only that value or a pending null. All seven Māori seats carry the official roster candidate ids; the fallback seats carry a labelled export source.
- **Consequences.** The fallback block is independent of the polled block and of the national draw (a stated default; coupling needs a stated correlation). New seat polls are adopted only in one combined later update, not seat by seat.
- Number D118 was assigned by the coordinator; D115 is Stage78.

<!-- fold: roadmap -->
| Stage80 | Register the Stage78 fallback and wire it into the assembly; official Māori candidate ids for all seven seats (internal) | review-ready (D118): live gate's only blocker is the D107 classification |
