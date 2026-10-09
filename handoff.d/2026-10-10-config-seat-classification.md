<!-- fold: changelog -->
## Config: 2026 general-seat classification recorded, 2026-10-10

- Added `config/general-seat-classification-2026.json`: all 64 general seats classified (12 `exceptional`, 52 `ordinary`) in the D107 schema, author James, recordedAt 2026-10-10, a one-line reason per seat and sources on every exceptional seat. Release-checklist item 4 is done.
- Exceptional: Auckland Central, Epsom, Glendene, Kapiti, Mt Albert, Papakura, Port Waikato, Tāmaki, Wellington Bays, Wellington North, Whangārei, Wigram. 12 of 64 is 18.8%, against 14.8% flagged in the 2014–2023 audit (12.5%, 9.4%, 15.4%, 21.9% by election).
- `docs/general-seat-classification-2026-draft.md` is renamed `docs/general-seat-classification-2026.md` and now records the approved list, the rule applied to candidate changes, the close calls and the one bounded scandal check (nothing found touching a major-party general-seat candidate). New appendix `docs/general-seat-classification-2026-historical-flags.md` lists the 2014–2023 flags by year with the repository's evidence for each.
- Regenerated `data/processed/nowcast-assembly/development-gate.json`: with the classification present the live development gate now simulates all 64 general seats (67 of 71 seats simulated with the three polled Māori seats); the only blocker left is `maori.unpolledFallbackModel` for the four unpolled Māori seats. The gate stays unpublishable. No model input, scale or fit changed, and `config/nowcast-2026.json` is unchanged.
- Tests: the Stage73 live-gate test now expects the single Māori-fallback blocker; a new Stage72 test pins the recorded classification (valid, 64 seats, James, the 12 exceptional ids).
- Updated `docs/release-checklist.md` (item 4), `docs/nowcast-specification.md` §4 and the assembly row, and the path in the Stage50, Stage72 and Stage73 docs.

<!-- fold: decisions -->
## D116 — 2026-10-10 — 2026 ordinary/exceptional classification and the candidate-change rule (James; number provisional, D115 is held by the Stage78 PR)

James approved the 2026 classification of the 64 general seats under D107: 12 exceptional, 52 ordinary (`config/general-seat-classification-2026.json`, reasons in `docs/general-seat-classification-2026.md`).

- **Candidate-change rule.** A candidate change on its own does not make a seat exceptional, because the S+R model already counts it. It does only when the candidate being replaced, or the replacement, is uniquely strong, weak or high-profile. Applied: Papakura (Judith Collins), Tāmaki (Brooke van Velden), Wigram (Megan Woods), Whangārei (Shane Reti) and Port Waikato (Andrew Bayly, which also has no 2023 candidate baseline) are exceptional; Kaipara ki Mahurangi, Waitākere, Christchurch Central and West Coast-Tasman are plain changes and ordinary. Damien O'Connor, moving from West Coast-Tasman to Waitaki, is not high-profile enough for either seat. Profile judgements are James's, from general knowledge, not repository data.
- **Other exceptional seats.** Auckland Central, Wellington Bays and Wellington North (Green-held minor-party seats), Epsom (deal seat), Glendene (redrawn, NZ First's former MP Alfred Ngaro, uncertain party-vote lead), Kapiti (the only seat whose party-vote leader changed against the old baseline, added by James) and Mt Albert (the Opportunity Party's two-ticks campaign with Qiulae Wong standing, decided by 18 votes in 2023, added by James).
- **Ordinary despite a close call.** Wairarapa (a former National MP standing for NZ First is not exceptional enough, James), Waitaki, the seven boundary-only seats (Botany, Henderson, Kenepuru, Mt Roskill, Ōtāhuhu, Rangitīkei, Upper Harbour; Stage69 baselines agree with the Tally Room cross-check) and Waitākere.
- **Limits that stay attached.** The 0.60 ordinary scale is still development-informed and flag-selection-sensitive (D107). The 2014–2023 audit recorded the flagged seats but not a reason for each, and 21 of its 38 flags came from a residual-ranked list. The scandal check was one bounded news pass and is not exhaustive. No general-seat electorate polls exist.

<!-- fold: state -->
# Config: 2026 general-seat classification — ready for review, 2026-10-10

Branch `claude/project-thread-o98s91`, from main `4b20089` (after #102). Records James's approved classification (release-checklist item 4) and regenerates the live development gate. Not changed: any model, scale, fit, the configuration, the assembly code, the export, `data/sources.json`, the rehearsal.

- **Counts.** 64 general seats: 12 exceptional (Auckland Central, Epsom, Glendene, Kapiti, Mt Albert, Papakura, Port Waikato, Tāmaki, Wellington Bays, Wellington North, Whangārei, Wigram), 52 ordinary. No Stage56 adjustment files exist, so no seat is forced exceptional from that route.
- **Development gate (live, 64 national draws).** 67 of 71 seats simulated (all 64 general, 3 polled Māori); 4 unavailable (the unpolled Māori seats). Failed checks: `configComplete` (pending `maori.unpolledFallbackModel`) and `allWinnersPresent` (4 unavailable). Classification multipliers and national reconciliation pass. Still unpublishable.
- **Not done:** the no-poll Māori fallback (Stage78, PR #103, wires into the assembly separately), seat counts and Parliament outputs, the first real run, any release. The rehearsal (`scripts.release_rehearsal`) still uses its synthetic stand-in classification and is unchanged.
- **Local checks.** See the PR body for exact counts.
- **Exact next action.** The coordinator reviews and merges this PR. Then, after #103 (the Māori fallback stage) and its wiring, run `python3 -m scripts.nowcast_assembly.run --require-complete` and the release steps. Any later change to the classification is a new dated entry set by James, with the Stage73 test pin updated.
