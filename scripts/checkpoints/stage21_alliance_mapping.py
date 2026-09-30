"""Audit preserved shared-party-ballot categories without changing historical models."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/checkpoints/stage21-alliance-mapping'
INPUTS = (
    'data/processed/elections/2014.json',
    'data/processed/elections/2023.json',
    'data/processed/split-votes/2014.json',
    'data/processed/split-votes/2023.json',
    'data/processed/models/conditional-candidate-share/inventory.json',
)
GROUPS = {
    2014: ('internetmana', {'internetparty', 'manamovement'}),
    2023: ('freedomsnz', {'visionnewzealand', 'rockthevotenz',
                         'nzoutdoorsfreedomparty'}),
}
SUMMARY_SOURCE = {
    2014: 'ec-2014-e9-csv-e9_part1.csv',
    2023: 'ec-2023-statistics-csv-overall-results-summary.csv',
}


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def allocate_unique_group(group_mass, destination_ids):
    """Synthetic accounting kernel; a shared group's mass cannot be duplicated."""
    if not 0 <= group_mass <= 1:
        raise ValueError('Invalid party group mass')
    if len(destination_ids) != len(set(destination_ids)):
        raise ValueError('Duplicate destination')
    if len(destination_ids) != 1:
        raise ValueError('Shared group lacks one unique standing destination')
    return {destination_ids[0]: group_mass}


def group_metadata(splits):
    first = splits[2014]['partyGrouping']
    if (first['splitReportParty'] != 'Internet MANA' or
            set(first['sourceCandidateParties']) != {'Internet Party', 'MANA Movement'}):
        raise ValueError('Changed 2014 published grouping')
    second = splits[2023]['aggregateAffiliationMappings']
    if ({row['sourceAffiliation'] for row in second} !=
            {'Vision New Zealand', 'Rock the Vote NZ', 'NZ Outdoors & Freedom Party'} or
            {row['aggregateSplitColumn'] for row in second} != {'Freedoms NZ'}):
        raise ValueError('Changed 2023 aggregate reporting grouping')


