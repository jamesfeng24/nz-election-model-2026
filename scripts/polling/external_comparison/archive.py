"""Deterministic cached-forecast audit; never invokes inference."""
import argparse
import json
import math
import tarfile
import numpy as np
from .common import ROOT,OUT,RAW,CASES,PIN,read,save,sha,validate_inputs


def check_provenance():
    validate_inputs();contract=read(OUT/'input-contract.json')
    for path,h in contract['runnerCode'].items():
        if sha(ROOT/path)!=h:raise ValueError('Changed frozen execution code '+path)
    with tarfile.open(RAW/'upstream.tar.gz') as tar:
        source={str(__import__('pathlib').Path(m.name).relative_to(__import__('pathlib').Path(m.name).parts[0])):m for m in tar.getmembers() if m.isfile()}
        import hashlib
        for p,h in contract['upstreamSource'].items():
            if hashlib.sha256(tar.extractfile(source[p]).read()).hexdigest()!=h:raise ValueError('Pinned upstream source mismatch '+p)
    ledger=read(RAW/'acquisition-ledger.json')
    if len(ledger['resources'])>ledger['resourceCap']:raise ValueError('Acquisition cap')
    for r in ledger['resources']:
        if sha(ROOT/r['rawPath'])!=r['sha256']:raise ValueError('Raw resource changed')
    prior=read(ROOT/'data/source-plans/stage38-prior-data-preservation.json')
    for p,h in prior['sha256'].items():
        if sha(ROOT/p)!=h:raise ValueError('Prior artifact changed '+p)
    return len(prior['sha256'])


def check_diagnostics(record):
    diag=record['diagnostics'];failed=[]
    for row in diag['variables']:
        active=row['coordinates'];shape=row['coordinateShape'];fixed=row['fixedCoordinates']
        count=math.prod(shape) if shape else 1
        if len(set(active+fixed))!=count or set(active)&set(fixed):raise ValueError('Missing diagnostic coordinates')
        if any(len(row[k])!=len(active) for k in ('rhat','bulkESS','tailESS')):raise ValueError('Diagnostic shape mismatch')
        bad=[i for i,r,b,t in zip(active,row['rhat'],row['bulkESS'],row['tailESS']) if r is None or b is None or t is None or not all(math.isfinite(v) for v in (r,b,t)) or r>1.01 or b<400 or t<400]
        if bad!=row['failedCoordinates']:raise ValueError('Incorrect coordinate gate')
        failed.extend(bad)
    passed=not failed and diag['divergences']==0 and diag['treeDepthContacts']==0 and all(math.isfinite(v) and v>=.3 for v in diag['energyBFMI'])
    if passed!=diag['passed'] or passed!=(record['status']=='accepted'):raise ValueError('Incorrect numerical disposition')


def inspect_case(year):
    attempts=[];accepted=None
    for attempt in (1,2):
        p=OUT/f'fits/{year}/attempt{attempt}.json'
        if not p.exists():continue
        record=read(p);attempts.append(record)
        if 'diagnostics' in record:check_diagnostics(record)
        if record.get('npzSha256'):
            archive=p.with_suffix('.npz')
            if sha(archive)!=record['npzSha256']:raise ValueError('Changed draw archive')
            with np.load(archive,allow_pickle=False) as a:
                x=a['electionDay']
                if list(x.shape)!=record['savedDrawChainShape'] or not np.isfinite(x).all() or (x<0).any() or not np.allclose(x.sum(-1),1,atol=1e-12,rtol=0):raise ValueError('Invalid election-day joint draws')
                if not np.allclose(x.mean((0,1)),record['expectedElectionDay'],atol=1e-15,rtol=0):raise ValueError('Wrong transformed mean')
                if len(set(record['drawIds']))!=8000:raise ValueError('Invalid paired draw IDs')
        if record['status']=='accepted':accepted=attempt;break
    if accepted:return {'year':year,'status':'accepted','attempt':accepted,'attemptFile':f'fits/{year}/attempt{accepted}.json','drawFile':f'fits/{year}/attempt{accepted}.npz','runtimeSeconds':sum(r['runtimeSeconds'] for r in attempts)}
    return {'year':year,'status':'numerical_failure' if attempts else 'not_completed','reason':'recorded numerical failure/cap; no accepted forecast','attempts':len(attempts),'runtimeSeconds':sum(r.get('runtimeSeconds',0) for r in attempts)}


def run(check=False):
    preserved=check_provenance();cases=[inspect_case(y) for y,_ in CASES]
    paths=[OUT/'batch.json']
    for y,_ in CASES:paths+=list((OUT/f'fits/{y}').glob('attempt*.json'))+list((OUT/f'fits/{y}').glob('attempt*.npz'))
    result={'cases':cases,'pin':PIN,'preservedPriorFiles':preserved,'sha256':{str(p.relative_to(OUT)):sha(p) for p in sorted(paths)},'scoresComputed':False,'inferenceResumed':False}
    save('forecast-contract.json',result,check);print('Forecast archive',[(r['year'],r['status']) for r in cases],'prior files',preserved)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
