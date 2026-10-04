"""Only pinned gauss inference: full-coordinate diagnostics, exact resume."""
import argparse
import gc
import importlib.metadata
import os
import platform
import time
import sys
import numpy as np
from .common import ROOT,OUT,UPSTREAM,CASES,PIN,read,save,digest,sha,validate_inputs

PRIMARY={'chains':4,'warmup':2000,'samples':2000,'target_accept':.95,'max_tree_depth':12,'seed':2034}
RETRY={**PRIMARY,'warmup':4000,'target_accept':.99,'max_tree_depth':15}


def signature(ds,settings):
    return {'dataset':ds.fingerprint(),'cutoff':ds.cutoff.isoformat(),'pin':PIN,'variant':'gauss','settings':settings,
            'environment':read(OUT/'environment.json'),'executionContract':sha(OUT/'specification.json'),
            'upstreamConfig':{str(p.relative_to(UPSTREAM)):sha(p) for p in sorted((UPSTREAM/'config').glob('*.yml'))},
            'runnerSha256':sha(__file__),'inputContract':sha(OUT/'input-contract.json')}


def constant_mask(name,flat,ds):
    """Exclude only mathematically fixed coordinates, never low-variance parameters."""
    mask=np.zeros(flat.shape[-1],dtype=bool)
    if name=='L_corr':
        k=ds.K-1; mask=np.triu(np.ones((k,k),dtype=bool),1).reshape(-1);mask[0]=True
    if name in ('theta','pi'):
        width=ds.K if name=='pi' else ds.K-1
        full=np.zeros((ds.T,width),dtype=bool);full[list(ds.anchors_t)]=True;mask=full.reshape(-1)
    return mask


def diagnose(samples,extra,ds,depth):
    import arviz as az
    rows=[]
    for name,values in samples.items():
        flat=np.asarray(values).reshape(4,2000,-1); fixed=constant_mask(name,flat,ds);indices=np.flatnonzero(~fixed)
        rh=[];bulk=[];tail=[]
        for start in range(0,len(indices),96):
            v=flat[:,:,indices[start:start+96]]
            rh.extend(np.asarray(az.rhat({'v':v},method='rank')['v']).reshape(-1).tolist())
            bulk.extend(np.asarray(az.ess({'v':v},method='bulk')['v']).reshape(-1).tolist())
            tail.extend(np.asarray(az.ess({'v':v},method='tail')['v']).reshape(-1).tolist())
        r=np.asarray(rh);b=np.asarray(bulk);t=np.asarray(tail)
        bad=~np.isfinite(r)|~np.isfinite(b)|~np.isfinite(t)|(r>1.01)|(b<400)|(t<400)
        clean=lambda a:[float(x) if np.isfinite(x) else None for x in a]
        rows.append({'variable':name,'coordinateShape':list(np.asarray(values).shape[2:]),'coordinates':indices.tolist(),'fixedCoordinates':np.flatnonzero(fixed).tolist(),'rhat':clean(r),'bulkESS':clean(b),'tailESS':clean(t),'failedCoordinates':indices[bad].tolist()})
        print('DIAGNOSTICS',name,'active',len(indices),'failed',int(bad.sum()),flush=True)
    r=[x for row in rows for x in row['rhat'] if x is not None];b=[x for row in rows for x in row['bulkESS'] if x is not None];t=[x for row in rows for x in row['tailESS'] if x is not None]
    divergences=int(np.asarray(extra['diverging']).sum());depth_hits=int((np.asarray(extra['num_steps'])>=2**depth-1).sum())
    bfmi=np.asarray(az.bfmi(np.asarray(extra['energy']))).tolist()
    passed=not any(row['failedCoordinates'] for row in rows) and divergences==0 and depth_hits==0 and all(np.isfinite(bfmi)) and min(bfmi)>=.3
    return {'passed':passed,'variables':rows,'maxRhat':max(r),'minBulkESS':min(b),'minTailESS':min(t),'divergences':divergences,'treeDepthContacts':depth_hits,'maxNumSteps':int(np.asarray(extra['num_steps']).max()),'energyBFMI':bfmi,'meanAccept':float(np.asarray(extra['accept_prob']).mean()),'allSampledAndDerivedCoordinatesAudited':True}


