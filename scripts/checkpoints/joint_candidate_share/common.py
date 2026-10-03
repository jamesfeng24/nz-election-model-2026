"""Stage32 companion IO, consumed dependencies and byte preservation."""
import json
import subprocess
from hashlib import sha256, sha1
from scripts.models.expanded_party_substitution.common import ROOT, read, verify_inputs as verify_party
from scripts.models.candidate_overperformance.run import verify_contract as verify_residuals
from scripts.evidence.practical_candidate_linkage.common import verify_inputs as verify_linkage
from scripts.models.source_provenance import validated_supporting_sources

PREFIX = 'data/processed/checkpoints/joint-candidate-share-design/'
DEST = ROOT / PREFIX
BASE = 'ff007d3ab59b6ce31bc873410c24259b5735c24e'
LINK = 'data/processed/evidence/practical-candidate-linkage/'
RES = 'data/processed/models/candidate-overperformance/'
GEO = 'data/processed/checkpoints/stage25-historical-geography/'
PARTY = 'data/processed/models/expanded-party-substitution/'
INPUTS = [PARTY+'input-inventory.json', PARTY+'party-vectors.json', PARTY+'input-contract.json',
          GEO+'geography.json', GEO+'fold-plan.json', GEO+'source-contract.json',
          LINK+'occurrences.json', LINK+'proposed-links.json', LINK+'accepted-relationships.json',
          LINK+'persons.json', LINK+'input-contract.json', LINK+'contract.json',
          RES+'occurrences.json', RES+'references.json', RES+'input-contract.json',
          'data/source-plans/stage6-7-supporting-candidate-sources.json',
          'scripts/checkpoints/stage22_fit.py', 'scripts/checkpoints/complete_share_feature_rank.py',
          'requirements-boundaries.txt']


def local(name):
    return read(PREFIX + name)


def keyed(rows, field):
    result = {r[field]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate ' + field)
    return result


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def save(name, value, check):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
    path = DEST / name
    if check:
        if path.read_bytes() != raw:
            raise ValueError('Changed Stage32 output ' + name)
    else:
        path.write_bytes(raw)


def snapshot():
    entries = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE, 'data'], cwd=ROOT).split(b'\0')
    hashes = {p.decode(): m.split()[2].decode() for e in entries if e for m, p in [e.split(b'\t', 1)]}
    return {'baseCommit': BASE, 'gitBlobSha1': hashes}


def preserve():
    hashes = local('prior-data-contract.json')['gitBlobSha1']
    for path, expected in hashes.items():
        raw = (ROOT / path).read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != expected:
            raise ValueError('Changed earlier artifact ' + path)
    return len(hashes)


def verify_inputs():
    for path, expected in local('input-contract.json')['inputSha256'].items():
        if digest(path) != expected:
            raise ValueError('Changed consumed input ' + path)
    verify_party(); verify_linkage(); verify_residuals(read(RES+'input-contract.json'))
    validated_supporting_sources(read('data/source-plans/stage6-7-supporting-candidate-sources.json'),
                                 read('data/sources.json'),lambda p:(ROOT/p).read_bytes())
