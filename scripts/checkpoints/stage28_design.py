"""Generate Stage28 design/coverage only. No historical estimation or scoring."""
import argparse
from collections import Counter
from hashlib import sha256, sha1
import json
from pathlib import Path
import subprocess

from scripts.checkpoints.stage25_geography import ROOT, read, encode
from scripts.checkpoints.stage25_availability import verify_contract
from scripts.models.asymmetric_response.inputs import election_inputs, fold_inventory

DEST = ROOT / 'data/processed/checkpoints/stage28-asymmetric-response-design'
BASE = 'cb1ca8fe1a50a5df4b8f6f4336b4ecc7072595ae'
GEO = 'data/processed/checkpoints/stage25-historical-geography/'
RESPONSE = 'data/processed/models/exact-geography-retests/inventory.json'
SPEC = str((DEST / 'specification.json').relative_to(ROOT))
AUDIT_INPUTS = (SPEC, GEO+'geography.json', GEO+'fold-plan.json', RESPONSE,
    'docs/statistical-specification.md', 'docs/audits/stage6-architecture.md',
    'docs/stage25-chronology-amendment.md',
    'data/processed/models/nat-lab-elasticity/specification.json',
    'data/processed/models/conditional-nat-lab-response/specification.json',
    'data/processed/models/candidate-overperformance/specification.json',
    'data/processed/evidence/practical-candidate-linkage/contract.json')


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def snapshot():
    existing = DEST / 'prior-data-contract.json'
    if existing.exists():
        return json.loads(existing.read_bytes())
    entries = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE, 'data'], cwd=ROOT)
    result = {}
    for entry in entries.split(b'\0'):
        if entry:
            metadata, path = entry.split(b'\t', 1)
            result[path.decode()] = metadata.split()[2].decode()
    return {'baseCommit': BASE, 'gitBlobSha1': result,
            'role': 'separate_stage_boundary_preservation_audit_not_registry_dependency_contract'}


def verify_preservation(include_registry=True):
    """All prior bytes at this stage boundary; optional appendable-registry exclusion."""
    prior = snapshot()
    count = 0
    for path, expected in prior['gitBlobSha1'].items():
        if not include_registry and path == 'data/sources.json':
            continue
        count += 1
        raw = (ROOT / path).read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != expected:
            raise ValueError(f'Prior data changed: {path}')
    return count


def outputs():
    geography = read(GEO+'geography.json')
    years = sorted({r[k] for r in geography['records'] for k in ('sourceYear','targetYear')})
    elections = {y: read(f'data/processed/elections/{y}.json') for y in years}
    aggregates = [r for e in elections.values() for r in election_inputs(e)]
    # Filter the existing immutable snapshot, never hash the whole live registry.
    consumed = {i for e in elections.values() for i in e['sourceIds']}
    saved = read(GEO+'source-contract.json')
    required = [r for r in saved['requiredSources'] if r['id'] in consumed]
    if {r['id'] for r in required} != consumed:
        raise ValueError('Missing required source dependency')
    sources = {'stage':28, 'requiredSources':required,
               'contract':'required_records_and_raw_bytes; unrelated_additions_allowed'}
    verify_contract(sources)
    folds = fold_inventory(read(GEO+'fold-plan.json')['folds'],
                           read(RESPONSE)['responseRecords'], aggregates)
    paths = list(AUDIT_INPUTS)+[f'data/processed/elections/{y}.json' for y in years]
    data = {'stage':28,'historicalEstimationPerformed':False,
            'electionAggregateInputs':aggregates, 'folds':folds,
            'coverage':{'fullGeographicTargets':len(geography['records']),
                'retainedGeographyScopeCounts':dict(Counter(r['scope'] for r in geography['records'])),
                'responseRecords':len(read(RESPONSE)['responseRecords']),
                'completedElectionSnapshotsPerParty':len(years),
                'countFeasiblePartyFolds':sum(f['countGatesPotentiallyFeasible'] for f in folds),
                'identifiedAnchorsOrRegimes':None, 'actualFitReadiness':'not_established',
                'historicalScoresOrPredictions':'not_calculated'}}
    generated = {'input-inventory.json':data, 'source-contract.json':sources,
        'input-contract.json':{'stage':28,'inputSha256':{p:digest(p) for p in paths},
            'sourceDependencies':'source-contract.json',
            'contract':'unchanged_input_bytes_and_required_sources; outcome_independence_tested_separately'},
        'prior-data-contract.json':snapshot()}
    code = ['scripts/checkpoints/stage28_design.py','scripts/models/asymmetric_response/design.py',
            'scripts/models/asymmetric_response/inputs.py', 'scripts/checkpoints/stage25_geography.py',
            'scripts/checkpoints/stage25_availability.py', 'scripts/transform/historical.py',
            'scripts/checkpoints/complete_share_feature_rank.py']
    generated['manifest.json'] = {'generatorSha256':{p:digest(p) for p in code},
        'outputSha256':{name:sha256(encode(value)).hexdigest() for name,value in generated.items()}}
    return generated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--verify-preservation',action='store_true')
    args = parser.parse_args()
    generated = outputs()
    DEST.mkdir(parents=True, exist_ok=True)
    for name, value in generated.items():
        path, raw = DEST/name, encode(value)
        if args.check:
            if path.read_bytes() != raw:
                raise ValueError(f'Stage28 changed deterministic output: {name}')
        else:
            path.write_bytes(raw)
    if args.verify_preservation:
        print({'priorArtifactsPreserved':verify_preservation()})
    print(generated['input-inventory.json']['coverage'])


if __name__ == '__main__':
    main()
