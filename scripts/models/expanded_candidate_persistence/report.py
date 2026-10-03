"""Readable fixed reporting tables from separate construction/evaluation artifacts."""
import argparse
from .common import ROOT,local


def number(x):
    return '—' if x is None else f'{x:.3f}'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'


def build():
    inv=local('inventory.json');data=local('evaluation.json')
    def selected(view='broad',scope='general',scale='additive',protocol='expanding_window'):
        return [f for f in data['folds'] if (f['view'],f['scope'],f['scale'],f['protocol'])==(view,scope,scale,protocol)]
    text=['''# Stage30 — expanded normalized-residual persistence

## Findings and forecasting assessment

Prior residual information deserves retention for a later bounded joint test: carry-forward beats zero in **all five general development holdouts**, including the newly admitted2014/2020 environments. This does not identify uniquely personal retention or establish complete candidate-share improvement. Estimating an unrestricted intercept/slope provides no consistent gain over carry-forward: broad primary MAE is worse in2014/2017/2020 and only0.024pp better in2023. No automatic regularization or variant follows.

S remains preferred for complete-share development, with baseline mandatory. Persistence is a complementary research candidate to test jointly later, not a separately fitted adjustment to add onto S. Parity response remains paused. **All operational selections stay null; null is not an estimated zero effect.** Mathematical estimability, description, retrospective prediction, chronological prediction, development retention and operational selection are separate evidence levels (D060).

## Frozen scope and input roles

Pre-fit checkpoint `d30f646` preceded coefficients; construction `ba81f4e` preceded scoring. Stage26 broad accepted linkage is primary; strict exact-name sensitivity excludes nickname/middle concessions. All accepted links here are algorithmic, not newly documentary-confirmed, and no precision percentage is claimed. Stage26 reversible person groups/acceptance are unchanged. No source-winner or target/later anchor filter, biography selection, career gate, acquisition or new adjudication is used.

The inventory retains3,007 original occurrences,1,630 relationship proposals and356 target-geography records.482 broad residual-supported pairs comprise452 general/30 Māori;413 strict comprise386/27. Fourteen of496 broad accepted relationships and11 of424 strict accepted relationships lack usable residual support. Nonaccepted proposals remain exclusions, never inferred replacements. The whole geographic frame retains changed/ambiguous membership, cancellations and Māori evidence limitations. Stage25 two-sided certification establishes membership, not identical voters. Held status is independently joined from preserved Stage7 candidature, rather than assumed from the geographic layer's unadjudicated statuses.

Parties are pooled within scope, following Stage8; general and Māori are never pooled. Each occurrence retains its candidate-valid and party-valid denominators. Source residual is the frozen source-election candidate-share deviation from a leave-one-whole-contest-out party/election reference; target residual/reference is evaluation-only for its holdout. Stage7 reference populations are not rebuilt on linked records. Proportional/log-odds sensitivities change the expected candidate-share normalization, **not the units of the residual**: every residual remains a candidate-share difference reported in percentage points.

Equation: `r_target = alpha + beta*r_source + error`. Equal-record unrestricted OLS, intercept separately fitted; zero, carry-forward and independently estimated training mean are benchmarked on identical IDs. Numeric centering/RMS scaling only improves solver conditioning. Full rank/finite variation/independent solver agreement are required, without minimum election replication for displaying an identified development estimate. No pseudoinverse rank rescue, clipping, confidence weights, coefficient imports or slope restriction.

Expanding-window training target ≤ holdout source and < holdout target is primary. More-separated training target < source is sensitivity. Overlapping transitions are dependence, not automatically leakage: completed source residuals are permitted even when that election was a training response.2011 regression/mean abstain;2014 more-separated regression/mean also abstain. Zero/carry still score. Other chronological fits are numerically identifiable, including small Māori samples.

## Verified coverage
''']
    text.append(table(['Transition','General broad / strict','Māori broad / strict'],[[f"{inv['coverage'][j]['sourceYear']}→{inv['coverage'][j]['targetYear']}",f"{inv['coverage'][j]['scales']['additive']['broad']} / {inv['coverage'][j]['scales']['additive']['strict']}",f"{inv['coverage'][j+1]['scales']['additive']['broad']} / {inv['coverage'][j+1]['scales']['additive']['strict']}"] for j in range(0,10,2)]))
    text.append('''
## Primary general chronological results

Errors in pp, signed error=prediction−actual. MAE averages absolute pair errors; RMSE takes the root after mean squared errors. Pooled weighting is per record, so smaller partial-election samples do not receive equal election weight. Primary trained comparison excludes the120 earliest records for **all four methods**, while full-frame zero/carry remain reported separately. Macro transition MAE is only a labelled sensitivity.
''')
    fs=selected()
    text.append(table(['Target','Train / eval','α pp','β','Fit MAE / RMSE / bias','Carry MAE / RMSE','Zero MAE / RMSE','Mean MAE / RMSE'],[[f['targetYear'],f"{f['trainingCoverage']['pairs']} / {f['eligiblePairs']}",number(100*f['fits']['regression']['alpha']) if f['fits']['regression']['status']=='available' else '—',number(f['fits']['regression'].get('beta')), ' / '.join(number(f['scores']['regression'][k]) for k in ('MAEpp','RMSEpp','biasPp')), *[' / '.join(number(f['scores'][m][k]) for k in ('MAEpp','RMSEpp')) for m in ('carry_forward','zero','historical_mean')]] for f in fs]))
    text.append('\nPositive paired gain means the fitted model improves on its benchmark.\n')
    text.append(table(['Target','MAE gain vs zero','vs carry','vs mean','RMSE gain vs carry'],[[f['targetYear'],number(f['pairedGains']['zero']['MAEgainPp']),number(f['pairedGains']['carry_forward']['MAEgainPp']),number(f['pairedGains']['historical_mean']['MAEgainPp']),number(f['pairedGains']['carry_forward']['RMSEgainPp'])] for f in fs]))
    text.append('\n## Linkage, chronology and normalization sensitivities\n\nPooled errors below use the identical trained sample within each row, never compare own-population broad/strict as if population were fixed.\n')
    text.append(table(['View / scope / chronology / scale','Trained n','Fit MAE / RMSE','Carry MAE / RMSE','Zero MAE / RMSE'],[[f"{p['view']} / {p['scope']} / {p['protocol']} / {p['scale']}",p['trainedCommonSample']['eligiblePairs'],*[' / '.join(number(p['trainedCommonSample']['scores'][m][k]) for k in ('MAEpp','RMSEpp')) for m in ('regression','carry_forward','zero')]] for p in data['pooled'] if p['scope']=='general']))
    text.append('\nOn the same strict evaluation IDs, changing only the training-linkage view has small effects:\n')
    text.append(table(['Target','Strict n','Broad-trained MAE','Strict-trained MAE'],[[int(c['broadFold'].split('-')[-1]),len(c['evaluationIds']),number(c['broadTrainedOnStrictEvaluation']['scores']['regression']['MAEpp']),number(c['strictTrainedOnStrictEvaluation']['scores']['regression']['MAEpp'])] for c in data['commonStrictEvaluation'] if ':general:additive:expanding_window:' in c['broadFold']]))
    text.append('\nBroad-only additions are reported separately without refitting or excluding their outcomes:\n')
    text.append(table(['Target','Broad-only n','Fit MAE','Carry MAE','Zero MAE'],[[int(c['foldId'].split('-')[-1]),c['eligiblePairs'],*[number(c['scores'][m]['MAEpp']) for m in ('regression','carry_forward','zero')]] for c in data['broadOnlyEvaluation'] if ':general:additive:expanding_window:' in c['foldId']]))
    text.append('\nOriginal versus added transitions use saved expanding primary predictions; earliest fit abstention stays explicit:\n')
    primary=next(p for p in data['pooled'] if (p['view'],p['scope'],p['scale'],p['protocol'])==('broad','general','additive','expanding_window'))
    text.append(table(['Composition','Eligible n','Fit n / MAE','Carry MAE','Zero MAE'],[[label,primary[key]['eligiblePairs'],f"{primary[key]['scores']['regression']['n']} / {number(primary[key]['scores']['regression']['MAEpp'])}",number(primary[key]['scores']['carry_forward']['MAEpp']),number(primary[key]['scores']['zero']['MAEpp'])] for key,label in [('originalTransitions','Original2011/2017/2023'),('added2014_2020Transitions','Added2014/2020')]]))
    text.append('''
The comparison with historical Stage8 is not a clean sample-size experiment. Stage8's source-winner-selected, retrospectively anchored cohort differs in identity, population and chronology. Its original selection.json stays byte-identical. Applying only its labelled2017/2023 numerical performance convention to these new populations still fails the0.25pp each-fold / no RMSE loss screen. This is a historical diagnostic, not an estimation gate or a claim that prior residual contains no useful information.

## Māori evidence, separate and small

Estimates are displayed when numerically identifiable. Tiny held-out counts and few shared election environments limit forecasting conclusions; no general/Māori pooling or operational coefficient.
''')
    text.append(table(['View','Target','Train / eval','α pp','β','Fit MAE / RMSE','Carry MAE','Zero MAE'],[[v,f['targetYear'],f"{f['trainingCoverage']['pairs']} / {f['eligiblePairs']}",number(100*f['fits']['regression']['alpha']) if f['fits']['regression']['status']=='available' else '—',number(f['fits']['regression'].get('beta')),' / '.join(number(f['scores']['regression'][k]) for k in ('MAEpp','RMSEpp')),number(f['scores']['carry_forward']['MAEpp']),number(f['scores']['zero']['MAEpp'])] for v in ('broad','strict') for f in selected(v,'maori')]))
    text.append('\n## Full-panel description and transition-deletion influence\n\nThese fits describe the retained panel. No deleted transition is scored as a forecast; adjacent retained transitions preserve election information. Deletion ranges are not confidence intervals.\n')
    text.append(table(['View / scope','Deleted transition','Pairs / environments','α pp','β','Retained fit MAE / RMSE'],[[f"{f['view']} / {f['scope']}",'none' if f['omittedTransition'] is None else '→'.join(map(str,f['omittedTransition'])),f"{f['coverage']['pairs']} / {f['coverage']['transitionEnvironments']}",number(100*f['fits']['regression']['alpha']) if f['fits']['regression']['status']=='available' else '—',number(f['fits']['regression'].get('beta')),' / '.join(number(f['retainedSampleScores']['scores']['regression'][k]) for k in ('MAEpp','RMSEpp'))] for f in data['descriptive'] if f['scale']=='additive']))
    text.append('\nLargest fixed-fit leave-one-pair changes in regression-versus-carry MAE gain (all pairs remain in primary scores):\n')
    text.append(table(['Target','Omitted pair ID','Model absolute error pp','Change in carry gain pp'],[[f['targetYear'],i['omittedId'],number(i['absoluteModelErrorPp']),number(i['changeInCarryGainPp'])] for f in fs for i in f['fixedFitLeaveOnePairInfluence'][:2]]))
    text.append('''
Party and rule-level bias/counts, complete influence lists, all three normalization scales and both chronology views are in evaluation.json. Sparse groups (<10 pairs) are visibly flagged; no subgroup-specific coefficient is fitted. The full-panel broad general slope0.867 and deletion range0.835–0.948 describe association; they do not justify importing that slope into a historical fold or candidate forecast. Māori slopes and deletions are more identity-sensitive.

## Dependence, evidence limitations and readiness

The sample is conditional on repeated candidacy, accepted practical names/context and exact geography with matched party references. It includes losers without a victory gate but is not a representative sample of all candidates, replacements or changed seats. Retrospective algorithmic linkage is not proof of identity or as-of source availability. The strict subset is a sensitivity, not documentary ground truth. Profile acquisition/history completeness never enters this sample; source availability and cross-election name changes can still affect accepted-link coverage. No linkage queue is reopened.

Shared party/election LOO references, repeated people, repeated seat membership chains and overlapping transitions induce dependence. Counts of records and transition environments are separate in construction.json. Even target records share reference information. Many candidate rows do not create independent elections. No iid significance, causal personal-vote claim, calibrated intervals or winner probability follows. Stable party-seat conditions, tactical voting and joint references can generate retention without uniquely personal effects.

**Graded assessment:** useful predictive information relative to zero is consistent on the general panel; carry-forward is a stronger mandatory comparator than zero/mean. Flexible retention does not yet establish a forecasting improvement over carry-forward. Reasonable linkage/chronology choices preserve that qualitative result, while normalizations affect absolute scales/errors. Keep prior residual for a specifically incremental future development test; do not deploy the fitted coefficient, reject complementary information merely because the historical screen fails, or translate residual error into complete-share gains.

**Exact next decision:** after independent review, separately authorize expanded Stage23 coherent party vectors and fixed-parameter baseline/S input substitution on the Stage25 exact panel. Then specify one small joint/regularized candidate-share comparison using defensible same-person evidence, coherent complete-slate shares and refitted ablations; no separately fitted coefficient stacking. No acquisition, tenure/replacement expansion, parity salvage or new variant is started here.

## Reproducibility and validation

Run the five Stage30 modules `inventory`, `construction`, `evaluation`, `verification`, `report` with `--check`, under `scripts.models.expanded_candidate_persistence`. Initial inventory generation pins consumed records/contracts and all1,402 prior data bytes; provenance accepts unrelated additions but rejects altered required records/raw bytes. Existing raw files, Stage7–29 numerical artifacts, Stage25 geography/folds, Stage26 adjudications/linkage and every prior selection remain unchanged.

Independent covariance arithmetic verifies156 OLS fits; direct vectors verify17,922 predictions,1,224 fold metric values and252 paired gains at1e−8 tolerance. Synthetic and real-adapter tests cover selection/units/rank failures, chronology, strict subsets, missingness, benchmarks, target-result mutation and legitimate earlier-response fitting. Full configured Python/source checks and final-head CI status are recorded in PROJECT_STATE.md/PR. No formatter/linter is configured; compilation/whitespace checks apply. Raw fits/errors are unrounded; three-decimal tables are display only.
''')
    result='\n'.join(text)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();raw=build().encode();path=ROOT/'docs/stage30-expanded-persistence-results.md'
    if a.check:
        if path.read_bytes()!=raw:raise ValueError('Changed report')
    else:path.write_bytes(raw)
    print('Stage30 report reproduced' if a.check else 'Stage30 report saved')


if __name__=='__main__':main()
