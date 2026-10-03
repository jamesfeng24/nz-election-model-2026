"""Complete-party diagnostics; target local counts/weights enter evaluation only."""
from collections import defaultdict
from statistics import mean
from math import sqrt
from scripts.models.complete_party_vector.inventory import evidence
from scripts.models.complete_party_vector.evaluation import metrics,contest_errors
from .common import read,S23,keyed


def describe(errors):
    if not errors:return None
    return {'n':len(errors),'MAEpp':mean(abs(e) for e in errors),'RMSEpp':sqrt(mean(e*e for e in errors)),'biasPp':mean(errors)}


def records(party,elections):
    seats={y:keyed(list(d['scopes']['general'].values()),'id') for y,d in elections.items()};result=[]
    for p in party['records']:
        target=seats[p['targetYear']][p['targetElectorateId']];actual={c:r['share'] for c,r in target['parties'].items()}
        predicted=p['localPartyShares'];national=p['suppliedNationalScenario']
        model_mae,model_mse=contest_errors(predicted,actual);flat_mae,flat_mse=contest_errors(national,actual)
        result.append({'targetYear':p['targetYear'],'targetElectorateId':p['targetElectorateId'],'scope':'general',
            'actualLocalShares':actual,'targetObservedValidPartyVotes':target['validVotes'],
            'model':{'contestMaePP':model_mae,'contestMsePP2':model_mse},
            'flat':{'contestMaePP':flat_mae,'contestMsePP2':flat_mse},
            'errors':{c:100*(v-actual[c]) for c,v in predicted.items()},
            'flatErrors':{c:100*(v-actual[c]) for c,v in national.items()},
            'targetPartyGroupKeys':p['targetPartyGroupKeys']})
    return result


def report(rows):
    model=[{'actualLocalShares':r['actualLocalShares'],**r['model']} for r in rows]
    flat=[{'actualLocalShares':r['actualLocalShares'],**r['flat']} for r in rows]
    weights=[r['targetObservedValidPartyVotes'] for r in rows]
    groups=defaultdict(lambda:{'model':[],'flat':[]});categories=defaultdict(lambda:{'model':[],'flat':[]})
    for r in rows:
        for c,e in r['errors'].items():
            key=r['targetPartyGroupKeys'][c];g='national' if key=='nationalparty' else 'labour' if key=='labourparty' else 'other_categories'
            groups[g]['model'].append(e);groups[g]['flat'].append(r['flatErrors'][c])
            categories[c]['model'].append(e);categories[c]['flat'].append(r['flatErrors'][c])
    return {'n':len(rows),'model':metrics(model),'flatNational':metrics(flat),
            'modelOracleValidPartyWeighted':metrics(model,weights) if rows else None,
            'flatOracleValidPartyWeighted':metrics(flat,weights) if rows else None,
            'byGroup':{g:{m:describe(es) for m,es in data.items()} for g,data in groups.items()},
            'byCategory':{g:{m:describe(es) for m,es in data.items()} for g,data in categories.items()}}


def subset_gap(predictions,actuals,year):
    index=keyed(actuals,'targetElectorateId');pairs=[(p,index[p['targetElectorateId']]) for p in predictions if p['targetYear']==year]
    total=sum(a['targetObservedValidPartyVotes'] for _,a in pairs);keys=list(pairs[0][0]['localPartyShares']);q=pairs[0][0]['suppliedNationalScenario']
    model={c:sum(a['targetObservedValidPartyVotes']*p['localPartyShares'][c] for p,a in pairs)/total for c in keys}
    observed={c:sum(a['targetObservedValidPartyVotes']*a['actualLocalShares'][c] for _,a in pairs)/total for c in keys}
    return {'targetYear':year,'electorates':len(pairs),'oracleValidPartyVotes':total,
            'label':'selected_exact_general_subset_not_full_national_reconciliation',
            'modelMinusNationalScenarioPp':{c:100*(model[c]-q[c]) for c in keys},
            'actualSubsetMinusNationalScenarioPp':{c:100*(observed[c]-q[c]) for c in keys},
            'modelMinusActualSubsetPp':{c:100*(model[c]-observed[c]) for c in keys},
            'maxAbsoluteSubsetModelScenarioGapPp':max(100*abs(model[c]-q[c]) for c in keys)}


def build(party,inventory,elections=None):
    elections=evidence()[0] if elections is None else elections
    actuals=records(party,elections);held={r['targetElectorateId'] for r in inventory['candidateRecords']}
    years=sorted({r['targetYear'] for r in actuals})
    folds=[{'targetYear':y,'heldGeneral':report([r for r in actuals if r['targetYear']==y and r['targetElectorateId'] in held]),
            'allExactGeneralPartyBallots':report([r for r in actuals if r['targetYear']==y])} for y in years]
    return {'stage':31,'role':'target_party_actuals_and_oracle_weights_evaluation_only','records':actuals,'folds':folds,
            'pooledHeldGeneral':report([r for r in actuals if r['targetElectorateId'] in held]),
            'subsetGaps':[subset_gap(party['records'],actuals,y) for y in years],
            'priorStage23FullPopulationGapContextUnchanged':read(S23+'scores.json')['fullPopulationNationalGaps'],
            'operationalSelection':None}
