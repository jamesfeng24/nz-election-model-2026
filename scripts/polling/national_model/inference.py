"""Resumable exact-signature MCMC. Evaluation is a separate command."""
import argparse
import gc
import hashlib
import importlib.metadata
import os
import time
import numpy as np
from .common import ROOT,OUT,FOUNDATION,read,save,digest
from .prepare import prepare
from .inventory import semantic
from .transforms import helmert,softmax

CODE_FILES=['prepare.py','transforms.py','model.py','inference.py']


def model_code():
    base=ROOT/'scripts/polling/national_model'
    return {name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in CODE_FILES}


def fit_signature(case):
    inputs=semantic(case);inputs={k:v for k,v in inputs.items() if k not in ('id','branch','excluded','informationSet')}
    for c in inputs['cycles']:c.pop('excluded')
    env=read(OUT/'environment.json');spec=read(FOUNDATION/'specification.json')
    return {'inputs':inputs,'inputDigest':digest(inputs),'environment':env,
            'configurationDigest':digest(spec),'code':model_code(),'seeds':spec['inference']['chainSeeds']}


def actual_environment_matches():
    expected=read(OUT/'environment.json')
    actual={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    if expected['packages']!=actual:raise ValueError('Inference environment differs from locked runtime')


def forecast(samples,case):
    year=str(case['year']);x=np.asarray(samples['path_'+year])[:,:,-1,:]
    sigma=np.asarray(samples['sigma']);h=helmert(len(case['schema']))
    seed=360000+case['year']*100+case['horizonDays'];rng=np.random.default_rng(seed)
    z=rng.normal(size=x.shape);future=x+sigma[...,None]*np.sqrt(case['horizonDays']/7)*z
    current=softmax(x@h.T);election=softmax(future@h.T)
    return {'drawIds':[f'chain{c+1}-iteration{i:04d}' for c in range(4) for i in range(2000)],
            'futureSeed':seed,'current':current.reshape(-1,len(h)).tolist(),
            'electionDay':election.reshape(-1,len(h)).tolist(),'xCutoff':x.reshape(-1,x.shape[-1]).tolist(),
            'futureNormals':z.reshape(-1,x.shape[-1]).tolist(),'sigma':sigma.reshape(-1).tolist(),
            'expectedCurrent':current.mean(axis=(0,1)).tolist(),'expectedElectionDay':election.mean(axis=(0,1)).tolist()}


def diagnostics(samples,projection,extra,depth):
    import arviz as az
    variables={k:np.asarray(v) for k,v in samples.items()}
    variables['election_day_shares']=np.asarray(projection['electionDay']).reshape(4,2000,-1)
    rows=[];failed=[];constants=[]
    for name,values in variables.items():
        flat=values.reshape(values.shape[0],values.shape[1],-1)
        constant=np.ptp(flat,axis=(0,1))==0
        constants.append({'variable':name,'exactConstantCoordinates':np.flatnonzero(constant).tolist()})
        idx=np.flatnonzero(~constant)
        if len(idx)==0:continue
        arr=flat[:,:,idx]
        rh=np.asarray(az.rhat({'v':arr},method='rank')['v']).reshape(-1)
        bulk=np.asarray(az.ess({'v':arr},method='bulk')['v']).reshape(-1)
        tail=np.asarray(az.ess({'v':arr},method='tail')['v']).reshape(-1)
        bad=~np.isfinite(rh)|~np.isfinite(bulk)|~np.isfinite(tail)|(rh>1.01)|(bulk<400)|(tail<400)
        clean=lambda x:[float(v) if np.isfinite(v) else None for v in x]
        row={'variable':name,'coordinates':idx.tolist(),'rhat':clean(rh),'bulkESS':clean(bulk),'tailESS':clean(tail),
             'maxRhat':float(np.max(rh)) if np.all(np.isfinite(rh)) else None,'minBulkESS':float(np.min(bulk)) if np.all(np.isfinite(bulk)) else None,'minTailESS':float(np.min(tail)) if np.all(np.isfinite(tail)) else None,'failedCoordinates':idx[bad].tolist()}
        rows.append(row)
        if any(bad):failed.append({'variable':name,'count':int(sum(bad))})
    divergence=int(np.asarray(extra['diverging']).sum());steps=np.asarray(extra['num_steps'])
    return {'passed':not failed and divergence==0,'failedVariables':failed,'divergences':divergence,'variables':rows,
            'constants':constants,'treeDepthContacts':int((steps>=2**depth-1).sum()),'maxNumSteps':int(steps.max()),
            'meanAcceptProbability':float(np.asarray(extra['accept_prob']).mean()),
            'energyBFMI':np.asarray(az.bfmi(np.asarray(extra['energy']))).tolist(),
            'maxRhat':max((r['maxRhat'] for r in rows if r['maxRhat'] is not None),default=None),'minBulkESS':min((r['minBulkESS'] for r in rows if r['minBulkESS'] is not None),default=None),
            'minTailESS':min((r['minTailESS'] for r in rows if r['minTailESS'] is not None),default=None)}


def calculate(case,signature,attempt):
    actual_environment_matches()
    from .model import national_model,arrays,mass_blocks
    import jax
    import jax.numpy as jnp
    from numpyro.infer import MCMC,NUTS,init_to_median
    spec=read(FOUNDATION/'specification.json')['inference'];settings=spec if attempt==1 else {**spec,**spec['failureRetry']}
    if len(jax.devices('cpu'))<4:raise ValueError('Four CPU chain devices required')
    data=arrays(case);start=time.monotonic()
    kernel=NUTS(national_model,target_accept_prob=settings['targetAccept'],max_tree_depth=settings['maxTreeDepth'],
                dense_mass=mass_blocks(data),init_strategy=init_to_median(num_samples=15))
    sampler=MCMC(kernel,num_warmup=settings['warmup'],num_samples=2000,num_chains=4,chain_method='parallel',progress_bar=True)
    keys=jnp.stack([jax.random.PRNGKey(x) for x in spec['chainSeeds']])
    print('START',case['id'],'attempt',attempt,'signature',digest(signature),flush=True)
    sampler.run(keys,data=data,n_pollsters=len(case['pollsterRoster']),extra_fields=('diverging','num_steps','accept_prob','energy'))
    samples=sampler.get_samples(group_by_chain=True);extra=sampler.get_extra_fields(group_by_chain=True)
    projection=forecast(samples,case);diag=diagnostics(samples,projection,extra,settings['maxTreeDepth'])
    hyper={k:{'mean':float(np.asarray(samples[k]).mean()),'quantiles':np.quantile(np.asarray(samples[k]),[.05,.5,.95]).tolist()}
           for k in ('sigma','house_scale','bias_scale')}
    result={'fitKey':digest(signature),'signature':signature,'attempt':attempt,'sourceCaseId':case['id'],'settings':settings,
            'status':'accepted' if diag['passed'] else 'numerical_failure','diagnostics':diag,'draws':projection,
            'parameterSummary':hyper,'runtimeSeconds':time.monotonic()-start,'pid':os.getpid(),
            'chainSeeds':spec['chainSeeds'],'drawsPerChain':2000,'categories':case['schema'],
            'availabilityLabel':case['informationSet']}
    save(f"fits/{digest(signature)}/attempt{attempt}.json.gz",result)
    print('FINISHED',case['id'],'attempt',attempt,result['status'],'seconds',round(result['runtimeSeconds'],1),flush=True)
    del sampler,samples,extra;gc.collect();jax.clear_caches()
    return result


def run(branches,years,horizons):
    cases=read(OUT/'inventory.json')['cases'];index=read(OUT/'construction.json') if (OUT/'construction.json').exists() else {'cases':[]}
    by_id={r['id']:r for r in index['cases']}
    for entry in cases:
        if entry['branch'] not in branches or entry['year'] not in years or entry['horizonDays'] not in horizons:continue
        case=prepare(entry['year'],entry['horizonDays'],entry['branch'])
        if digest(semantic(case))!=entry['inputDigest']:raise ValueError('Changed frozen inputs')
        if case['status']!='ready':
            by_id[case['id']]={'id':case['id'],'status':case['status'],'reason':case['reason']}
        else:
            sig=fit_signature(case);key=digest(sig);last=None;attempts=[]
            for attempt in (1,2):
                path=OUT/f'fits/{key}/attempt{attempt}.json.gz'
                if path.exists():
                    last=read(path)
                    if last['signature']!=sig:raise ValueError('Incompatible cache signature')
                    print('REUSE',case['id'],key,'attempt',attempt,flush=True)
                else:
                    try:last=calculate(case,sig,attempt)
                    except Exception as e:
                        last={'fitKey':key,'signature':sig,'attempt':attempt,'status':'numerical_failure','exception':str(e),'exceptionType':type(e).__name__}
                        save(f'fits/{key}/attempt{attempt}.json.gz',last)
                        print('FAILED_EXCEPTION',case['id'],attempt,str(e),flush=True)
                        if not isinstance(e,FloatingPointError) and 'Cannot find valid initial parameters' not in str(e):
                            raise RuntimeError('Implementation/runtime exception requires investigation; not a completed numerical abstention') from e
                attempts.append(str(path.relative_to(OUT)))
                if last['status']=='accepted':break
            by_id[case['id']]={'id':case['id'],'fitKey':key,'status':last['status'],'attempts':attempts,
                               'acceptedAttempt':last['attempt'] if last['status']=='accepted' else None,
                               'reason':None if last['status']=='accepted' else 'frozen_numerical_gates_failed_after_retry'}
        save('construction.json',{'cases':[by_id[k] for k in sorted(by_id)]})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--branch',nargs='+',default=['primary','publication_lag10','missing_n1000','verified_only']);p.add_argument('--year',nargs='+',type=int,default=[2014,2017,2020,2023]);p.add_argument('--horizon',nargs='+',type=int,default=[14,56]);a=p.parse_args();run(a.branch,a.year,a.horizon)
