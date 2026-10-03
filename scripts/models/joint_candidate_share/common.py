"""Consumed-input, phase and historical-byte contracts for Stage33."""
import json
import subprocess
from hashlib import sha256, sha1
from scripts.checkpoints.joint_candidate_share.common import ROOT, PREFIX as DESIGN, verify_inputs as verify_design
from scripts.checkpoints.stage25_availability import ELECTIONS

DEST=ROOT/'data/processed/models/joint-candidate-share'
BASE='c612c953c567b1fa8ba76e0db675cba63a1d81f5'
METHODS={'baseline':(), 'baseline_plus_S':('S',), 'baseline_plus_R':('R',),
         'baseline_plus_S_plus_R':('S','R')}
PAIRS=(('baseline_plus_S','baseline'),('baseline_plus_R','baseline'),
       ('baseline_plus_S_plus_R','baseline'),('baseline_plus_S_plus_R','baseline_plus_S'),
       ('baseline_plus_S_plus_R','baseline_plus_R'))
INPUTS=[DESIGN+n for n in ('specification.json','inventory.json','fold-plan.json','coverage.json','input-contract.json','manifest.json')]
INPUTS+=list(ELECTIONS.values())+['scripts/checkpoints/stage22_fit.py',
    'scripts/checkpoints/complete_share_feature_rank.py','scripts/checkpoints/joint_candidate_share/kernel.py',
    'scripts/checkpoints/joint_candidate_share/folds.py','scripts/checkpoints/joint_candidate_share/residuals.py',
    'requirements-boundaries.txt']


def read(path):return json.loads((ROOT/path).read_bytes())

def local(name):return json.loads((DEST/name).read_bytes())

def encode(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def digest(path):return sha256((ROOT/path).read_bytes()).hexdigest()

def save(name,value,check=False):
    raw=encode(value);path=DEST/name
    if check:
        if path.read_bytes()!=raw:raise ValueError('Changed Stage33 output '+name)
    else:path.write_bytes(raw)

def keyed(rows,field):
    result={r[field]:r for r in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate '+field)
    return result

def phase(name,files,code,check=False):
    save(name+'-manifest.json',{'outputSha256':{n:sha256((DEST/n).read_bytes()).hexdigest() for n in files},
                               'generatorSha256':{p:digest(p) for p in code}},check)

def verify_phase(name):
    data=local(name+'-manifest.json')
    for n,v in data['outputSha256'].items():
        if sha256((DEST/n).read_bytes()).hexdigest()!=v:raise ValueError('Changed '+name+' output '+n)
    for p,v in data['generatorSha256'].items():
        if digest(p)!=v:raise ValueError('Changed '+name+' code '+p)

def verify_inputs():
    for p,v in local('input-contract.json')['inputSha256'].items():
        if digest(p)!=v:raise ValueError('Changed consumed input '+p)
    verify_design()

def prior_snapshot():
    raw=subprocess.check_output(['git','ls-tree','-r','-z',BASE,'data'],cwd=ROOT)
    rows=[e.split(b'\t',1) for e in raw.split(b'\0') if e]
    return {'baseCommit':BASE,'gitBlobSha1':{p.decode():m.split()[2].decode() for m,p in rows}}

def preserve():
    data=local('prior-data-contract.json')['gitBlobSha1']
    for p,v in data.items():
        raw=(ROOT/p).read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=v:raise ValueError('Changed earlier artifact '+p)
    return len(data)
