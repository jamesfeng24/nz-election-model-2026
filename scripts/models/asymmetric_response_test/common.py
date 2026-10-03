"""Pinned companion inputs and deterministic phase writing."""
from hashlib import sha256, sha1
from pathlib import Path
import json
import subprocess

from scripts.checkpoints.stage25_geography import ROOT, read, encode
from scripts.checkpoints.stage25_availability import verify_contract

DEST = ROOT / 'data/processed/models/asymmetric-response-test'
DESIGN = 'data/processed/checkpoints/stage28-asymmetric-response-design/'
BASE = '44fab0aed181397692ea32c671ad66febc64e9cd'


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def verify_inputs():
    contract = read(str((DEST/'input-contract.json').relative_to(ROOT)))
    for path, expected in contract['inputSha256'].items():
        if digest(path) != expected:
            raise ValueError(f'Changed pinned input: {path}')
    verify_contract(read(DESIGN+'source-contract.json'))


def preserve(include_registry=True):
    prior = json.loads((DEST/'prior-data-contract.json').read_bytes())
    count = 0
    for path, expected in prior['gitBlobSha1'].items():
        if not include_registry and path == 'data/sources.json':
            continue
        raw = (ROOT/path).read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != expected:
            raise ValueError(f'Prior artifact changed: {path}')
        count += 1
    return count


def phase_write(name, value, check):
    raw = encode(value)
    path = DEST/name
    if check:
        if path.read_bytes() != raw:
            raise ValueError(f'Changed deterministic output: {name}')
    else:
        path.write_bytes(raw)


def phase_manifest(phase, names, code, check):
    phase_write(phase+'-manifest.json', {
        'outputSha256': {p: digest(str((DEST/p).relative_to(ROOT))) for p in names},
        'generatorSha256': {p: digest(p) for p in code}}, check)


def prefit():
    inventory = read(DESIGN+'input-inventory.json')
    responses = read('data/processed/models/exact-geography-retests/inventory.json')['responseRecords']
    parties = sorted({r['party'] for r in responses})
    descriptive = []
    for party in parties:
        rows = [r for r in responses if r['party'] == party]
        environments = sorted({f'{r["sourceYear"]}-{r["targetYear"]}:{party}' for r in rows})
        descriptive.append({'party': party, 'snapshotIds': [r['id'] for r in inventory['electionAggregateInputs'] if r['party']==party],
            'responseIds': [r['id'] for r in rows], 'transitionDeletions': [
                {'deletedEnvironment': env, 'retainedIds': [r['id'] for r in rows if f'{r["sourceYear"]}-{r["targetYear"]}:{party}' != env]}
                for env in environments]})
    return {'stage':29, 'chronologicalFolds': inventory['folds'],
            'fullPanelDescriptive': descriptive,
            'fullGeographicFrame': inventory['coverage'],
            'notOutcomeSelected': True}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    paths = [DESIGN+'specification.json', DESIGN+'input-inventory.json', DESIGN+'source-contract.json',
        'data/processed/checkpoints/stage25-historical-geography/geography.json',
        'data/processed/checkpoints/stage25-historical-geography/fold-plan.json',
        'data/processed/models/exact-geography-retests/inventory.json',
        'scripts/models/asymmetric_response/design.py', 'scripts/models/asymmetric_response/inputs.py',
        'scripts/models/exact_geography_retests/adapters.py',
        'scripts/models/conditional_nat_lab_response/model.py',
        'scripts/checkpoints/complete_share_feature_rank.py',
        'requirements-boundaries.txt']
    paths += [f'data/processed/elections/{y}.json' for y in (2008,2011,2014,2017,2020,2023)]
    phase_write('input-contract.json', {'inputSha256': {p:digest(p) for p in paths},
        'requiredSourceContract': DESIGN+'source-contract.json'}, False)
    phase_write('sample-inventory.json', prefit(), False)
    entries = subprocess.check_output(['git','ls-tree','-r','-z',BASE,'data'],cwd=ROOT)
    prior = {path.decode(): meta.split()[2].decode() for entry in entries.split(b'\0') if entry
             for meta,path in [entry.split(b'\t',1)]}
    phase_write('prior-data-contract.json', {'baseCommit':BASE,'gitBlobSha1':prior}, False)
    phase_manifest('prefit', ['specification.json','sample-inventory.json','input-contract.json','prior-data-contract.json'],
                   ['scripts/models/asymmetric_response_test/common.py'], False)
    print({'priorArtifacts':len(prior),'responseRecords':490,'chronologicalCases':20,'descriptiveCases':2,'deletionCases':10})


if __name__ == '__main__':
    main()
