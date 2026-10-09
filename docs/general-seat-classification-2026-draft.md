# DRAFT: 2026 ordinary/exceptional classification of the 64 general seats (for James)

**Status: a proposal, not an input.** Nothing here is read by any code. After James approves or edits it, it is written to `config/general-seat-classification-2026.json` in the D107 schema (`scripts/nowcast_config/validate.py`), with James as `author`. Drafted 7 October 2026 from repository evidence only, before final nominations (8 October, 12:00 NZDT). **Rechecked 10 October 2026 against the official candidate list** (Stage50 part 2, `data/processed/nominations-2026/2026-10-10/`): two seats move to the core list, one fact is corrected, and the known gaps below are closed.

## What the class changes

The class changes only the seat-level standard deviation of the candidate National/Labour balance (D107):
- **ordinary** uses 0.60 × the 2026 scale;
- **exceptional** uses 1.00 × the 2026 scale (the frozen default).

Means, the shared election effect, the party-vote layer and Māori seats are unaffected.

A missing seat fails the build. A wrong "ordinary" understates uncertainty in that seat, while a wrong "exceptional" only restores the frozen default width. When in doubt, **exceptional is the safe side**.

## Criteria used

These are the Stage56/57 pre-voting facts (D098), judged on 2026 evidence keyed by 2026 boundary id, never by carrying a historical flag over by name:
- `candidate_change`: the incumbent party's candidate is not the 2023 seat holder;
- `boundary_change`: the seat is materially different from its predecessor. Proposed test: the largest 2023 predecessor supplies under 75% of the new seat, or Stage64 marked the seat heterogeneity-sensitive;
- `scandal`;
- `tactical_arrangement`: an Epsom-type arrangement;
- `new_strong_challenger`: a credible new candidate with a winning claim;
- `other`.

The historical (2014–2023) audit flagged about 15% of seat-elections, and the 0.60 multiplier was estimated against that rate.

## Proposed exceptional (core: 15 seats)

| Id | Seat | Fact(s) | 2026 evidence (repository) |
|---|---|---|---|
| 001 | Auckland Central | tactical_arrangement / minor-party seat | Green incumbent (Swarbrick) restanding; National stands Kinser |
| 010 | Epsom | tactical_arrangement | ACT-held deal seat (Seymour restanding). **Corrected 10 October:** the official list has National's Paul Goldsmith standing in Epsom, as in 2023; the draft's "no National candidate" came from the party roster and was wrong |
| 047 | Tāmaki | candidate_change | ACT-held; ACT stands James Christmas. Confirmed 10 October: van Velden is on no official electorate list |
| 058 | Wellington Bays | tactical / minor-party; boundary (Rongotai 84%) | Green incumbent of the predecessor (Genter); ACT deputy leader McKee stands |
| 059 | Wellington North | minor-party seat; boundary_change (Wellington Central 70%, abolished Ōhāriu 29%) | Green incumbent of the predecessor (Tamatha Paul); Willis is list-only |
| 037 | Papakura | candidate_change | National stands Emma Chatterton; Collins is not on National's MP list |
| 038 | Port Waikato | candidate_change | National stands Matthew Paul, not Bayly |
| 019 | Kaipara ki Mahurangi | candidate_change | National stands Jessica Rowe, not Penk; ACT stands Simon Court |
| 063 | Whangārei | candidate_change | National stands Lloyd Budd, not Reti |
| 060 | West Coast-Tasman | candidate_change | National stands Katie Milne, not Pugh |
| 056 | Waitākere | candidate_change; boundary_change (New Lynn 64%, Kelston 34%) | National's New Lynn holder (Garcia) replaced by Agnes Loheni |
| 011 | Glendene | new_strong_challenger; boundary_change (Kelston 47%, Te Atatū 43%) | NZ First stands Alfred Ngaro (former MP); Stage64 party-vote lead is 0.0pp |
| 055 | Wairarapa | new_strong_challenger (judgement) | NZ First stands Ron Mark (former MP). **James's call:** this is the weakest core case |
| 004 | Christchurch Central | candidate_change (new, 10 October) | Labour-held; Duncan Webb is not on the official list; Labour stands George Hampton |
| 064 | Wigram | candidate_change (new, 10 October) | Labour-held; Megan Woods stands list-only (Labour list no. 5); Labour stands Dominik Yanzick |

