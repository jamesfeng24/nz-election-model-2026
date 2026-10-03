"""Stage34 consumed inputs and separate historical byte-preservation checks."""
import json
import subprocess
from hashlib import sha256, sha1
from scripts.models.joint_candidate_share.common import ROOT, METHODS, read, keyed
from scripts.models.joint_candidate_share.common import verify_inputs as verify_stage33_inputs, verify_phase as verify_stage33_phase
from scripts.models.expanded_party_substitution.common import verify_inputs as verify_stage31_inputs
from scripts.models.expanded_party_substitution.integrity import verify_phase as verify_stage31_phase

BASE = '304de1fb9b78bf617d6856ec995ca562c84d53ea'
PREFIX = 'data/processed/diagnostics/s-r-robustness/'
DEST = ROOT / PREFIX
S33 = 'data/processed/models/joint-candidate-share/'
S32 = 'data/processed/checkpoints/joint-candidate-share-design/'
S31 = 'data/processed/models/expanded-party-substitution/'
GEO = 'data/processed/checkpoints/stage25-historical-geography/'
BRANCHES = ('primary', 'strict', 'separated', 'observed_retrained', 'primary_fixed_to_observed')
S = 'baseline_plus_S'
R = 'baseline_plus_R'
JOINT = 'baseline_plus_S_plus_R'
CODE_PREFIX = 'scripts/diagnostics/s_r_robustness/'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(path):
    return sha256((ROOT/path).read_bytes()).hexdigest()


def local(name):
    return read(PREFIX+name)


def save(name, value, check=False):
    path = DEST/name
    raw = encode(value)
    if check:
        if path.read_bytes() != raw:
            raise ValueError('Changed Stage34 '+name)
    else:
        path.write_bytes(raw)


def phase(name, files, modules, check=False):
    save(name+'-manifest.json', {'outputSha256': {p: digest(PREFIX+p) for p in files},
        'generatorSha256': {CODE_PREFIX+m+'.py': digest(CODE_PREFIX+m+'.py') for m in modules}}, check)


def verify_phase(name):
    d = local(name+'-manifest.json')
    for p, expected in d['outputSha256'].items():
        if digest(PREFIX+p) != expected:
            raise ValueError('Changed Stage34 output '+p)
    for p, expected in d['generatorSha256'].items():
        if digest(p) != expected:
            raise ValueError('Changed Stage34 generator '+p)


def verify_inputs():
    for p, expected in local('input-contract.json')['inputSha256'].items():
        if digest(p) != expected:
            raise ValueError('Changed consumed Stage34 input '+p)
    verify_stage33_inputs()
    for p in ('construction', 'evaluation', 'verification', 'numerical-audit'):
        verify_stage33_phase(p)
    verify_stage31_inputs()
    verify_stage31_phase('construction')
    verify_phase('preanalysis')


def snapshot():
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE, 'data'], cwd=ROOT)
    return {'baseCommit': BASE, 'gitBlobSha1': {p.decode(): m.split()[2].decode()
        for e in tree.split(b'\0') if e for m, p in [e.split(b'\t', 1)]}}


def preserve():
    data = local('prior-data-contract.json')['gitBlobSha1']
    for p, expected in data.items():
        raw = (ROOT/p).read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != expected:
            raise ValueError('Changed earlier artifact '+p)
    return len(data)
