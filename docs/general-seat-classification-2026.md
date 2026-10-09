# 2026 ordinary / exceptional classification of the 64 general seats (recorded)

**Status: recorded and live.** James approved this classification on 2026-10-10 (nominations closed 8 October; official candidate list, Stage50 part 2). It is stored in [`config/general-seat-classification-2026.json`](../config/general-seat-classification-2026.json) in the D107 schema (author James, recordedAt 2026-10-10), read by the assembly through `uncertainty.classification` and validated fail-closed by `scripts.nowcast_config.validate`. It supersedes the 7 and 10 October draft proposal, whose history is in git. The tables below are the reasons and evidence as approved.

**Result: 13 exceptional (20.3%), 51 ordinary.** Weights per D107: ordinary 0.60, exceptional 1.00 of the seat scale; this changes only the seat-level spread of the candidate National/Labour balance. A wrong *ordinary* understates uncertainty in that seat; a wrong *exceptional* only restores the frozen default width. The list passes the repository's classification check (`check_classification`): 64 seats, no duplicates, every exceptional seat sourced. No Stage56 adjustment files exist, so no seat is forced exceptional from that route.

**Rule applied to candidate changes (James, 10 Oct; D116 provisional).** A candidate change on its own is already counted in the S+R model, so it makes a seat exceptional only when the candidate being replaced, or the replacement, is uniquely strong, weak or high-profile. Profile judgements come from general knowledge, not repository data, and are James's calls.

**Compared with past elections.** The frozen 2014-2023 audit used for Stage67 flagged 38 of 257 seat-elections (14.8%): 2014 8 of 64 (12.5%), 2017 6 of 64 (9.4%), 2020 10 of 65 (15.4%), 2023 14 of 64 (21.9%). The 0.60 multiplier was fitted against that audit. 13 of 64 (20.3%) sits between the four-election average and 2023 (21.9%). By-year detail: [general-seat-classification-2026-historical-flags.md](general-seat-classification-2026-historical-flags.md).

## Exceptional (13)

| Id | Seat | Class | Stage56 facts | Reason |
|---|---|---|---|---|
| 001 | Auckland Central | exceptional | tactical_arrangement / minor-party seat | Green-held seat where the incumbent (Swarbrick) restands; National's Candace Kinser is the main challenger (2023 margin over National 3.9k). |
| 010 | Epsom | exceptional | tactical_arrangement | Epsom deal seat: ACT's Seymour restands and National's Paul Goldsmith also stands (as in 2023), so the arrangement is not explicit. |
| 011 | Glendene | exceptional | new_strong_challenger; boundary_change | Redrawn seat (Kelston 48%, Te Atatu 44%) with Labour's Sepuloni restanding; NZ First stands former MP Alfred Ngaro; Stage69 party-vote lead is razor thin (P(National ahead) 0.08). |
| 020 | Kapiti | exceptional | boundary_change (method-sensitive) | Redrawn seat (Ōtaki 54% / Mana 46%) and the only seat whose party-vote leader changes against the old baseline: the adopted Stage69 baseline has National ahead by 3.9pp where the old one had Labour by 0.5pp (Tally Room agrees with the new one). National's Tim Costley restands. Added by James. |
| 025 | Mt Albert | exceptional | tactical_arrangement | The Opportunity Party (TOP) is running a two-ticks campaign here with Qiulae Wong standing; 2023 was decided by 18 votes (Labour's Helen White restanding, National's Melissa Lee rematches; Green Ricardo Menéndez March stood third on 9.3k). Added by James. |
| 033 | Northland | exceptional | new_strong_challenger / other (three-way contest) | Three-way contest: National's Grant McCallum (2023 winner on 16.3k) restands against Labour's Ashleigh Latimer and NZ First's Shane Jones (third on 8.1k in 2023, standing again); no Northland two-way is safe. Added by James. |
| 037 | Papakura | exceptional | candidate_change (high-profile replaced) | High-profile departure: Judith Collins (former National leader, senior minister, 2023 majority 13.5k) is on neither official list; National stands Emma Chatterton. |
| 038 | Port Waikato | exceptional | candidate_change (minister replaced); missing 2023 candidate baseline | Andrew Bayly (minister) is on neither official list and National stands Matthew Paul; also the 2023 contest was cancelled, so the seat has no 2023 candidate baseline. |
| 047 | Tāmaki | exceptional | candidate_change (high-profile replaced) | High-profile departure: Brooke van Velden (senior ACT minister, won by 4.2k) is on neither the electorate list nor ACT's list; ACT stands James Christmas against National's Mahesh Muralidhar. |
| 058 | Wellington Bays | exceptional | tactical_arrangement / minor-party seat; boundary_change | Green incumbent of the predecessor (Genter, Rongotai 85%) restands; ACT stands Nicole McKee, National stands Karuna Muthu; Labour stands Craig Renney. |
| 059 | Wellington North | exceptional | minor-party seat; boundary_change | Green incumbent of the predecessor (Tamatha Paul, Wellington Central 70%) restands; Labour stands Ayesha Verrall; abolished Ōhāriu supplies 30%. |
| 063 | Whangārei | exceptional | candidate_change (minister replaced, judgement) | Health Minister Shane Reti is on neither official list; National stands Lloyd Budd. Judgement: a senior minister, but not a leader-level profile. |
| 064 | Wigram | exceptional | candidate_change (high-profile replaced) | High-profile replacement: former minister Megan Woods is list-only (Labour list 5); Labour stands Dominik Yanzick. 2023 margin was 1.2k; National's Tracy Summerfield rematches. |

