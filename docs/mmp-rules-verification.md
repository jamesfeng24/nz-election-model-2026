# MMP rules verification — 2026-10-06

Documentation-only checkpoint. **No data, code, model, coefficient, test or workflow changed.** One question: which 2026 MMP seat-allocation rules named in [statistical-specification.md](statistical-specification.md) (items 10–12, "requested design requirements, not independently verified") can now be supported by official sources, and which remain open? Authorized by Corinna on 2026-10-06 as a rule check only; implementation is **not** authorized (see the proposal at the end).

## Evidence quality — read first

- Every page below was read through the session's web-fetch tool, which returns a model-written extraction of the page, not the page bytes. Quoted strings are what that tool returned for a "quote verbatim" request and were **not** byte-checked or checksummed. They are tool-readable evidence in the same sense as the Stage40 readable extracts, not preserved raw sources. Nothing was added under `data/raw/`.
- **The statute text itself was not obtained.** `legislation.govt.nz` (section pages and "whole" view), NZLII, `natlex.ilo.org` (2014 reprint PDF: only the first ~108k characters are readable, which stops before Part 6), and the Parliamentary Practice chapter (blocked by robots.txt) were all unreadable; direct `curl` to the official hosts is denied by the environment's egress policy. What is verified is the Electoral Commission's own plain-language statement of the rules, which is the body that administers them. Section numbers come from legislation.govt.nz page titles and the 2014 reprint contents page (see ledger), not from section text.
- Status vocabulary: **Official** = stated on an Electoral Commission page; **Corroborated** = Official plus an independent secondary source; **Derived** = arithmetic from verified inputs; **Open** = not found in any readable source.

## Findings

| # | Rule | Finding | Status |
|---|---|---|---|
| 1 | House size | 120 seats nominally. "Your two votes help decide which candidates get the 120 seats in Parliament." The Commission's divisor description allocates "the 120 highest numbers (which are called quotients)". | Official |
| 2 | Qualification | A party qualifies for a Sainte-Laguë share with **at least 5% of the party vote or one electorate seat**: "If a party gets at least 5% of the party vote or wins an electorate, we use the Sainte-Laguë formula to decide how many seats it gets." The 2017 page words the threshold as "5% of the total number of party votes". Winning an electorate seat is an alternative route, not an additional requirement. | Official; Corroborated (Peden brief to the Canadian electoral-reform committee cites ACT, Māori Party and United Future entering below 5% via electorate wins) |
| 3 | Allocation | Sainte-Laguë: each qualifying party's nationwide party vote is divided by 1, 3, 5, 7, 9, 11, 13 … and the 120 highest quotients give both each party's seat count and the order of allocation. | Official |
| 4 | Electorate seats first | A party's seats first go to its electorate winners; remaining seats go to its list candidates in party-ranked order. | Official |
| 5 | Overhang | A party that wins more electorates than its entitlement "does not receive any list seats. It keeps the extra seats, and the size of Parliament is increased by that number of seats until the next general election." So the other parties' entitlements are not recomputed; Parliament size is 120 plus overhang. | Official |
| 6 | Overhang evidence, 2023 | Official 2023 results: "The number of seats in Parliament on these results will be 122"; "There is an overhang of two seats because Te Pāti Māori won more electorate seats than it would otherwise have" (6 electorate, 0 list, 3.08%). | Official |
| 7 | Electorate count, 2026 | 64 general plus 7 Māori = 71 electorates. Commission boundary release (8 Aug 2025): 19 unchanged, 49 general and 3 Māori adjusted (19+49+3 = 71). Stats NZ headline "General electorates down by one, number of Māori electorates stays at seven" (body text unreadable). Matches the repo's Schedule C inventory (Stage40). | Official + repo; Derived |
| 8 | List seats, 2026 | Nominal list seats = 120 − 71 = 49. This subtraction is not stated on any readable official page. The NZ Initiative note also says 49. | Derived; secondary corroboration only |
| 9 | 2026 law changes | The Justice Ministry's summary of the Electoral Amendment Act 2025 (Royal Assent 19 Dec 2025) lists enrolment and advance-voting deadlines, a single nomination deadline, Commission board size, donation disclosure, prisoner voting, voting-place offences and digital contact, and **no change to the threshold, electorate exemption, Sainte-Laguë, overhang or house size**. The legislation.govt.nz Act page was headed "Version as at 1 January 2026". No enacted threshold change was found (a 2012 Commission review recommended 4%; not enacted). | Official summary, by absence; not confirmed against Act text |
| 10 | Postponed electorate poll | 2023 results gave 122 seats, and "one more seat will be added to Parliament after the Port Waikato by-election, taking the total to 123". The mechanism is stated only at that level. | Official (fact); mechanism Open |
| 11 | Statute locations | legislation.govt.nz titles: s 191 "Election of other members", s 192 "Determination of party eligibility for list seats" (as at 1 July 2025); 2014 reprint contents also lists s 193 "Selection of candidates" (list candidates). | Titles only |

