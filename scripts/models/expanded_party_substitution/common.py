"""Stage31 IO and phase/input contracts; companions never overwrite earlier work."""
import json
from hashlib import sha256,sha1
from pathlib import Path
from scripts.models.exact_geography_retests.common import ROOT,read,keyed,verify_inputs as verify_stage27
from scripts.models.complete_party_vector.common import verify_contract as verify_stage23
from scripts.checkpoints.stage24_common import verify_contract as verify_stage24
from scripts.checkpoints.stage25_availability import verify_contract

DEST=ROOT/'data/processed/models/expanded-party-substitution'
S23='data/processed/models/complete-party-vector/'
S24='data/processed/checkpoints/stage24-party-input-substitution/'
S27='data/processed/models/exact-geography-retests/'
GEO='data/processed/checkpoints/stage25-historical-geography/'
BASE='aa330f859c6a75ae500209e45edbb0af4e745bbf'
SCENARIOS=('printed','selected_lower','selected_upper')
PROTOCOLS=('expanding_window','more_separated')


def local(name):return json.loads((DEST/name).read_bytes())


def digest(path):return sha256((ROOT/path).read_bytes()).hexdigest()


def encode(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def save(name,value,check=False):
    raw=encode(value);path=DEST/name
    if check:
        if path.read_bytes()!=raw:raise ValueError('Changed deterministic '+name)
    else:path.write_bytes(raw)


def phase(name,files,code,check):
    save(name+'-manifest.json',{'outputSha256':{n:sha256((DEST/n).read_bytes()).hexdigest() for n in files},
                              'generatorSha256':{p:digest(p) for p in code}},check)


def verify_inputs():
    for p,expected in local('input-contract.json')['inputSha256'].items():
        if digest(p)!=expected:raise ValueError('Changed required input '+p)
    verify_stage23();verify_stage24();verify_stage27();verify_contract(read(GEO+'source-contract.json'))
    for p,expected in local('prefit-manifest.json')['generatorSha256'].items():
        if digest(p)!=expected:raise ValueError('Changed preconstruction generator '+p)
    for n,expected in local('prefit-manifest.json')['outputSha256'].items():
        if sha256((DEST/n).read_bytes()).hexdigest()!=expected:raise ValueError('Changed preconstruction file '+n)


def preserve():
    snapshot=local('prior-data-contract.json');n=0
    for p,expected in snapshot['gitBlobSha1'].items():
        raw=(ROOT/p).read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=expected:raise ValueError('Changed prior artifact '+p)
        n+=1
    return n
