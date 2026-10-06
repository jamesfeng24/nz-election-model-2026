# Stage56 — manual-adjustment interface and replay tooling

Authorised by the coordinator on James's request (6 October 2026), roadmap items 7 and the tooling half of 8. One question: **through what interface does James enter dated seat-level judgements so that a model + James forecast exists beside the untouched automatic one, and what tooling does the Stage57 historical replay need so that its labels cannot be contaminated?** This stage builds the interface and the tooling. It estimates no scale, changes no model scale, forecast or frozen output, adds no source, and touches neither `data/sources.json` nor any CI registry file.

| Output | Meaning |
|---|---|
| A | Automatic model, never edited by this layer |
| B | Model + James: A with dated, sourced, expiring seat adjustments applied by this layer |
| C | Ordinary-seat automatic calibration set: Stage57 only, built from the frozen labels |

Māori electorates are modelled separately and are out of scope: the schema refuses their ids and the labelling template filters them by electorate type.

## 1. Seat adjustment files

`data/manual-adjustments/nz-general-2026/<electorateId>.json`, one file per general seat (64 valid ids, from the 2026 target frame), created and extended only through the tool (`scripts.manual_adjustment.run add-adjustment`), which writes ids, the hash chain and the digest. The directory is empty until James records a first entry; the loader accepts an empty or missing directory.

```json
{
  "schemaVersion": 1,
  "electionId": "nz-general-2026",
  "electorateId": "nz-general-2026-boundary-001",
  "entries": [
    {
      "entryId": "nz-general-2026-boundary-001#001",
      "supersedes": null,
      "author": "James",
      "recordedAt": "2026-10-10T09:00:00+13:00",
      "expiresAt": "2026-10-18T09:00:00+13:00",
      "reason": "One line: what changed and why it moves this seat",
      "sources": [{"description": "...", "date": "2026-10-09", "url": "https://... or null"}],
      "exceptionalSeat": {"flag": true, "reason": "One line, required when flag is true"},
      "adjustment": {"target": {"kind": "nl_balance"}, "meanShiftPp": 3.0, "extraSdPp": 1.5},
      "unadjusted": {"forecastId": "...", "snapshotSha256": "<hex of the automatic forecast file>", "candidateShares": {"nationalparty": 0.42, "...": 0.0}},
      "previousDigest": null,
      "digest": "<sha256 of this entry>"
    }
  ]
}
```