## Still open (not found in any readable source)

1. **Verbatim text of ss 3, 191–193** and the exact statutory order of operations, including the definition of "party votes" used as the 5% denominator (valid party votes assumed, consistent with the repo's valid-party-vote denominators).
2. **Independent electorate winners.** The repo's `MmpAllocation` carries `independentElectorateSeats`, but no source states whether an independent's seat is inside or on top of the 120. Not needed for qualification (an independent does not qualify any party). Material only if an independent is competitive; low prior, correctness-critical if it occurs.
3. **Tie-breaking** between equal quotients and equal vote totals (assumed lot; unverified). Practically negligible with integer vote counts in the millions but must be an explicit fail-closed branch.
4. **Postponed electorate poll** mechanism (item 10 above) and **list vacancy / list ordering and eligibility** rules (s 193 and related). The latter does not affect seat counts and is deferred, matching the data-dictionary note that list schemas await source review.
5. **A party that wins an electorate through a candidate whose party is not on the party-vote ballot.** The Commission's overhang wording speaks of parties "on the party vote side of the ballot paper"; the treatment of other labels is unverified.
6. **Whether any 2026 amendment beyond the Act-summary page touches Part 6.** Re-check against the current Act text at final readiness.

## Consequences for the repo (no edits made here)

- `docs/data-dictionary.md` `MmpAllocation` convention ("verify/revise conventions against official rules") should become: `nominalSeats` = 120; `parliamentSize` = 120 + overhang (plus any postponed-poll seat once its rule is confirmed); list seats nominally 49 for 2026. Left to the implementation stage so the dictionary and code change together.
- Overhang must follow the Commission's description (other parties' entitlements fixed, Parliament grows), not a "re-allocate 120 among the remaining parties" variant. The two differ whenever any overhang exists, so an overhang oracle is mandatory.
- Threshold bypass makes electorate-win probabilities for ACT, Green, Te Pāti Māori and NZ First candidates a hard input to the later assembly. Whether the Stage44–47 candidate layer produces named minor-party winner probabilities is **not verified here** and belongs in the implementation stage's input inventory.

## Source ledger (retrieved 2026-10-06, web-fetch extraction, no checksums)

