"""Generate Stage 21 corrected Stage 11 diagnostics beside the original files."""

import argparse
import hashlib

from scripts.models.historical_split_ticket.corrected_analysis import corrected_diagnostics
from scripts.models.historical_split_ticket.analysis_run import encode as score_encode
from scripts.models.historical_split_ticket.correction_run import (
    DEST, INPUTS as INVENTORY_INPUTS, ORIGINAL, ROOT, build as build_inventory,
    encode as inventory_encode, read, sha)
from scripts.models.historical_split_ticket.evidence import YEARS


INPUTS = (
    DEST / 'corrected-applicability.json',
    DEST / 'original-artifact-hashes.json',
    DEST / 'correction-scope.json',
    DEST / 'inventory-manifest.json',
    ORIGINAL / 'predictions.json',
    ORIGINAL / 'party-input-sensitivity.json',
    'data/processed/models/party-vote-transform/backtest-records.json',
    'data/processed/models/replacement-candidate/inventory.json',
    *INVENTORY_INPUTS,
)


def build():
    inventory = build_inventory()
    for name, expected in inventory.items():
        if (ROOT / DEST / name).read_bytes() != inventory_encode(expected):
            raise ValueError(f'Pre-score geographic correction checkpoint changed: {name}')
    original_hashes = read(DEST / 'original-artifact-hashes.json')['artifacts']
    if any(sha(path) != expected for path, expected in original_hashes.items()):
        raise ValueError('Historical Stage 11 artifact changed')
    elections = {year: read(f'data/processed/elections/{year}.json') for year in YEARS}
    splits = {year: read(f'data/processed/split-votes/{year}.json') for year in YEARS}
    stage10 = {row['eventId']: row for row in
               read('data/processed/models/replacement-candidate/inventory.json')['records']}
    output = corrected_diagnostics(
        read(ORIGINAL / 'applicability.json'), read(DEST / 'corrected-applicability.json'),
        elections, splits,
        read('data/processed/models/party-vote-transform/party-continuity.json')['records'],
        read('data/processed/models/party-vote-transform/backtest-records.json')['records'],
        stage10, read(ORIGINAL / 'predictions.json'),
        read(ORIGINAL / 'party-input-sensitivity.json'))
    output['corrected-analysis-manifest.json'] = {
        'schemaVersion': 1, 'stage': 21,
        'role': 'explicit_stage11_geographic_join_correction_existing_diagnostic_rules',
        'inputHashes': {str(path): sha(path) for path in INPUTS},
        'generatorHashes': {str(path): sha(path) for path in (
            'scripts/models/historical_split_ticket/corrected_analysis.py',
            'scripts/models/historical_split_ticket/corrected_analysis_run.py')},
        'outputHashes': {name: hashlib.sha256(score_encode(value)).hexdigest()
                         for name, value in output.items()}}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    output = build()
    if args.check:
        for name, value in output.items():
            if (ROOT / DEST / name).read_bytes() != score_encode(value):
                raise ValueError(f'Changed corrected Stage 11 output: {name}')
        print('Corrected Stage 11 diagnostics reproducible')
    else:
        for name, value in output.items():
            (ROOT / DEST / name).write_bytes(score_encode(value))
        print('Corrected Stage 11 diagnostics written')


if __name__ == '__main__':
    main()
