# 2023 published split evidence: bounded inconsistency

The preserved official general aggregate Te Pāti Māori row reports 29,607 party votes and 6.69% Party Vote Only. Summing all held general-electorate local Party Vote Only cells gives the closed rounding enclosure **[1937.4629, 1940.3855] votes**. The aggregate cell gives **[1979.22795, 1982.18865] votes**. These intervals are disjoint by at least **38.84245 votes**. These are validation bounds, not reconstructed joint counts.

For each published percentage p and row count n, use n × [max(0,p−0.005), min(100,p+0.005)] / 100. Compute and sum using exact rational arithmetic. Closed endpoints conservatively admit either tie-rounding convention. Intersecting envelopes do not prove unique integer cell counts; disjoint envelopes prove incompatibility even under this conservative enclosure. No midpoint-equality test, tolerance increase, rescaling or imputation is used.

## Investigation and scope

- All 147 preserved official CSVs pass their registry SHA-256 checks. Parsing retains source labels, percentages and row totals. No files were downloaded or altered during this investigation.
- All 65 local files reconcile to electorate party/candidate controls, including the explicitly non-behavioural Port Waikato publication. All candidate-destination aggregate/local joins reconcile within their rounding envelopes. The mismatch is confined to Party Vote Only and its row/column consequences.
- Within-election Leighton Baker/NZ Loyal labels have explicit joins. The Freedoms NZ constituent-affiliation mapping applies to aggregate candidate destinations only. Neither mapping touches Party Vote Only, so these joins do not explain this discrepancy.
- General/Māori/national party denominators reconcile exactly, including Port Waikato. General and Māori aggregate percentage envelopes reconcile with the national table. Independent local and aggregate rounding has already been included on both sides of each comparison.
- Port Waikato contributes 42,657 valid-plus-informal party votes, including 381 Te Pāti Māori votes. Its local report publishes zero destinations. Removing its denominator would contradict the official aggregate row counts and is not done.
- The cancellation-adjusted Te Pāti Māori row would allocate 29,226 votes. Its aggregate destination sum permits [29238.39285, 29296.1265], which is also disjoint. Aotearoa Legalise Cannabis Party has a similar row-sum discrepancy.
- Fifteen Party Vote Only local/general comparisons are disjoint. Together with two general row-sum discrepancies and four general/national column-control discrepancies, the report records **21 failed reconciliation assertions**, not 21 independent errors. No other aggregate destination is exempted.

## Possible relationship to disallowed ballots — not an allocation

Held general-contest controls give 34,068 Party Vote Only votes; the published aggregate total percentage permits [34611.4132, 34878.6828]. National held-contest controls give 41,791; the national aggregate permits [42295.3005, 42582.0483].

Port Waikato publishes 804 candidate-ballot special-disallowed votes and 185 party-ballot special-disallowed votes: a difference of 619. Adding 619 to the respective held-contest controls lies within both published aggregate envelopes and their weighted-row envelopes. This is consistent with a cancellation/disallowed-ballot reporting difference, but the preserved sources do not identify its party-level allocation or explain it. It is **not** proof that 619 ballots were substantively Party Vote Only, and no processed cell receives such an assignment. The cause remains unresolved at source-publication level.

The exact national summary reports 1,849,366 non-split and 1,018,112 split votes, summing to 2,867,478. Its non-split rows reconcile with published aggregate diagonals (informal-party non-split uses Party Vote Only). Its residual split counts include cancellation-related ballots; they are not wholly behavioural observations and cannot identify local joint cells.

## Machine-readable evidence and failure boundary

`data/source-plans/2023-split-discrepancies.json` records the reviewed exact rational endpoint fingerprints and provenance IDs. `split_intervals.py` recomputes them from sources. A new discrepancy, altered endpoint, or missing reviewed discrepancy fails validation. It does not ignore an entire party, column, table or year. The same records are exported in the validation and split JSON, with status `unresolved-official-source-discrepancy`; overall split status is `validated-with-source-discrepancies`.

Official sources are under `data/raw/elections/2023/statistics/csv/`; exact URLs, retrieval timestamps and checksums are in `data/sources.json`. Relevant publications are split-votes-general.csv, split-votes-all.csv, the 65 general local split files and both turnout tables. All raw and reported values are preserved; candidate/split models must not treat these unresolved aggregate observations as reconciled exact evidence.
