"""Held-out actuals and scores are confined to this post-construction phase."""
import argparse
from .common import *
from .adapters import folds_inventory
from .metrics import score,summary,aggregate

CODE=['scripts/models/joint_candidate_share/'+n+'.py' for n in ('metrics','evaluation')]


def actuals_for(inventory,elections):
    seats={s['id']:s for d in elections.values() for s in d['electorates']};result={}
    for row in inventory['contestRecords']:
        if row['status']!='available':continue
        s=seats[row['targetElectorateId']];ids=[c['targetOccurrenceId'] for c in row['candidates']];valid=s['validCandidateVotes']
        totals={c['id']:c['votes'] for c in s['candidates']}
        if valid<=0 or set(totals)!=set(ids) or valid!=sum(totals.values()) or valid!=s['candidateBallot']['validVotes']:raise ValueError('Evaluation denominator/slate mismatch')
        result[s['id']]={'candidateShares':{cid:v/valid for cid,v in totals.items()},'winnerCandidateId':s['winnerCandidateId']}
    return result


def evaluate_case(case,rows,actuals):
    predictions={m:keyed(case['predictions'][m],'targetElectorateId') for m in METHODS}
    expected=set(case['evaluationIds'])
    for m,p in predictions.items():
        if set(p) not in (set(),expected):raise ValueError('Partial/model-specific contest trimming')
        if bool(p)!=(case['fits'][m]['parameters']['status']=='fitted'):raise ValueError('Fit/prediction availability mismatch')
    common=sorted(expected.intersection(*(set(p) for p in predictions.values())))
    records=[];available={m:[] for m in METHODS}
    for cid in case['evaluationIds']:
        r=rows[cid];scores={m:score(p[cid]['candidateShares'],actuals[cid],r,case['view']) for m,p in predictions.items() if cid in p}
        for m,s in scores.items():available[m].append(s)
        if cid in common:records.append({'targetYear':r['targetYear'],'targetElectorateId':cid,'originalFrame':r['originalFrame'],'scores':scores})
    contextual={}
    for name,data in case['contextualBenchmarks'].items():
        scores=[score(p['candidateShares'],actuals[p['targetElectorateId']],rows[p['targetElectorateId']],case['view']) for p in data['predictions']]
        contextual[name]={'summary':aggregate(scores),'expectedContests':len(expected),'excludedIds':data['excludedIds'],
            'supportedIds':[p['targetElectorateId'] for p in data['predictions']],
            'fourModelsSameSupportedSample':summary([r for r in records if r['targetElectorateId'] in {p['targetElectorateId'] for p in data['predictions']}])}
    return {'id':case['id'],'branch':case['branch'],'targetYear':case['targetYear'],
        'expectedContests':len(expected),'commonFourModelIds':common,'abstentions':{m:sorted(expected-set(p)) for m,p in predictions.items()},
        'status':'evaluated' if records else 'no_common_fitted_comparison','records':records,
        'availableMethodMetrics':{m:aggregate(s) for m,s in available.items()},**summary(records),
        'originalTransitions':summary([r for r in records if r['originalFrame']]),
        'added2014_2020':summary([r for r in records if not r['originalFrame']]),'contextual':contextual}


def build(construction=None,inventory=None,elections=None):
    construction=local('construction.json') if construction is None else construction
    inventory=read(DESIGN+'inventory.json') if inventory is None else inventory
    elections={y:read(p) for y,p in ELECTIONS.items()} if elections is None else elections
    actuals=actuals_for(inventory,elections);rows=keyed(inventory['contestRecords'],'targetElectorateId')
    folds=[evaluate_case(c,rows,actuals) for c in construction['folds']];pooled=[]
    for branch in read(DESIGN+'specification.json')['comparisonMatrix']:
        cases=[c for c in folds if c['branch']==branch['id']];records=[r for c in cases for r in c['records']]
        pooled.append({'branch':branch['id'],**summary(records),
            'fittedTargetYears':[c['targetYear'] for c in cases if c['records']],
            'unfittedTargetYears':[c['targetYear'] for c in cases if not c['records']],
            'originalTransitions':summary([r for r in records if r['originalFrame']]),
            'added2014_2020':summary([r for r in records if not r['originalFrame']])})
    return {'stage':33,'folds':folds,'pooled':pooled,'evaluationOnlyActuals':actuals,'operationalSelection':None,
        'information':'conditional supplied observed national support; retrospective slates; reused development elections',
        'improvementSign':'positive=control_error_minus_model_error; lower_error_for_model'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify_inputs();verify_phase('construction')
    result=build();save('evaluation.json',result,a.check);phase('evaluation',['evaluation.json'],CODE,a.check)
    print('Evaluated common primary contests',next(p['contests'] for p in result['pooled'] if p['branch']=='primary'),'prior preserved',preserve())


if __name__=='__main__':main()
