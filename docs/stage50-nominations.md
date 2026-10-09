# Stage50: official 2026 nominations and the live-roster refresh

**Question.** When the Electoral Commission publishes the official 2026 electorate nominations (after the 12:00 NZDT 8 October close), can the live roster be rebuilt from them? The rebuild must be reproducible, checksummed and fail-closed, with every seat a complete official slate, so the assembly can simulate general seats.

Authorized by James on 2026-10-07 (roadmap item 3), with two decisions:
- **Acquisition.** James downloads the official files and supplies them unchanged. If they are late, the tool-rendered text of the official page is the fallback, with its own provenance.
- **Superseding.** The official list replaces party announcements in the live roster. The announcements stay in the 2026-10-05 snapshot and are compared in a reconciliation report.

This stage has two parts:
1. **Pipeline, before the close.** This document and its PR. Built and tested on a labelled synthetic list.
2. **Acquisition and refresh, after publication.** A second PR, run with the procedure below.

## Pipeline (`scripts/nominations_2026/`)

| Step | Code | Behaviour |
|---|---|---|
| Official table | `official.py` | A line-for-line transcription of the preserved publication: `{schemaVersion 1, sourceId, publishedAt, rows[{electorateLabel, displayName, affiliationLabel, locator}]}`. Affiliation labels map to the 2026 registered parties (exact registered name, key or a listed alias) or `independent`. An unknown label fails. Duplicate candidates in one seat fail. |
| Claims and completeness | `official.py` | Every row becomes a Stage40 `official_nomination` claim dated by the publication. Every electorate in the table gets an `official_complete_nominations` declaration listing its candidates' Stage40 occurrence ids. Any of the 71 electorates missing from the publication fails. |
| Roster snapshot | `refresh.py` → unchanged `scripts.readiness.run.build` | Stage40 runs with only the official claims (no retained announcements), the preserved Schedule C and party register, and the declarations. Stage40's own rules still apply: only elections.nz/vote.nz sources may be official; declarations must be published after 23:00Z on 7 October and before the cutoff; conflicts block completeness. Output: `data/processed/forecast-readiness/snapshots/<date>/`. |
| Candidate features | unchanged `scripts.transport.continuous.readiness.build` | The Stage42 continuous S/R features for the official candidates, with the frozen Stage42 code and identity linkage. Output: `data/processed/nominations-2026/<date>/features-raw.json`. The frozen Stage42 file is untouched. |
| Recentring | `scripts.candidate_fit_2026.run.recentre` | Recentred on the Stage75 all-elections fit. Output: `features-centred.json` (fit id and means checked by the assembly). |
| Reconciliation | `refresh.py` | Official list against the 2026-10-05 announcements: matched, new, and announced-but-not-nominated (flagging whether the party stands someone else there), per-party counts and parties with no ballot group. |
| Config | `refresh.py --apply-config` | Sets `roster.snapshotId`, removes it from `pending`, and points `candidate.features`, `candidate.centredFeatures` and `partyRelationships` at the refreshed files. |

The assembly's `live_slates` now takes general seats only. The Māori seats always come from the Māori layer.

**Test** (`scripts/tests/test_stage50_nominations.py`, about 12 seconds). A SYNTHETIC official table, held in memory only, contains the 206 announced candidates plus one invented Labour and one invented independent per electorate. With it, the tests check:
- all 71 seats become official complete slates;
- independents have no ballot group;
- features cover every candidate and are centred on the live fit;
- the reconciliation is exact;
- the assembly simulates all 64 general seats from the refreshed roster.

The fail-closed tests cover unmapped affiliations, unknown electorates, duplicates, malformed rows and missing seats.

## Procedure after publication (part 2)

1. **Preserve.** James downloads the official electorate-candidate publication (and the party lists, if separate) from elections.nz and supplies the files unchanged. Save them under `data/raw/nominations/<YYYY-MM-DD>/` and record each in a new standalone registry, `data/processed/nominations-2026/source-registry.json` (schema as the Stage40 registry: id, organisation, url, retrievedAt, rawPath, sha256, licence, limitations). `data/sources.json` is frozen and never edited. Commit this checkpoint before any transformation.
   - **Fallback, if the files are not available:** tool-rendered page text, saved as its own file with `contentStatus` stating that it is a rendering, not the original bytes.
2. **Transcribe.** Write a small publication-specific extractor that turns the preserved file into the official table (one row per published candidate, `locator` giving the row or cell). Save the table as `data/processed/nominations-2026/<date>/official-table.json`. If an affiliation label is new, add it to `ALIASES` from the publication, or amend the Stage40 party register if the party registered after 4 October.
3. **Acquisition record.** Write `data/processed/nominations-2026/<date>/acquisition.json` with `snapshotDateNZ`, `acquisitionCutoffUTC`, `sourceRegistryPath` and the tables list.
4. **Run.** `python3 -m scripts.nominations_2026.refresh --acquisition data/processed/nominations-2026/<date>/acquisition.json --apply-config`. Then `--check`, then `python3 -m scripts.nowcast_assembly.run` to regenerate the development gate.
5. **Review.**
   - The reconciliation report.
   - Labour and the other newly known candidates against the classification draft.
   - Any parties without a ballot group.
   - Then open the part-2 PR.

Later withdrawals or corrections become a new dated snapshot, never an edit.

## Part 2: official list applied (10 October 2026)

