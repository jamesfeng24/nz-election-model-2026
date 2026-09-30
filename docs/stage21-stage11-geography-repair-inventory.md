# Stage 21 Stage 11 geographic join repair: pre-score inventory

This is the **post-Stage 11 correction checkpoint before any recalculation of historical scores**. The original twelve files in `data/processed/models/historical-split-ticket/` remain unchanged; their raw SHA-256 hashes are pinned in `data/processed/checkpoints/stage21-stage11-geography-repair/original-artifact-hashes.json`. The correction companion, its exact source/target IDs, and the original versus corrected candidate IDs are under that same checkpoint directory. Reproduce with `python -m scripts.models.historical_split_ticket.correction_run --check`.

## Defect and corrected scope

The Stage 11 applicability generator matched source to target electorates using identical recorded seat names. Its main evaluation (`analysis.analyze` and `_joint_accounting`) and Stage 5 input sensitivity (`sensitivity.evaluate`) repeat that assumption. The certified, unchanged-boundary Stage 14 frame instead identifies source and target **electorate IDs** based on preserved geographic validation. This correction applies only to those certified pairs, with election-local seat, slate and source-matrix checks. It does not equate numeric codes without the geographic frame, normalize diacritics, or infer person identity.

Eight 2008→2011 general seats had source labels without and target labels with macrons: Kaikoura/Kaikōura (5 new partial candidates), Mangere/Māngere (4), Ohariu/Ōhariu (4), Otaki/Ōtaki (6), Rangitikei/Rangitīkei (3), Tamaki/Tāmaki (4), Taupo/Taupō (3), and Te Atatu/Te Atatū (4). The correction recovers **33** partial-applicable categories. The Stage 11 partial sample changes from **247/285/271** to **280/285/271** candidates across 2011/2017/2023, or 803 to 836 total. Every originally partial-applicable occurrence remains in the sample with its original source-dependent fields unchanged. The full unmatched-group restriction and any later analysis gates have not been altered.

The new `certified_pair_for_row` adapter returns separate source and target seats by their pinned IDs and refuses missing or inconsistent rows; the downstream evaluation and sensitivity correction must use it. This checkpoint has **not** read candidate outcomes for new scores or recalculated model results. The original Stage 11 score, selection and operational-null files remain historical, not authoritative corrected diagnostics.

## Downstream dependencies

The corrected companion must recalculate the original Stage 11 main candidate predictions, matched-component local/pooled/party-only comparisons, joint accounting, inherited Stage 10 diagnostic strata, and Stage 5 input sensitivity on the corrected applicability. It must report the original common sample, 33 newly admitted observations, and full corrected sample separately. The original Stage 11 generator and saved artifacts must remain reproducible from their unchanged code and source contracts. Stage 19's diagnostic inventory and manifest pin the old Stage 11 predictions hash and must not silently regenerate. Stage 20 already uses the certified ID frame and is not changed by this correction. Other Stages 12–20 artifacts are retained as historical outputs; any future dependency adjustment must be explicit.

Five focused tests cover each recovered seat, source/target adapter resolution, preservation of the original 803 candidate records, rejection of changed or ambiguous geographic joins, winner-flag invariance and deterministic original-hash/inventory reproduction.

## Subsequent corrected diagnostic checkpoint

After the preceding inventory was committed, the existing Stage 11 formulas were rerun through a certified-ID adapter. It constructs **in-memory only** seat-name lookup aliases after checking the frozen source/target IDs; the official seat labels and original election files remain unchanged. Both the main/joint-accounting and Stage 5 sensitivity paths consume this adapter. The original 803 candidate predictions are checked field-for-field against their saved historical records before a corrected output is accepted.

| 2011 matched party-ballot component | Candidates | Local MAE range, pp | Pooled MAE range, pp | Party-only MAE range, pp |
| --- | ---: | ---: | ---: | ---: |
| Original common sample | 247 | 2.244–2.263 | 3.659–3.677 | 3.855–3.865 |
| Newly admitted certified seats | 33 | 2.530–2.549 | 4.944–4.962 | 4.546–4.556 |
| Corrected full sample | 280 | 2.277–2.297 | 3.810–3.828 | 3.937–3.947 |

The 2017 and 2023 common samples remain 285 and 271, with unchanged predictions and scores. Local matched-component MAE/RMSE ranges remain strictly below pooled and party-only controls in all three holdouts under the original Stage 11 comparison rule. Full published candidate votes lie within the transported full-vote bounds in 102/280, 96/285 and 87/271 events by holdout, **285/836** overall; the original historical checkpoint was 267/803. All **191** comparable contests still have unmatched target party groups, so this does not establish a complete candidate forecast. The corrected operational split-view selection remains null.

The Stage 5 sensitivity for the 2011 corrected sample covers all 280 events. Its observed-valid-party-input MAE range is 2.261–2.280 pp, additive transformed input 2.442–2.461 pp, and proportional transformed input 2.558–2.577 pp. The original 247-event common-sample sensitivity is byte-equivalent to the saved result; the 33 new events and corrected full sample are reported separately in `correction-comparison.json`. These remain conditional on observed target national support and turnout. No Stage 5 transform is selected here.

The authoritative **corrected Stage 11 diagnostic** is the explicit companion `corrected-predictions.json`, `corrected-party-input-sensitivity.json`, `corrected-identity-diagnostics.json`, `corrected-selection.json`, and `correction-comparison.json` under the Stage 21 checkpoint. The original Stage 11 files and Stage 19's old-hash diagnostic inventory remain historical and untouched. Reproduce the corrected companion with `python -m scripts.models.historical_split_ticket.corrected_analysis_run --check`.
