"""Fixed earlier S+R parameters; explicit centered S/R interface, no fitting."""
import argparse
from decimal import Decimal,localcontext
from math import isfinite
from .common import read,save,verify,PREFIX,METHOD

POLICIES={'exact_fallback':('exact','broad'),'stage41_90':('90','broad'),'continuous':('continuous','broad'),
    'exact_fallback_strict':('exact','strict'),'stage41_90_strict':('90','strict'),'continuous_strict':('continuous','strict')}


def columns(candidate, tier, policy, view):
    if policy=='continuous':
        f=candidate['continuous']
        return [f['S']['contribution'],f['RStrict' if view=='strict' else 'R']['contribution']]
    if tier=='exact' or policy=='90' and tier in ('approximate_95','approximate_90'):
        f=candidate['inheritedStage41Centered'][view];return [f['S'],f['R']]
    return [0.0,0.0]


def shares(base, features, parameters):
    if parameters['status']!='fitted' or len(parameters['theta'])!=2:
        raise ValueError('Earlier frozen S+R fit unavailable')
    if not .0001<=parameters['kappa']<=.1 or any(abs(t)>4 or not isfinite(t) for t in parameters['theta']):
        raise ValueError('Frozen family parameter bounds')
    if len(base)!=len(features) or not base:raise ValueError('Incomplete candidate slate')
    with localcontext() as context:
        context.prec=50;weights=[]
        for b,x in zip(base,features):
            if not isfinite(b) or not 0<=b<=1 or len(x)!=2 or not all(isfinite(v) for v in x):
                raise ValueError('Invalid fixed candidate inputs')
            movement=sum((Decimal(str(t))*Decimal(str(v)) for t,v in zip(parameters['theta'],x)),Decimal(0))
            weights.append((Decimal(str(b))+Decimal(str(parameters['kappa'])))*movement.exp())
        total=sum(weights);q=[float(w/total) for w in weights]
    if not all(isfinite(v) and v>=0 for v in q) or abs(sum(q)-1)>1e-12:raise ValueError('Candidate simplex failure')
    return q


def build(inv=None, samples=None, saved=None, old=None):
    inv=read(PREFIX+'/inventory.json') if inv is None else inv
    samples=read(PREFIX+'/sample-manifest.json')['folds'] if samples is None else samples
    saved=read('data/processed/models/joint-candidate-share/construction.json') if saved is None else saved
    old=read('data/processed/forecast-transport/construction.json') if old is None else old
    folds=[]
    for sample in samples:
        earlier=next(f for f in saved['folds'] if f['id']==sample['savedFoldId'])
        if (earlier['trainingOnlyMeans']!=sample['trainingOnlyMeans'] or earlier['fits'][METHOD]!=sample['savedFit']
            or earlier['trainingIds']!=sample['trainingIds']):raise ValueError('Saved parameters/preprocessing changed')
        if any(int(i.split('-')[2])>=sample['targetYear'] for i in sample['trainingIds']):raise ValueError('Target/later fit')
        rows=[r for r in inv['records'] if r['targetYear']==sample['targetYear']]
        if [r['targetElectorateId'] for r in rows]!=sample['comparisonIds'] or [c['targetOccurrenceId'] for r in rows for c in r['candidates']]!=sample['candidateIds']:
            raise ValueError('Frozen complete common IDs changed')
        predictions={}
        for branch,(policy,view) in POLICIES.items():
            predictions[branch]=[]
            for row in rows:
                candidates=row['candidates'];ids=[c['targetOccurrenceId'] for c in candidates]
                if len(ids)!=len(set(ids)):raise ValueError('Duplicate candidate occurrence')
                x=[columns(c,row['transportTier'],policy,view) for c in candidates]
                q=shares([c['observedPartySupport'] for c in candidates],x,sample['savedFit']['parameters'])
                predictions[branch].append({'targetElectorateId':row['targetElectorateId'],
                    'candidateShares':dict(zip(ids,q)),'centeredContributions':dict(zip(ids,x))})
        reference=next(f for f in old['folds'] if f['targetYear']==sample['targetYear'])
        deviations=[]
        for new,previous in (('exact_fallback','fallback'),('stage41_90','transport_90'),
                ('exact_fallback_strict','fallback_strict'),('stage41_90_strict','transport_90_strict')):
            actual={p['targetElectorateId']:p['candidateShares'] for p in predictions[new]}
            for p in reference['predictions'][previous]:
                q=actual[p['targetElectorateId']]
                if q.keys()!=p['candidateShares'].keys():raise ValueError('Stage41 common slate mismatch')
                deviations.extend(abs(q[c]-v) for c,v in p['candidateShares'].items())
        if max(deviations,default=0)>1e-12:raise ValueError('Stage41 prediction reproduction failed')
        # Exact membership remains one predecessor with weight one.
        for row in rows:
            if row['transportTier']=='exact':
                for c in row['candidates']:
                    for view in ('broad','strict'):
                        if max(abs(a-b) for a,b in zip(columns(c,'exact','continuous',view),columns(c,'exact','exact',view)))>1e-12:
                            raise ValueError('Exact centered feature equivalence failed')
        folds.append({'targetYear':sample['targetYear'],'savedFoldId':sample['savedFoldId'],
            'savedFit':sample['savedFit'],'trainingOnlyMeans':sample['trainingOnlyMeans'],'trainingIds':sample['trainingIds'],
            'predictions':predictions,'stage41ReproductionWithin1e12':True,
            'fittingPerformed':False,'heldoutCandidateOutcomesConsumed':False})
    return {'stage':42,'folds':folds,'operationalSelection':None,'informationSet':'conditional observed target local parties; retrospective slates; fixed earlier fits'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();count=verify()
    value=build();save('construction.json',value,a.check);print('Prediction folds',[(f['targetYear'],len(f['predictions']['continuous'])) for f in value['folds']],'prior preserved',count)


if __name__=='__main__':main()
