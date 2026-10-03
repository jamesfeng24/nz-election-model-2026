"""Exact Stage32 fold/feature adapters; held-out outcomes are never training inputs."""
import numpy as np
from scripts.checkpoints.joint_candidate_share import kernel
from scripts.checkpoints.stage22_fit import earlier_actuals
from scripts.models.exact_geography_retests.adapters import permitted_fold
from .common import read,DESIGN,METHODS,keyed,encode,sha256


def folds_inventory():return read(DESIGN+'fold-plan.json')['folds'],read(DESIGN+'inventory.json')

def fold_rows(fold,inventory):
    canonical=next(f for f in read('data/processed/checkpoints/stage25-historical-geography/fold-plan.json')['folds'] if f['foldId']==fold['canonicalFoldId'])
    train,test=permitted_fold(canonical,inventory['contestRecords'])
    train=[r for r in train if r['status']=='available'];test=[r for r in test if r['status']=='available']
    if ([r['targetElectorateId'] for r in train]!=fold['trainingIds'] or
        [r['targetElectorateId'] for r in test]!=fold['evaluationIds']):raise ValueError('Frozen fold IDs differ')
    if train and kernel.means(train,fold['view'],fold['roundingScenario'])!=fold['trainingOnlyMeans']:
        raise ValueError('Frozen training-only means differ')
    return train,test

def arrays(rows,fold,method,regime=None):
    if method not in METHODS:raise ValueError('Unknown S/R restriction')
    center=fold['trainingOnlyMeans'];base=[];features=[];starts=[]
    for row in rows:
        starts.append(len(base))
        ids=[c['targetOccurrenceId'] for c in row['candidates']]
        if not ids or len(ids)!=len(set(ids)):raise ValueError('Incomplete slate')
        for c in row['candidates']:
            base.append(kernel.support(c,regime or fold['partyInput']))
            features.append([kernel.centered(c,n,center,fold['view'],fold['roundingScenario']) for n in METHODS[method]])
    return np.array(base),np.array(features).reshape(len(base),len(METHODS[method])),np.array(starts,dtype=int)

def prepare(fold,inventory,elections,method):
    train,test=fold_rows(fold,inventory)
    if not train:return None
    regime='constructed' if fold['reusePrimaryFitId'] else fold['partyInput']
    base,features,starts=arrays(train,fold,method,regime)
    prior={y:elections[y] for y in {r['targetYear'] for r in train}}
    actual=earlier_actuals(train,prior)
    payload={'method':method,'trainingIds':fold['trainingIds'],'candidateIds':fold['trainingCandidateIds'],
             'base':base.tolist(),'features':features.tolist(),'starts':starts.tolist(),'actual':actual.tolist(),
             'selectedMeans':{n:fold['trainingOnlyMeans'][n] for n in METHODS[method]}}
    return {'signature':sha256(encode(payload)).hexdigest(),'payload':payload}
