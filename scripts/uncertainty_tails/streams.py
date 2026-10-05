"""Canonical multidimensional QMC registry: shared keys, separate seat/layer streams."""
from functools import lru_cache
import hashlib
import numpy as np
from scipy.stats import norm,t,qmc
from scripts.uncertainty_revision.coordinates import partition
from scripts.uncertainty_revision.estimation import labels
from .common import INVENTORY,read
from .integration import open_unit


def keys(row):
    prefix=f"{row['layer']}:{row['targetYear']}";seat=row['targetElectorateId'];result={}
    for name in ('balance','mass'):
        result[name]=(prefix+':shared:'+name,prefix+':seat:'+seat+':'+name)
    tags=labels(row);other=partition(row['groups'])[2]
    result['within']=[(prefix+':shared:within:'+tags[i],prefix+':seat:'+seat+':within:'+row['ids'][i]) for i in other]
    return result


def registry(rows):
    names=set()
    for row in rows:
        k=keys(row)
        names.update(k['balance']);names.update(k['mass'])
        for pair in k['within']:names.update(pair)
    return sorted(names)


@lru_cache(maxsize=1)
def uniforms(year,count):
    inventory=read(INVENTORY)
    rows=[r for key in ('partyRecords','candidateRecords') for r in inventory[key] if r['targetYear']==year]
    names=registry(rows)
    if count & (count-1):raise ValueError('Simulation count must be power of two')
    bank=open_unit(qmc.Sobol(len(names),scramble=True,bits=30,seed=460046+year).random_base2(int(np.log2(count))))
    return names,bank


def noise(row,scales,count,student=False):
    names,bank=uniforms(row['targetYear'],count);index={name:i for i,name in enumerate(names)};k=keys(row)
    def u(name):return bank[:,index[name]]
    result,total={},{}
    for name in ('balance','mass'):
        shared,seat=k[name];s=scales[name]
        z=t.ppf(u(seat),4) if student and name=='balance' else norm.ppf(u(seat))
        result[name]=s['shared']*norm.ppf(u(shared))+s['seat']*z
        total[name]=float(np.hypot(s['shared'],s['seat']))
    other=k['within']
    if other:
        eta=np.column_stack([scales['within']['shared']*norm.ppf(u(shared))+scales['within']['seat']*norm.ppf(u(seat)) for shared,seat in other])
        result['within']=eta-eta.mean(axis=1,keepdims=True)
    else:result['within']=np.empty((count,0))
    total['within']=float(np.hypot(scales['within']['shared'],scales['within']['seat']))
    total['balanceShared']=scales['balance']['shared'];total['balanceSeat']=scales['balance']['seat']
    return result,total


def permutation(count,key):
    seed=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'little')
    return np.random.default_rng(seed).permutation(count)
