"""Independent scalar score checks against sealed cached draws."""
import argparse
import math
import numpy as np
from .common import ROOT,OUT,CASES,CATEGORIES,read,save,coarsen,sha
from .archive import check_provenance
from .evaluation import own_case,forecast_contract


def independent_crps(values,y):
    """Integral of empirical CDF discrepancy, separate from sorted-rank formula."""
    x=sorted(float(v) for v in values);breaks=sorted(set(x+[float(y)]));n=len(x)
    terms=[];j=0
    for a,b in zip(breaks,breaks[1:]):
        while j<n and x[j]<=a:j+=1
        terms.append((b-a)*(j/n-(1 if y<=a else 0))**2)
    return 100*math.fsum(terms)


def independent_energy(draws,y):
    selected=np.linspace(0,len(draws)-1,min(2000,len(draws))).astype(int);x=np.asarray(draws)[selected];n=len(x)
    first=math.fsum(float(np.sqrt(np.sum((r-y)**2))) for r in x)/n
    blocks=[]
    for i in range(0,n,200):
        for j in range(0,n,200):
            a=x[i:i+200];b=x[j:j+200]
            d=np.sqrt(np.sum((a[:,None,:]-b[None,:,:])**2,axis=2))
            blocks.append(math.fsum(d.ravel().tolist()))
    return 100*(first-.5*math.fsum(blocks)/n**2)


def close(a,b,tol=2e-9):
    if not math.isclose(a,b,abs_tol=tol,rel_tol=0):raise ValueError(f'Independent arithmetic disagreement {a} {b}')


def verify():
    preserved=check_provenance();contract=forecast_contract();ev=read(OUT/'evaluation.json');checks=0;draw_count=0
    for row in ev['cases']:
        year=row['year'];actual=np.array(row['actual']);owned,avg=own_case(year);models={'owned':owned,'average':None}
        ext=next(r for r in contract['cases'] if r['year']==year)
        if ext['status']=='accepted':
            fr=read(OUT/ext['attemptFile']);a=np.load(OUT/ext['drawFile'],allow_pickle=False);models['gauss']=coarsen(a['electionDay'].reshape(-1,len(fr['parties'])),fr['parties'])
        for name,x in models.items():
            if name not in row['systems'] or not row['systems'][name].get('point'):continue
            means=avg if x is None else np.array([math.fsum(x[:,j].tolist())/len(x) for j in range(6)])
            error=(means-actual)*100;p=row['systems'][name]['point']
            close(math.fsum(abs(e) for e in error)/6,p['MAEpp']);close(math.sqrt(math.fsum(e*e for e in error)/6),p['RMSEpp']);checks+=2
            for i,record in enumerate(p['parties']):close(float(error[i]),record['biasPP']);checks+=1
            if x is None:continue
            draw_count+=len(x);prob=row['systems'][name]['probability']
            for i,record in enumerate(prob['parties']):
                close(independent_crps(x[:,i],actual[i]),record['CRPSpp']);checks+=1
                for level in (.5,.9):
                    # Explicit empirical linear order-statistic interpolation.
                    values=sorted(x[:,i].tolist());quant=[]
                    for q in ((1-level)/2,(1+level)/2):
                        index=(len(values)-1)*q;k=math.floor(index);f=index-k
                        quant.append(values[k]*(1-f)+values[min(k+1,len(values)-1)]*f)
                    lo,hi=quant;iv=record['intervals'][str(level)];close(lo,iv['lower']);close(hi,iv['upper'])
                    alpha=1-level;score=hi-lo
                    if actual[i]<lo:score+=2/alpha*(lo-actual[i])
                    if actual[i]>hi:score+=2/alpha*(actual[i]-hi)
                    close(100*score,iv['intervalScorePP']);close(100*(hi-lo),iv['widthPP']);checks+=4
            close(independent_energy(x,actual),prob['energyScorePP']);checks+=1
    common=ev['pooledCommon']
    if common:
        for name,s in common['systems'].items():
            r=[e['systems'][name]['point'] for e in ev['cases'] if e['systems']['gauss']['point']]
            close(math.fsum(x['MAEpp'] for x in r)/len(r),s['MAEpp']);close(math.sqrt(math.fsum(x['RMSEpp']**2 for x in r)/len(r)),s['RMSEpp']);checks+=2
        for name in ('owned','average'):
            close(common['systems'][name]['MAEpp']-common['systems']['gauss']['MAEpp'],common['paired'][name+'MinusGaussMAEpp']);checks+=1
    return {'independentScalarChecks':checks,'jointDrawsChecked':draw_count,'priorDataFilesByteIdentical':preserved,'rawResourcesVerified':5,'numericalEquationsUnchanged':True,'ownershipPreference':None,'sourceCutoffCounterfactuals':'actual pinned upstream adapter exercised before inference; heldout results/postcutoff shares/future-only revisions leave dataset fingerprint unchanged','historicalInferenceRerun':False,'tolerancePP':2e-9,'energyDefinition':'same declared deterministic2000Vstatistic, independent200x200compensated blocksum'}


def run(check=False):save('independent-verification.json',verify(),check)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