`adjustment` is `null` for a flag-only entry (the seat is marked exceptional or annotated, nothing moves). Otherwise `target` is `{"kind": "nl_balance"}` (positive shifts share from Labour to National by the stated points, the National+Labour mass and every other candidate untouched) or `{"kind": "party_share", "partyKey": "<2026 ballot group key>"}` (positive raises that party's candidate share; the other candidates are rescaled proportionally). `meanShiftPp` is percentage points of candidate vote share, within ±25 and inside the recorded unadjusted shares. `extraSdPp` is extra standard deviation, in points of the same quantity, 0 to 25.

### What the validator refuses (each raises `AdjustmentError`, never a warning)

- unknown or missing fields (so there is no field that could ask for less uncertainty: a `sdMultiplier` is rejected as unknown, a negative `extraSdPp` as out of range);
- a naive timestamp, an `expiresAt` not after `recordedAt` (every entry is dated and expires), a multi-line or too-short reason, no dated source;
- a shift that takes a recorded share below zero or outside 0-100%; a no-op adjustment (zero shift and zero extra sd); a party key that is not a 2026 ballot group;
- a nonzero mean shift on a seat not flagged exceptional (an adjusted seat is by definition not ordinary and never inherits the ordinary-seat scale; flag-only and extra-uncertainty-only entries may leave the flag false);
- Māori seat ids and ids outside the 2026 general frame;
- history edits: entries are append-only, `recordedAt` strictly increasing, each digest chained to the previous one, so a retrospective edit fails. A new entry recorded while an earlier one is still active must name it in `supersedes`; an expired entry needs no supersession; an entry can be superseded once.

`active_entry(file, as_of)` returns the one entry recorded at or before `as_of`, not expired and not superseded, so replaying an earlier date reproduces what had been entered then.

## 2. The layer (`scripts/manual_adjustment/layer.py`)

Input: an `automatic-seat-forecast` v1 document, per seat the candidate `groups` (party keys) and `draws` (rows on the simplex). The real exporter that writes this from the Stage47/54 composed draws does not exist yet; this stage defines the layer's input only. `apply_layer(forecast, files, as_of)` returns a second document, `model-plus-james-seat-forecast`, holding the automatic file's SHA-256, every adjusted seat's entry, digest, report and drift, and the list of exceptional seats; seats without an active entry are copied unchanged, and the automatic forecast is verified unmodified before returning.

For an adjusted seat the targeted quantity moves in the model's own coordinate (log(N/L), or logit of the party share): `z' = zbar + delta + k (z - zbar)` with `k = sqrt(1 + (extra/sd_z)^2)` and `delta` solved so the mean of the targeted share moves by exactly `meanShiftPp` (checked to 1e-9, also when the shift is zero and only uncertainty is added). Hence **`sd(z') = sqrt(sd(z)^2 + extra^2) >= sd(z)` exactly**, where `extra` is converted from points to the coordinate by the average local slope. A mean shift alone leaves the coordinate sd unchanged; nothing can narrow it; the layer asserts this and fails otherwise.

Limits, stated rather than hidden. The no-narrowing guarantee holds in the uncertainty coordinate in which the Stage45-48 laws are Gaussian. In share space a shift toward 0 or 100% can mechanically compress the interval (the logistic slope is smaller there); the report carries `shareWidth90Ratio` so this is visible. The layer needs draws (a mean-only forecast cannot carry added uncertainty), handles one adjustment per seat entry, and does not propagate a seat adjustment into national totals or the MMP allocation: that belongs to the assembly stage, which must treat B's national result as derived from A's draws plus these seat changes, not as a second national forecast.

## 3. Stage57 replay tooling

James labels every historical general-electorate seat-election 2014-2023 (257: 64, 64, 65 and 64; Port Waikato 2023, the postponed contest, is out as in the layer inventory) `ordinary` or `exceptional` knowing the outcomes. He accepts the selection-bias risk (6 October 2026); the design records that and does not relitigate it. The guards:

| Guard | Mechanism |
|---|---|
| Fixed pre-election checklist | six facts, each `yes`/`no`: `candidate_change`, `boundary_change`, `scandal`, `tactical_arrangement`, `new_strong_challenger`, `other` |
| One-line reasons | every `yes` needs `<fact>_reason`; every label needs `label_reason` (10 to 300 characters, one line); an `exceptional` label must cite at least one fact marked `yes` |
| Blind view | the template builder reads only the boundary crosswalk (`forecast-transport/geography.json`), candidate lists and source-election winners (`elections/*.json`, vote counts dropped), and the Stage51 ledger and transition table; it never opens a model, score, residual or scale file; every column is on an allow-list and column names containing residual, error, score, sigma, prediction, probability, votes, margin and similar tokens are refused; tested |
| Labels frozen before any scale | `freeze-labels` needs complete, valid labels and an explicit attestation that no model residual or error was viewed; it records the SHA-256 of the labels file and of the template and refuses to overwrite; `require_frozen_labels()` is the only supported way for an estimation stage to read labels and fails if the freeze is absent or the labels changed |
| Read-only evidence | identity and evidence columns must equal the regenerated template, so a label cannot be attached to an edited seat |

### The template

`data/processed/manual-replay/labelling-template.csv` (UTF-8, 257 rows, 26 columns) with `template-manifest.json`, regenerated deterministically by `python3 -m scripts.manual_adjustment.run build-template` (`--check` verifies; also asserted by the unit tests). Per row: seat, year, the previous election's winner in the dominant predecessor seat, the National and Labour candidates and the other candidates listed in the official candidate list, boundary evidence, Stage51 candidate-change evidence, and the pre-filled facts.

Pre-filled from repo evidence only:

- `boundary_change`: **no** when the crosswalk certifies identical membership (182 seats, equal to the 182 exact-geography cases), **yes** when it shows a change (75); each yes carries the inheritance and retention bounds in `boundary_evidence`. Electoral-population bounds, not ballots.
- `candidate_change` (the incumbent party's candidate; National and Labour seat holders only, from Stage51): **yes** 60, **no** 188 (incumbent recontested; this says nothing about the other major party's candidate), blank 9 (Epsom ×4, Ōhāriu ×2, Upper Harbour 2014, Takanini 2020, Auckland Central 2023: source winner not National or Labour, or no mapping). Replacements by by-election succession count as changes.
- `scandal`: **yes** for 6 seats whose Stage51 tags are `scandal_context` or `expelled_from_party` (Clutha-Southland 2017, Botany, Invercargill, Rangitata and Southland 2020, Hamilton West 2023). Other Stage51 tags appear in the evidence column but are not turned into a scandal call.
- `tactical_arrangement`, `new_strong_challenger`, `other`: blank for every seat. The repo holds no pre-election arrangement or challenger data; these are the gaps James fills. `previous_election_winner` is shown so that, for example, ACT- and United Future-held seats are visible.

The candidate lists come from the official results files because the repository holds no historical pre-election nomination lists; a candidate who withdrew late may appear. Stage51 evidence is tool-rendered (Stage51 limitations apply).

### Filling and freezing

```
python3 -m scripts.manual_adjustment.run init-labels                      # copies the template to data/manual-replay/labels.csv
python3 -m scripts.manual_adjustment.run validate-labels [--complete]     # work in progress is allowed without --complete
python3 -m scripts.manual_adjustment.run freeze-labels --labeller James --attest-no-residuals
python3 -m scripts.manual_adjustment.run check-freeze
```

Fact definitions for the checklist. `candidate_change`: the seat's incumbent-party candidate is not the previous incumbent (retirement, resignation, deselection, party switch, by-election successor). `boundary_change`: the seat is materially different from its predecessor. `scandal`: a pre-election scandal or misconduct allegation touching the incumbent or a leading candidate. `tactical_arrangement`: a known or widely reported arrangement or endorsement for a candidate of a party that is not standing a serious candidate (the Epsom type). `new_strong_challenger`: a newly standing candidate with a credible winning claim who was not in the previous contest. `other`: any further fact James would have acted on before voting opened. Judge only from information available before voting first became possible; do not open model residual, score or width files while labelling. A relabel after any scale estimate is a new, separately recorded design.

## Recorded defaults (reversible; James may change them)

1. A numeric mean shift requires the exceptional flag, because B's adjusted seats must not enter the ordinary-seat calibration set C. Flag-only or uncertainty-only entries do not.
2. Shifts are in percentage points of candidate share, not log-odds, so they read as James thinks of them; the log-odds coordinate is internal.
3. `unknown` is not a permitted answer at freeze: a fact is `yes` or `no`, where `no` means none known before voting opened.
4. Labels are a CSV (editable in a spreadsheet, saved as UTF-8) rather than JSON; the frozen artefact is that file plus its hash.

## Not done

No scale is estimated; no label is entered or frozen; no 2026 adjustment exists; no real automatic seat forecast is exported to this layer's input format; no change to Stage44-55 outputs, scales, widths or any frozen artefact; no frontend change; no source or acquisition; no Māori model; no CI registry or `data/sources.json` edit. The ordinary-seat sigma, the replay scoring (Stage57) and the assembly of B into national and MMP results remain separate, separately authorised work.
