"""Independent scalar scales, complete means, scores and preserved input audit."""
import math
import numpy as np
from scipy.stats import norm,t
from scipy.integrate import quad
from scipy.special import expit,roots_hermitenorm
from .integration import student_location
from .common import PREFIX,INVENTORY,CONTROL,read,save,verify,arguments,signature
from .construction import arrays,METHODS
from .streams import permutation
TOLERANCE=1e-10


def close(a,b,label):
    if not np.allclose(a,b,rtol=0,atol=TOLERANCE):raise ValueError('Independent disagreement: '+label)


def quantile(x,p):
    values=sorted(map(float,x));position=(len(values)-1)*p;i=int(math.floor(position));fraction=position-i
    return values[i]*(1-fraction)+values[min(i+1,len(values)-1)]*fraction


def scores(q,y,key):
    n=len(q);means=[math.fsum(map(float,q[:,i]))/n for i in range(q.shape[1])]
    crps=[];intervals={}
    for i,actual in enumerate(y):
        x=sorted(map(float,100*q[:,i]));v=100*actual
        absolute=math.fsum(abs(a-v) for a in x)/n
        pair=math.fsum((2*j-n+1)*a for j,a in enumerate(x))/(n*n)
        crps.append(absolute-pair)
    for level in (.5,.8,.9):
        alpha=1-level;lower=[quantile(100*q[:,i],alpha/2) for i in range(q.shape[1])]
        upper=[quantile(100*q[:,i],1-alpha/2) for i in range(q.shape[1])]
        score=[b-a+2/alpha*(max(a-100*v,0)+max(100*v-b,0)) for a,b,v in zip(lower,upper,y)]
        intervals[str(level)]=(lower,upper,score)
    first=math.fsum(math.sqrt(math.fsum((100*(a-b))**2 for a,b in zip(row,y))) for row in q)/n
    energies=[]
    for repeat in (0,1):
        order=permutation(n,f'{key}:energy:{repeat}')
        second=math.fsum(math.sqrt(math.fsum((100*(a-b))**2 for a,b in zip(q[order[j]],q[order[j-1]]))) for j in range(n))/n
        energies.append(first-second/2)
    return np.array(means),crps,intervals,math.fsum(energies)/2


def independent_student_expectations(scales):
    nodes,weights=roots_hermitenorm(41);weights=weights/np.sqrt(2*np.pi);checks=[]
    for central in scales['centralFits']:
        old=next(f for f in scales['methods']['stage45']['folds']['candidate'] if f['targetYear']==central['targetYear'])
        shared=old['scales']['balance']['shared'];seat=central['studentScale']
        for probability in (.1,.5,.9):
            location=float(student_location(np.array([probability]),shared,seat)[0])
            def integrand(x):return float(np.sum(expit(location+shared*nodes+seat*x)*weights))*t.pdf(x,4)
            expected,error=quad(integrand,-np.inf,np.inf,epsabs=1e-11,epsrel=1e-11)
            checks.append({'year':central['targetYear'],'conditionalMean':probability,'independentExpectation':expected,
                           'gapPP':100*abs(expected-probability),'quadratureAbsoluteError':error})
    return checks


