"""Frozen national metrics; probability scores apply to election-day draws only."""
import numpy as np
from .common import COARSE,coarsen


def point(prediction,actual,categories):
    error=np.asarray(prediction)-np.asarray(actual)
    return {'MAEpp':float(100*np.mean(abs(error))),'RMSEpp':float(100*np.sqrt(np.mean(error**2))),
            'accountingBiasPP':float(100*np.mean(error)),
            'parties':[{'category':p,'prediction':float(x),'actual':float(y),'biasPP':float(100*e),'absoluteErrorPP':float(100*abs(e))}
                       for p,x,y,e in zip(categories,prediction,actual,error)]}


def crps(draws,actual):
    x=np.sort(np.asarray(draws));n=len(x)
    return float(100*(np.mean(abs(x-actual))-np.dot(2*np.arange(1,n+1)-n-1,x)/n**2))


def energy(draws,actual):
    x=np.asarray(draws);idx=np.linspace(0,len(x)-1,min(2000,len(x))).astype(int);x=x[idx];n=len(x)
    first=np.linalg.norm(x-np.asarray(actual),axis=1).mean();total=0.
    for start in range(0,n,128):total+=np.linalg.norm(x[start:start+128,None,:]-x[None,:,:],axis=-1).sum()
    return {'energyScorePP':float(100*(first-.5*total/n**2)),'subsampleSize':n,'subsampleIndices':idx.tolist()}


def probabilities(draws,actual,categories):
    draws=np.asarray(draws);rows=[]
    for i,p in enumerate(categories):
        intervals={}
        for level in (.5,.9):
            lo,hi=np.quantile(draws[:,i],[(1-level)/2,(1+level)/2],method='linear')
            intervals[str(level)]={'lower':float(lo),'upper':float(hi),'widthPP':float(100*(hi-lo)),'covered':bool(lo<=actual[i]<=hi)}
        rows.append({'category':p,'CRPSpp':crps(draws[:,i],actual[i]),'intervals':intervals})
    return {'meanCRPSpp':float(np.mean([r['CRPSpp'] for r in rows])),
            'coverage50':float(np.mean([r['intervals']['0.5']['covered'] for r in rows])),
            'coverage90':float(np.mean([r['intervals']['0.9']['covered'] for r in rows])),
            'width50PP':float(np.mean([r['intervals']['0.5']['widthPP'] for r in rows])),
            'width90PP':float(np.mean([r['intervals']['0.9']['widthPP'] for r in rows])),
            'parties':rows,**energy(draws,actual)}


def grouped(point_result):
    groups={'NAT':['NAT'],'LAB':['LAB'],'other_explicit':['GRN','ACT','NZF','MRI','TOP'],'Other':['OTH']}
    out=[]
    for name,cats in groups.items():
        rows=[r for r in point_result['parties'] if r['category'] in cats]
        if not rows:continue
        e=np.array([r['biasPP'] for r in rows])
        out.append({'group':name,'categories':[r['category'] for r in rows],'count':len(rows),
                    'MAEpp':float(np.mean(abs(e))),'RMSEpp':float(np.sqrt(np.mean(e**2))),'biasPP':float(np.mean(e))})
    return out
