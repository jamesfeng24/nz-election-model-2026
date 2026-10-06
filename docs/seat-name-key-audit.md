# Seat-name key audit (6 October 2026)

One question: where does the repository join seats across elections by exact `electorateName`, what does that drop, and can it be fixed without touching preserved outputs?

Nothing frozen is changed. The audit and an additive Stage 10 supplement are produced by `python3 -m scripts.audits.seat_name_keys` (`--check` verifies), outputs in `data/processed/audits/seat-name-keys/` (`audit.json`, `stage10-keyed-additions.json`, `manifest.json`), tests `scripts/tests/test_seat_name_keys.py`.

## The data problem

Seat names are spelled differently across elections by diacritics only. Twelve seats have more than one spelling in the candidate occurrence table (`data/processed/models/candidate-overperformance/occurrences.json`):

| Seat (folded) | Spellings and elections |
|---|---|
| Kaikōura, Māngere, Ōtaki, Rangitīkei, Tāmaki, Taupō, Te Atatū | 2008 without macrons; 2011 to 2023 with |
| Ōhariu | 2008 `Ohariu`; 2011 `Ōhariu`; 2014 to 2023 `Ōhāriu` |
| Whangārei | 2008 to 2017 `Whangarei`; 2020, 2023 `Whangārei` |
| Ikaroa-Rāwhiti, Tāmaki Makaurau, Te Tai Hauāuru (Māori) | 2008 without macrons; later with |

Within any one election the folded name is unique, so a case- and diacritic-insensitive key that keeps spaces and hyphens (`fold` in `scripts/audits/seat_name_keys.py`; `key()` in `scripts/transform/historical.py` is the same without spaces) identifies a seat without ambiguity. Where an electorate or occurrence ID exists, prefer it.

## What exact-name joins miss

| Location | Join | Effect |
|---|---|---|
| `scripts/models/replacement_candidate/inventory.py` `_indexed` and `same_chain` (Stage 10) | seat index keyed by exact name; continuation test compares exact seat names | 52 party-seat records absent from the pinned inventory (1,433 pinned, 1,485 with folding): 33 general and 7 Māori in 2008-11, 5 Ōhariu in 2011-14, 7 Whangārei in 2017-20. 2 of them are primary eligible: the same-person incumbent continuations of Colin King (Kaikōura, National) and Peter Dunne (Ōhariu, United Future) in 2008-11 (pinned primary cohort 44, folded 46). Of the other 50, 47 are `unresolved_identity`, 2 are `retrospective_distinct_people` and 1 is Dunne's 2011-14 continuation (changed boundary). Every pinned record is reproduced exactly. |
| `scripts/models/candidate_persistence/identity.py` `_chain_key` and `official.py` chain key (Stage 8) | chain of same candidate name, party, **exact seat name**, scope across years | 534 adjacent same-name same-party chain links with folding against 517 exact: 17 are not chained (for example Dunne, Upston, Guy, Sharples, Turia). |
| `scripts/models/candidate_persistence/pairs.py` `_reasons` and `same_chain` (Stage 8) | exact seat-name equality gives `different_electorate_or_scope` | 3 persistence pairs wrongly excluded: Kaikōura (King) and Ōhariu (Dunne) 2008-11, both in a primary transition, and Ōhariu 2011-14 (changed boundary anyway). |

Fail closed (a macron seat reaching them would raise, not drop silently, and none currently does): `scripts/models/replacement_candidate/identity_evidence.py` lines 59-60 (adjudication seat name must equal both occurrences'), `scripts/models/historical_split_ticket/analysis.py` and `sensitivity.py` (`by_name[target_year][('general', source-year name)]`), `correction.py` lines 100 and 125, `scripts/readiness/geography.py` `source_electorate` (exact 2023 name; raises on a miss, so Stage64's 2026 boundary work must key by the folded name or ID), `scripts/evidence/candidate_transitions/run.py` `supplementary` (same-year curated name, unique-hit check).

Safe (macron-insensitive `key()` or `_fold`, or same-election only): `scripts/boundaries/secondary.py` and `party_inputs.py`, `scripts/models/party_vote_transform/inputs.py`, `scripts/models/nat_lab_elasticity/records.py`, `scripts/audits/stage6.py`, `scripts/checkpoints/stage25_geography.py` and `identity_cohort.py` (label key), `scripts/models/freshman_incumbency/inventory.py`, `scripts/models/candidate_overperformance/inputs.py`, `scripts/transform/historical.py` and `modern_election.py`, `scripts/models/replacement_candidate/maori_winners.py`, `scripts/checkpoints/adjudicate_identity.py` (same-year). Stage 51 and Stage 55 join by occurrence ID. The TypeScript app joins by `electorateId`. This list comes from reading the join lines found by searching for `electorateName`, `sourceElectorate`, `targetElectorate` and seat-name dictionary keys, not every file in full; a later join added without `key()` would reintroduce the problem.

## Why nothing is fixed in place

The Stage 8 and Stage 10 outputs are preserved: `data/processed/models/replacement-candidate/inventory.json` and `scripts/models/replacement_candidate/inventory.py` are hash-pinned by 35 data files (29 are other stages' preservation or prior-data contracts) and by the Stage39 fingerprint (`.github/validation/stage39.json`). The repository rule is to preserve validated historical outputs and never edit those pinned hashes. A fix to `inventory.py` would therefore not be a re-run: it would change the Stage 10 manifest and make the cheap preservation `--check` behind each of those 29 contract files fail until its pins were rewritten, and it would force Stage39's full validation (about 143 seconds of construction plus verification on the saved Linux log). The frozen Stage45 to Stage48 and Stage54 pipelines are not affected: none of their import closures or consumed paths (checked with `scripts/validate/ci_frozen.closure`) contains a Stage 8 or Stage 10 file, and none lists a cache dependency on them.

## Materiality

Stage 10's operational replacement effect (-6.64pp) is not deployed and Stage 55 retained neutral R, so the two missing primary records (two same-person winner continuations in 44 pinned) affect no live component. The 17 unchained Stage 8 links and 3 misflagged pairs are in already-superseded historical diagnostics; whether they would move those diagnostics was not measured (the Stage 10 analysis could not be re-run on folded records without rebuilding its own consistency checks, which pin the exact-name inventory). No effect on Stage45 to Stage48 or Stage54.

## Recommendation

1. Leave Stage 8 and Stage 10 outputs as preserved and treat `stage10-keyed-additions.json` as the corrected additive record. It is the only artifact that lists what the exact-name join missed.
2. New cross-election seat joins use electorate or occurrence IDs, or `fold`/`key()`. Stage64 (2026 boundaries) and any new inventory should be reviewed against this rule.
3. Re-pinning Stage 8 and Stage 10 outputs and every dependent preservation contract is a separate, explicitly authorized task; it is not recommended on this evidence.
