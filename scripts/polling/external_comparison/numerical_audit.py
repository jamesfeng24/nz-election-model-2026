"""Independent saved-chain audit; only explicit --raw-cache reads runtime paths."""
import argparse
import numpy as np
from .common import ROOT,OUT,CASES,read,save,sha


def audit(check=False,raw_cache=False):
    saved=read(OUT/'numerical-audit.json') if check else None;rows=[]
    for year,_ in CASES:
        fr=read(OUT/f'fits/{year}/attempt1.json')
        if fr['status']!='accepted':continue
        archive=np.load(OUT/f'fits/{year}/attempt1.npz',allow_pickle=False);ds=read(OUT/f'datasets/{year}.json')
        if raw_cache:
            import arviz as az
            cache=ROOT/'.cache/stage38/raw-samples'
            theta=np.load(cache/f'{year}-attempt1-theta.npy',mmap_mode='r')[:,:,ds['target_t'],:]
            indices=[(c,i) for c in range(4) for i in (0,37,999,1999)]
            for c,i in indices:
                full=np.r_[0.,theta[c,i]];e=np.exp(full-full.max());q=e/e.sum()
                if not np.allclose(q,archive['electionDay'][c,i],atol=1e-14,rtol=0):raise ValueError('Wrong latent election-day transformation')
            coordinates=[]
            for name in ('sigma','industry_end_sd'):
                v=archive['hyper__'+name].reshape(4,2000,-1)
                rh=np.asarray(az.rhat({'v':v},method='rank')['v']).reshape(-1);b=np.asarray(az.ess({'v':v},method='bulk')['v']).reshape(-1);t=np.asarray(az.ess({'v':v},method='tail')['v']).reshape(-1)
                diag=next(r for r in fr['diagnostics']['variables'] if r['variable']==name)
                for i in range(len(rh)):
                    for a,z in ((rh[i],diag['rhat'][i]),(b[i],diag['bulkESS'][i]),(t[i],diag['tailESS'][i])):
                        if not np.isclose(a,z,atol=1e-10,rtol=0):raise ValueError('Independent cached-chain diagnostic mismatch')
                    coordinates.append({'variable':name,'coordinate':i,'rhat':float(rh[i]),'bulkESS':float(b[i]),'tailESS':float(t[i])})
            row={'year':year,'checkedPosteriorTransformations':len(indices),'cachedHyperCoordinates':coordinates,'rawThetaSha256':fr['rawSampleCacheSha256']['theta'],'jointArchiveSha256':fr['npzSha256']}
        else:
            row=next(r for r in saved['cases'] if r['year']==year)
            if row['jointArchiveSha256']!=sha(OUT/f'fits/{year}/attempt1.npz'):raise ValueError('Changed audited archive')
            for c in row['cachedHyperCoordinates']:
                diag=next(r for r in fr['diagnostics']['variables'] if r['variable']==c['variable']);idx=diag['coordinates'].index(c['coordinate'])
                for key in ('rhat','bulkESS','tailESS'):
                    if c[key]!=diag[key][idx]:raise ValueError('Changed recorded raw-chain check')
        rows.append(row)
    result={'cases':rows,'rawCacheIndependentAuditPerformed':True,'ciScope':'checks recorded audit against sealed diagnostic coordinates/archive checksums; does not regenerate MCMC or local full-dimensional raw sample files'}
    save('numerical-audit.json',result,check)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--raw-cache',action='store_true');a=p.parse_args();audit(a.check,a.raw_cache)
