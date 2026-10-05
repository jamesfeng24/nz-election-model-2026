"""Identical-sample centre/tail scores after distributions have been sealed."""
import numpy as np
from .common import PREFIX,INVENTORY,read,save,verify,arguments,signature
from .construction import arrays,METHODS
from .metrics import record,summarize


def build():
    construction=read(PREFIX+'/construction.json')
    if construction['signature']!=signature():raise ValueError('Forecast construction changed before evaluation')
    inventory=read(INVENTORY);lookup={r['targetElectorateId']:r for key in ('partyRecords','candidateRecords') for r in inventory[key]}
    completed=[]
    for case in construction['cases']:
        key='partyRecords' if case['layer']=='local_party' else 'candidateRecords'
        lookup={r['targetElectorateId']:r for r in inventory[key]}
        results={m:[] for m in METHODS+('point',)};shifts=[];numerical=[]
        with arrays(case) as bank:
            for item in case['records']:
                row=lookup[item['id']];metadata=item['metadata'];point=np.array(metadata['stage45'].get('deterministicNationalOnlyMean',row['mean']))
                for method in METHODS:
                    q=bank[method+':'+row['targetElectorateId']]
                    results[method].append(record(row,q,point))
                    shifts.append({'id':item['id'],'method':method,'meanShiftPP':(100*(q.mean(axis=0)-point)).tolist(),
                                   'nonlinearShiftPP':metadata[method].get('nonlinearShiftPP')})
                    numerical.append({'id':item['id'],'method':method,'conditionalCheck':metadata[method].get('conditionalCheck')})
                results['point'].append(record(row,np.broadcast_to(point,(128,len(point))),point))
        ids=[r['id'] for r in results['point']]
        if any([r['id'] for r in records]!=ids for records in results.values()):raise ValueError('Unequal scoring records')
        summaries={m:summarize(records) for m,records in results.items()}
        if case['layer']!='local_party':
            for method,records in results.items():
                pairs=[r['ranking']['predictionTimePair'] for r in records]
                summaries[method]['predictionTimeMarginIntervals']={str(level):{
                    'covered':sum(p['interval'+str(level)]['covered'][0] for p in pairs),'total':len(pairs),
                    'widthPP':float(np.mean([p['interval'+str(level)]['widths'][0] for p in pairs])),
                    'scorePP':float(np.mean([p['interval'+str(level)]['scores'][0] for p in pairs]))}
                    for level in (50,80,90)}
        paired={m:{control:float(np.mean([np.mean(r['crpsPP'])-np.mean(c['crpsPP']) for r,c in zip(results[m],results[control])]))
                   for control in ('stage45','robust_gaussian','point') if control!=m} for m in ('student','robust_gaussian')}
        misses={m:sorted([{'id':r['id'],'name':r['name'],'option':r['ids'][i],'group':r['groups'][i],
                           'actualPP':100*r['actual'][i],'lowerPP':r['interval90']['lower'][i],
                           'upperPP':r['interval90']['upper'][i],'intervalScorePP':r['interval90']['scores'][i]}
                          for r in records for i,v in enumerate(r['interval90']['covered']) if not v],key=lambda x:(-x['intervalScorePP'],x['option']))[:8]
                for m,records in results.items()}
        completed.append({'id':case['id'],'layer':case['layer'],'year':case['year'],
                          'methods':{m:{'summary':summaries[m],'records':records,'largest90Misses':misses[m]} for m,records in results.items()},
                          'methodMinusComparatorCRPSPP':paired,'meanShifts':shifts,'conditionalChecks':numerical})
        print('Scored',case['id'],{m:round(s['contestEqualCRPSPP'],4) for m,s in summaries.items()},flush=True)
    pooled={}
    for layer in ('local_party','candidate','composed'):
        subset=[c for c in completed if c['layer']==layer]
        pooled[layer]={m:{'contestWeighted':summarize([r for c in subset for r in c['methods'][m]['records']]),
                          'equalElectionCRPSPP':float(np.mean([c['methods'][m]['summary']['contestEqualCRPSPP'] for c in subset]))}
                       for m in METHODS+('point',)}
    return {'stage':46,'constructionSignature':construction['signature'],'draws':construction['draws'],
            'precisionStatus':construction['precisionStatus'],'cases':completed,'pooled':pooled,
            'outcomesUsedForScoringOnly':True,'operationalSelection':None,'calibratedElectorateProbabilities':False,
            'zeroWinnerFrequencyInterpretation':'finite-bank zero, not mathematically zero; no arbitrary probability floor'}


def main():
    args=arguments();verify();save('evaluation.json',build(),args.check)


if __name__=='__main__':main()