def run_case(year,attempt=1):
    validate_inputs();sys.path.insert(0,str(UPSTREAM/'src'))
    from pollofpolls.prep.marshal import Dataset
    from pollofpolls.config import Config
    from pollofpolls.model.numpyro_model import ModelData,poll_model
    import jax
    from numpyro.infer import MCMC,NUTS,init_to_median
    cfg=Config(UPSTREAM);ds=Dataset.load(OUT/f'datasets/{year}');settings=PRIMARY if attempt==1 else RETRY;sig=signature(ds,settings)
    path=f'fits/{year}/attempt{attempt}.json';prefix=OUT/f'fits/{year}/attempt{attempt}'
    if (OUT/path).exists():
        prior=read(OUT/path)
        if prior['signature']!=sig:raise ValueError('Incompatible cached signature')
        if prior.get('npzSha256') and sha(prefix.with_suffix('.npz'))!=prior['npzSha256']:raise ValueError('Changed cached joint draws')
        print('REUSE',year,attempt,prior['status'],flush=True);return prior
    if attempt==2:
        previous=read(OUT/f'fits/{year}/attempt1.json')
        if previous['status']!='numerical_failure':raise ValueError('Retry requires recorded numerical failure')
    env=read(OUT/'environment.json');actual={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    if actual!=env['packages'] or sys.version!=env['python']:raise ValueError('Changed isolated runtime')
    if len(jax.devices())<4 or not jax.config.jax_enable_x64:raise ValueError('Require four CPU chains and x64')
    data=ModelData.from_dataset(ds,cfg.variant('gauss'));start=time.monotonic();prefix.parent.mkdir(parents=True,exist_ok=True)
    # Preserve running checkpoint before any compilation; original upstream equations stay unchanged.
    save(f'fits/{year}/running-attempt{attempt}.json',{'year':year,'attempt':attempt,'signature':sig,'startedUnix':time.time(),'pid':os.getpid()})
    kernel=NUTS(poll_model,max_tree_depth=settings['max_tree_depth'],target_accept_prob=settings['target_accept'],init_strategy=init_to_median(num_samples=20),dense_mass=False)
    mcmc=MCMC(kernel,num_warmup=settings['warmup'],num_samples=2000,num_chains=4,chain_method='parallel',progress_bar=False)
    print('START',year,attempt,digest(sig),flush=True)
    try:
        mcmc.run(jax.random.PRNGKey(2034),data,cfg.variant('gauss'),cfg.priors,cfg.model_cfg['election_obs_sd'],extra_fields=('diverging','num_steps','accept_prob','energy'))
        samples={k:np.asarray(v) for k,v in mcmc.get_samples(group_by_chain=True).items()};extra={k:np.asarray(v) for k,v in mcmc.get_extra_fields(group_by_chain=True).items()}
        # Save actual joint draws immediately, before expensive all-coordinate audit or any scores.
        pi=samples['pi'];saved={'electionDay':pi[:,:,ds.target_t,:],'lastDataSupport':pi[:,:,ds.last_data_t,:],**{'hyper__'+k:v for k,v in samples.items() if k not in ('pi','theta','z')},**{'extra__'+k:v for k,v in extra.items()}}
        tmp=prefix.with_name(prefix.name+'-writing.npz');np.savez_compressed(tmp,**saved);tmp.replace(prefix.with_suffix('.npz'))
        # Full raw samples remain in the isolated runtime cache for independent numerical audit.
        cache=ROOT/'.cache/stage38/raw-samples';cache.mkdir(parents=True,exist_ok=True)
        for k,v in samples.items():np.save(cache/f'{year}-attempt{attempt}-{k}.npy',v)
        diag=diagnose(samples,extra,ds,settings['max_tree_depth'])
        result={'year':year,'attempt':attempt,'signature':sig,'status':'accepted' if diag['passed'] else 'numerical_failure','settings':settings,'parties':ds.parties,'diagnostics':diag,'npzSha256':sha(prefix.with_suffix('.npz')),'runtimeSeconds':time.monotonic()-start,'drawIds':[f'gauss-{year}-attempt{attempt}-chain{c+1}-draw{i:04d}' for c in range(4) for i in range(2000)],'expectedElectionDay':pi[:,:,ds.target_t,:].mean((0,1)).tolist(),'distribution':'election-week latent support, including future random walk and common industry offset uncertainty; no extra bias draw','rawSampleCacheSha256':{k:sha(cache/f'{year}-attempt{attempt}-{k}.npy') for k in samples},'savedDrawChainShape':[4,2000,ds.K]}
    except (FloatingPointError,ValueError) as e:
        if isinstance(e,ValueError) and 'Cannot find valid initial parameters' not in str(e):raise
        result={'year':year,'attempt':attempt,'signature':sig,'status':'numerical_failure','exception':str(e),'runtimeSeconds':time.monotonic()-start}
    save(path,result);print('FINISHED',year,attempt,result['status'],'seconds',result['runtimeSeconds'],flush=True)
    del mcmc;gc.collect();jax.clear_caches();return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,choices=[2017,2020,2023],required=True);p.add_argument('--attempt',type=int,choices=[1,2],default=1);a=p.parse_args();run_case(a.year,a.attempt)
