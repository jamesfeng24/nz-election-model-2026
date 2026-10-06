# MMP rules verification — 2026-10-06

Documentation-only checkpoint. **No code, model, coefficient, test or workflow changed.** One question: which 2026 MMP seat-allocation rules named in [statistical-specification.md](statistical-specification.md) (items 10–12, "requested design requirements, not independently verified") are supported by the Electoral Act and Electoral Commission sources, and which remain open? Authorized by James (working on Corinna's account) on 2026-10-06 as a rule check only; implementation is **not** authorized (see the proposal at the end).

## Evidence

- **Statute (primary).** James uploaded the Electoral Act 1993, version 238.0 as at 1 January 2026, as a PDF text extraction. It is preserved unchanged at `data/raw/legislation/electoral-act-1993/` with SHA-256 `8f6f5229…9c01a` and a provenance note (full hash in `provenance.json`). The session's own access to legislation.govt.nz was blocked, so this is the PDF's text extraction, not a byte-verified download. The version header and the amendment notes (Part 6 sections last amended in 2017 and earlier; the file also carries Electoral Amendment Act 2025 notes elsewhere) show it is the current text for 2026. It is not yet in `data/sources.json`, which is a pinned Stage39 CI dependency; register it after the CI-scoping change merges.
- **Electoral Commission pages (secondary to the Act).** Read through a summarising web-fetch tool on 2026-10-06; quoted strings are tool output, not byte-checked, and nothing from them is preserved under `data/raw/`. They corroborate the Act and supply facts the Act does not hold (2023 results, 2026 boundaries).
- Status vocabulary: **Statute** = text of the Act as at 1 January 2026; **Official** = stated on an Electoral Commission or Ministry page; **Derived** = arithmetic or reasoning from verified inputs; **Open** = not established.

## Findings

| # | Rule | Finding | Status |
|---|---|---|---|
| 1 | House size | s 191(7): the Commission takes "the highest 120 quotients or such lower number as is required by subsection (8)". | Statute; Official |
| 2 | Qualification | s 191(4): the Commission disregards a party that (a) "has not achieved a total that is at least 5% of the total number of all the party votes received by all the parties listed on the part of the ballot paper that relates to the party vote" **and** (b) has no constituency candidate, of the party or of a component party, endorsed on the writ as elected (s 185). So 5% **or** one electorate win suffices; the threshold is inclusive (≥ 5%). | Statute |
| 3 | Threshold denominator | The 5% base is all party votes received by all listed parties, i.e. the valid party votes of s 179(1)(a) ("total number of valid votes received by each of the parties listed"); informal party votes are set aside under the count rules. Disregarded parties are treated as deleted from the ballot list (s 191(4A)). | Statute |
| 4 | Sainte-Laguë | s 191(5): each remaining party's total is divided by 1, 3, 5, 7, 9, 11, 13 and every odd number as needed; quotients are compared across all columns and the highest are taken (s 191(6)–(7), (10)). A party's entitlement is the number of its quotients selected (s 192(1)). | Statute |
| 5 | Electorate seats deducted | s 192(2)–(4): from each party's entitlement the number of its constituency winners (including component-party winners, s 192(2)(b), (3)) is deducted; the remainder is its list allocation. | Statute |
| 6 | Overhang | s 192(5): if a party's constituency seats are "equal to or greater than" its entitlement it gets no list seats and its constituency seats "shall not be affected". Nothing in ss 191–193 recomputes other parties' entitlements or reduces the number of quotients taken, so Parliament is larger by the excess (Commission: "the size of Parliament is increased"; 2023: 122 seats, overhang 2, Te Pāti Māori 6 electorate seats at 3.08%). Equal seats give zero list seats and no overhang. | Statute; Official |
| 7 | Independents and off-ballot winners | s 191(8): if a person elected for an electorate is an independent, or belongs to a party that was not on the party-vote list (other than a component party of a listed party), the Commission deducts the number of such persons from 120 before taking quotients. Their seats are inside the 120, not on top of it. Parliament is then 120 + overhang. | Statute |
| 8 | Ties | s 191(9): if the lowest selected quotient is shared by two or more columns "of exactly the same value", the Commission decides "by lot" which is selected. | Statute |
| 9 | List exhaustion | s 193(4): if a party's list runs out, it takes no more and "those seats shall not be filled" (Parliament has unfilled seats). s 193(3): names of candidates who won electorates are disregarded when selecting from the list; list order selects the rest (s 193(2)). | Statute |
| 10 | Cancelled electorate poll | ss 153A–153B: when a constituency candidate dies or is found incapacitated before or on polling day, the electorate poll is cancelled and the party vote proceeds; s 153E triggers a fresh by-election-style poll. ss 191–192 contain no special deduction for such a seat, so the list allocation proceeds as normal and the seat, once filled, adds one member. This reading matches the official 2023 account (122 seats at declaration, 123 after the Port Waikato poll). | Statute (cancellation, by-election); the +1 consequence is Derived and consistent with Official 2023 |
| 11 | Electorate count | s 35(3): South Island fixed at 16 general electorates; North Island derived from population; s 45: Māori electorates by the Māori option. 2026 final boundaries: 64 general + 7 Māori = 71 (Commission release 8 Aug 2025: 19 unchanged, 49 general and 3 Māori adjusted; matches the repo Schedule C inventory). | Statute (method); Official + repo (count) |
| 12 | List seats, 2026 | 120 − 71 = 49 nominal list seats before overhang. Not printed in any source as a single figure by the Act; the NZ Initiative also gives 49. | Derived |
| 13 | 2026 law changes | The Act text supplied is version 238.0 as at 1 January 2026 and ss 191–193 carry no amendment after 2017 in their notes. The Ministry of Justice summary of the Electoral Amendment Act 2025 (Royal Assent 19 Dec 2025) lists no change to the threshold, exemption, Sainte-Laguë, overhang or house size. | Statute; Official |

## Still open

1. **Component parties** (s 3 definition, ss 127(3A), 128A): constituency wins by a registered component party count for the listed party. Whether any 2026 party has component-party registrations is not established; the allocator must accept an explicit party-to-constituency-seat mapping rather than assume none.
2. **Postponed-poll seat arithmetic** (item 10) rests on reading ss 191–192 plus the 2023 outcome; there is no express "add one member" provision in the text read. A cancellation-aware test case should reproduce 2023 exactly.
3. **Official 2008–2023 seat tables** as test oracles: not yet inventoried in the repo.
4. **Practical tie handling** by lot: the model can only flag an exact tie, never resolve it.
5. **Final nomination slate and party-vote ballot roster** for 2026 (after 8 Oct): determines which parties are listed, and so which can qualify and which winners count as "off-ballot".

## Consequences for the repo (no edits made here)

- `docs/data-dictionary.md` `MmpAllocation` convention ("verify/revise conventions against official rules") should become: `nominalSeats` = 120; `parliamentSize` = 120 + overhang (+1 per filled cancelled-poll seat if confirmed); `unfilledSeats` arise only from list exhaustion (s 193(4)); independents' seats are inside the 120 (s 191(8)). `independentElectorateSeats` stays a first-class input. Changed in the implementation stage so dictionary and code move together.
- Overhang must follow s 192(5) (other entitlements fixed, Parliament grows), not a "re-allocate among the remaining parties" variant; the two differ whenever an overhang exists, so an overhang oracle is mandatory.
- Threshold bypass makes electorate-win probabilities for ACT, Green, Te Pāti Māori and NZ First candidates a hard input to the later assembly (see inventory below).

## Inventory: can the candidate layer name minor-party winners?

Checked in repo artifacts only (no run, no new data); question raised by the process audit (item A3).

- **Historical frames: yes, structurally.** The Stage39–47 candidate model assigns a share vector to every candidate in a slate, whatever the party, and winners are the per-draw maxima. `data/processed/uncertainty-tails/evaluation.json` stores per-seat vectors for named seats (for example Epsom 2011 carries 13 candidate options with simulated means), and the specifications report "full-slate winner frequencies" with `zeroWinnerProbabilityCount`. "National/Labour/other" in Stage44–47 is the uncertainty-class grouping used to scale variance, not a limit on which candidates can win.
- **Not calibrated.** Every Stage39–47 document labels winner frequencies as diagnostics. Minor-party seats (Epsom-type personal-vote contests) rely on the "other" variance class and the Gaussian development default; a frequency of zero in a finite draw bank is not a zero probability. Using them for the threshold bypass inherits that.
- **2026: no named-winner output exists yet.** Stage40 records 70 of 71 targets with partial or unknown slates and no complete slate; Labour's electorate assignments are unpublished there, ACT's Seymour is context only, TPM has two confirmed 2026 candidates, and the 2026 party ballot roster is not final. Nominations close noon 8 Oct. The Māori seats lack a baseline and poll layer (Stage40, roadmap).
- **Consequence for MMP assembly.** Which minor parties can clear the threshold via an electorate depends on (a) the post-close official slate, (b) the Māori baseline for TPM, and (c) an explicit decision on how uncalibrated winner frequencies feed qualification. These are inputs to a later assembly stage, not to the allocation core, which takes electorate winners as given. A cheap sensitivity (qualification probability bounds from the existing Stage44–47 draws) is possible once slates exist; none is claimed here.

## Module plan notes (for the proposed stage)

- Pure TypeScript, no DOM or React imports, no `Date.now`/`Math.random`; inputs and outputs are plain serializable objects so the same function runs in a module Web Worker.
- Inputs: integer national valid party votes per ballot party; per-party electorate seat counts (general + Māori) plus an explicit independent/off-ballot constituency winner count; rules-version identifier citing this document. Output: the `MmpAllocation` shape in `src/types/domain.ts` plus the per-quotient allocation order for auditing.
- Explicit-result branches (typed result or error, never a guess): exact ties at the cut-off (s 191(9) decides by lot, which the model cannot do), unknown ballot-party or component-party mapping, and cancelled electorate polls.
- Edge-case tests: 4.99% versus 5.00%; sub-5% party with one electorate (ACT-style); independent winner reducing the seats to 120 − n; sub-5% party with zero electorates excluded; several overhang parties at once; overhang party's entitlement computed from the same single 120-seat run; electorate winners fewer than entitlement; party with all votes; very close quotients decided by exact cross-multiplication; invariance under scaling all votes; replay of 2008–2023 official tables.

## Source ledger

| Source | Used for | Result |
|---|---|---|
| Electoral Act 1993, version 238.0 as at 1 Jan 2026 (uploaded text extraction; preserved raw file above) | ss 3, 35, 45, 127A, 153–153E, 179, 191–193 | Read in full for the sections cited |
| [Electoral Commission, How are MPs elected?](https://elections.nz/democracy-in-nz/what-is-new-zealands-system-of-government/how-are-mps-elected) | Plain-language corroboration | Read via fetch tool; no page date |
| [electionresults.govt.nz, Sainte-Laguë formula explained (2017 edition)](https://www.electionresults.govt.nz/electionresults_2017/statistics/sainte-lague-formula.html) | Corroboration of items 4, 6 | Read via fetch tool |
| [Electoral Commission, Official results for the 2023 General Election (3 Nov 2023)](https://elections.nz/media-and-news/2023/official-results-for-the-2023-general-election) | Item 6, 10 evidence | Read via fetch tool |
| [Electoral Commission, Electorate boundaries finalised (8 Aug 2025)](https://elections.nz/media-and-news/2025/electorate-boundaries-finalised) | Item 11 | Read via fetch tool; no totals stated |
| [Stats NZ, General electorates down by one…](https://www.stats.govt.nz/news/general-electorates-down-by-one-number-of-maori-electorates-stays-at-seven/) | Item 11 | Headline only |
| [Ministry of Justice, Electoral law changes](https://www.justice.govt.nz/about/news-and-media/news/electoral-law-changes/) | Item 13 | Read via fetch tool; undated, cites Royal Assent 19 Dec 2025 |
| [NZ Initiative, Unravelling MMP](https://www.nzinitiative.org.nz/reports-and-media/reports/unravelling-mmp-how-the-2026-election-could-break-the-voting-system-from-two-sides/document/946), [Peden brief](https://www.ourcommons.ca/Content/Committee/421/ERRE/Brief/BR8391757/br-external/2PedenR-e.pdf), [Wikipedia](https://en.wikipedia.org/wiki/Electoral_system_of_New_Zealand) | Secondary corroboration only | Read via fetch tool |

## Implementation stage (done: see [mmp-allocation-core.md](mmp-allocation-core.md); design below was frozen first)

**Question:** given fixed national valid party-vote counts, electorate winners by party, independent/off-ballot winners and the party-vote ballot roster, does a deterministic, DOM-free, serializable TypeScript allocator in `src/models/mmp` reproduce the official 2008–2023 seat allocations exactly, including every overhang case?

**Frozen design (statute-backed, to be recorded before code):**
1. Qualify: party on the ballot with party votes ≥ 5% of total valid party votes of listed parties, **or** ≥ 1 constituency win (own or component-party). Others are deleted.
2. Seats to allocate N = 120 − (independent or off-ballot constituency winners).
3. Quotients v/(2k+1) for qualifying parties; take the N highest, comparing by exact integer cross-multiplication; ties at the cut-off by lot, surfaced as an explicit `exactTie` result rather than silently resolved.
4. Entitlement = quotients taken; list seats = max(0, entitlement − constituency seats); overhang = max(0, constituency seats − entitlement); equal ⇒ zero list seats.
5. Parliament size = 120 + total overhang (independent seats sit inside the 120); list exhaustion yields `unfilledSeats`; a cancelled electorate poll is an explicit input affecting only the filled count.

**Validation:** official seat tables for 2008, 2011, 2014, 2017, 2020 and 2023 (inventory of what is preserved is the first task; any missing table is one bounded Electoral Commission acquisition with checksums before use); independent hand-worked examples; property tests (total = 120 + overhang, scale invariance, monotonicity in votes, 4.99%/5.00% boundary, one-electorate bypass, multiple overhangs, independent winner, exact tie flagged, list exhaustion).

**Do not:** wire into forecasts or Monte Carlo, build electorate probabilities, touch the frontend, `.github/workflows` or Stage47 files, or start any later stage. Checks: `npm run test`, `typecheck`, `build`, plus the dictionary/doc updates and registering the Act text in `data/sources.json` with the source-validation tests re-run. No Python, no new dependencies.