## Close calls and how they were decided

1. **Candidate-change seats under the rule.**
   - *Exceptional, clear:* Papakura (Judith Collins), Tāmaki (Brooke van Velden) and Wigram (Megan Woods).
   - *Exceptional, James's call:* Whangārei (Health Minister Shane Reti) and Port Waikato (minister Andrew Bayly replaced; the seat also has no 2023 candidate baseline because that contest was cancelled).
   - *Ordinary, plain changes:* Kaipara ki Mahurangi (Penk to Rowe), Waitākere (Garcia to Loheni), Christchurch Central (Webb to Hampton) and West Coast-Tasman (Pugh to Milne; Damien O'Connor, now standing in Waitaki, is judged not high-profile enough). Christchurch Central is the closest of these: Labour won by 1.8k and National's 2023 runner-up Dale Stephens rematches. West Coast-Tasman was decided by 1.0k in 2023.
2. **Boundary-only seats, ordinary.** Seven remain: Botany (003), Henderson (014), Kenepuru (021), Mt Roskill (027), Ōtāhuhu (034), Rangitīkei (040) and Upper Harbour (052), plus Waitākere (056, a plain candidate change in a redrawn seat). The 2023 holder restands in all but Waitākere. Stage69 rebuilt these baselines from voting-place data; they agree with the Tally Room cross-check (same leader in 50 of 50 changed seats) with a median 90% width of 0.48pp. Kapiti (020) and Mt Albert (025) are exceptional at James's instruction.
3. **Wairarapa (055) and Waitaki (057), ordinary (James).** Wairarapa was close in 2023 (National 20.3k, Labour 17.5k) and Labour's Kieran McAnulty rematches; a former National MP standing for NZ First is judged not exceptional enough. Waitaki was won by National by 12.2k.
4. **Auckland Central (001), Wellington Bays (058), Wellington North (059), exceptional.** Green-held minor-party seats where the incumbent, or the predecessor's incumbent, restands; flagged because the National-Labour balance is poorly defined where a Green is the favourite. Wellington North also has Labour's Ayesha Verrall standing; Wellington Bays and Epsom carry the tactical-arrangement fact.
5. **Northland (033), exceptional (James, 10 Oct, after the draft was approved).** A three-way contest: National's Grant McCallum (16.3k in 2023), Labour's Ashleigh Latimer and NZ First's Shane Jones (8.1k, third in 2023). Northland was flagged in 2017 and 2020 in the frozen 2014-2023 audit, which is unchanged; see the appendix.
6. **Very close 2023 margins, ordinary (not a criterion).** Nelson (26 votes; Rachel Boyack against National's Blair Cameron rematch) and Henderson (131 votes, as Te Atatū). Mt Albert (18 votes) is exceptional for the TOP campaign.

## Ordinary (51)

| Id | Seat | Class | Reason |
|---|---|---|---|
| 002 | Banks Peninsula | ordinary | National holder Vanessa Weenink restanding, no candidate change. |
| 003 | Botany | ordinary | National holder Christopher Luxon restanding, no candidate change; boundary: Botany 70% of seat (material change judged covered by Stage69 notionals). |
| 004 | Christchurch Central | ordinary | Plain candidate change (Labour's Duncan Webb not standing, Labour stands George Hampton; National's Dale Stephens, the 2023 runner-up, restands); no unusually strong or weak candidate, so left to the candidate model. Close call: 2023 margin 1.8k. |
| 005 | Christchurch East | ordinary | Labour holder Reuben John Davidson restanding, no candidate change. |
| 006 | Coromandel | ordinary | National holder Scott Simpson restanding, no candidate change. |
| 007 | Dunedin | ordinary | Labour holder Rachel Brooking restanding, no candidate change. |
| 008 | East Cape | ordinary | National holder Dana Margot Kirkpatrick restanding, no candidate change. |
| 009 | East Coast Bays | ordinary | National holder Erica Stanford restanding, no candidate change. |
| 012 | Hamilton East | ordinary | National holder Ryan Hamilton restanding, no candidate change. |
| 013 | Hamilton West | ordinary | National holder Tama William Potaka restanding, no candidate change. |
| 014 | Henderson | ordinary | Labour holder Phil Twyford restanding, no candidate change; boundary: Te Atatū 60% of seat (material change judged covered by Stage69 notionals). |
| 015 | Hutt South | ordinary | National holder Chris Bishop restanding, no candidate change; boundary: Hutt South 89% of seat. |
| 016 | Ilam | ordinary | National holder Hamish Campbell restanding, no candidate change. |
| 017 | Invercargill | ordinary | National holder Penny Simmonds restanding, no candidate change. |
| 018 | Kaikōura | ordinary | National holder Stuart Smith restanding, no candidate change. |
| 019 | Kaipara ki Mahurangi | ordinary | Plain candidate change (National stands Jessica Rowe, holder Chris Penk on neither official list; ACT stands Simon Court); no unusually strong or weak candidate, so left to the candidate model. |
| 021 | Kenepuru | ordinary | Labour holder Barbara Edmonds restanding, no candidate change; boundary: Mana 50% of seat (material change judged covered by Stage69 notionals). |
| 022 | Māngere | ordinary | Labour holder Lemauga Lydia Sosene restanding, no candidate change. |
| 023 | Manurewa | ordinary | Labour holder Arena Williams restanding, no candidate change. |
| 024 | Maungakiekie | ordinary | National holder Greg Fleming restanding, no candidate change; boundary: Maungakiekie 86% of seat. |
| 026 | Mt Maunganui | ordinary | National holder Tom Rutherford restanding, no candidate change; boundary: Bay of Plenty 88% of seat. |
| 027 | Mt Roskill | ordinary | National holder Carlos Cheung restanding, no candidate change; boundary: Mt Roskill 73% of seat (material change judged covered by Stage69 notionals). |
| 028 | Napier | ordinary | National holder Katie Nimon restanding, no candidate change. |
| 029 | Nelson | ordinary | Labour holder Rachel Boyack restanding, no candidate change. |
| 030 | New Plymouth | ordinary | National holder David MacLEOD restanding, no candidate change. |
| 031 | North Shore | ordinary | National holder Simon Watts restanding, no candidate change. |
| 032 | Northcote | ordinary | National holder Dan Bidois restanding, no candidate change. |
| 034 | Ōtāhuhu | ordinary | Labour holder Jenny Salesa restanding, no candidate change; boundary: Panmure-Ōtāhuhu 83% of seat (material change judged covered by Stage69 notionals). |
| 035 | Pakuranga | ordinary | National holder Simeon Brown restanding, no candidate change. |
| 036 | Palmerston North | ordinary | Labour holder Tangi Utikere restanding, no candidate change; boundary: Palmerston North 85% of seat. |
| 039 | Rangitata | ordinary | National holder James Meager restanding, no candidate change. |
| 040 | Rangitīkei | ordinary | National holder Suze Redmayne restanding, no candidate change; boundary: Rangitīkei 61% of seat (material change judged covered by Stage69 notionals). |
| 041 | Remutaka | ordinary | Labour holder Chris Hipkins restanding, no candidate change. |
| 042 | Rotorua | ordinary | National holder Todd McCLAY restanding, no candidate change. |
| 043 | Selwyn | ordinary | National holder Nicola Grigg restanding, no candidate change. |
| 044 | Southland | ordinary | National holder Joseph Mooney restanding, no candidate change. |
| 045 | Taieri | ordinary | Labour holder Ingrid Leary restanding, no candidate change. |
| 046 | Takanini | ordinary | National holder Rima Nakhle restanding, no candidate change. |
| 048 | Taranaki-King Country | ordinary | National holder Barbara Joan Kuriger restanding, no candidate change. |
| 049 | Taupō | ordinary | National holder Louise Claire Upston restanding, no candidate change. |
| 050 | Tauranga | ordinary | National holder Sam Uffindell restanding, no candidate change; boundary: Tauranga 85% of seat. |
| 051 | Tukituki | ordinary | National holder Catherine Wedd restanding, no candidate change. |
| 052 | Upper Harbour | ordinary | National holder Cameron Brewer restanding, no candidate change; boundary: Upper Harbour 79% of seat (material change judged covered by Stage69 notionals). |
| 053 | Waikato | ordinary | National holder Tim Van De Molen restanding, no candidate change. |
| 054 | Waimakariri | ordinary | National holder Matt Doocey restanding, no candidate change. |
| 055 | Wairarapa | ordinary | National holder Mike Butterick restanding; Labour's Kieran McAnulty rematches (2023: 20.3k to 17.5k) and NZ First stands a former National MP, Ron Mark, which James judges not exceptional enough. |
| 056 | Waitākere | ordinary | Plain candidate change (National's New Lynn holder Garcia is replaced by Agnes Loheni; Labour stands Vanushi Walters) in a redrawn seat (New Lynn 65%, Kelston 35%); no unusually strong or weak candidate, boundary covered by Stage69 notionals. |
| 057 | Waitaki | ordinary | National holder Miles Anderson restanding (2023 margin 12.2k); Labour's Damien O'Connor, moved from West Coast-Tasman, is judged by James not high-profile enough to make the seat exceptional. |
| 060 | West Coast-Tasman | ordinary | Plain candidate change (National stands Katie Milne, holder Maureen Pugh on neither official list; Labour stands Rory Paterson, Damien O'Connor now standing in Waitaki); James judges O'Connor not high-profile enough, so left to the candidate model. |
| 061 | Whanganui | ordinary | National holder Carl Bates restanding, no candidate change. |
| 062 | Whangaparāoa | ordinary | National holder Mark Mitchell restanding, no candidate change. |

## Checked and not checked

- **Checked:** every 2023 holder of the largest predecessor seat was matched to the official 2026 electorate list by surname and given name. In the ordinary table the holder restands in 47 seats and the other 4 are the plain candidate changes above. Papakura, Port Waikato, Tāmaki, Wigram and Whangārei (exceptional) have a holder who is not restanding. Port Waikato has no 2023 electorate result.
- **Scandal check (10 Oct, one bounded news pass, not exhaustive):** nothing found touching any major-party general-seat candidate. Two controversies, ACT's Lyra Yan Zhang in Kenepuru (undisclosed link to a Chinese political group; resigned in July) and NZ First's Murray Chong in New Plymouth (Confederate flag), concern candidates who are not on the official list, so they do not affect any class. No class changed.
- **Not checked:** electorate-level polls (none exist for general seats), tactical arrangements announced outside the official list (other than the TOP campaign in Mt Albert, which is James's information), and candidate profiles beyond general knowledge. The Opportunity Party's candidate in Mt Albert is listed in the official table as Qiulae Wong.
- The Māori seats are separate and not classified here (the four unpolled ones use the Stage78 fallback wired in by Stage80; the three polled ones use their seat polls).

## Sources (repository paths)

- `data/processed/nominations-2026/2026-10-10/official-table.json` and the party-list PDF `data/raw/nominations/2026-10-10/` (official candidates, PR #102)
- `data/processed/historical/2008-2023/candidate-votes.json` (2023 results and holders)
- `data/processed/electorate-baseline/mapping.json` (predecessor shares)
- `docs/stage69-voting-place-notionals.md`, `docs/stage64-electorate-baseline-audit.md` (baselines and heterogeneity)
- `docs/stage56-manual-adjustment-interface.md` (the fact checklist)
- `data/processed/exceptional-balance-scale/design-contract.json` (the 2014-2023 flag counts)
- the 7 and 10 October draft proposal (`docs/general-seat-classification-2026-draft.md`, renamed to this file; history in git)