def build():
    inventory=read(INVENTORY);scales=read(PREFIX+'/scales.json');old=read(CONTROL+'/scales.json');checks=0
    # Separate Python scalar arithmetic, no producer shared effect or MAD routines.
    for fold in scales['centralFits']:
        earlier=[r for r in inventory['candidateRecords'] if r['targetYear']<fold['targetYear']]
        mads=[]
        for year in sorted({r['targetYear'] for r in earlier}):
            values=[]
            for row in [r for r in earlier if r['targetYear']==year]:
                if 'national' not in row['groups'] or 'labour' not in row['groups']:continue
                n,l=row['groups'].index('national'),row['groups'].index('labour')
                a,b=row['actual'],row['mean']
                values.append(math.log((a[n]+1e-6)/(a[l]+1e-6))-math.log((b[n]+1e-6)/(b[l]+1e-6)))
            center=math.fsum(values)/len(values);left=[v-center for v in values]
            median=sorted(left)[math.ceil(len(left)*.5)-1]
            mad=sorted(abs(v-median) for v in left)[math.ceil(len(left)*.5)-1];mads.append(mad)
        prior=.35*norm.ppf(.75);mad=math.sqrt((math.fsum(v*v for v in mads)+3*prior*prior)/(len(mads)+3))
        close(mad,fold['pooledMAD'],'central MAD');close(mad/norm.ppf(.75),fold['gaussianSD'],'Gaussian central conversion')
        close(mad/t.ppf(.75,4),fold['studentScale'],'Student central conversion');close(fold['studentScale']*math.sqrt(2),fold['studentSD'],'Student SD')
        if fold['trainingIds']!=[r['targetElectorateId'] for r in earlier]:raise ValueError('Earlier-only membership')
        checks+=1
    # Shared and all unchanged directions exactly match Stage45.
    if scales['methods']['stage45']!=old:raise ValueError('Stage45 control altered')
    for method in ('student','robust_gaussian'):
        if scales['methods'][method]['folds']['local_party']!=old['folds']['local_party']:raise ValueError('Unexpected local scale change')
        for a,b in zip(scales['methods'][method]['folds']['candidate'],old['folds']['candidate']):
            for direction in ('mass','within'):close(list(a['scales'][direction].values()),list(b['scales'][direction].values()),'unchanged direction')
            close(a['scales']['balance']['shared'],b['scales']['balance']['shared'],'shared untouched')
    construction=read(PREFIX+'/construction.json');evaluation=read(PREFIX+'/evaluation.json')
    if construction['signature']!=signature() or evaluation['constructionSignature']!=signature():raise ValueError('Stale sealed forecasts')
    total_vectors=0;representatives=0;largest_mean_shift=0.;conditional_gaps=[];energy_gaps=[]
    for case,result in zip(construction['cases'],evaluation['cases']):
        if case['id']!=result['id']:raise ValueError('Different case ordering')
        rows=result['methods']['stage45']['records'];selected=sorted({0,len(rows)//2,len(rows)-1})
        with arrays(case) as bank:
            for method in METHODS:
                saved=result['methods'][method]['records']
                for item,row in zip(case['records'],saved):
                    q=bank[method+':'+row['id']]
                    if not np.isfinite(q).all() or np.any(q<0) or not np.allclose(q.sum(axis=1),1,rtol=0,atol=1e-12):raise ValueError('Incoherent vectors')
                    close(q.mean(axis=0),row['simulatedMean'],'saved mean');total_vectors+=len(q)
                    shift=next(s for s in result['meanShifts'] if s['id']==row['id'] and s['method']==method)
                    largest_mean_shift=max(largest_mean_shift,max(abs(v) for v in shift['meanShiftPP']))
                    metadata=item['metadata'][method].get('conditionalCheck')
                    if metadata:
                        dictionaries=metadata.values() if case['layer']=='composed' else [metadata]
                        conditional_gaps += [v for d in dictionaries for v in d.values()]
                    energy_gaps.append(row['energyPrecision']['pairDifference'])
                for i in selected:
                    row=saved[i];q=bank[method+':'+row['id']];y=row['actual']
                    mean,crps,intervals,energy=scores(q,y,row['id']);close(mean,row['simulatedMean'],'independent mean');close(crps,row['crpsPP'],'independent CRPS')
                    close(energy,row['energyPP'],'independent energy')
                    for level,(lower,upper,score) in intervals.items():
                        field='interval'+str(int(float(level)*100));close(lower,row[field]['lower'],'independent interval lower')
                        close(upper,row[field]['upper'],'independent interval upper');close(score,row[field]['scores'],'independent interval score')
                    representatives+=1
        for method,pairs in result['methodMinusComparatorCRPSPP'].items():
            for control,value in pairs.items():
                independent=math.fsum(math.fsum(r['crpsPP'])/len(r['crpsPP'])-math.fsum(c['crpsPP'])/len(c['crpsPP'])
                                     for r,c in zip(result['methods'][method]['records'],result['methods'][control]['records']))/len(rows)
                close(independent,value,'paired arithmetic')
    return {'stage':46,'tolerance':TOLERANCE,'independentScaleFolds':checks,'independentScoreRecords':representatives,
            'completeSimplexVectors':total_vectors,'largestTotalMeanShiftPP':largest_mean_shift,
            'maximumConditionalIntegrationGapPP':max(conditional_gaps),'conditionalIntegrationPassed':max(conditional_gaps)<=.05,
            'maximumEnergyPairDifferencePP':max(energy_gaps),'precisionStatus':construction['precisionStatus'],
            'earlierOnlyScaleMembership':True,'stage45ControlPreserved':True,'priorArtifactsPreserved':True,
            'noMeanRefitOrAcquisition':True,'independentStudentExpectations':independent_student_expectations(scales)}


def main():
    args=arguments();verify();save('verification.json',build(),args.check)


if __name__=='__main__':main()
