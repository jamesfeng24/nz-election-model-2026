"""Outcome-blind inventory of complete historical slates and party categories."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'data/processed/models/conditional-candidate-share'
SOURCE_PLAN = ROOT / 'data/source-plans/stage18-conditional-candidate-share-sources.json'
YEARS = (2008, 2011, 2014, 2017, 2020, 2023)
FRAME = 'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json'
ELECTION_PATHS = tuple(f'data/processed/elections/{year}.json' for year in YEARS)
REPORT_ONLY = {2014: {'internetparty', 'manamovement'},
               2023: {'visionnewzealand'}}


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def classify(seat, registered_keys, year):
    """Classify election-local affiliation without reading candidate outcomes."""
    local = {row['partyKey'] for row in seat['parties']}
    if len(local) != len(seat['parties']):
        raise ValueError('Duplicate local party-ballot group')
    seen = set()
    candidates = []
    for row in seat['candidates']:
        key = row['partyKey']
        if key in local:
            status, party = 'mapped_registered_party_group', key
        elif key == 'independent':
            status, party = 'verified_no_party_group_independent', None
        elif key in REPORT_ONLY.get(year, set()):
            status, party = 'ambiguous_report_only_alliance', None
        elif key in registered_keys:
            status, party = 'missing_local_registered_party_group', None
        else:
            status, party = 'verified_no_party_group_unregistered_affiliation', None
        if row['id'] in seen:
            raise ValueError('Duplicate candidate occurrence')
        seen.add(row['id'])
        candidates.append({'candidateOccurrenceId': row['id'], 'sourceAffiliation': row['party'],
                           'sourcePartyKey': key, 'mappingStatus': status,
                           'partyKey': party,
                           'noRegisteredPartyGroup': status.startswith('verified_no_party_group')})
    mapped = [row['partyKey'] for row in candidates if row['partyKey'] is not None]
    if len(mapped) != len(set(mapped)):
        raise ValueError('Multiple candidates assigned to one party-ballot group')
    return candidates


def source_snapshot(registry, elections):
    records = registry['sources']
    indexed = {row['id']: row for row in records}
    if len(indexed) != len(records):
        raise ValueError('Duplicate source registry ID')
    ids = {sid for election in elections.values() for seat in election['electorates']
           if seat['kind'] == 'general' for sid in seat['sourceIds']}
    if ids - indexed.keys():
        raise ValueError('Missing required source record')
    return {'schemaVersion': 1, 'stage': 18,
            'selection': 'all held and cancelled general election seat source IDs in six processed elections',
            'sources': [indexed[sid] for sid in sorted(ids)]}


def build_inventory(elections, frame):
    by_year = {year: {seat['id']: seat for seat in doc['electorates']}
               for year, doc in elections.items()}
    registered = {year: {p['partyKey'] for seat in doc['electorates']
                         for p in seat['parties']} for year, doc in elections.items()}
    training = []
    for year in YEARS:
        for seat in sorted(elections[year]['electorates'], key=lambda item: item['id']):
            if seat['kind'] != 'general':
                continue
            candidates = classify(seat, registered[year], year)
            held = seat['validCandidateVotes'] > 0 and len(candidates) > 0
            ambiguous = any(row['mappingStatus'].startswith(('ambiguous_', 'missing_'))
                            for row in candidates)
            training.append({'year': year, 'electorateId': seat['id'],
                             'status': ('complete' if held and not ambiguous else
                                        'cancelled_or_unheld' if not held else 'ambiguous_mapping'),
                             'candidateCount': len(candidates),
                             'hasNoPartyGroup': any(row['noRegisteredPartyGroup'] for row in candidates),
                             'candidates': candidates})
    training_by_id = {(row['year'], row['electorateId']): row for row in training}
    records = []
    for row in frame['records']:
        if row['scope'] != 'general':
            records.append({'sourceYear': row['sourceYear'], 'targetYear': row['targetYear'],
                            'targetElectorateId': row['targetElectorateId'], 'scope': row['scope'],
                            'candidateCount': len(row['targetOccurrenceIds']),
                            'status': 'coverage_only_maori'})
            continue
        target = by_year[row['targetYear']][row['targetElectorateId']]
        local = training_by_id[(row['targetYear'], target['id'])]
        if {c['candidateOccurrenceId'] for c in local['candidates']} != set(row['targetOccurrenceIds']):
            raise ValueError('Fixed frame candidature changed')
        status = local['status'] if row['contestStatus'] == 'held_both' else 'cancelled_or_unheld'
        records.append({'sourceYear': row['sourceYear'], 'targetYear': row['targetYear'],
                        'targetElectorateId': target['id'], 'scope': 'general',
                        'candidateCount': len(local['candidates']), 'status': status,
                        'candidates': local['candidates']})
    if len(records) != 213 or len([r for r in records if r['scope'] == 'general' and
                                   r['status'] != 'cancelled_or_unheld']) != 191:
        raise ValueError('Changed fixed frame')
    counts = Counter((row['targetYear'], row['status']) for row in records)
    return {'schemaVersion': 1, 'stage': 18,
            'role': 'pre_fit_mapping_inventory_no_outcomes_or_fitted_parameters',
            'trainingGeneralContests': training, 'frame': records,
            'summary': {'frameContests': len(records),
                        'heldGeneralCandidates': sum(row['candidateCount'] for row in records
                                                     if row['scope'] == 'general' and
                                                     row['status'] != 'cancelled_or_unheld'),
                        'byTargetYearStatus': {f'{y}:{status}': n for (y, status), n in sorted(counts.items())},
                        'trainingByYearStatus': {f'{y}:{status}': n for (y, status), n in sorted(
                            Counter((r['year'], r['status']) for r in training).items())}}}


def build():
    elections = {year: read(path) for year, path in zip(YEARS, ELECTION_PATHS)}
    frame = read(FRAME)
    registry = read('data/sources.json')
    snapshot = source_snapshot(registry, elections)
    verify_source_files(ROOT, {'schemaVersion': 1, 'sources': snapshot['sources']})
    data = build_inventory(elections, frame)
    manifest = {'schemaVersion': 1, 'stage': 18, 'phase': 'inventory_before_fitting',
                'inputSha256': {p: digest(ROOT / p) for p in (FRAME, *ELECTION_PATHS)},
                'sourceSnapshotSha256': sha256(encode(snapshot)).hexdigest(),
                'generatorSha256': digest(Path(__file__)),
                'inventorySha256': sha256(encode(data)).hexdigest()}
    return snapshot, {'inventory.json': data, 'inventory-manifest.json': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    snapshot, outputs = build()
    if args.check:
        if SOURCE_PLAN.read_bytes() != encode(snapshot):
            raise ValueError('Changed required registry source record')
        for name, data in outputs.items():
            if (DEST / name).read_bytes() != encode(data):
                raise ValueError(f'Changed saved Stage 18 {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        SOURCE_PLAN.write_bytes(encode(snapshot))
        for name, data in outputs.items():
            (DEST / name).write_bytes(encode(data))
    print(json.dumps(outputs['inventory.json']['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
