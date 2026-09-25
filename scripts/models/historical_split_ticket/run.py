"""Generate or verify the Stage 11 split evidence checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.models.historical_split_ticket.evidence import (
    YEARS, candidate_inventory, table_coverage, verify_snapshot)


ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/models/historical-split-ticket'
INPUTS = (
    *(f'data/processed/elections/{year}.json' for year in YEARS),
    *(f'data/processed/split-votes/{year}.json' for year in YEARS),
    'data/processed/models/party-vote-transform/party-continuity.json',
    'data/source-plans/stage11-local-split-sources.json',
    'data/source-plans/2023-split-discrepancies.json',
)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


def build():
    elections = {year: read(f'data/processed/elections/{year}.json') for year in YEARS}
    splits = {year: read(f'data/processed/split-votes/{year}.json') for year in YEARS}
    verify_snapshot(ROOT, read('data/sources.json'),
                    read('data/source-plans/stage11-local-split-sources.json'), splits)
    discrepancy = read('data/source-plans/2023-split-discrepancies.json')['discrepancies']
    if splits[2023]['sourceDiscrepancies'] != discrepancy:
        raise ValueError('Changed reviewed 2023 split discrepancy record')
    coverage = table_coverage(elections, splits)
    applicability = candidate_inventory(
        elections, splits,
        read('data/processed/models/party-vote-transform/party-continuity.json')['records'])
    inputs = {name: digest(ROOT / name) for name in INPUTS}
    outputs = {
        'evidence.json': {'schemaVersion': 1, 'stage': 11,
                          'tableCoverage': coverage,
                          'ballotPopulation': 'Party ballot groups, including informal party ballots; each local row is an exact group count. Candidate, informal-candidate and party-vote-only columns are rounded conditional percentages of that row, not exact joint counts.',
                          'candidateShareMapping': 'The sum of predicted candidate votes must be divided by the separately observed or forecast valid-candidate-vote denominator. Party-ballot totals and candidate valid votes differ.',
                          'maoriStatus': 'Aggregate general/Māori/national matrices have destination party groups rather than local named candidates. One supporting 2020 Māori local matrix is not a six-election comparable panel.',
                          'discrepancyStatus': '2023 preserves 21 unresolved aggregate Party Vote Only reconciliation assertions; do not allocate the mass or reinterpret cancelled Port Waikato as behaviour.',
                          'exactJointCountsAvailable': False},
        'applicability.json': applicability,
        'input-contract.json': inputs,
    }
    code = [ROOT / 'scripts/models/historical_split_ticket' / name
            for name in ('evidence.py', 'run.py')]
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'stage': 11, 'phase': 'evidence_before_specification',
        'inputHashes': inputs,
        'codeHashes': {str(path.relative_to(ROOT)): digest(path) for path in code},
        'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest()
                         for name, value in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 11 evidence output: {name}')
        print('Stage 11 evidence reproducible')
        return
    DEST.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        (DEST / name).write_bytes(encode(value))
    print('Stage 11 evidence written')


if __name__ == '__main__':
    main()
