"""Separate held-out evaluation of previously saved national forecasts."""
import argparse
import hashlib
import numpy as np
from .common import FOUNDATION,OUT,read,save,COARSE,coarsen
from .metrics import point,probabilities,grouped


def validate_archive():
    contract=read(OUT/'forecast-contract.json')
    for path,expected in contract['sha256'].items():
        if hashlib.sha256((OUT/path).read_bytes()).hexdigest()!=expected:raise ValueError('Changed forecast archive '+path)


def evaluate():
    validate_archive()
    inventory=read(OUT/'inventory.json')['cases'];construction={r['id']:r for r in read(OUT/'construction.json')['cases']};benchmarks={r['id']:r for r in read(OUT/'benchmark.json')['cases']}
    actuals={r['year']:r for r in read(FOUNDATION/'official-results-isolated.json')['records']}
    rows=[]
    for entry in inventory:
        cid=entry['id'];c=construction.get(cid);b=benchmarks[cid];actual=actuals[entry['year']]['shares']
        actual_coarse=[actual[p]+(actual.get('TOP',0) if p=='OTH' else 0) for p in COARSE]
        row={'id':cid,'branch':entry['branch'],'year':entry['year'],'horizonDays':entry['horizonDays'],
             'cutoff':entry['cutoff'],'status':c['status'] if c else 'not_run','reason':c.get('reason') if c else 'unfinished',
             'benchmarkStatus':b['status'],'benchmark':None,'model':None,'coarseComparison':None,
             'currentCyclePolls':len(entry['cycles'][-1]['pollIds']),'earlierCompletedCycles':len(entry['cycles'])-1,
             'informationSet':'conditional inferred historical availability; not verified archived as-of'}
        if b['status']=='constructed':row['benchmark']=point(b['shares'],actual_coarse,COARSE)
        if c and c['status']=='accepted':
            fit=read(OUT/c['attempts'][-1]);cats=fit['categories'];draws=np.asarray(fit['draws']['electionDay']);observed=[actual[p] for p in cats]
            pred=fit['draws']['expectedElectionDay'];current=np.asarray(fit['draws']['current'])
            coarse_draws=np.array([coarsen(d,cats) for d in draws]);coarse_mean=coarse_draws.mean(axis=0)
            p=point(pred,observed,cats);cp=point(coarse_mean,actual_coarse,COARSE)
            row['model']={'point':p,'probability':probabilities(draws,observed,cats),'groups':grouped(p),
                         'coarsePoint':cp,'coarseProbability':probabilities(coarse_draws,actual_coarse,COARSE),
                         'uncertainty':{'currentStdPP':(100*current.std(axis=0)).tolist(),'electionDayStdPP':(100*draws.std(axis=0)).tolist(),
                           'currentMean':fit['draws']['expectedCurrent'],'electionDayMean':pred,
                           'currentCovariance':np.cov(current,rowvar=False,ddof=0).tolist(),
                           'electionDayCovariance':np.cov(draws,rowvar=False,ddof=0).tolist(),
                           'initialCommonBiasPriorWarning':entry['year']==2014},
                         'fitKey':c['fitKey'],'attempt':fit['attempt'],'diagnosticsSummary':{k:fit['diagnostics'][k] for k in ['maxRhat','minBulkESS','minTailESS','divergences','treeDepthContacts','energyBFMI']},
                         'parameterSummary':fit['parameterSummary']}
            if row['benchmark']:
                row['coarseComparison']={'modelMAEpp':cp['MAEpp'],'benchmarkMAEpp':row['benchmark']['MAEpp'],
                     'MAEImprovementPP':row['benchmark']['MAEpp']-cp['MAEpp'],
                     'modelRMSEpp':cp['RMSEpp'],'benchmarkRMSEpp':row['benchmark']['RMSEpp'],
                     'RMSEImprovementPP':row['benchmark']['RMSEpp']-cp['RMSEpp']}
        rows.append(row)
    return {'cases':rows,'pooled':pooled(rows),'currentSupportScored':False,
            'limitations':['four reused election environments, two dependent horizons each','most publication timing inferred','unidentified fine allocation within Other','conditional independent Gaussian reporting approximation']}


def pooled(rows):
    out=[]
    for branch in sorted({r['branch'] for r in rows}):
        selected=[r for r in rows if r['branch']==branch];common=[r for r in selected if r['coarseComparison']]
        model=[r for r in selected if r['model']];benchmark=[r for r in selected if r['benchmark']]
        result={'branch':branch,'plannedCases':8,'modelCases':len(model),'benchmarkCases':len(benchmark),'commonCases':len(common),
                'fullPlannedPoolAvailable':len(model)==8,'plannedWeightPerCase':.125,
                'availableOnlyWeightDenominator':.125*len(common),'availableOnlyLabel':'original1/8 case weights renormalized over available comparisons; incomplete full pool remains unavailable'}
        if common:
            for k in ('modelMAEpp','benchmarkMAEpp','MAEImprovementPP'):
                result[k]=float(np.mean([r['coarseComparison'][k] for r in common]))
            # Pool squared party errors before square root, not fold RMSEs.
            result['modelRMSEpp']=float(np.sqrt(np.mean([r['coarseComparison']['modelRMSEpp']**2 for r in common])))
            result['benchmarkRMSEpp']=float(np.sqrt(np.mean([r['coarseComparison']['benchmarkRMSEpp']**2 for r in common])))
            result['RMSEImprovementPP']=result['benchmarkRMSEpp']-result['modelRMSEpp']
            result['partyMetrics']=[]
            for i,party in enumerate(COARSE):
                errors_model=[r['model']['coarsePoint']['parties'][i]['biasPP'] for r in common]
                errors_bench=[r['benchmark']['parties'][i]['biasPP'] for r in common]
                result['partyMetrics'].append({'category':party,'caseCount':len(common),
                    'modelMAEpp':float(np.mean(np.abs(errors_model))),'benchmarkMAEpp':float(np.mean(np.abs(errors_bench))),
                    'modelRMSEpp':float(np.sqrt(np.mean(np.square(errors_model)))),'benchmarkRMSEpp':float(np.sqrt(np.mean(np.square(errors_bench)))),
                    'modelBiasPP':float(np.mean(errors_model)),'benchmarkBiasPP':float(np.mean(errors_bench))})
        if model:
            for k in ('meanCRPSpp','coverage50','coverage90','width50PP','width90PP','energyScorePP'):
                result[k]=float(np.mean([r['model']['coarseProbability'][k] for r in model]))
        out.append(result)
    return out


def run(check=False):
    result=evaluate();save('evaluation.json',result,check)
    print('Evaluated',sum(r['model'] is not None for r in result['cases']),'saved accepted forecasts; no inference')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