**Sources.** James supplied the two official Electoral Commission files unchanged. They are preserved under `data/raw/nominations/2026-10-10/` and recorded with checksums in the standalone registry `data/processed/nominations-2026/source-registry.json`:
- `Electorate-Candidates-2026.xlsx`: one sheet, 469 candidates, columns Name, Electorate, Party;
- `Party-lists-for-the-2026-General-Election.pdf`: three pages of party lists.

The exact download URLs were not recorded. elections.nz blocks automated retrieval, and one bounded search found no stable asset URL, so the registry records the publishing host and says so. `retrievedAt` is when the files reached the project (2026-10-09T15:45:30Z, 10 October NZDT). Claims are dated by the spreadsheet's embedded modification time (2026-10-09T00:22:58Z), the earliest moment it can have been published.

**Transcription** (`scripts/nominations_2026/extract.py`, standard library only).
- The spreadsheet becomes `official-table.json`: 469 rows, 71 electorates, each row's locator a cell range. A published name `SURNAME, Given names` becomes `Given names SURNAME`, letters unchanged, because the Stage40 identity linkage parses given-then-surname order.
- The PDF's party headings, transcribed by hand with their page, become `party-lists.json`. They are exactly the 17 parties of the Stage40 register, so every registered party lodged a list and is a 2026 ballot group. List rankings are preserved but not transcribed (the model allocates seats to parties, not people).

**Affiliations.**
- One new alias: `Alliance Party` → Alliance Party of Aotearoa New Zealand.
- Eleven printed affiliations are not registered parties and have no party list: Progressive Party of Aotearoa New Zealand, Money Free Party NZ, NAP, People's Party New Zealand, Economic Euthenics, New World Order McCann Party, Jobseeker Party, Socialist Equality Group, Te Pāti Hira, Balance New Zealand and Your PIC Party, covering 17 candidates. They are listed explicitly in `official.UNREGISTERED`. Each maps to its own `unregistered:<label>` key, with no ballot group, exactly like the 48 independents. Any other unknown label still fails closed.

**Roster.** The refresh produced:
- 469 official nominations, and every one of the 71 electorates is an official complete slate;
- no conflicts and no unmatched claims;
- 64 general-seat slates for the assembly, each with exactly one Labour candidate.

Candidates by party: Labour 71, National 65, Green 55, ACT 48, NZ First 48, independent 48, Opportunity 42, NZ Loyal 16, Alliance 11, NZ Outdoors & Freedom 11, Legalise Cannabis 10, Animal Justice 9, Te Pāti Māori 7, Conservative 5, Vision 4, Free Palestine 1, Te Tai Tokerau Party 1, unregistered 17.

**Reconciliation** against the 2026-10-05 announcements: 179 of 206 announced candidates match by seat, party and name, and 290 official candidates are new.
- The 27 others all have a candidate of the same party in the same seat.
- Every one of the 27 checked is the same person under the official spelling: middle names (Mark Russell Arneil), titles (Hon Ron Mark), accents and hyphens (Menéndez March, Tofilau Tevaga) or a known form (Johno/John Ormond).
- No announced candidate was replaced by a different person.

**Identity links.** No candidate who had a 2023 link under the announced names lost it under the official spelling. One link was gained: Ricardo Menéndez March, whose official spelling now matches 2023.
- 38 names do not parse under the frozen rule (multi-token names with no 2023 surname match, or a bracketed nickname). None of them stood in 2023.
- 23 candidates changed party since 2023, so they get no continuity R, by the frozen Stage40 rule. Examples: Mariameno Kapa-Kingi (Te Tai Tokerau Party) and Tākuta Ferris (independent).

**Config** (`apply_config` now edits only the affected values and keeps the reviewed layout):
- `roster.snapshotId` = `nz-2026-official-nominations-2026-10-10`, and it is no longer pending;
- the candidate features, centred features and party relationships point at the refreshed files;
- `configVersion` is 2026-10-10.1.

The config validator now also requires that a non-null roster's files exist, and that a null roster is listed as pending.

**Classification.** `docs/general-seat-classification-2026.md` was rechecked against the official list.
- Two seats join the core exceptional list as candidate changes:
  - Christchurch Central: Duncan Webb is not standing; Labour stands George Hampton.
  - Wigram: Megan Woods is list-only; Labour stands Dominik Yanzick.
- One fact is corrected: National's Paul Goldsmith does stand in Epsom.
- Every other 2023 holder is restanding in their seat.

The core list is now 15 seats (23%).

**Development gate** (`scripts.nowcast_assembly.run`): the live roster is accepted. The run stays unpublishable on two counts: the classification James has not yet entered (D107), and the four unpolled Māori seats (`maori.unpolledFallbackModel`, D114).

**Not done.**
- No classification entries.
- No Māori candidate mapping: the Māori layer keeps its poll-derived candidate keys, and mapping them to the official Māori candidates is a separate step.
- No model, scale or fit change.
- No edit to `data/sources.json` or to frozen Stage40/42 outputs; the 2026-10-05 snapshot is unchanged.

Reproduce:

```
python3 -m scripts.nominations_2026.extract --check
python3 -m scripts.nominations_2026.refresh --acquisition data/processed/nominations-2026/2026-10-10/acquisition.json --check
python3 -m unittest scripts.tests.test_stage50_official_2026 scripts.tests.test_stage50_nominations
```

## Not done (part 1)

- No official data (part 1 was built before nominations closed at 12:00 NZDT on 8 October; part 2 applies them).
- No classification entries.
- No model, scale or fit change.
- No Māori candidate-id replacement: the poll-derived keys stay until a separate step maps the official Māori candidates.
- No edit to frozen Stage40/42 outputs or `data/sources.json`.
