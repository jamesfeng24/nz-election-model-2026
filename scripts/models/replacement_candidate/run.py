"""Generate or verify the pinned Stage 10 pre-fit inventory."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.models.replacement_candidate.inventory import build_inventory
from scripts.models.replacement_candidate.identity_evidence import (
    build_person_links, validate_adjudications, verify_identity_snapshot)
from scripts.models.replacement_candidate.maori_winners import build_overlay, verify_snapshot
from scripts.validate.source_files import verify_source_files


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
    'data/source-plans/stage10-identity-review-plan.json',
    'data/source-plans/stage10-identity-adjudications.json',
    'data/source-plans/stage10-identity-sources.json',
    'data/source-plans/stage10-maori-winner-sources.json',
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
    occurrences = read(INPUTS[0])['records']
    links = read(INPUTS[1])['links']
    profiles = read(INPUTS[3])['profiles']
    identity_sources = read('data/source-plans/stage10-identity-sources.json')
    tenure_sources = read('data/source-plans/freshman-incumbency-tenure-sources.json')
    registry = read('data/sources.json')
    verify_identity_snapshot(registry, identity_sources)
    verify_source_files(ROOT, identity_sources)
    verify_source_files(ROOT, tenure_sources)
    maori_snapshot = read('data/source-plans/stage10-maori-winner-sources.json')
    maori_records = verify_snapshot(ROOT, occurrences, registry, maori_snapshot)
    maori_overlay = build_overlay(ROOT, occurrences, maori_records)
    adjudications = validate_adjudications(
        ROOT, read('data/source-plans/stage10-identity-review-plan.json'),
        read('data/source-plans/stage10-identity-adjudications.json'), occurrences,
        identity_sources['sources'], tenure_sources['sources'], profiles, links)
    person_links = build_person_links(adjudications, links, occurrences)
    inventory = build_inventory(
        occurrences, links, read(INPUTS[2])['records'], elected, profiles,
        adjudications, {row['winnerOccurrenceId'] for row in maori_overlay['records']},
        {row['candidateOccurrenceId']: row for row in person_links['links']})
    by_event = {row['eventId']: row for row in inventory['records']}
    review = {'schemaVersion': 1, 'records': [
        {'eventId': row['eventId'], 'externalPriority': row['externalPriority'],
         'originalIdentityClass': row['inheritedIdentityClass'],
         'correctedIdentityClass': by_event[row['eventId']]['identityClass'],
         'adjudication': adjudications.get(row['eventId']),
         'reviewOutcome': ('supported_by_new_evidence' if row['eventId'] in adjudications
                           else 'preserved_evidence_only; unresolved identity retained where applicable')}
        for row in read('data/source-plans/stage10-identity-review-plan.json')['records']],
        'acquisitionSelection': '20 cases predeclared without target wins or residual changes. Retrospective Parliament profiles are stronger for winners; five requested seat pages failed and no exhaustive biography search followed.'}
    outputs = {'input-contract.json': expected, 'maori-winner-overlay.json': maori_overlay,
               'person-links.json': person_links, 'identity-review.json': review,
               'inventory.json': inventory}
    code = [ROOT / f'scripts/models/replacement_candidate/{name}.py'
            for name in ('__init__', 'identity_evidence', 'inventory', 'maori_winners', 'run')]
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
