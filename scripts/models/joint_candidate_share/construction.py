"""Chronological fits and complete predictions, saved before scoring."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from scripts.checkpoints.stage25_availability import ELECTIONS
from .common import *
from .adapters import folds_inventory,fold_rows,prepare
from .numerics import calculate,checked_saved,predict

CODE=['scripts/models/joint_candidate_share/'+n+'.py' for n in ('common','adapters','numerics','construction')]


def jobs_for(folds,inventory,elections):
    jobs={};references={}
    for fold in folds:
        references[fold['id']]={}
        for method in METHODS:
            job=prepare(fold,inventory,elections,method)
            references[fold['id']][method]=job['signature'] if job else None
            if job:jobs[job['signature']]=job
    return jobs,references


def construct(folds,inventory,elections,cache):
    jobs,refs=jobs_for(folds,inventory,elections);records=[]
    for fold in folds:
        train,test=fold_rows(fold,inventory);fits={};predictions={}
        for method in METHODS:
            sid=refs[fold['id']][method]
            fitted=({'status':'abstain','reason':'no_earlier_training'} if sid is None else checked_saved(jobs[sid],cache[sid])['fit'])
            fits[method]={'fitId':sid,'parameters':fitted}
            predictions[method]=predict(test,fold,method,fitted)
        contextual={}
        for method in ('uniform','restricted_zero_floor'):
            rows=[];excluded=[]
            for row in test:
                cs=row['candidates'];supports=[c['constructedPartySupport' if fold['partyInput']=='constructed' else 'observedPartySupport'] for c in cs]
                if method=='restricted_zero_floor' and (any(c['partyBallotGroupKey'] is None or p<=0 for c,p in zip(cs,supports))):
                    excluded.append(row['targetElectorateId']);continue
                q=[1/len(cs)]*len(cs) if method=='uniform' else [p/sum(supports) for p in supports]
                rows.append({'targetElectorateId':row['targetElectorateId'],'candidateShares':{c['targetOccurrenceId']:p for c,p in zip(cs,q)}})
            contextual[method]={'predictions':rows,'excludedIds':excluded}
        records.append({**fold,'stage':33,'fits':fits,'predictions':predictions,'contextualBenchmarks':contextual,
                        'historicalFitPerformed':bool(train),'predictionInformation':'conditional observed national/retrospective slate; no heldout candidate outcome'})
    return {'stage':33,'folds':records,'uniqueFitCount':len(jobs),'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--refit',action='store_true');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    verify_inputs();folds,inventory=folds_inventory();elections={y:read(path) for y,path in ELECTIONS.items()}
    jobs,refs=jobs_for(folds,inventory,elections)
    if a.check:verify_phase('construction')
    cache=local('fit-cache.json') if (DEST/'fit-cache.json').exists() and not a.refit else {}
    for sid in list(cache):
        if sid not in jobs:raise ValueError('Unrelated fit in cache')
        checked_saved(jobs[sid],cache[sid])
    missing=[job for sid,job in sorted(jobs.items()) if sid not in cache]
    if a.check and missing:raise ValueError('Missing frozen fits')
    if missing:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            pending={pool.submit(calculate,j):j for j in missing}
            for future in as_completed(pending):
                result=future.result();cache[result['signature']]=result
                save('fit-cache.json',cache)
                print({'completed':len(cache),'total':len(jobs),'method':result['method'],'status':result['fit']['status'],'detail':result['fit'].get('detail')},flush=True)
    save('fit-cache.json',cache,a.check)
    result=construct(folds,inventory,elections,cache);save('construction.json',result,a.check)
    phase('construction',['fit-cache.json','construction.json'],CODE,a.check)
    print('Unique fits',len(jobs),'prior preserved',preserve())


if __name__=='__main__':main()
