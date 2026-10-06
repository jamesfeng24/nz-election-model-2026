# Candidate-transition evidence pass (National and Labour electorates, 2008–2023)

Evidence acquisition only. This pass answers one question: across every adjacent election pair 2008→11, 2011→14, 2014→17, 2017→20 and 2020→23, which National and Labour electorate candidate changes are genuine incumbent-to-successor transitions, and of what type. It fits no replacement effect, changes no R/S code and touches no model output. `selectedOperationalReplacementEffectPP` stays `null`. The later `R_new = a + rho R_old` analysis is a separate, unauthorized-here stage.

## What was built

| Artifact | Role |
|---|---|
| `data/raw/candidate-transitions/2026-10-06/` | 78 preserved tool-rendered extracts plus the search-result listing (committed before transformation) |
| `data/processed/evidence/candidate-transitions/source-registry.json` | Dated registry: id, URL, raw path, SHA-256, limitations, licence. Separate from `data/sources.json`, which about 25 historical stages hash |
| `data/source-plans/candidate-transition-curation.json` | Hand-authored judgements: 75 transitions, 8 identity judgements, 1 continuation note, 1 supplementary seat gain |
| `scripts/evidence/candidate_transitions/{universe,run}.py` | Deterministic generator with `--check` |
| `data/processed/evidence/candidate-transitions/` | `incumbent-seat-ledger.json`, `transition-table.json`, `transition-table.md`, `identity-judgements.json`, `summary.json`, `manifest.json` |
| `scripts/tests/test_candidate_transitions.py` | 15 tests |

## Universe

Every National and Labour electorate winner (general and Māori seats) at 2008, 2011, 2014, 2017 and 2020 is an incumbent seat: 333 in all (62, 64, 68, 70, 69 by pair). The winner is the candidate with the most published votes among held candidatures; a tie raises an error, and winners are verified against the published elected flag and the Stage10 Māori overlay. Each is joined to the same party's candidate in the dominant Stage25 successor seat at the next election. Māori seats are included and flagged (`scope = maori`); no Māori baseline is needed for this evidence pass.

The effective incumbent at the target election is the sitting MP after any by-election. A by-election winner who recontests is a continuation of the effective incumbent, not a newcomer, and is classed `by_election_succession` or `by_election_party_change`.

## Identity policy (James's rule)

Names are not matched by exact string only. Macrons, transliteration, nicknames, middle or title tokens, name order and Pacific title names are resolved on evidence and judgement, with the confidence and reasoning recorded for each call.

1. Stage26 `name_match` flags (exact name, middle omission, frozen nickname; counts in `summary.json`) accept 250 same-party successor-seat pairs automatically.
2. Eight further same-person variants are curated with evidence: Su'a Viliamu / Sua William Sio (Māngere, three pairs), Peseta Samuela / Samuelu Masunu Lotu-Iiga, Nicolas Rex / Nick Smith (two pairs, direction differs), Meka / Melissa Heni Mekameka Whaitiri, and Neru Leavasa / Anae Neru Asi Tuiataga Leavasa.
3. A name difference that remains after (1) and (2) must be a curated change; a curated change on a row the rules treat as same-person fails the build, and so does an unclassified difference.

Of the 59 National/Labour Stage10 "apparent changes" in the 2008→11, 2014→17 and 2020→23 pairs, 20 are same-person name variants (17 automatic, 3 curated). The old exact-string count therefore overstates replacements.

## Results

333 incumbent seats: 258 continuations (250 automatic, 8 curated) and **75 candidate changes**.

| Transition type | n |
|---|---|
| retirement | 53 |
| resignation_before_election | 5 |
| by_election_succession | 9 |
| by_election_party_change | 2 |
| party_change | 3 |
| boundary_complication | 1 |
| deselection | 1 |
| death_or_illness_withdrawal | 1 |

Changes per pair: 12, 14, 15, 17, 17. Confidence: 52 high, 23 medium (low is unused). **60 changes are election-time incumbent exits** (the effective incumbent did not recontest and the departure is neither a party switch nor a boundary move); this is the cleanest incumbent-to-newcomer set. Tags such as `list_only` (7), `scandal_context` (4), `expelled_from_party` (3), `international_appointment` (3) and `maori_seat` (3) are carried for later stratification, not for fitting.

Cases worth knowing: National's Kaikōura 2014 is a deselection (the sitting MP lost selection in December 2013), which a "did not stand" list would hide. Port Waikato 2023 is a postponed contest (candidate death) classed as a continuation. Waitakere (2011→14 pair) is a boundary complication (the incumbent moved to Upper Harbour). Tāmaki (2008→11 pair) is a death or illness withdrawal. No National/Labour transition was typed as an unusual third-party environment; the vocabulary keeps the category available.

A departure with no documented reason would be recorded as `unknown`, never as retirement by default; none was needed.

## Reconciliation with Stage10

Stage10 listed 61 exact-name contrasts across three pairs (including ACT and United Future). Same-person variants and by-election successions are not election-time replacements. Three ledger changes fall in seats absent from the Stage10 inventory (Te Atatu 2008, Rangitikei 2008 and Tāmaki 2008 pair). The cause was not investigated; Stage10 outputs are unchanged.

## Provenance and limitations

- Evidence is tool-rendered (WebFetch/WebSearch summaries of Wikipedia and news pages), not original bytes, following the Stage40 precedent. Each extract is hashed in the registry and each claim carries a date, a `dateKind` (event or publication) and a `reading` (direct or inferred).
- Some summariser-rendered tables contain errors (a by-elections list with spurious 1907/1908 and 2004 rows, a mislabelled Falloon successor line, an inconsistent Dalziel citation date). These are recorded in registry limitations and used only where cross-checked against a second source.
- Pre-2008 history, ACT, NZ First, Green and other parties are out of scope.
- A change is a transition fact, not a statement about candidate quality or vote effect. Nothing here licenses a replacement coefficient.

## Reproduction

```
python3 -m scripts.evidence.candidate_transitions.run          # regenerate
python3 -m scripts.evidence.candidate_transitions.run --check  # byte-for-byte check against manifest
python3 -m unittest scripts.tests.test_candidate_transitions
```

`manifest.json` records SHA-256s of the nine inputs, three generator files and five outputs. No network access is needed.
