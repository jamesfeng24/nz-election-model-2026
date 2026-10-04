"""Independent saved-draw arithmetic/provenance; never runs historical MCMC."""
import argparse
import hashlib
import math
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.distance import pdist
from .common import OUT,FOUNDATION,ROOT,read,save,COARSE,digest
from .inventory import preserved,semantic
from .prepare import prepare
from .inference import fit_signature,model_code


def independent_projection(record):
    cats=COARSE[:-1];x=np.array([record['estimates'][p]['share'] for p in cats])
    lo=np.array([record['estimates'][p]['bounds'][0] for p in cats]);hi=np.array([record['estimates'][p]['bounds'][1] for p in cats])
    factor=1-record['nonresponseCombined'] if record['denominator']=='all_respondents' else 1
    x=x/factor;lo=lo/factor;hi=hi/factor
    minor=record['additionalPublishedCategories'];keys={k for k,v in minor.items() if v['bounds'] and k in ('UNF','NCP','MNA','INT','INM')}
    lower=0 if 'INM' in keys and keys&{'MNA','INT'} else sum(minor[k]['bounds'][0] for k in keys)
    top=record['estimates']['TOP'];lower+=(top['bounds'][0] if top['bounds'] else 0);lower/=factor
    maximum=1-lower
    if sum(np.clip(x,lo,hi))<=maximum:return np.r_[np.clip(x,lo,hi),1-sum(np.clip(x,lo,hi))]
    result=minimize(lambda y:sum((y-x)**2),np.clip(x,lo,hi),jac=lambda y:2*(y-x),method='SLSQP',bounds=list(zip(lo,hi)),
                    constraints=[{'type':'ineq','fun':lambda y:maximum-sum(y),'jac':lambda y:-np.ones(len(y))}],options={'ftol':1e-14,'maxiter':200})
    if not result.success:raise ValueError('Independent benchmark projection '+result.message)
    return np.r_[result.x,1-sum(result.x)]


def independent_draw(x,z,sigma,horizon):
    k=len(x)+1;matrix=[[0.]*(k-1) for _ in range(k)]
    for j in range(1,k):
        scale=math.sqrt(j*(j+1))
        for i in range(j):matrix[i][j-1]=1/scale
        matrix[j][j-1]=-j/scale
    def compose(state):
        logits=[math.fsum(a*b for a,b in zip(row,state)) for row in matrix];maximum=max(logits)
        e=[math.exp(v-maximum) for v in logits];total=math.fsum(e)
        return [v/total for v in e]
    return compose(x),compose([a+sigma*math.sqrt(horizon/7)*b for a,b in zip(x,z)])


def independent_crps(values,y):
    sorted_values=sorted(values);prefix=0.;pair=0.
    for i,x in enumerate(sorted_values):pair+=i*x-prefix;prefix+=x
    return 100*(math.fsum(abs(x-y) for x in values)/len(values)-pair/len(values)**2)


def independent_quantile(values,p):
    ordered=sorted(values);position=(len(ordered)-1)*p;lower=math.floor(position)
    upper=min(lower+1,len(ordered)-1);fraction=position-lower
    return ordered[lower]*(1-fraction)+ordered[upper]*fraction


def verify_intervals(values,actual,reported):
    for level in (.5,.9):
        lo=independent_quantile(values,(1-level)/2);hi=independent_quantile(values,(1+level)/2)
        interval=reported[str(level)]
        if max(abs(lo-interval['lower']),abs(hi-interval['upper']),abs(100*(hi-lo)-interval['widthPP']))>1e-10:
            raise ValueError('Independent interval arithmetic')
        if bool(lo<=actual<=hi)!=interval['covered']:raise ValueError('Independent interval coverage')


