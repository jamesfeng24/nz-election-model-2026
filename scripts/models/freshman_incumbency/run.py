"""Generate or verify pinned Stage 9 pre-fit tenure inventory."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.models.freshman_incumbency.inventory import build_inventory
from scripts.models.freshman_incumbency.tenure import parse_profile
from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/models/freshman-incumbency'
SOURCE_PLAN = 'data/source-plans/freshman-incumbency-tenure-sources.json'
YEARS = (2008, 2011, 2014, 2017, 2020, 2023)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def elected_ids():
    elected = set()
    for year in YEARS:
        election = json.loads((ROOT / f'data/processed/elections/{year}.json').read_bytes())
        for seat in election['electorates']:
            elected.update(candidate['id'] for candidate in seat['candidates'] if candidate['elected'])
    return elected


def input_paths(source_plan):
    paths = ['data/processed/models/candidate-persistence/pairs.json',
             'data/processed/models/candidate-overperformance/occurrences.json',
             SOURCE_PLAN, *(f'data/processed/elections/{year}.json' for year in YEARS),
             *(source['rawPath'] for source in source_plan['sources'])]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate Stage 9 input path')
    return sorted(paths)


def build():
    source_plan = json.loads((ROOT / SOURCE_PLAN).read_bytes())
    verify_source_files(ROOT, source_plan)
    expected = {name: digest(ROOT / name) for name in input_paths(source_plan)}
    profiles = [parse_profile((ROOT / source['rawPath']).read_bytes(), source)
                for source in source_plan['sources'] if '-profile-' in source['id']]
    if len({profile['sourceUrl'] for profile in profiles}) != len(profiles):
        raise ValueError('Duplicate official profile URL')
    occurrences = json.loads((ROOT / 'data/processed/models/candidate-overperformance/occurrences.json').read_bytes())['records']
    pairs = json.loads((ROOT / 'data/processed/models/candidate-persistence/pairs.json').read_bytes())['pairs']
    outputs = {
        'input-contract.json': expected,
        'tenure-evidence.json': {'schemaVersion': 1, 'profiles': sorted(profiles, key=lambda row: row['sourceId']),
                                 'interpretation': 'Publication and retrieval dates are separate from dated historical service facts. A missing or incomplete table remains unknown.'},
        'inventory.json': build_inventory(pairs, occurrences, profiles, elected_ids()),
    }
    code = [ROOT / f'scripts/models/freshman_incumbency/{name}.py'
            for name in ('__init__', 'tenure', 'inventory', 'run')]
    code.append(ROOT / 'scripts/validate/source_files.py')
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'stage': 9, 'phase': 'pre_fit_inventory',
        'inputHashes': expected,
        'codeHashes': {str(path.relative_to(ROOT)): digest(path) for path in code},
        'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest()
                         for name, value in outputs.items()},
    }
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['inventory'])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        contract = json.loads((DEST / 'input-contract.json').read_bytes())
        if contract != outputs['input-contract.json']:
            raise ValueError('Changed pinned Stage 9 inventory input')
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 9 inventory output: {name}')
        print('Stage 9 pre-fit inventory reproducible')
        return
    DEST.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        (DEST / name).write_bytes(encode(value))
    print(f'Stage 9 pre-fit inventory: {len(outputs["inventory.json"]["records"])} linked pairs')


if __name__ == '__main__':
    main()