## Boundary change only (9 seats; James decides as a block)

The incumbent is apparently recontesting, and the only fact is a material boundary change:

| Seat | Boundary evidence |
|---|---|
| 003 Botany | 70% |
| 014 Henderson | 59% |
| 020 Kapiti | 53% |
| 021 Kenepuru | 49%, plurality predecessor unidentified |
| 025 Mt Albert | 71% |
| 027 Mt Roskill | 72% |
| 034 Ōtāhuhu | Stage64 heterogeneity-sensitive |
| 040 Rangitīkei | 60% |
| 052 Upper Harbour | Stage64 heterogeneity-sensitive |

- **For "exceptional":** historical boundary-only seats (2014 Rodney, Papakura, New Lynn and East Coast Bays; 2020 Papakura, Northland and Dunedin) were flagged.
- **For "ordinary":** boundary uncertainty mostly lives in the party-vote baseline, which D107 does not touch and Stage69 is rebuilding.

Including all nine gives 24 of 64 (38%), well above the historical rate. The core 15 alone is 23%.

## Everything else: ordinary (40 seats, or 49 if the boundary block is ordinary)

002 Banks Peninsula · 005 Christchurch East · 006 Coromandel · 007 Dunedin · 008 East Cape · 009 East Coast Bays · 012 Hamilton East · 013 Hamilton West · 015 Hutt South · 016 Ilam · 017 Invercargill · 018 Kaikōura · 022 Māngere · 023 Manurewa · 024 Maungakiekie · 026 Mt Maunganui · 028 Napier · 029 Nelson · 030 New Plymouth · 031 North Shore · 032 Northcote · 033 Northland · 035 Pakuranga · 036 Palmerston North · 039 Rangitata · 041 Remutaka · 042 Rotorua · 043 Selwyn · 044 Southland · 045 Taieri · 046 Takanini · 048 Taranaki-King Country · 049 Taupō · 050 Tauranga · 051 Tukituki · 053 Waikato · 054 Waimakariri · 057 Waitaki · 061 Whanganui · 062 Whangaparāoa

## Recheck against the official list (10 October 2026)

Every general seat's 2023 holder (of the largest predecessor) was compared with the official 2026 electorate candidates:
- **Restanding in the seat:** every other holder, including all Labour holders in Labour-held seats except Webb and Woods (Christchurch East, Dunedin, Glendene, Henderson, Kenepuru, Māngere, Manurewa, Mt Albert, Ōtāhuhu, Palmerston North, Remutaka, Taieri), Nelson (Rachel Boyack, published in 2023 as Boyack-Mayer) and the Green holders (Auckland Central, Wellington Bays, Wellington North).
- **Not restanding:** exactly the nine core candidate changes above (Christchurch Central, Kaipara ki Mahurangi, Papakura, Port Waikato's 2023 holder, Tāmaki, Waitākere, West Coast-Tasman, Whangārei, Wigram; Port Waikato had no 2023 general-election result because of the cancelled contest).
- **Still not checked:** no scandal facts and no general-seat electorate polls are in the repository. Close 2023 margins are not a criterion (Mt Albert 18 votes, Nelson 26, Te Atatū/Henderson 131).

## Sources

Every path below is in this repository:
- `data/processed/nominations-2026/2026-10-10/official-table.json` and `data/processed/forecast-readiness/snapshots/2026-10-10/` (the official list, Stage50 part 2); 2023 holders from `data/processed/historical/2008-2023/candidate-votes.json`;
- `data/processed/forecast-readiness/snapshots/2026-10-05/` (`review-table.tsv`, `snapshot.json` and `target-frame.json`; built from party pages saved in `data/raw/forecast-readiness/2026-10-05/`);
- `data/processed/electorate-baseline/mapping.json` and `docs/stage64-electorate-baseline-audit.md` (predecessor shares, heterogeneity);
- `docs/stage56-manual-adjustment-interface.md` (the fact checklist).