def build_overlay(elections, splits, old_inventory):
    group_metadata(splits)
    old = {(row['year'], row['electorateId']): row
           for row in old_inventory['trainingGeneralContests']}
    records = []
    consumed = set(SUMMARY_SOURCE.values())
    for year in (2014, 2023):
        group_key, constituent_keys = GROUPS[year]
        matrices = {row['electorateId']: row for row in splits[year]['matrices']}
        for seat in elections[year]['electorates']:
            affected = [candidate for candidate in seat['candidates']
                        if candidate['partyKey'] in constituent_keys]
            if not affected:
                continue
            held = seat['validCandidateVotes'] > 0
            ballot_groups = [party for party in seat['parties']
                             if party['partyKey'] == group_key]
            if len(ballot_groups) != 1:
                raise ValueError('Missing or duplicate shared party ballot group')
            if any(party['partyKey'] in constituent_keys for party in seat['parties']):
                raise ValueError('Constituent unexpectedly has a separate party ballot group')
            matrix = matrices[seat['id']]
            rows = [row for row in matrix['rows'] if row['partyLabel'] in
                    ('Internet MANA', 'Freedoms NZ')]
            if len(rows) != 1 or rows[0]['totalPartyVotes'] != ballot_groups[0]['votes']:
                raise ValueError('Shared split row does not reconcile with party count')
            candidates_in_split = {cell['candidateId'] for row in matrix['rows']
                                   for cell in row['cells'] if cell['category'] == 'candidate'}
            if held and any(candidate['id'] not in candidates_in_split
                            for candidate in affected):
                raise ValueError('Constituent candidate missing from split destinations')
            old_row = old[(year, seat['id'])]
            old_by_id = {candidate['candidateOccurrenceId']: candidate
                         for candidate in old_row['candidates']}
            source_ids = sorted(set(seat['sourceIds'] + matrix['sourceIds'] +
                                    [SUMMARY_SOURCE[year]]))
            consumed.update(source_ids)
            records.append({
                'year': year, 'electorateId': seat['id'], 'electorate': seat['name'],
                'scope': seat['kind'], 'held': held,
                'sharedPartyBallotGroup': ballot_groups[0]['partyName'],
                'sharedPartyKey': group_key, 'sharedPartyVotes': ballot_groups[0]['votes'],
                'candidateCountInGroup': len(affected),
                'status': ('shared_group_single_local_destination' if len(affected) == 1
                           else 'shared_group_multiple_destinations_unresolved'),
                'sourceIds': source_ids,
                'candidates': [{
                    'candidateOccurrenceId': candidate['id'],
                    'name': candidate['name'],
                    'sourceAffiliation': candidate['party'],
                    'sourcePartyKey': candidate['partyKey'],
                    'oldMappingStatus': old_by_id[candidate['id']]['mappingStatus'],
                    'oldPartyKey': old_by_id[candidate['id']]['partyKey'],
                    'officialSplitDestinationExists': candidate['id'] in candidates_in_split,
                } for candidate in affected],
                'evidenceInterpretation': 'joint ballot category and local candidate destination; no constituent-specific party-vote allocation',
                'modelEligibilityInterpretation': 'single-destination group-level route is a modelling representation decision, not proof of constituent-specific votes',
            })
    counts = Counter((row['year'], 'held' if row['held'] else 'cancelled',
                      row['status']) for row in records)
    summary = {
        'affectedSeatCount': len(records),
        'byYearHeldStatus': {':'.join(map(str, key)): value
                             for key, value in sorted(counts.items())},
        'old2014AmbiguousTrainingSeats': sum(
            row['year'] == 2014 and row['held'] and
            any(c['oldMappingStatus'] == 'ambiguous_report_only_alliance'
                for c in row['candidates']) for row in records),
        'old2023AmbiguousHeldFrameSeats': sum(
            row['year'] == 2023 and row['held'] and
            any(c['oldMappingStatus'] == 'ambiguous_report_only_alliance'
                for c in row['candidates']) for row in records),
        'old2023IncorrectNoGroupHeldSeats': sum(
            row['year'] == 2023 and row['held'] and
            any(c['oldMappingStatus'] == 'verified_no_party_group_unregistered_affiliation'
                for c in row['candidates']) for row in records),
        'potentialNew2014TrainingSeatsUnderSingleGroupRoute': sum(
            row['year'] == 2014 and row['held'] and
            row['status'] == 'shared_group_single_local_destination'
            for row in records),
        'potentialNew2023FrameSeatsUnderSingleGroupRoute': sum(
            row['year'] == 2023 and row['held'] and
            any(c['oldMappingStatus'] == 'ambiguous_report_only_alliance'
                for c in row['candidates']) and
            row['status'] == 'shared_group_single_local_destination'
            for row in records),
    }
    return {'schemaVersion': 1, 'stage': 21,
            'role': 'supplemental_preserved_evidence_mapping_no_model_output_change',
            'records': records, 'summary': summary}, sorted(consumed)


def build():
    elections = {year: read(f'data/processed/elections/{year}.json')
                 for year in (2014, 2023)}
    splits = {year: read(f'data/processed/split-votes/{year}.json')
              for year in (2014, 2023)}
    overlay, ids = build_overlay(
        elections, splits,
        read('data/processed/models/conditional-candidate-share/inventory.json'))
    registry = read('data/sources.json')['sources']
    if len({row['id'] for row in registry}) != len(registry):
        raise ValueError('Duplicate source ID')
    by_id = {row['id']: row for row in registry}
    if set(ids) - by_id.keys():
        raise ValueError('Missing required source ID')
    snapshot = {'schemaVersion': 1, 'stage': 21,
                'sources': [by_id[source_id] for source_id in ids]}
    verify_source_files(ROOT, snapshot)
    manifest = {'schemaVersion': 1, 'stage': 21,
                'inputSha256': {path: digest(ROOT / path) for path in INPUTS},
                'generatorSha256': digest(Path(__file__)),
                'sourceSnapshotSha256': sha256(encode(snapshot)).hexdigest(),
                'overlaySha256': sha256(encode(overlay)).hexdigest()}
    return {'overlay.json': overlay, 'source-contract.json': snapshot,
            'manifest.json': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, data in outputs.items():
            if (DEST / name).read_bytes() != encode(data):
                raise ValueError(f'Changed Stage 21 {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        for name, data in outputs.items():
            (DEST / name).write_bytes(encode(data))
    print(json.dumps(outputs['overlay.json']['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
