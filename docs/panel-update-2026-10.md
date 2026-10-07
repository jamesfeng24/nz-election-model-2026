# Stage59 — derived 2026-cycle national poll panel (RNZ–Reid 6 Oct, Talbot Mills repairs)

One bounded question: which waves are missing from, or duplicated in, the frozen Stage35 national panel for the current cycle, and what is the corrected panel the later live-fit stage should read? Offline, stdlib only; no fit, average or forecast. Code `scripts/polling/panel_update/build.py` (`--check` reproduces every output byte for byte); outputs in `data/processed/polling/panel-update-2026-10/`; tests `scripts/tests/test_panel_update.py`.

## Design: a new derived panel, not an edit of Stage35

`data/processed/polling/national-foundation/polls.json` (496 waves, fieldwork to 27 Sep 2026) is pinned by hash in the later input contracts and preservation files (national backtest, category interface, candidate integration, uncertainty stages and others). Editing it would fail those checks and force frozen-pipeline replays. So the update is an overlay: `panel.json` = Stage35 records, minus one collapsed duplicate, plus three waves, in the unchanged record schema (498 waves; cycle counts 136/78/46/116/**122**). `changes.json` is the ledger and `input-contract.json` the input and generator hashes. Stage35, Stage52 and every earlier file are byte-identical. The later live-fit stage should read `panel.json`; Stage36–48 keep reading Stage35.

Waves this update added or changed carry `evidenceGrade` (`primary_verified` or `aggregator_only`) and `panelUpdateNote`; unchanged Stage35 waves do not.

## What changed

| Item | Finding | Action |
|---|---|---|
| RNZ–Reid Research, fieldwork 24 Sep–1 Oct 2026, published 6 Oct 06:27 NZDT | Already in the Stage52 raw capture (`rnz-reid-2026-10-06.html`, SHA-256 `3c4c52a5…e321ec`) and its verified audit, and in both GitHub snapshots; **not** in the Stage35 panel (its Wikipedia snapshot predates the poll) | Added from the RNZ article: n=1000 online quota sample, NAT 25.9, LAB 30.8, GRN 14.8, ACT 9, NZF 10.6, TPM 2, TOP 5.5; 3% undecided and 2.6% would-not-vote excluded by RNZ. Each share and the dates are asserted as verbatim text in the preserved bytes. Others 0.7 comes only from the Wikipedia capture and is labelled so. |
| Talbot Mills 1–10 Nov 2024 | Wikipedia lists it; the Stage35 adapter rejects any row with a blank sample cell, so it was dropped. Stage52 recovered the NZ Herald article | Added: NAT 34, LAB 33, GRN 10, ACT 10, NZF 7, TPM 3.3, no n (margin 3.1%); Wikipedia row and Herald text agree; `primary_verified`. |
| Talbot Mills 1–10 May 2024 | Same adapter gap. Only NAT 35 and LAB 32 are published. The sources cited by the two scrapers are The Post pages that are JavaScript shells; web.archive.org is denied; a second bounded search found nothing | Added as `aggregator_only` (same evidence class as every other Stage35 row, flagged); unreported parties are missing, not zero. A filter on `evidenceGrade` removes it. |
| Talbot Mills April 2026 | Two Stage35 waves for one poll: Nixinova interval `2026-04-00…2026-04-16` and a Wikipedia single date `2026-04-16`, with identical shares and n=1082. The NZ Herald (June article, preserved) confirms the April values; no fieldwork dates are published | Kept the interval row, dropped the single-date copy (collapsed, provenance merged). The 16 April date is when the poll was first reported, so the interval row keeps the true uncertainty (start day unknown) whereas the single date would present an end bound as a fieldwork day. |

Why exactly these two rows: of the 11 rows the Stage35 adapter rejects for a blank or `1,000+` sample, nine were already recovered through the Nixinova bulk file; the build asserts the remaining gap is exactly these two and fails loudly if the source changes.

## Stage52 raw acquisition

The Stage52 snapshots (labo49 and danylmc) list each Talbot Mills row once. Against the Stage35 panel two of their 22 Talbot Mills rows (May and Nov 2024) had no match; against the new panel all 22 match in both snapshots, none twice. Two snapshot defects are recorded, neither changed (they are preserved raw): danylmc dates the 6 Oct RNZ–Reid shares 4–11 Sep (the RNZ article says 24 Sep–1 Oct; labo49 is right) and treats the 16 Apr Talbot Mills date as fieldwork start and end. The frozen Stage52 audits still say the May 2024 row was excluded and the panel unchanged; that remains true of Stage35 and is superseded for the live-fit input by this panel.

## Not done

No change to the Stage35 panel, Stage36–48 inputs, `data/sources.json` or any frozen output; no new raw acquisition (everything used was already preserved and checksummed in Stage35/Stage52, so no new source registry); no house-effect grouping of Talbot Mills and Anacta, no recent-window rule, no publication-lag or denominator assumption beyond what each source states; no Talbot Mills sample sizes invented. The Labour-commissioned Talbot Mills rows (30 Apr and 22–28 Nov 2024) share code TBM with the corporate rows, as in Stage35, unchanged.

Reproduce: `python3 -m scripts.polling.panel_update.build --check`; `python3 -m unittest scripts.tests.test_panel_update`.
