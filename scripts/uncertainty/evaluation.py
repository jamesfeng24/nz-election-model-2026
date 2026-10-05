"""Evaluate sealed Stage44 draws without feeding outcomes back into simulation."""
import numpy as np
from .common import PREFIX, read, save, verify, arguments, digest
from .construction import signature,audited_cache
from .metrics import record,distribution_summary


def build():
    construction=read(PREFIX+'/construction.json')
    if construction['signature']!=signature():raise ValueError('Construction code signature changed')
    inv=read(PREFIX+'/inventory.json')
    parties={r['targetElectorateId']:r for r in inv['partyRecords']}
    candidates={r['targetElectorateId']:r for r in inv['candidateRecords']}
    cases=[]
    for case in construction['cases']:
        archive=audited_cache(case,construction['signature'])
        lookup=parties if case['layer']=='local_party' else candidates
        records=[record(lookup[r['id']],archive['vectors'][r['id']],r['metadata'].get('deterministicNationalOnlyMean',lookup[r['id']]['mean'])) for r in case['records']]
        value={'id':case['id'],'layer':case['layer'],'year':case['year'],'records':records,
            'summary':distribution_summary(records),'draws':len(archive['drawIds']),
            'uncertaintyStatus':case.get('scaleFit',case.get('candidateScaleFit'))['status'],
            'uncertaintyTrainingYears':case.get('scaleFit',case.get('candidateScaleFit'))['trainingYears']}
        if case['layer']!='local_party':
            stress=[record(lookup[r['id']],archive['vectors'][r['id']+':transport_stress'],r['metadata'].get('deterministicNationalOnlyMean',lookup[r['id']]['mean'])) for r in case['records']]
            value['transportStress']={'label':'assumed 50% excess candidate seat variance; possibly duplicates pooled transport errors',
                'summary':distribution_summary(stress),'records':stress,
                'pairedContestCRPSChangePP':float(np.mean([np.mean(s['crpsPP'])-np.mean(r['crpsPP']) for s,r in zip(stress,records)]))}
        value['largest90IntervalMisses']=[{'id':r['id'],'optionId':r['ids'][i],
            'actualPP':100*r['actual'][i],'lowerPP':r['interval90']['lower'][i],
            'upperPP':r['interval90']['upper'][i],'intervalScorePP':r['interval90']['scores'][i]}
            for r,i in sorted(((r,i) for r in records for i,c in enumerate(r['interval90']['covered']) if not c),
                key=lambda p:(-p[0]['interval90']['scores'][p[1]],p[0]['ids'][p[1]]))[:5]]
        cases.append(value)
    pooled={}
    for layer in ('local_party','candidate','composed'):
        group=[c for c in cases if c['layer']==layer];records=[r for c in group for r in c['records']]
        pooled[layer]={'contestWeighted':distribution_summary(records),
            'equalElectionMAEPP':float(np.mean([c['summary']['contestEqualMAEPP'] for c in group])),
            'equalElectionCRPSPP':float(np.mean([c['summary']['contestEqualCRPSPP'] for c in group])),
            'elections':[c['year'] for c in group],
            'independenceWarning':'correlated coordinates, overlapping transitions and reused development elections'}
    shifts={}
    for layer in ('local_party','candidate','composed'):
        values=[c for c in construction['cases'] if c['layer']==layer];summary=[]
        for c in values:
            if layer=='composed':
                nonlinear=[v for r in c['records'] for v in r['metadata']['nonlinearUpstreamMeanShiftPP']]
                residual_shift=[v for r in c['records'] for v in r['metadata']['candidateAdjustmentMeanShiftPP']]
                local_shift=[v for r in c['records'] for v in r['metadata']['localMarginalMeanShiftPP']]
                summary.append({'year':c['year'],'meanAbsoluteNonlinearShiftPP':float(np.mean(np.abs(nonlinear))),
                    'maximumAbsoluteNonlinearShiftPP':float(np.max(np.abs(nonlinear))),
                    'maximumCandidateMeanAdjustmentErrorPP':float(np.max(np.abs(residual_shift))),
                    'maximumLocalMeanAdjustmentErrorPP':float(np.max(np.abs(local_shift)))})
            else:
                gap=[v for r in c['records'] for v in r['metadata']['expectedShareShiftPP']]
                summary.append({'year':c['year'],'maximumMeanAdjustmentErrorPP':float(np.max(np.abs(gap)))})
        shifts[layer]=summary
    return {'stage':44,'constructionSignature':construction['signature'],'cases':cases,'pooled':pooled,
        'meanShifts':shifts,'scoresUseHeldOutOutcomesOnly':True,'scoreUnits':'percentage points; energy Euclidean complete-vector norm',
        'operationalSelection':None,'calibratedElectorateProbabilities':False}


def main():
    args=arguments();verify();result=build();save('evaluation.json',result,args.check)
    for c in result['cases']:
        s=c['summary'];print(c['id'],s['contestEqualMAEPP'],s['contestEqualCRPSPP'],s['interval90'])


if __name__=='__main__':main()
