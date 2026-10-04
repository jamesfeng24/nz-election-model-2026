"""Frozen six-category scores; no inference or constructed pseudo-distribution."""
import math
import numpy as np
from scripts.polling.national_model.metrics import crps,energy,point
from .common import CATEGORIES


def interval_score(lower,upper,actual,level):
    if not all(math.isfinite(v) for v in (lower,upper,actual,level)) or not 0<level<1 or lower>upper:raise ValueError('Invalid interval')
    alpha=1-level
    return 100*((upper-lower)+2/alpha*max(lower-actual,0)+2/alpha*max(actual-upper,0))


def distribution(draws,actual):
    x=np.asarray(draws,dtype=float);y=np.asarray(actual,dtype=float)
    if x.ndim!=2 or x.shape[1]!=len(CATEGORIES) or y.shape!=(len(CATEGORIES),):raise ValueError('Score schema mismatch')
    if not np.isfinite(y).all() or (y<0).any() or not np.isclose(y.sum(),1,atol=1e-10,rtol=0):raise ValueError('Invalid official complete simplex')
    if not np.isfinite(x).all() or (x<0).any() or not np.allclose(x.sum(1),1,atol=1e-10,rtol=0):raise ValueError('Invalid joint draws')
    rows=[]
    for i,p in enumerate(CATEGORIES):
        intervals={}
        for level in (.5,.9):
            lo,hi=np.quantile(x[:,i],[(1-level)/2,(1+level)/2],method='linear')
            intervals[str(level)]={'lower':float(lo),'upper':float(hi),'widthPP':float(100*(hi-lo)),'covered':bool(lo<=y[i]<=hi),'intervalScorePP':interval_score(lo,hi,y[i],level)}
        rows.append({'category':p,'CRPSpp':crps(x[:,i],y[i]),'intervals':intervals})
    result={'meanCRPSpp':float(np.mean([r['CRPSpp'] for r in rows])),'parties':rows,**energy(x,y)}
    for level,label in [(0.5,'50'),(0.9,'90')]:
        iv=[r['intervals'][str(level)] for r in rows]
        result['coverage'+label]=sum(r['covered'] for r in iv)/len(iv)
        result['coveredCount'+label]=sum(r['covered'] for r in iv)
        result['width'+label+'PP']=float(np.mean([r['widthPP'] for r in iv]))
        result['intervalScore'+label+'PP']=float(np.mean([r['intervalScorePP'] for r in iv]))
    return result


def major(point_metrics,probability=None):
    rows=[r for r in point_metrics['parties'] if r['category'] in ('NAT','LAB')]
    errors=[r['biasPP'] for r in rows]
    out={'count':len(rows),'MAEpp':sum(abs(e) for e in errors)/len(errors),'RMSEpp':math.sqrt(sum(e*e for e in errors)/len(errors)),'biasPP':sum(errors)/len(errors),'parties':rows}
    if probability:
        p=[r for r in probability['parties'] if r['category'] in ('NAT','LAB')]
        out['meanCRPSpp']=sum(r['CRPSpp'] for r in p)/len(p)
        for level,label in [(0.5,'50'),(0.9,'90')]:
            out['coveredCount'+label]=sum(r['intervals'][str(level)]['covered'] for r in p)
            out['width'+label+'PP']=sum(r['intervals'][str(level)]['widthPP'] for r in p)/len(p)
    return out
