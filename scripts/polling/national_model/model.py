"""Frozen Stage35 generative model in explicit S/R-independent national code."""
import os
os.environ.setdefault('JAX_ENABLE_X64','true')
os.environ.setdefault('XLA_FLAGS','--xla_force_host_platform_device_count=4')
import jax
jax.config.update('jax_enable_x64',True)
import jax.numpy as jnp
from jax.scipy.special import log_ndtr,logsumexp
import numpy as np
import numpyro
import numpyro.distributions as dist
from .common import ORDER
from .transforms import helmert

GL_X,GL_W=np.polynomial.legendre.leggauss(8)


def interval_logprob(lower,upper,mu,sd):
    """Stable Gaussian intervals, including narrow finite cells and censoring."""
    finite=jnp.isfinite(upper)
    safe_upper=jnp.where(finite,upper,mu)
    a=(lower-mu)/sd;b=(safe_upper-mu)/sd;right=a>=0
    la=jnp.where(right,log_ndtr(-b),log_ndtr(a));lb=jnp.where(right,log_ndtr(-a),log_ndtr(b))
    difference=jnp.minimum(la-lb,-jnp.finfo(jnp.float64).eps)
    tail=lb+jnp.log(-jnp.expm1(difference))
    width=jnp.where(finite,(safe_upper-lower)/sd,1.)
    mid=jnp.where(finite,(lower-mu)/sd+width/2,0.)
    z=mid[...,None]+width[...,None]/2*jnp.asarray(GL_X)
    quadrature=jnp.log(width/2)+logsumexp(jnp.log(jnp.asarray(GL_W))-.5*z*z-.5*jnp.log(2*jnp.pi),axis=-1)
    bounded=jnp.where(width<.001,quadrature,tail)
    return jnp.where(finite,bounded,log_ndtr(-a))


def arrays(case):
    roster=case['pollsterRoster'];data=[]
    for c in case['cycles']:
        h=helmert(len(c['categories']));n=len(c['polls'])
        d={k:c[k] for k in ('year','categories','endpointShares')}
        d.update(h=jnp.asarray(h),canonicalIndices=jnp.array([ORDER.index(p) for p in c['categories']]),
                 initialMean=jnp.array(c['initial']['mean']),initialFactor=jnp.array(c['initial']['factor']),
                 bridge=jnp.array(c['bridgeFactor']),nPolls=n,
                 pollster=jnp.array([roster.index(r['pollster']) for r in c['polls']],dtype=int),
                 method=jnp.array([r['segment']=='Reid-after-2017-assumed' for r in c['polls']],float),
                 n=jnp.array([r['nDecided'] for r in c['polls']]),
                 dayPoll=jnp.array([x['poll'] for x in c['days']],dtype=int),
                 dayLo=jnp.array([x['lo'] for x in c['days']],dtype=int),dayHi=jnp.array([x['hi'] for x in c['days']],dtype=int),
                 dayFraction=jnp.array([x['fraction'] for x in c['days']]),dayWeight=jnp.array([x['weight'] for x in c['days']]),
                 rowPoll=jnp.array([x['poll'] for x in c['rows']],dtype=int),rowCategory=jnp.array([x['index'] for x in c['rows']],dtype=int),
                 lower=jnp.array([x['lower'] for x in c['rows']]),upper=jnp.array([jnp.inf if x['upper'] is None else x['upper'] for x in c['rows']]))
        data.append(d)
    return data


def poll_expectation(path,house,method,bias,c):
    fraction=c['dayFraction'][:,None]
    state=path[c['dayLo']]*(1-fraction)+path[c['dayHi']]*fraction
    idx=c['dayPoll'];logits=state@c['h'].T+house[c['pollster'][idx]]+method*c['method'][idx,None]+bias
    daily=jax.nn.softmax(logits,axis=-1)
    return jax.ops.segment_sum(daily*c['dayWeight'][:,None],idx,c['nPolls'])


def national_model(data,n_pollsters):
    sigma=numpyro.sample('sigma',dist.HalfNormal(.035))
    house_scale=numpyro.sample('house_scale',dist.HalfNormal(.12))
    bias_scale=numpyro.sample('bias_scale',dist.HalfNormal(.08))
    canonical=jnp.asarray(helmert(8))
    u=numpyro.sample('house_raw',dist.Normal(0,1).expand((n_pollsters,7)).to_event(2))
    house=house_scale*(u-u.mean(axis=0))@canonical.T
    method=numpyro.sample('method_raw',dist.Normal(0,1).expand((7,)).to_event(1))@canonical.T*.05
    for c in data:
        name=str(c['year']);k=len(c['categories'])-1;t=c['bridge'].shape[0]
        initial=numpyro.sample('initial_'+name,dist.Normal(0,1).expand((k,)).to_event(1))
        endpoint=numpyro.sample('endpoint_'+name,dist.Normal(0,1).expand((k,)).to_event(1))
        detail=numpyro.sample('detail_'+name,dist.Normal(0,1).expand((t-1,k)).to_event(2))
        innovation=jnp.concatenate([endpoint[None,:],detail],axis=0)
        x0=c['initialMean']+c['initialFactor']@initial
        path=jnp.concatenate([x0[None,:],x0+sigma*(c['bridge']@innovation)],axis=0)
        raw_bias=numpyro.sample('bias_raw_'+name,dist.Normal(0,1).expand((k,)).to_event(1))
        bias=bias_scale*raw_bias@c['h'].T
        numpyro.deterministic('bias_'+name,bias)
        numpyro.deterministic('path_'+name,path)
        if c['nPolls']:
            mu=poll_expectation(path,house[:,c['canonicalIndices']],method[c['canonicalIndices']],bias,c)
            means=mu[c['rowPoll'],c['rowCategory']]
            sd=jnp.sqrt(2*means*(1-means)/c['n'][c['rowPoll']]+.005**2)
            numpyro.factor('poll_likelihood_'+name,jnp.sum(interval_logprob(c['lower'],c['upper'],means,sd)))
        if c['endpointShares'] is not None:
            # Earlier endpoint only; no endpoint for the target election.
            numpyro.sample('earlier_result_'+name,dist.Normal(jax.nn.softmax(path[-1]@c['h'].T),.0005).to_event(1),obs=jnp.asarray(c['endpointShares']))
        numpyro.deterministic('current_'+name,jax.nn.softmax(path[-1]@c['h'].T))
    numpyro.deterministic('house_effect',house)
    numpyro.deterministic('method_effect',method)


def mass_blocks(data):
    global_names=['sigma','house_scale','bias_scale','house_raw','method_raw']
    for c in data:
        global_names.extend(k+'_'+str(c['year']) for k in ('initial','endpoint','bias_raw'))
    return [tuple(global_names)]
