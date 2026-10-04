"""Offline numerical contracts shared by adapters and independent tests."""
import numpy as np
from scipy.special import log_ndtr, logsumexp


def helmert(k):
    h=np.zeros((k,k-1))
    for j in range(1,k):
        h[:j,j-1]=1/np.sqrt(j*(j+1));h[j,j-1]=-j/np.sqrt(j*(j+1))
    return h


def softmax(x):
    x=np.asarray(x);return np.exp(x-logsumexp(x,axis=-1,keepdims=True))


def log_interval(lower,upper,mean,sd):
    """Normal interval probability using the tail with less cancellation."""
    a=(np.asarray(lower)-mean)/sd;b=(np.asarray(upper)-mean)/sd
    left=b<=0;right=a>=0
    la=np.where(right,log_ndtr(-b),log_ndtr(a))
    lb=np.where(right,log_ndtr(-a),log_ndtr(b))
    gap=np.minimum(la-lb,-np.finfo(float).eps)
    return lb+np.log(-np.expm1(gap))


def project_box(points,lower,upper,max_sum=1,min_sum=0):
    """Strictly convex squared-distance projection; no poll renormalization."""
    points=np.asarray(points,float);lo=np.asarray(lower,float);hi=np.asarray(upper,float)
    if np.any(~np.isfinite(points)) or np.any(lo>hi) or sum(lo)>max_sum+1e-12 or sum(hi)<min_sum-1e-12:
        raise ValueError('Infeasible rounding projection')
    answer=np.clip(points,lo,hi)
    target=max_sum if sum(answer)>max_sum else min_sum if sum(answer)<min_sum else None
    if target is None:return answer
    a=min(points-hi)-1;b=max(points-lo)+1
    for _ in range(100):
        m=(a+b)/2;v=np.clip(points-m,lo,hi)
        if sum(v)>target:a=m
        else:b=m
    v=np.clip(points-(a+b)/2,lo,hi)
    if abs(sum(v)-target)>1e-12:raise ValueError('Projection numerical failure')
    return v


def bridge_factor(times):
    """Endpoint-first Brownian transform: L L' = min(t,u)/7."""
    t=np.asarray(times,float);n=len(t);cov=np.minimum.outer(t,t)/7
    first=t/np.sqrt(7*t[-1])
    if n==1:return first[:,None]
    bridge=cov[:-1,:-1]-np.outer(first[:-1],first[:-1])
    detail=np.linalg.cholesky(bridge)
    out=np.zeros((n,n));out[:,0]=first;out[:-1,1:]=detail
    return out
