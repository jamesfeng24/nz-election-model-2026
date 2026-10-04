"""Evaluate only forecast artifacts sealed in a prior Git checkpoint."""
import argparse
import math
import numpy as np
from scripts.polling.national_model.common import read as national_read
from scripts.polling.national_model.metrics import point
from .common import ROOT,OUT,CASES,CATEGORIES,read,save,sha,coarsen,validate_inputs
from .metrics import distribution,major


def forecast_contract():
    c=read(OUT/'forecast-contract.json')
    for p,h in c['sha256'].items():
        if sha(OUT/p)!=h:raise ValueError('Changed sealed forecast '+p)
    return c


def own_case(year):
    base=ROOT/'data/processed/polling/national-backtest'
    construction=national_read(base/'construction.json')['cases']
    c=next(r for r in construction if r['id']==f'primary-{year}-56')
    fit=national_read(base/c['attempts'][-1]);draws=coarsen(fit['draws']['electionDay'],fit['categories'])
    b=next(r for r in national_read(base/'benchmark.json')['cases'] if r['id']==f'primary-{year}-56')
    benchmark=coarsen(b['shares'],b['categories']) if 'categories' in b else coarsen(b['shares'],['NAT','LAB','GRN','ACT','NZF','MRI','OTH'])
    return draws,benchmark


def evaluate():
    validate_inputs();contract=forecast_contract();official=read(ROOT/'data/processed/polling/national-foundation/official-results-isolated.json')
    rows=[]
    for year,cutoff in CASES:
        o=next(r for r in official['records'] if r['year']==year)['shares'];cats=list(o);actual=coarsen([o[k] for k in cats],cats)
        draws,average=own_case(year);systems={}
        for name,mean,dist in [('owned',draws.mean(0),draws),('average',average,None)]:
            p=point(mean,actual,CATEGORIES);prob=distribution(dist,actual) if dist is not None else None
            systems[name]={'point':p,'probability':prob,'major':major(p,prob),'drawCount':len(dist) if dist is not None else 0}
        ext=next(r for r in contract['cases'] if r['year']==year)
        if ext['status']=='accepted':
            fr=read(OUT/ext['attemptFile']);archive=np.load(OUT/ext['drawFile'],allow_pickle=False)
            ex=coarsen(archive['electionDay'].reshape(-1,len(fr['parties'])),fr['parties']);p=point(ex.mean(0),actual,CATEGORIES);prob=distribution(ex,actual)
            systems['gauss']={'point':p,'probability':prob,'major':major(p,prob),'drawCount':len(ex)}
        else:systems['gauss']={'status':ext['status'],'reason':ext.get('reason'),'point':None,'probability':None}
        paired={}
        if systems['gauss']['point']:
            for name in ('owned','average'):
                paired[name+'MinusGaussMAEpp']=systems[name]['point']['MAEpp']-systems['gauss']['point']['MAEpp']
                paired[name+'MinusGaussRMSEpp']=systems[name]['point']['RMSEpp']-systems['gauss']['point']['RMSEpp']
            for k in ('meanCRPSpp','energyScorePP','intervalScore50PP','intervalScore90PP'):
                paired['ownedMinusGauss_'+k]=systems['owned']['probability'][k]-systems['gauss']['probability'][k]
        rows.append({'year':year,'cutoff':cutoff,'horizonDays':56,'actual':actual.tolist(),'systems':systems,'paired':paired})
    common=[r for r in rows if r['systems']['gauss']['point']]
    return {'cases':rows,'pooledFullOwnedAverage':pool(rows,['owned','average']),
            'pooledCommon':pool(common,['owned','average','gauss']) if common else None,
            'commonCaseCount':len(common),'fullThreeCaseComparisonAvailable':len(common)==3,
            'leaveOneElectionOut':[{'omitted':r['year'],'retainedYears':[x['year'] for x in common if x['year']!=r['year']], 'pool':pool([x for x in common if x['year']!=r['year']],['owned','average','gauss'])} for r in common if len(common)>1],
            'informationSet':'retrospective reconstructed system comparison; inferred publication, retrospective fixed calibration, different datasets; not matched-input architecture or fully as-of validation','categoryCount':6,'operationalSelection':None}


def pool(rows,names):
    out={'caseCount':len(rows),'years':[r['year'] for r in rows],'weightPerElection':1/len(rows),'categoryCases':6*len(rows),'majorPartyCases':2*len(rows),'systems':{}}
    for name in names:
        systems=[r['systems'][name] for r in rows];p=[r['point'] for r in systems]
        s={'MAEpp':float(np.mean([r['MAEpp'] for r in p])),'RMSEpp':math.sqrt(float(np.mean([r['RMSEpp']**2 for r in p]))),'majorMAEpp':float(np.mean([r['major']['MAEpp'] for r in systems])),'majorRMSEpp':math.sqrt(float(np.mean([r['major']['RMSEpp']**2 for r in systems]))),
           'partyBias':[{'category':k,'biasPP':float(np.mean([r['parties'][i]['biasPP'] for r in p])),'MAEpp':float(np.mean([r['parties'][i]['absoluteErrorPP'] for r in p]))} for i,k in enumerate(CATEGORIES)]}
        if systems[0]['probability']:
            probs=[r['probability'] for r in systems]
            s['probability']={k:float(np.mean([r[k] for r in probs])) for k in ('meanCRPSpp','energyScorePP','width50PP','width90PP','intervalScore50PP','intervalScore90PP')}
            for label in ('50','90'):
                s['probability']['coveredCount'+label]=sum(r['coveredCount'+label] for r in probs)
                s['probability']['coverage'+label]=s['probability']['coveredCount'+label]/(6*len(rows))
        else:s['probability']=None
        out['systems'][name]=s
    out['paired']={name+'MinusGaussMAEpp':out['systems'][name]['MAEpp']-out['systems']['gauss']['MAEpp'] for name in names if name!='gauss' and 'gauss' in names}
    return out


def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items()}
    if isinstance(value,list):return [stable(v) for v in value]
    if isinstance(value,float):return round(value,12)
    return value


def run(check=False):save('evaluation.json',stable(evaluate()),check)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
