"""Pre-inference IDs and consumed-source contracts, not forecasts."""
import argparse
import hashlib
import json
import subprocess
from .common import ROOT,FOUNDATION,OUT,BASE,read,save,digest
from .prepare import prepare


def semantic(case):
    obj=json.loads(json.dumps(case))
    for c in obj['cycles']:
        c.pop('bridgeFactor');c['initial']={k:v for k,v in c['initial'].items() if k not in ('mean','factor')}
    return obj


def preserved():
    manifest=read(OUT/'prior-data-preservation.json')
    for p,expected in manifest['gitBlobSha1'].items():
        raw=(ROOT/p).read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=expected:raise ValueError('Changed prior '+p)
    return len(manifest['gitBlobSha1'])


def run(check=False):
    if not (OUT/'prior-data-preservation.json').exists():
        tree=subprocess.check_output(['git','ls-tree','-r','-z',BASE,'data'],cwd=ROOT);files={}
        for entry in tree.split(b'\0'):
            if entry:
                meta,name=entry.split(b'\t',1);files[name.decode()]=meta.split()[2].decode()
        save('prior-data-preservation.json',{'baseCommit':BASE,'gitBlobSha1':files})
    cases=[]
    for branch in ('primary','publication_lag10','missing_n1000','verified_only'):
        for year in (2014,2017,2020,2023):
            for horizon in (14,56):
                c=prepare(year,horizon,branch)
                cases.append({'id':c['id'],'branch':branch,'year':year,'horizonDays':horizon,'cutoff':c['cutoff'],
                              'status':c['status'],'reason':c['reason'],'inputDigest':digest(semantic(c)),
                              'anchors':c['permittedAnchorYears'],'pollsterRoster':c['pollsterRoster'],
                              'cycles':[{'year':x['year'],'categories':x['categories'],'pollIds':[r['id'] for r in x['polls']],
                                         'rows':len(x['rows']),'nodes':len(x['nodes']),'excluded':x['excluded']} for x in c['cycles']]})
    paths=[str((FOUNDATION/x).relative_to(ROOT)) for x in ['polls.json','specification.json','coverage.json','input-contract.json','official-results-isolated.json']]
    paths+=['requirements-polling.lock','docs/stage36-national-implementation-contract.md','data/processed/polling/national-backtest/environment.json']
    save('inventory.json',{'stage':36,'cases':cases,'priorFilesPreserved':preserved()},check)
    save('input-contract.json',{'baseCommit':BASE,'consumedSha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'sourceContract':'Stage35 consumed raw resources remain pinned; unrelated registry additions allowed'},check)
    print(len(cases),'cases;',sum(c['status']=='ready' for c in cases),'fit-ready;',preserved(),'prior files unchanged')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
