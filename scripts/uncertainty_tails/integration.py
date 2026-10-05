"""Outcome-free conditional logistic locations and explicit integration checks."""
from functools import lru_cache
import numpy as np
from scipy.special import expit, logit, softmax
from scipy.stats import norm, t, qmc
from scipy.interpolate import PchipInterpolator
from scripts.uncertainty_revision.coordinates import partition, binary_draw
from scripts.uncertainty.transforms import validate


def open_unit(u):
    """Midpoints of Sobol's 30-bit cells, including the cell beginning at zero."""
    return np.asarray(u,float)+.5/(2**30)


@lru_cache(maxsize=32)
def quadrature(dimension, count):
    if count<2 or count & (count-1): raise ValueError('Quadrature count must be a power of two')
    u=open_unit(qmc.Sobol(dimension,scramble=True,bits=30,seed=460046+dimension).random_base2(int(np.log2(count))-1))
    return np.concatenate((u,1-u))


def student_nodes(shared, seat, count, nu=4):
    u=quadrature(2,count)
    return shared*norm.ppf(u[:,0])+seat*t.ppf(u[:,1],nu)


def solve_binary(p, nodes):
    p=np.asarray(p,float); active=(p>0)&(p<1); result=np.zeros_like(p)
    if not np.any(active): return result
    target=p[active]; centre=logit(target); low=centre-80;high=centre+80
    for _ in range(100):
        mid=(low+high)/2
        expectation=expit(mid[:,None]+nodes).mean(axis=1)
        low=np.where(expectation<target,mid,low);high=np.where(expectation>=target,mid,high)
        if np.max(high-low)<1e-12:break
    result[active]=(low+high)/2
    return result


@lru_cache(maxsize=16)
def student_table(shared, seat, count=4096):
    grid=np.linspace(-20,20,1025)
    location=solve_binary(expit(grid),student_nodes(shared,seat,count))
    return PchipInterpolator(grid,location)


def student_location(p, shared, seat):
    p=np.asarray(p,float); out=np.zeros_like(p); active=(p>0)&(p<1)
    logits=logit(p[active]); inside=np.abs(logits)<=20
    locations=np.empty_like(logits)
    locations[inside]=student_table(shared,seat)(logits[inside])
    locations[~inside]=solve_binary(p[active][~inside],student_nodes(shared,seat,4096))
    out[active]=locations
    return out


def within_factor(tags, shared, seat):
    """Label-specific shared effects plus independent seat effects."""
    names=sorted(set(tags));factor=np.zeros((len(tags),len(names)+len(tags)))
    for i,tag in enumerate(tags):factor[i,names.index(tag)]=shared;factor[i,len(names)+i]=seat
    return factor-factor.mean(axis=0,keepdims=True)


def within_nodes(dimension, sd, count, tags=None, shared=None, seat=None, seed=None):
    factor=None if tags is None or len(set(tags))==dimension else within_factor(tags,shared,seat)
    width=dimension if factor is None else factor.shape[1]
    if seed is None:u=quadrature(width,count)
    else:
        u=open_unit(qmc.Sobol(width,scramble=True,bits=30,seed=seed).random_base2(int(np.log2(count))-1))
        u=np.concatenate((u,1-u))
    normal=norm.ppf(u)
    if factor is not None:return np.einsum('ij,kj->ik',normal,factor,optimize=False)
    normal*=sd
    return normal-normal.mean(axis=1,keepdims=True)


