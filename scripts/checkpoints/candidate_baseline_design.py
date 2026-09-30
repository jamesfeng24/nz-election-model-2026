"""Inventory preserved target-boundary candidate evidence without forecasting."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from scripts.transform.modern_tables import candidate_table


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/checkpoints/candidate-baseline-design'
CONTRACT = DEST / 'design-contract.json'
SOURCE_PLAN = ROOT / 'data/source-plans/stage17-candidate-baseline-preserved-sources.json'
RAW_ROOT = 'data/raw/elections/2023/statistics/csv'
INPUTS = (
    'data/processed/boundaries/2023-2026/crosswalk.json',
    'data/processed/boundaries/2023-2026/party-votes.json',
    'data/processed/boundaries/secondary-availability.json',
    'data/processed/models/candidate-overperformance/occurrences.json',
    'data/processed/models/candidate-persistence/person-links.json',
    'data/processed/models/candidate-persistence/history-status.json',
    'data/processed/checkpoints/identity-evidence-pass/final/occurrence-evidence.json',
)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def required_raw_paths():
    return tuple(f'{RAW_ROOT}/candidate-votes-by-voting-place-{number}.csv'
                 for number in range(1, 73))


def source_snapshot(registry):
    """Pin consumed records and bytes without pinning unrelated registrations."""
    records = registry['sources']
    ids = [record['id'] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate registry source ID')
    by_path = defaultdict(list)
    for record in records:
        by_path[record['rawPath']].append(record)
    required = []
    for path in required_raw_paths():
        matches = by_path[path]
        if len(matches) != 1:
            raise ValueError(f'Missing or ambiguous required source: {path}')
        record = matches[0]
        if digest(ROOT / path) != record['sha256']:
            raise ValueError(f'Changed required raw source: {path}')
        required.append(record)
    return {'schemaVersion': 1, 'stage': 17,
            'role': 'preserved_2023_candidate_tables_only_no_new_acquisition',
            'sources': required}


def verify_source_snapshot(saved, registry):
    if source_snapshot(registry) != saved:
        raise ValueError('Changed or deleted required source record')


def validate_candidate_tables(occurrences):
    by_number = defaultdict(list)
    for row in occurrences:
        by_number[row['sourceElectorateNumber']].append(row)
    if set(by_number) != set(range(1, 73)):
        raise ValueError('Incomplete 2023 source candidate tables')
    names = {row['electorateName'] for row in occurrences}
    audit = []
    for number in range(1, 73):
        path = required_raw_paths()[number - 1]
        parsed = candidate_table((ROOT / path).read_bytes(),
                                 electorate_names=names, cancelled=(number == 39))
        expected = by_number[number]
        observed = [(row['name'], row['party'], row['votes'])
                    for row in parsed['candidates']]
        saved = [(row['sourceCandidateName'], row['sourceAffiliation'],
                  row['sourcePublishedCandidateVotes']) for row in expected]
        if observed != saved:
            raise ValueError(f'Candidate footer differs from Stage 7 occurrences: {number}')
        audit.append({'sourceElectorateNumber': number, 'rawPath': path,
                      'candidateOccurrences': len(expected),
                      'votingPlaceRowsValidated': parsed['votingPlaceRowsValidated'],
                      'validCandidateVotes': parsed['validVotes'],
                      'cancelled': number == 39,
                      'residenceMeshblockKey': None,
                      'reason': 'place-of-voting rows and aggregated special votes do not locate voter residence'})
    return audit, by_number


def unique_index(records, field):
    result = {}
    for record in records:
        key = record[field]
        if key in result:
            raise ValueError(f'Duplicate {field}: {key}')
        result[key] = record
    return result


def candidate_lead(row, target, source_code, links, history, primary):
    occurrence_id = row['candidateOccurrenceId']
    linked = links[occurrence_id]
    sampled = primary.get(occurrence_id)
    is_identity = (target['unchangedMembershipStatus'] == 'identity' and
                   target['dominantPredecessor'] == source_code and
                   len(target['composition']) == 1)
    if row['candidateContestStatus'] != 'held':
        geography = 'cancelled_source_no_valid_candidate_share'
    elif is_identity:
        geography = 'observed_2023_count_on_certified_unchanged_geography'
    elif target['unchangedMembershipStatus'] == 'suppressed_technical_uncertainty':
        geography = 'unresolved_membership_technical_exception'
    else:
        geography = 'unidentified_on_changed_boundary'
    return {
        'sourceOccurrenceId': occurrence_id,
        'sourceElectorateNumber': row['sourceElectorateNumber'],
        'sourceCandidateName': row['sourceCandidateName'],
        'sourceAffiliation': row['sourceAffiliation'],
        'sourcePartyKey': row['partyKey'],
        'observed2023CandidateVotes': row['sourcePublishedCandidateVotes'],
        'observed2023ValidCandidateVotes': row['validCandidateVotes'],
        'targetBoundaryHistoricalCandidateStatus': geography,
        'stage8OccurrenceConfidence': linked['status'],
        'stage13SampledPrimaryConfidence': (sampled['primaryOccurrenceConfidence']
                                            if sampled else None),
        'stage13RetrospectiveReconstruction': (sampled['retrospectiveReconstruction']
                                               if sampled else None),
        'inherited2023HistoryStatus': history[occurrence_id]['status'],
        'inheritedCareerHistoryEvidenceStatus': history[occurrence_id]['careerHistoryEvidenceStatus'],
        'personIdentityFor2026': None,
        'nominationFor2026': None,
    }


def inventory(crosswalk, party_bounds, occurrences, links, history, primary, raw_audit):
    occurrence_by_number = defaultdict(list)
    for row in occurrences:
        occurrence_by_number[row['sourceElectorateNumber']].append(row)
    raw_by_number = {row['sourceElectorateNumber']: row for row in raw_audit}
    records = []
    for scope in ('general', 'maori'):
        boundary = crosswalk['scopes'][scope]
        party = unique_index(party_bounds['scopes'][scope]['targets'], 'targetCode')
        source = unique_index(boundary['sources'], 'code')
        for target in sorted(boundary['targets'], key=lambda item: item['code']):
            target_party = party[target['code']]
            codes = sorted({part['source'] for part in target['composition']})
            if codes != sorted(target_party['sourceCodes']):
                raise ValueError('Party/crosswalk predecessor mismatch')
            leads = []
            source_seats = []
            for code in codes:
                number = int(code) + (65 if scope == 'maori' else 0)
                raw = raw_by_number[number]
                source_seats.append({'code': code, 'name': source[code]['name'],
                                     'sourceElectorateNumber': number,
                                     'candidateTableRawPath': raw['rawPath'],
                                     'candidateContestStatus': ('cancelled' if raw['cancelled']
                                                                else 'held')})
                leads.extend(candidate_lead(row, target, code, links, history, primary)
                             for row in occurrence_by_number[number])
            category_rows = []
            for item in target_party['parties']:
                category_rows.append({
                    'source2023PartyKey': item['partyKey'],
                    'syntheticTargetBoundary2023Votes': item['votes'],
                    'syntheticTargetBoundary2023VoteBounds': [item['votesLower'],
                                                               item['votesUpper']],
                    'syntheticTargetBoundary2023ShareBounds': [item['shareLower'],
                                                                item['shareUpper']],
                    'evidenceClass': ('exact_artifact_point' if item['votes'] is not None
                                      else 'coupled_synthetic_bounds'),
                    'partySupportFor2026': None,
                })
            if len(category_rows) != len({row['source2023PartyKey'] for row in category_rows}):
                raise ValueError('Duplicate party category')
            records.append({
                'targetBoundaryId': '2025', 'targetElectionYear': 2026,
                'scope': scope, 'targetCode': target['code'], 'targetName': target['name'],
                'officialChangeStatus': target['officialChangeStatus'],
                'unchangedMembershipStatus': target['unchangedMembershipStatus'],
                'predecessorSeats': source_seats,
                'historical2023PartyCategories': category_rows,
                'historical2023CandidateLeads': leads,
                'target2026CandidateSlate': None,
                'asOf2026PartySupport': None,
                'asOf2026CandidateTurnoutAndValidity': None,
                'asOfCutoffEvidenceStatus': 'not_in_preserved_input_bundle',
                'candidateOnlyBoundaryTransport': 'unsupported_without_voter_residence_and_candidate_mapping',
            })
    if len(records) != 71:
        raise ValueError('Unexpected target seat count')
    support = Counter(lead['targetBoundaryHistoricalCandidateStatus']
                      for record in records for lead in record['historical2023CandidateLeads'])
    party_support = Counter(item['evidenceClass'] for record in records
                            for item in record['historical2023PartyCategories'])
    boundary_status = Counter(f"{record['scope']}:{record['unchangedMembershipStatus'] or 'changed'}"
                              for record in records)
    return {'schemaVersion': 1, 'stage': 17,
            'dataClass': 'preserved_evidence_availability_not_candidate_forecasts',
            'records': records,
            'summary': {'targetSeats': len(records),
                        'byScopeAndMembership': dict(sorted(boundary_status.items())),
                        'historicalCandidateLeadRows': sum(len(record['historical2023CandidateLeads'])
                                                           for record in records),
                        'historicalCandidateLeadGeography': dict(sorted(support.items())),
                        'syntheticPartyCategoryRows': dict(sorted(party_support.items())),
                        'rawCandidateTablesVerified': len(raw_audit),
                        'unique2023CandidateOccurrences': len(occurrences),
                        'target2026SlateAvailableSeats': 0,
                        'strictAsOfForecastInputReadySeats': 0},
            'rawVotingPlaceAudit': raw_audit}


def build(registry=None):
    registry = registry if registry is not None else read('data/sources.json')
    snapshot = source_snapshot(registry)
    inputs = {path: read(path) for path in INPUTS}
    occurrences = [row for row in inputs[INPUTS[3]]['records'] if row['year'] == 2023]
    raw_audit, _ = validate_candidate_tables(occurrences)
    link_doc = inputs[INPUTS[4]]
    links = unique_index(link_doc['links'] + link_doc['unresolved'], 'candidateOccurrenceId')
    histories = unique_index(inputs[INPUTS[5]]['records'], 'candidateOccurrenceId')
    primary = unique_index(inputs[INPUTS[6]]['records'], 'candidateOccurrenceId')
    result = inventory(inputs[INPUTS[0]], inputs[INPUTS[1]], occurrences,
                       links, histories, primary, raw_audit)
    outputs = {'target-inventory.json': result}
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'stage': 17, 'phase': 'preserved_evidence_design_only',
        'inputSha256': {path: digest(ROOT / path) for path in INPUTS},
        'requiredRawSha256': {path: digest(ROOT / path) for path in required_raw_paths()},
        'sourceSnapshotSha256': sha256(encode(snapshot)).hexdigest(),
        'designContractSha256': digest(CONTRACT),
        'codeSha256': digest(ROOT / 'scripts/checkpoints/candidate_baseline_design.py'),
        'outputSha256': {'target-inventory.json': sha256(encode(result)).hexdigest()},
    }
    return snapshot, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    snapshot, outputs = build()
    if args.check:
        saved = json.loads(SOURCE_PLAN.read_bytes())
        verify_source_snapshot(saved, read('data/sources.json'))
        if SOURCE_PLAN.read_bytes() != encode(snapshot):
            raise ValueError('Changed Stage 17 consumed-source snapshot')
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 17 inventory: {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        SOURCE_PLAN.write_bytes(encode(snapshot))
        for name, value in outputs.items():
            (DEST / name).write_bytes(encode(value))
    print(json.dumps(outputs['target-inventory.json']['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
