"""Generate or verify the pinned Stage 10 pre-fit inventory."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.models.replacement_candidate.inventory import build_inventory


ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/models/replacement-candidate'
YEARS = (2008, 2011, 2014, 2017, 2020, 2023)
INPUTS = (
    'data/processed/models/candidate-overperformance/occurrences.json',
    'data/processed/models/candidate-persistence/person-links.json',
    'data/processed/models/party-vote-transform/party-continuity.json',
    'data/processed/models/freshman-incumbency/tenure-evidence.json',
    'data/processed/models/freshman-incumbency/input-contract.json',
    'data/processed/models/freshman-incumbency/manifest.json',
    *(f'data/processed/elections/{year}.json' for year in YEARS),
)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    expected = {name: digest(ROOT / name) for name in INPUTS}
    def read(name):
        return json.loads((ROOT / name).read_bytes())
    elected = set()
    for year in YEARS:
        for seat in read(f'data/processed/elections/{year}.json')['electorates']:
            elected.update(candidate['id'] for candidate in seat['candidates'] if candidate['elected'])
    inventory = build_inventory(
        read(INPUTS[0])['records'], read(INPUTS[1])['links'], read(INPUTS[2])['records'],
        elected, read(INPUTS[3])['profiles'])
    outputs = {'input-contract.json': expected, 'inventory.json': inventory}
    code = [ROOT / f'scripts/models/replacement_candidate/{name}.py'
            for name in ('__init__', 'inventory', 'run')]
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'stage': 10, 'phase': 'pre_fit_inventory',
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
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed pinned Stage 10 pre-fit {name}')
        print('Stage 10 pre-fit inventory reproducible')
        return
    DEST.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        (DEST / name).write_bytes(encode(value))
    print(f'Stage 10 inventory: {len(outputs["inventory.json"]["records"])} party-seat comparisons')


if __name__ == '__main__':
    main()
