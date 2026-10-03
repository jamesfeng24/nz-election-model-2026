"""Paired held-out residual diagnostics; descriptive influence is separate."""
import argparse
from math import sqrt
from collections import defaultdict
from .common import local,read,unique,RES,save,manifest,verify_inputs,verify_prefit,preservation
from .inventory import value

METHODS=('regression','zero','carry_forward','historical_mean')
CODE=['scripts/models/expanded_candidate_persistence/evaluation.py']


def metrics(errors):
    if not errors:return {'n':0,'MAEpp':None,'RMSEpp':None,'biasPp':None}
    return {'n':len(errors),'MAEpp':100*sum(abs(v) for v in errors)/len(errors),
            'RMSEpp':100*sqrt(sum(v*v for v in errors)/len(errors)),'biasPp':100*sum(errors)/len(errors)}


def summary(rows):
    scores={m:metrics([r['errors'][m] for r in rows if m in r['errors']]) for m in METHODS}
    paired={}
    for control in METHODS[1:]:
        common=[r for r in rows if 'regression' in r['errors'] and control in r['errors']]
        model=metrics([r['errors']['regression'] for r in common]);base=metrics([r['errors'][control] for r in common])
        paired[control]={'ids':[r['id'] for r in common],'n':len(common),
            'MAEgainPp':base['MAEpp']-model['MAEpp'] if common else None,
            'RMSEgainPp':base['RMSEpp']-model['RMSEpp'] if common else None,
            'meanPairedAbsoluteGainPp':100*sum(abs(r['errors'][control])-abs(r['errors']['regression']) for r in common)/len(common) if common else None}
    carry_common=[r for r in rows if 'zero' in r['errors'] and 'carry_forward' in r['errors']]
    carry_zero={'ids':[r['id'] for r in carry_common],'n':len(carry_common),
        'MAEgainPp':100*sum(abs(r['errors']['zero'])-abs(r['errors']['carry_forward']) for r in carry_common)/len(carry_common) if carry_common else None,
        'RMSEgainPp':metrics([r['errors']['zero'] for r in carry_common])['RMSEpp']-metrics([r['errors']['carry_forward'] for r in carry_common])['RMSEpp'] if carry_common else None}
    return {'eligiblePairs':len(rows),'scores':scores,'pairedGains':paired,'carryVersusZeroGain':carry_zero,
            'abstentions':{m:len(rows)-scores[m]['n'] for m in METHODS}}


def evaluate(predictions,ids,index,actuals,scale):
    maps={m:unique(predictions[m]['values'],'id') for m in METHODS}
    for m in METHODS:
        if predictions[m]['status']=='available' and set(maps[m])!=set(ids):raise ValueError('Different evaluation IDs')
        if predictions[m]['status']!='available' and maps[m]:raise ValueError('Abstention with predictions')
    rows=[]
    for i in ids:
        r=index[i];y=value(actuals[r['targetOccurrenceId']],scale)
        rows.append({'id':i,'targetYear':r['targetYear'],'scope':r['scope'],'targetPartyKey':r['targetPartyKey'],
            'ruleFlags':r['ruleFlags'],'originalFrame':r['originalFrame'],'actual':y,
            'targetReferenceId':actuals[r['targetOccurrenceId']]['referenceId'],
            'errors':{m:maps[m][i]['prediction']-y for m in METHODS if i in maps[m]}})
    return rows


def influence(rows):
    common=[r for r in rows if 'regression' in r['errors']]
    if len(common)<2:return []
    base=summary(common)['pairedGains']['carry_forward']['MAEgainPp']
    result=[]
    for r in common:
        reduced=[x for x in common if x['id']!=r['id']]
        new=summary(reduced)['pairedGains']['carry_forward']['MAEgainPp']
        result.append({'omittedId':r['id'],'absoluteModelErrorPp':100*abs(r['errors']['regression']),
                       'carryGainWithoutPairPp':new,'changeInCarryGainPp':new-base})
    return sorted(result,key=lambda r:(-abs(r['changeInCarryGainPp']),r['omittedId']))


def groups(rows,field):
    grouped=defaultdict(list)
    for r in rows:
        key='|'.join(r[field]) if isinstance(r[field],list) else r[field]
        grouped[key].append(r)
    return [{'group':g,'sparseWarning':len(rs)<10,**summary(rs)} for g,rs in sorted(grouped.items())]