def run(check=False):
    inputs=read(OUT/'input-contract.json')
    for p,h in inputs['consumedSha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Changed consumed input '+p)
    polls={r['id']:r for r in read(FOUNDATION/'polls.json')['records']};bench=read(OUT/'benchmark.json')['cases']
    waves=0;means=0
    for b in bench:
        if b['status']!='constructed':continue
        groups={}
        for w in b['polls']:
            r=polls[w['id']];v=independent_projection(r)
            if np.max(abs(v-np.array(w['shares'])))>1e-10:raise ValueError('Independent poll projection '+w['id'])
            weight=math.pow(2,-w['ageDays']/30)*math.sqrt(min(r['sampleSize'] or 750,1500)/1000)
            if abs(weight-w['weight'])>1e-14:raise ValueError('Benchmark weight')
            groups.setdefault(w['pollster'],[]).append((v,weight,w['ageDays']));waves+=1
        vectors=[];weights=[]
        for name,rows in sorted(groups.items()):
            total=math.fsum(r[1] for r in rows);vectors.append([math.fsum(r[0][i]*r[1] for r in rows)/total for i in range(7)])
            weights.append(math.pow(2,-min(r[2] for r in rows)/30))
        total=math.fsum(weights);v=[math.fsum(x[i]*w for x,w in zip(vectors,weights))/total for i in range(7)]
        if np.max(abs(np.array(v)-b['shares']))>1e-11:raise ValueError('Independent benchmark mean')
        means+=1
    verified_fits=set();draws_checked=0;vector_means=0;attempt_count=0
    index=read(OUT/'construction.json')['cases']
    for entry in index:
        for path in entry.get('attempts',[]):
            if path in verified_fits:continue
            fit=read(OUT/path);sig=fit['signature'];attempt_count+=1
            if digest(sig)!=fit['fitKey'] or sig['code']!=model_code():raise ValueError('Fit signature/code mismatch')
            source=fit['sourceCaseId'].split('-');case=prepare(int(source[-2]),int(source[-1]),'-'.join(source[:-2]))
            if fit_signature(case)!=sig:raise ValueError('Fit input membership changed')
            if 'draws' not in fit:
                verified_fits.add(path);continue
            d=fit['draws'];n=len(d['drawIds'])
            if n!=8000 or len(set(d['drawIds']))!=n:raise ValueError('Draw IDs/count')
            current=np.asarray(d['current']);future=np.asarray(d['electionDay'])
            for a in (current,future):
                if not np.all(np.isfinite(a)) or np.any(a<0) or np.max(abs(a.sum(axis=1)-1))>1e-12:raise ValueError('Draw conservation')
            for i in [0,1999,2000,3999,4000,5999,6000,7999]:
                a,b=independent_draw(d['xCutoff'][i],d['futureNormals'][i],d['sigma'][i],case['horizonDays'])
                if max(abs(x-y) for x,y in zip(a,d['current'][i]))>1e-12 or max(abs(x-y) for x,y in zip(b,d['electionDay'][i]))>1e-12:raise ValueError('Independent transformed draw')
                draws_checked+=1
            for array,label in [(d['current'],'expectedCurrent'),(d['electionDay'],'expectedElectionDay')]:
                mean=[math.fsum(row[j] for row in array)/n for j in range(len(fit['categories']))]
                if max(abs(x-y) for x,y in zip(mean,d[label]))>1e-12:raise ValueError('Expected transformed draw mean')
                vector_means+=1
            if fit['status']=='accepted':
                dg=fit['diagnostics']
                if not dg['passed'] or dg['divergences'] or dg['maxRhat']>1.01 or min(dg['minBulkESS'],dg['minTailESS'])<400:raise ValueError('Accepted invalid numerical fit')
                if any(r['failedCoordinates'] for r in dg['variables']):raise ValueError('Concealed latent diagnostic failure')
            verified_fits.add(path)
    point_checks=0;probability_checks=0
    if (OUT/'evaluation.json').exists():
        from .evaluation import validate_archive
        validate_archive()
        result=read(OUT/'evaluation.json')
        for row in result['cases']:
            if not row['model']:continue
            entry=next(c for c in index if c['id']==row['id']);fit=read(OUT/entry['attempts'][-1]);d=fit['draws']
            metrics=row['model']['point'];parties=metrics['parties'];error=[100*(p['prediction']-p['actual']) for p in parties]
            if abs(math.fsum(abs(e) for e in error)/len(error)-metrics['MAEpp'])>1e-11:raise ValueError('Independent national MAE')
            if abs(math.sqrt(math.fsum(e*e for e in error)/len(error))-metrics['RMSEpp'])>1e-11:raise ValueError('Independent national RMSE')
            point_checks+=2
            for i,p in enumerate(parties):
                values=[v[i] for v in d['electionDay']];score=independent_crps(values,p['actual'])
                got=row['model']['probability']['parties'][i]['CRPSpp']
                if abs(score-got)>1e-10:raise ValueError('Independent CRPS')
                verify_intervals(values,p['actual'],row['model']['probability']['parties'][i]['intervals'])
                probability_checks+=1
            coarse=[]
            for vector in d['electionDay']:
                shares=dict(zip(fit['categories'],vector));shares['OTH']+=shares.get('TOP',0)
                coarse.append([shares[p] for p in COARSE])
            for i,p in enumerate(row['model']['coarsePoint']['parties']):
                mean=math.fsum(v[i] for v in coarse)/len(coarse)
                if abs(mean-p['prediction'])>1e-12:raise ValueError('Independent coarse/fine aggregation')
                values=[v[i] for v in coarse]
                verify_intervals(values,p['actual'],row['model']['coarseProbability']['parties'][i]['intervals'])
                if abs(independent_crps(values,p['actual'])-row['model']['coarseProbability']['parties'][i]['CRPSpp'])>1e-10:
                    raise ValueError('Independent coarse CRPS')
                probability_checks+=1
            idx=np.linspace(0,7999,2000).astype(int);a=np.array(d['electionDay'])[idx];y=np.array([p['actual'] for p in parties])
            energy=100*(np.mean([math.dist(v,y) for v in a])-pdist(a).sum()/len(a)**2)
            if abs(energy-row['model']['probability']['energyScorePP'])>1e-10:raise ValueError('Independent joint energy score')
            probability_checks+=1
        for pool in result['pooled']:
            common=[r for r in result['cases'] if r['branch']==pool['branch'] and r['coarseComparison']]
            if not common:continue
            for label in ('model','benchmark'):
                errors=[p['biasPP'] for r in common for p in (r['model']['coarsePoint'] if label=='model' else r['benchmark'])['parties']]
                mae=math.fsum(abs(e) for e in errors)/len(errors);rmse=math.sqrt(math.fsum(e*e for e in errors)/len(errors))
                if max(abs(mae-pool[label+'MAEpp']),abs(rmse-pool[label+'RMSEpp']))>1e-11:
                    raise ValueError('Independent equal-election/horizon pooling')
                point_checks+=2
    save('independent-verification.json',{'benchmarkPollVectors':waves,'benchmarkCaseMeans':means,'uniqueAttempts':attempt_count,
         'representativeTransformedDraws':draws_checked,'posteriorMeanVectors':vector_means,
         'pointMetrics':point_checks,'probabilityMetrics':probability_checks,'priorFilesPreserved':preserved(),
         'method':'independent SLSQP projections/math weights; scalar Helmert/exp and fsum; prefix-pair CRPS; SciPy pdist energy; signatures/membership/diagnostic gates'},check)
    print('Independent verification:',waves,'poll vectors;',draws_checked,'paired draws;',point_checks,'point /',probability_checks,'probability metrics;',preserved(),'prior files unchanged')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
