"""Generate the conditional construction only; target outcomes are never read."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.models.conditional_candidate_ledger.construct import construct
from scripts.models.conditional_candidate_ledger.pool import build_source_pools
from scripts.models.conditional_candidate_ledger.sources import (
    ROOT, SNAPSHOT, SOURCE_YEARS, TARGET_YEARS, verify_snapshot)


DEST = ROOT / 'data/processed/models/conditional-candidate-ledger'
INPUTS = (
    'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json',
    'data/processed/checkpoints/complete-candidate-baseline/specification.json',
    'data/processed/checkpoints/complete-candidate-baseline/contracts.json',
    'data/processed/models/party-vote-transform/party-continuity.json',
    str(SNAPSHOT),
    *(f'data/processed/elections/{year}.json' for year in SOURCE_YEARS + TARGET_YEARS),
    *(f'data/processed/split-votes/{year}.json' for year in SOURCE_YEARS),
)
CODE = ('sources.py', 'pool.py', 'geometry.py', 'construct.py', 'run.py')


def read(relative_path):
    return json.loads((ROOT / relative_path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    elections = {year: read(f'data/processed/elections/{year}.json')
                 for year in SOURCE_YEARS + TARGET_YEARS}
    splits = {year: read(f'data/processed/split-votes/{year}.json')
              for year in SOURCE_YEARS}
    verify_snapshot(read(str(SNAPSHOT)), read('data/sources.json'), elections, splits)
    pools = {year: build_source_pools(year, elections[year], splits[year])
             for year in SOURCE_YEARS}
    frame = read(INPUTS[0])['records']
    continuity = read('data/processed/models/party-vote-transform/party-continuity.json')['records']
    outputs = {
        'source-pools.json': {'schemaVersion': 1, 'stage': 15,
                              'mode': 'source_only_before_target_outcomes',
                              'sourceYears': {str(year): pools[year] for year in SOURCE_YEARS}},
        'ledgers.json': construct(frame, elections, pools, continuity),
    }
    manifest = {'schemaVersion': 1, 'stage': 15, 'phase': 'construction_before_evaluation',
                'inputSha256': {name: digest(ROOT / name) for name in INPUTS},
                'generatorSha256': {f'scripts/models/conditional_candidate_ledger/{name}':
                                    digest(Path(__file__).parent / name) for name in CODE},
                'outputSha256': {name: sha256(encode(value)).hexdigest()
                                 for name, value in outputs.items()}}
    outputs['construction-manifest.json'] = manifest
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 15 construction output: {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        for name, value in outputs.items():
            (DEST / name).write_bytes(encode(value))
    print('Stage 15 conditional construction: 191 held general contests; 213 total frame')


if __name__ == '__main__':
    main()