def build(construction=None,inventory=None,actuals=None):
    construction=local('construction.json') if construction is None else construction
    inventory=local('inventory.json') if inventory is None else inventory
    actuals=unique(read(RES+'occurrences.json')['records'],'candidateOccurrenceId') if actuals is None else actuals
    index=unique(inventory['pairs'],'id');folds=[];pooled=defaultdict(list);fold_index={}
    for f in construction['folds']:
        rows=evaluate(f['predictions'],f['evaluationIds'],index,actuals,f['scale'])
        result={k:f[k] for k in ('id','view','scope','scale','protocol','sourceYear','targetYear','trainingCoverage','evaluationCoverage','fits')}
        result.update({'records':rows,**summary(rows),'partyDiagnostics':groups(rows,'targetPartyKey'),
                       'acceptanceRuleDiagnostics':groups(rows,'ruleFlags'),'fixedFitLeaveOnePairInfluence':influence(rows)})
        folds.append(result);fold_index[f['id']]=result
        pooled[(f['view'],f['scope'],f['scale'],f['protocol'])].extend(rows)
    pooled_results=[]
    for key,rows in pooled.items():
        view,scope,scale,protocol=key
        trained=[r for r in rows if 'regression' in r['errors']]
        yearly=[summary([r for r in trained if r['targetYear']==y]) for y in sorted({r['targetYear'] for r in trained})]
        pooled_results.append({'view':view,'scope':scope,'scale':scale,'protocol':protocol,
            'weighting':'equal_pair_records; pooled_RMSE_root_after_pooled_MSE',**summary(rows),
            'trainedCommonSample':summary(trained),
            'equalTransitionMacroMAESensitivity':{m:sum(s['scores'][m]['MAEpp'] for s in yearly)/len(yearly) if yearly else None for m in METHODS},
            'originalTransitions':summary([r for r in rows if r['originalFrame']]),
            'added2014_2020Transitions':summary([r for r in rows if not r['originalFrame']]),
            'partyDiagnostics':groups(rows,'targetPartyKey')})
    common_strict=[];broad_only=[]
    for f in folds:
        if f['view']!='broad':continue
        strict=fold_index[f['id'].replace('broad:','strict:',1)]
        ids=set(r['id'] for r in strict['records']);broad_rows=[r for r in f['records'] if r['id'] in ids]
        if {r['id'] for r in broad_rows}!=ids:raise ValueError('Strict is not broad subset')
        common_strict.append({'broadFold':f['id'],'strictFold':strict['id'],'evaluationIds':sorted(ids),
            'broadTrainedOnStrictEvaluation':summary(broad_rows),'strictTrainedOnStrictEvaluation':summary(strict['records'])})
        broad_only.append({'foldId':f['id'],'records':[r for r in f['records'] if r['id'] not in ids],
                           **summary([r for r in f['records'] if r['id'] not in ids])})
    descriptive=[]
    for f in construction['descriptive']:
        rows=evaluate(f['predictions'],f['retainedIds'],index,actuals,f['scale'])
        descriptive.append({k:v for k,v in f.items() if k not in ('predictions',)})
        descriptive[-1].update({'retainedSampleScores':summary(rows),'deletedTransitionScored':False})
    screen=[]
    for view in ('broad','strict'):
        for protocol in ('expanding_window','more_separated'):
            selected=[f for f in folds if (f['view'],f['scope'],f['scale'],f['protocol'])==(view,'general','additive',protocol) and f['targetYear'] in (2017,2023)]
            tests=[]
            for f in selected:
                gains=f['pairedGains'];best=max((f['scores'][m]['MAEpp']*-1,m) for m in ('zero','carry_forward'))[1]
                tests.append({'targetYear':f['targetYear'],'bestSimpleBenchmark':best,
                    'MAEgainPp':gains[best]['MAEgainPp'],'RMSEgainPp':gains[best]['RMSEgainPp'],
                    'numericalConventionPass':gains[best]['MAEgainPp'] is not None and gains[best]['MAEgainPp']>=0.25 and gains[best]['RMSEgainPp']>=0})
            screen.append({'view':view,'protocol':protocol,'tests':tests,'numericalPerformanceConventionPass':all(r['numericalConventionPass'] for r in tests) and len(tests)==2,
                           'label':'Stage8_performance_convention_only_on_new_cohort; not_old_selection_or_estimation_gate'})
    return {'stage':30,'folds':folds,'pooled':pooled_results,'commonStrictEvaluation':common_strict,
            'broadOnlyEvaluation':broad_only,'descriptive':descriptive,'historicalScreenComparison':screen,
            'oldStage8SelectionUnchanged':read('data/processed/models/candidate-persistence/selection.json'),
            'operationalSelection':None,'completeCandidateShareImprovementEstablished':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    verify_inputs();verify_prefit();data=build();save('evaluation.json',data,args.check)
    manifest('evaluation',['evaluation.json'],CODE,args.check)
    print('Evaluated',len(data['folds']),'folds;',len(data['commonStrictEvaluation']),'common-strict comparisons; prior files',preservation())


if __name__=='__main__':main()
