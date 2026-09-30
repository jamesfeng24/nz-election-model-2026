"""Pin original Stage 11 outputs and generate the pre-score geographic repair."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.models.historical_split_ticket.correction import corrected_inventory
from scripts.models.historical_split_ticket.evidence import YEARS
from scripts.models.historical_split_ticket.run import ROOT


ORIGINAL = Path('data/processed/models/historical-split-ticket')
DEST = Path('data/processed/checkpoints/stage21-stage11-geography-repair')
FRAME = Path('data/processed/checkpoints/complete-candidate-baseline/input-inventory.json')
PARTY = Path('data/processed/models/party-vote-transform/party-continuity.json')
INPUTS = (FRAME, PARTY, ORIGINAL / 'applicability.json',
          *(Path(f'data/processed/elections/{year}.json') for year in YEARS),
          *(Path(f'data/processed/split-votes/{year}.json') for year in YEARS))


def read(path):
    return json.loads((ROOT / path).read_bytes())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def build():
    original_paths = sorted((ROOT / ORIGINAL).glob('*.json'))
    if len(original_paths) != 12:
        raise ValueError('Original Stage 11 artifact set changed')
    original = {str(path.relative_to(ROOT)): sha(path.relative_to(ROOT)) for path in original_paths}
    elections = {year: read(Path(f'data/processed/elections/{year}.json')) for year in YEARS}
    splits = {year: read(Path(f'data/processed/split-votes/{year}.json')) for year in YEARS}
    applicability = corrected_inventory(read(ORIGINAL / 'applicability.json'), read(FRAME),
                                        elections, splits, read(PARTY)['records'])
    # The original and corrected samples are compared directly, not inferred
    # from the presence of a certified seat ID on a row.
    before = {row['targetOccurrenceId'] for row in read(ORIGINAL / 'applicability.json')['records']
              if row['conditionalPartialApplicability']}
    after = {row['targetOccurrenceId'] for row in applicability['records']
             if row['conditionalPartialApplicability']}
    if not before <= after:
        raise ValueError('Original Stage 11 common sample was removed')
    summary = {'schemaVersion': 1, 'stage': 21,
               'originalPartialCandidateCount': len(before),
               'correctedPartialCandidateCount': len(after),
               'newPartialCandidateCount': len(after - before),
               'newPartialOccurrenceIds': sorted(after - before),
               'originalPartialOccurrenceIds': sorted(before),
               'repairedSeatPairs': applicability['correction']['repairedSourceTargetPairs'],
               'scope': 'Only pre-score Stage 11 applicability; original diagnostics unchanged'}
    output = {'original-artifact-hashes.json': {'schemaVersion': 1, 'stage': 21,
                                                'role': 'immutable_stage11_pre_correction_checkpoint',
                                                'artifacts': original},
              'corrected-applicability.json': applicability,
              'correction-scope.json': summary}
    output['inventory-manifest.json'] = {'schemaVersion': 1, 'stage': 21,
                                         'inputHashes': {str(path): sha(path) for path in INPUTS},
                                         'generatorHashes': {
                                             str(path): sha(path) for path in (
                                                 Path('scripts/models/historical_split_ticket/correction.py'),
                                                 Path('scripts/models/historical_split_ticket/correction_run.py'))},
                                         'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest()
                                                          for name, value in output.items()}}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    output = build()
    dest = ROOT / DEST
    if args.check:
        for name, value in output.items():
            if (dest / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 21 corrected Stage 11 inventory: {name}')
        print('Stage 21 Stage 11 pre-score inventory reproducible')
    else:
        dest.mkdir(parents=True, exist_ok=True)
        for name, value in output.items():
            (dest / name).write_bytes(encode(value))
        print('Stage 21 Stage 11 pre-score inventory written')


if __name__ == '__main__':
    main()
