"""Global outer bounds for sums/ratios of population-weighted votes.

Spatial branch-and-bound uses McCormick relaxations of x=P*w. A relaxation
bound is reported separately from an attainable feasible value and its gap.
No optimizer witness is a nominal population or notional-vote estimate.
"""
import heapq
import itertools
import math
import numpy as np
from scipy.optimize import linprog
from scripts.boundaries.contract import fraction


class TargetEnvelope:
    def __init__(self, population, scope, target):
        self.p=population
        self.edges=[e for e in scope['edges'] if e['target']==target]
        self.sources=[e['source'] for e in self.edges]
        self.k=len(self.edges);self.n=population.n
        self.flows=[population.vector(s,target) for s in self.sources]
        self.totals=[population.vector(s) for s in self.sources]
        src={r['code']:r for r in scope['sources']}
        self.ranges=[(src[s]['populationLower'],src[s]['populationUpper']) for s in self.sources]
        if any(lo<=0 for lo,_ in self.ranges):raise ValueError('Undefined notional source denominator')
        self.wbounds=[(float(fraction(e['weightLower'])),float(fraction(e['weightUpper']))) for e in self.edges]
        self.E=np.pad(population.E,((0,0),(0,self.k)))

    def relaxation(self, ranges, numerator, denominator, sign):
        scale=100000.0
        A=list(np.pad(self.p.A,((0,0),(0,self.k))));b=list(self.p.b/scale)
        for i,((lo,hi),(wl,wu)) in enumerate(zip(ranges,self.wbounds)):
            lo,hi=lo/scale,hi/scale
            P=np.pad(self.totals[i],(0,self.k));x=np.pad(self.flows[i],(0,self.k))
            w=np.zeros(self.n+self.k);w[self.n+i]=1
            A.extend([P,-P,-x+lo*w+wl*P,-x+hi*w+wu*P,x-hi*w-wl*P,x-lo*w-wu*P])
            b.extend([hi,-lo,lo*wl,hi*wu,-hi*wl,-lo*wu])
        A,b=np.array(A),np.array(b)
        num=np.concatenate((np.zeros(self.n),numerator))
        den=None if denominator is None else np.concatenate((np.zeros(self.n),denominator))
        ratio=0.0
        for _ in range(40):
            c=sign*(num if den is None else num-ratio*den)
            c=c/max(1.0,max(abs(c)))
            r=linprog(c,A_ub=A,b_ub=b,A_eq=self.E,b_eq=self.p.c/scale,
                      bounds=[(0,None)]*self.n+self.wbounds,method='highs-ds',
                      options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
            if r.status==2:return None
            if not r.success:raise ValueError('Notional bound solver: '+r.message)
            self.p.verify(r.x[:self.n]*scale)
            if max(np.sum(A*r.x,axis=1)-b)>1e-6:raise ValueError('Relaxation witness residual')
            value=float(sum(num*r.x))
            if den is not None:
                d=float(sum(den*r.x))
                if d<=0:raise ValueError('Notional target valid votes may vanish')
                value/=d
            if den is None or abs(value-ratio)<1e-12:break
            ratio=value
        else:raise ValueError('Fractional relaxation did not converge')
        x=r.x[:self.n]*scale
        weights=np.array([sum(a*x)/sum(d*x) for a,d in zip(self.flows,self.totals)])
        actual=float(sum(numerator*weights))
        if denominator is not None:actual/=float(sum(denominator*weights))
        if sign*value>sign*actual+1e-6:raise ValueError('Invalid relaxation direction')
        return sign*value,sign*actual,x

    def bound(self, numerator, denominator=None, maximize=False, max_nodes=64, tolerance=None):
        numerator=np.array(numerator,dtype=float)
        denominator=None if denominator is None else np.array(denominator,dtype=float)
        if len(numerator)!=self.k or np.any(numerator<0):raise ValueError('Invalid vote coefficients')
        if denominator is not None and (len(denominator)!=self.k or np.any(denominator<=0) or np.any(numerator>denominator)):
            raise ValueError('Invalid share coefficients')
        # A one-source share cancels its unknown geographic weight exactly.
        if self.k==1 and denominator is not None:
            v=float(numerator[0]/denominator[0]);return {'outer':v,'attainable':v,'gap':0.0,'nodes':0}
        if self.k==1:
            v=float(numerator[0]*fraction(self.edges[0]['weightUpper' if maximize else 'weightLower']))
            return {'outer':v,'attainable':v,'gap':0.0,'nodes':0}
        if not np.any(numerator):return {'outer':0.0,'attainable':0.0,'gap':0.0,'nodes':0}
        sign=-1 if maximize else 1
        tolerance=tolerance if tolerance is not None else (2e-6 if denominator is not None else .25)
        root=self.relaxation(self.ranges,numerator,denominator,sign)
        if root is None:raise ValueError('Infeasible root notional system')
        best=root[1];serial=itertools.count()
        heap=[(root[0],next(serial),self.ranges,root[2])];nodes=1
        while heap and nodes+2<=max_nodes:
            lower,_,ranges,x=heapq.heappop(heap)
            if best-lower<=tolerance:
                heapq.heappush(heap,(lower,next(serial),ranges,x));break
            widths=[(hi-lo)/max(1,lo) for lo,hi in ranges]
            i=max(range(self.k),key=lambda j:widths[j])
            lo,hi=ranges[i]
            if hi-lo<1e-7:raise ValueError('Numerical notional bound gap with fixed denominators')
            mid=(lo+hi)/2
            for interval in [(lo,mid),(mid,hi)]:
                child=list(ranges);child[i]=interval
                result=self.relaxation(child,numerator,denominator,sign);nodes+=1
                if result is None:continue
                bound,actual,witness=result
                best=min(best,actual)
                if bound<best:heapq.heappush(heap,(bound,next(serial),child,witness))
            heap=[h for h in heap if h[0]<best];heapq.heapify(heap)
        lower=min(best,heap[0][0] if heap else best)
        # Outward serialization padding is numerical only, not a relaxation of
        # source disclosure/rounding constraints. Gap remains explicitly visible.
        padding=1e-9 if denominator is not None else 1e-6
        outer=sign*(lower-padding)
        outer=max(0.0,min(1.0,outer)) if denominator is not None else max(0.0,outer)
        return {'outer':outer,'attainable':sign*best,'gap':max(0.0,best-lower)+padding,'nodes':nodes}