def within_offsets(base, sd, count=64, tags=None, shared=None, seat=None):
    b=np.asarray(base,float)
    options={} if tags is None else {'count':count,'tags':tags,'shared':shared,'seat':seat}
    if b.ndim==2 and len(b)>4096 and len(b)%4096==0 and np.array_equal(b,np.tile(b[:4096],(len(b)//4096,1))):
        return np.tile(conditional_offsets(b[:4096],sd,**options),(len(b)//4096,1))
    return conditional_offsets(b,sd,**options)


def conditional_offsets(base, sd, count=64, block=128, tags=None, shared=None, seat=None):
    """Solve each conditional remainder composition, never a target-outcome correction."""
    b=np.asarray(base,float); one=b.ndim==1
    if one:b=b[None,:]
    if b.shape[1]==1 or sd==0: return np.zeros_like(b)[0] if one else np.zeros_like(b)
    nodes=within_nodes(b.shape[1],sd,count,tags,shared,seat)
    output=np.empty_like(b)
    for start in range(0,len(b),block):
        p=b[start:start+block];positive=p>0
        logs=np.full(p.shape,-np.inf);np.log(p,out=logs,where=positive)
        delta=-.5*sd*sd*(1-2*p);delta=np.where(positive,delta,0.)
        for _ in range(200):
            expected=softmax(logs[:,None,:]+delta[:,None,:]+nodes[None,:,:],axis=-1).mean(axis=1)
            if np.max(np.abs(expected-p))<=1e-10:break
            update=np.zeros_like(p);np.log(p/np.where(expected>0,expected,1),out=update,where=positive)
            delta+=update
            delta-=np.sum(delta*positive,axis=1,keepdims=True)/positive.sum(axis=1,keepdims=True)
        else: raise ValueError('Conditional remainder location did not converge')
        output[start:start+block]=delta
    return output[0] if one else output


def conditional_inverse(base, groups, eta, scales, student=False, nodes=64, tags=None):
    b=validate(base);draws=len(eta['balance']);constant=b.ndim==1
    n,l,other=partition(groups);major=n+l
    if constant:b=np.broadcast_to(b,(draws,len(b)))
    q=np.zeros_like(b);mass=b[:,major].sum(axis=1) if major else np.zeros(draws)
    if major and other:mass=binary_draw(mass,eta['mass'],scales['mass'])
    elif major:mass=np.ones(draws)
    if n and l:
        original=b[:,major].sum(axis=1)
        ratio=np.divide(b[:,n[0]],original,out=np.zeros(draws),where=original>0)
        if student:
            location=student_location(ratio,scales['balanceShared'],scales['balanceSeat'])
            varied=expit(location+eta['balance'])
            ratio=np.where(ratio==0,0,np.where(ratio==1,1,varied))
        else:ratio=binary_draw(ratio,eta['balance'],scales['balance'])
        q[:,n[0]],q[:,l[0]]=mass*ratio,mass*(1-ratio)
    elif major:q[:,major[0]]=mass
    if other:
        original=b[:,other];total=original.sum(axis=1)
        p=np.divide(original,total[:,None],out=np.zeros_like(original),where=total[:,None]>0)
        p[total==0,0]=1
        options={'count':nodes,'tags':None if tags is None else [tags[i] for i in other],
                 'shared':scales.get('withinShared'),'seat':scales.get('withinSeat')}
        offset=within_offsets(p[0] if constant else p,scales['within'],**options)
        logs=np.full(p.shape,-np.inf);np.log(p,out=logs,where=p>0)
        q[:,other]=(1-mass)[:,None]*softmax(logs+offset+eta['within'],axis=-1)
    validate(q)
    return q,{'scope':'conditional outcome-free quadrature for every supplied vector','nodes':nodes,
              'zeroLock':bool(np.all(q[:,np.all(b==0,axis=0)]==0))}


def conditional_check(base, groups, scales, student=False, tags=None):
    """Independent larger-node expectation checks, without target outcomes."""
    b=validate(base);b=b[None,:] if b.ndim==1 else b
    n,l,other=partition(groups);results={}
    if n and l and student:
        mass=b[:,n+l].sum(axis=1);p=np.divide(b[:,n[0]],mass,out=np.zeros(len(b)),where=mass>0)
        location=student_location(p,scales['balanceShared'],scales['balanceSeat'])
        expected=expit(location[:,None]+student_nodes(scales['balanceShared'],scales['balanceSeat'],8192)).mean(axis=1)
        expected=np.where(p==0,0,np.where(p==1,1,expected))
        results['balanceMaximumGapPP']=float(100*np.max(np.abs(expected-p)))
    if len(other)>1:
        raw=b[:,other];mass=raw.sum(axis=1)
        p=np.divide(raw,mass[:,None],out=np.zeros_like(raw),where=mass[:,None]>0);p[mass==0,0]=1
        within_tags=None if tags is None else [tags[i] for i in other]
        offset=within_offsets(p,scales['within'],tags=within_tags,shared=scales.get('withinShared'),seat=scales.get('withinSeat'));logs=np.full(p.shape,-np.inf);np.log(p,out=logs,where=p>0)
        for count in (128,256):
            # Different scrambling, not merely another prefix of the construction bank.
            z=within_nodes(len(other),scales['within'],count,within_tags,scales.get('withinShared'),scales.get('withinSeat'),460146+count)
            expected=softmax(logs[:,None,:]+offset[:,None,:]+z,axis=-1).mean(axis=1)
            results[f'withinMaximumGapPP{count}']=float(100*np.max(np.abs(expected-p)*mass[:,None]))
    return results
