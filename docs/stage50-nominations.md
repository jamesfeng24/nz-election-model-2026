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

## Not done

- No official data yet: nominations close at 12:00 NZDT on 8 October.
- No classification entries.
- No model, scale or fit change.
- No Māori candidate-id replacement: the poll-derived keys stay until a separate step maps the official Māori candidates.
- No edit to frozen Stage40/42 outputs or `data/sources.json`.