| Source | Used for | Result |
|---|---|---|
| [Electoral Commission, How are MPs elected?](https://elections.nz/democracy-in-nz/what-is-new-zealands-system-of-government/how-are-mps-elected) | Items 1, 2, 4, 5 | Read; no page date shown |
| [electionresults.govt.nz, Sainte-Laguë formula explained (2017 edition)](https://www.electionresults.govt.nz/electionresults_2017/statistics/sainte-lague-formula.html) | Items 2, 3, 5 | Read; the 2023 edition of the same page was refused by the fetch proxy and not read |
| [Electoral Commission, Official results for the 2023 General Election (3 Nov 2023)](https://elections.nz/media-and-news/2023/official-results-for-the-2023-general-election) | Items 6, 10 | Read |
| [Electoral Commission, Electorate boundaries finalised (8 Aug 2025)](https://elections.nz/media-and-news/2025/electorate-boundaries-finalised) | Item 7 | Read; states no totals or list-seat count |
| [Stats NZ, General electorates down by one…](https://www.stats.govt.nz/news/general-electorates-down-by-one-number-of-maori-electorates-stays-at-seven/) | Item 7 | Headline only |
| [Ministry of Justice, Electoral law changes](https://www.justice.govt.nz/about/news-and-media/news/electoral-law-changes/) | Item 9 | Read; undated, cites Royal Assent 19 Dec 2025 |
| [Peden, New Zealand's Electoral System (undated brief)](https://www.ourcommons.ca/Content/Committee/421/ERRE/Brief/BR8391757/br-external/2PedenR-e.pdf) | Items 2, 5 (secondary) | Read; cites no section numbers |
| [NZ Initiative, Unravelling MMP](https://www.nzinitiative.org.nz/reports-and-media/reports/unravelling-mmp-how-the-2026-election-could-break-the-voting-system-from-two-sides/document/946), [Equal Justice Project](https://www.equaljusticeproject.co.nz/articles/the-electoral-amendment-act2025), [Wikipedia, Electoral system of NZ](https://en.wikipedia.org/wiki/Electoral_system_of_New_Zealand) | Secondary corroboration only (items 2, 8, 9) | Read |
| legislation.govt.nz Act pages and section pages, NZLII, natlex 2014 reprint, Parliamentary Practice ch. 2 | Statute text | **Not obtained** (403 / truncated / robots.txt) |

## Inventory: can the candidate layer name minor-party winners?

Checked in repo artifacts only (no run, no new data); question raised by the process audit (item A3).

- **Historical frames: yes, structurally.** The Stage39–47 candidate model assigns a share vector to every candidate in a slate, whatever the party, and winners are the per-draw maxima. `data/processed/uncertainty-tails/evaluation.json` stores per-seat vectors for named seats (for example Epsom 2011 carries 13 candidate options with simulated means), and the specifications report "full-slate winner frequencies" with `zeroWinnerProbabilityCount`. "National/Labour/other" in Stage44–47 is the uncertainty-class grouping used to scale variance, not a limit on which candidates can win.
- **Not calibrated.** Every Stage39–47 document labels winner frequencies as diagnostics. Minor-party seats (Epsom-type personal-vote contests) rely on the "other" variance class and the Gaussian development default; a frequency of zero in a finite draw bank is not a zero probability. Using them for the threshold bypass inherits that.
- **2026: no named-winner output exists yet.** Stage40 records 70 of 71 targets with partial or unknown slates and no complete slate; Labour's electorate assignments are unpublished there, ACT's Seymour is context only, TPM has two confirmed 2026 candidates, and the 2026 party ballot roster is not final. Nominations close noon 8 Oct. The Māori seats lack a baseline and poll layer (Stage40, roadmap).
- **Consequence for MMP assembly.** Which minor parties can clear the threshold via an electorate depends on (a) the post-close official slate, (b) the Māori baseline for TPM, and (c) an explicit decision on how uncalibrated winner frequencies feed qualification. These are inputs to a later assembly stage, not to the allocation core, which takes electorate winners as given. A cheap sensitivity (qualification probability bounds from the existing Stage44–47 draws) is possible once slates exist; none is claimed here.

## Module plan notes (for the proposed stage)

- Pure TypeScript, no DOM or React imports, no `Date.now`/`Math.random`; inputs and outputs are plain serializable objects so the same function runs in a module Web Worker.
- Inputs: integer national valid party votes per ballot party; per-party electorate seat counts (general + Māori) plus an explicit independent count; rules-version identifier citing this document. Output: the `MmpAllocation` shape in `src/types/domain.ts` plus the per-quotient allocation order for auditing.
- Fail-closed branches (throw a typed error or return an explicit `unverified` flag) for: tied quotients, independent electorate winners, postponed electorate polls, and unknown ballot-party mapping. Tests assert these branches rather than guessing.
- Edge-case tests: 4.99% versus 5.00%; sub-5% party with one electorate (ACT-style); sub-5% party with zero electorates excluded; several overhang parties at once; overhang party's entitlement computed from the same single 120-seat run; electorate winners fewer than entitlement; party with all votes; very close quotients decided by exact cross-multiplication; invariance under scaling all votes; replay of 2008–2023 official tables.

## Proposed implementation stage (not started; needs Corinna's go-ahead)

**Question:** given fixed national party-vote counts and fixed electorate winners, does a deterministic, DOM-free, serializable TypeScript allocator in `src/models/mmp` reproduce the official 2008–2023 seat allocations exactly, including every overhang case?

**Frozen design to record before code:** integer-only quotient comparison by cross-multiplication (no floating point); qualification by ≥5% of valid party votes or ≥1 electorate win by a party on the party-vote ballot; seats from one Sainte-Laguë run over 120; overhang keeps electorate seats, gives no list seats, grows Parliament; ties and unresolved items 2–5 above are explicit fail-closed branches, not guesses; output is the existing `MmpAllocation` contract with the dictionary convention updated in the same change.

**Validation:** official seat tables for 2008, 2011, 2014, 2017, 2020 and 2023 (2023 includes the 2-seat overhang and the Port Waikato note; an inventory of which tables are already preserved is the first task, and any missing table is one bounded Electoral Commission acquisition with checksums before use); independent hand-worked examples; property tests (total = 120 + overhang, scale invariance, monotonicity in votes, 4.99%/5.00% boundary, one-electorate bypass, multiple overhangs).

**Do not:** wire into forecasts or Monte Carlo, build electorate probabilities, touch the frontend, `.github/workflows` or Stage47 files, or start any later stage. Checks: `npm run test`, `typecheck`, `build`, plus the dictionary/doc updates. No Python, no new dependencies.

**Needed from Corinna before starting:** (a) go-ahead; (b) either the text of Electoral Act 1993 ss 3, 191–193 (a pasted PDF or an environment allow-list entry for legislation.govt.nz) so open items 1–5 can close, or consent to implement with those branches fail-closed and documented as unverified.
