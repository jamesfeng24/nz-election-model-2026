"""Generate frozen Stage 18 predictions before opening target candidate outcomes."""

import argparse
from hashlib import sha256

from scripts.models.conditional_candidate_share.inventory import (
    DEST, ELECTION_PATHS, ROOT, SOURCE_PLAN, YEARS, digest, encode,
    read, source_snapshot)
from scripts.models.conditional_candidate_share.model import construct
from scripts.validate.source_files import verify_source_files


INPUTS = ('data/processed/models/conditional-candidate-share/inventory.json',
          'data/processed/models/conditional-candidate-share/inventory-manifest.json',
          'data/processed/models/conditional-candidate-share/implementation-contract.json',
          'data/processed/models/party-vote-transform/backtest-records.json',
          *ELECTION_PATHS)
CODE = ('inventory.py', 'model.py', 'run.py')


def build():
    elections = {year: read(path) for year, path in zip(YEARS, ELECTION_PATHS)}
    snapshot = source_snapshot(read('data/sources.json'), elections)
    if SOURCE_PLAN.read_bytes() != encode(snapshot):
        raise ValueError('Changed required source record')
    verify_source_files(ROOT, {'schemaVersion': 1, 'sources': snapshot['sources']})
    inventory = read(INPUTS[0])
    if digest(ROOT / INPUTS[0]) != read(INPUTS[1])['inventorySha256']:
        raise ValueError('Changed committed pre-fit inventory')
    stage5 = read(INPUTS[3])['records']
    construction = construct(inventory, elections, stage5)
    manifest = {'schemaVersion': 1, 'stage': 18, 'phase': 'construction_before_target_evaluation',
                'inputSha256': {name: digest(ROOT / name) for name in INPUTS},
                'requiredSourceSnapshotSha256': digest(SOURCE_PLAN),
                'generatorSha256': {name: digest(ROOT / 'scripts/models/conditional_candidate_share' / name)
                                    for name in CODE},
                'constructionSha256': sha256(encode(construction)).hexdigest()}
    return {'construction.json': construction, 'construction-manifest.json': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, data in outputs.items():
            if (DEST / name).read_bytes() != encode(data):
                raise ValueError(f'Changed Stage 18 {name}')
    else:
        for name, data in outputs.items():
            (DEST / name).write_bytes(encode(data))
    print(outputs['construction.json']['summary'])


if __name__ == '__main__':
    main()
