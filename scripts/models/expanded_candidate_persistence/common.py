"""Pinned Stage30 inputs, phase manifests and prior-artifact protection."""
from hashlib import sha256, sha1
import json
from pathlib import Path

from scripts.checkpoints.stage25_geography import ROOT, read, encode
from scripts.checkpoints.stage25_availability import verify_contract
from scripts.evidence.practical_candidate_linkage.common import verify_inputs as verify_linkage
from scripts.models.candidate_overperformance.run import verify_contract as verify_residual_inputs
from scripts.models.source_provenance import validated_supporting_sources

DEST=ROOT/'data/processed/models/expanded-candidate-persistence'
LINK='data/processed/evidence/practical-candidate-linkage/'
GEO='data/processed/checkpoints/stage25-historical-geography/'
RES='data/processed/models/candidate-overperformance/'
BASE='5c754823110073d479016fc993108eb33989589a'
SCALES=('additive','proportional','log_odds')


def digest(path):
    return sha256((ROOT/path).read_bytes()).hexdigest()


def local(name):
    return json.loads((DEST/name).read_bytes())


def unique(rows,field):
    result={r[field]:r for r in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate '+field)
    return result


def save(name,value,check=False):
    raw=encode(value);path=DEST/name
    if check:
        if path.read_bytes()!=raw:raise ValueError('Changed deterministic output: '+name)
    else:path.write_bytes(raw)


def manifest(phase,names,code,check):
    save(phase+'-manifest.json',{'outputSha256':{n:digest(str((DEST/n).relative_to(ROOT))) for n in names},
        'generatorSha256':{p:digest(p) for p in code}},check)


def verify_inputs():
    for p,expected in local('input-contract.json')['inputSha256'].items():
        if digest(p)!=expected:raise ValueError('Changed pinned input: '+p)
    verify_linkage()
    verify_contract(read(GEO+'source-contract.json'))
    verify_residual_inputs(read(RES+'input-contract.json'))
    validated_supporting_sources(read('data/source-plans/stage6-7-supporting-candidate-sources.json'),
                                 read('data/sources.json'),lambda p:(ROOT/p).read_bytes())


def preservation(include_registry=True):
    data=local('prior-data-contract.json');n=0
    for p,expected in data['gitBlobSha1'].items():
        if not include_registry and p=='data/sources.json':continue
        raw=(ROOT/p).read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=expected:
            raise ValueError('Changed prior artifact: '+p)
        n+=1
    return n


def verify_prefit():
    data=local('prefit-manifest.json')
    for name,expected in data['outputSha256'].items():
        if digest(str((DEST/name).relative_to(ROOT)))!=expected:raise ValueError('Changed pre-fit file: '+name)
    for p,expected in data['generatorSha256'].items():
        if digest(p)!=expected:raise ValueError('Changed pre-fit generator: '+p)
