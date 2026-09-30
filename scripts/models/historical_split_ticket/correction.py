"""Stage 21 certified-geography correction to Stage 11 applicability.

The original Stage 11 implementation and outputs remain the historical checkpoint.
This module only assembles the corrected pre-score inventory.
"""

from collections import Counter

from scripts.models.historical_split_ticket.evidence import UNCHANGED, candidate_inventory
from scripts.transform.historical import key


def _unique(rows, field):
    result = {row[field]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f'Ambiguous {field}')
    return result


def _certified_pairs(frame, elections):
    pairs = {}
    seats = {year: _unique(doc['electorates'], 'id') for year, doc in elections.items()}
    for item in frame['records']:
        if item['scope'] != 'general':
            continue
        source_year, target_year = item['sourceYear'], item['targetYear']
        source_id, target_id = item['sourceElectorateId'], item['targetElectorateId']
        if (source_year, target_year) not in UNCHANGED:
            raise ValueError('Changed-boundary pair in certified unchanged frame')
        source = seats[source_year].get(source_id)
        target = seats[target_year].get(target_id)
        if source is None or target is None or source['kind'] != item['scope'] or target['kind'] != item['scope']:
            raise ValueError('Certified pair has missing or wrong-scope electorate')
        if source['name'] != item['sourceSeatLabel'] or target['name'] != item['targetSeatLabel']:
            raise ValueError('Certified geography labels differ from election records')
        if item['boundaryRegime'] not in ('2007', '2014', '2020'):
            raise ValueError('Unrecognised certified boundary regime')
        if {candidate['id'] for candidate in source['candidates']} != set(item['sourceOccurrenceIds']):
            raise ValueError('Certified source slate does not match election')
        if {candidate['id'] for candidate in target['candidates']} != set(item['targetOccurrenceIds']):
            raise ValueError('Certified target slate does not match election')
        pair = (target_year, target_id)
        if pair in pairs:
            raise ValueError('Ambiguous certified target electorate')
        pairs[pair] = (item, source, target)
    if len(frame['records']) != 213 or len(pairs) != 192:
        raise ValueError('Changed certified 213-contest frame or 192 general contests')
    return pairs


def _repair_candidate(row, source, target, matrix, party_map):
    """Rebuild only source-dependent fields for a certified label-changed seat."""
    candidate = _unique(target['candidates'], 'id')[row['targetOccurrenceId']]
    source_party = party_map.get((row['sourceYear'], row['targetYear'], candidate['partyKey']))
    if row['sourcePartyKey'] != source_party:
        raise ValueError('Historical party-continuity contract changed')
    prior = [person for person in source['candidates'] if person['partyKey'] == source_party] if source_party else []
    exact = [person for person in prior if person['name'] == candidate['name']]
    if len(exact) == 1 and len(prior) == 1:
        mapping = 'probable_exact_name_party_seat_chain'
    elif prior:
        mapping = 'unresolved_same_party_predecessor'
    else:
        mapping = 'no_same_party_source_candidacy'
    target_rows = {party['partyKey'] for party in target['parties']} | {'informalpartyvotes'}
    source_rows = {key(part['partyLabel']) for part in matrix['rows'][:-1]}
    missing = sorted(party for party in target_rows if
                     (party if party == 'informalpartyvotes' else
                      party_map.get((row['sourceYear'], row['targetYear'], party))) not in source_rows)
    reasons = []
    if matrix.get('behaviouralEvidence') is False:
        reasons.append('cancelled_source_contest')
    if target.get('candidateContestStatus', 'held') != 'held':
        reasons.append('cancelled_target_contest')
    if not source_party:
        reasons.append('no_supported_cross_election_party_continuity')
    if source_party and source_party not in {person['partyKey'] for person in source['candidates']}:
        reasons.append('source_candidate_party_absent')
    partial = not reasons
    if missing:
        reasons.append('target_party_group_absent_in_source_local_split')
    return {**row, 'sourceCandidateIds': [person['id'] for person in prior],
            'candidateMapping': mapping, 'sourceMatrixId': matrix['id'],
            'targetPartyGroupCount': len(target_rows), 'missingSourcePartyGroups': missing,
            'geography': 'same_verified_boundary_regime',
            'conditionalPartialApplicability': partial,
            'conditionalLocalApplicability': not reasons, 'exclusionReasons': reasons}


def certified_pair_for_row(row, elections):
    """Resolve corrected Stage 11 analysis/sensitivity seats by certified IDs."""
    source_id = row.get('sourceElectorateId')
    target_id = row.get('targetElectorateId')
    if source_id is None or target_id is None:
        raise ValueError('Candidate lacks certified comparable geography')
    source = _unique(elections[row['sourceYear']]['electorates'], 'id').get(source_id)
    target = _unique(elections[row['targetYear']]['electorates'], 'id').get(target_id)
    if source is None or target is None or source['kind'] != 'general' or target['kind'] != 'general':
        raise ValueError('Certified candidate source/target electorate missing')
    if target['name'] != row['electorateName']:
        raise ValueError('Certified target label differs from election')
    if row['targetOccurrenceId'] not in {candidate['id'] for candidate in target['candidates']}:
        raise ValueError('Candidate not in certified target electorate')
    return source, target


def corrected_inventory(original, frame, elections, splits, continuity):
    """Use certified IDs for geography; retain every nonrepaired original row."""
    if original != candidate_inventory(elections, splits, continuity):
        raise ValueError('Original Stage 11 applicability differs from historical generator')
    certified = _certified_pairs(frame, elections)
    party_map = {(record['sourceYear'], record['targetYear'], record['target']['sourceKey']):
                 record['source']['sourceKey'] for record in continuity if record['status'] == 'eligible'}
    matrices = {year: _unique(doc['matrices'], 'electorateId') for year, doc in splits.items()}
    records = []
    repaired = Counter()
    original_by_id = _unique(original['records'], 'targetOccurrenceId')
    for old in original['records']:
        target_id = old['targetOccurrenceId'].rsplit('-candidate-', 1)[0]
        pair = certified.get((old['targetYear'], target_id))
        if pair is None:
            records.append(old)
            continue
        item, source, target = pair
        if old['sourceYear'] != item['sourceYear'] or old['electorateName'] != target['name']:
            raise ValueError('Original candidate mismatches certified contest')
        row = {**old, 'sourceElectorateId': source['id'], 'targetElectorateId': target['id']}
        if source['name'] != target['name']:
            if item['scope'] != 'general':
                raise ValueError('Unexpected non-general changed label')
            matrix = matrices[item['sourceYear']].get(source['id'])
            if matrix is None or matrix['id'] != item['sourceLocalSplitMatrixId']:
                raise ValueError('Missing certified source split matrix')
            row = _repair_candidate(row, source, target, matrix, party_map)
            repaired[(source['id'], target['id'])] += row['conditionalPartialApplicability']
        records.append(row)
    if len(original_by_id) != len(records) or {row['targetOccurrenceId'] for row in records} != set(original_by_id):
        raise ValueError('Changed occurrence universe')
    counts = Counter((row['sourceYear'], row['targetYear'], row['electorateType'],
                      row['conditionalLocalApplicability']) for row in records)
    partial_counts = Counter((row['sourceYear'], row['targetYear'], row['electorateType'])
                             for row in records if row['conditionalPartialApplicability'])
    return {'schemaVersion': 1, 'records': records,
            'counts': [{'sourceYear': source, 'targetYear': target, 'scope': scope,
                        'applicable': applicable, 'count': count}
                       for (source, target, scope, applicable), count in sorted(counts.items())],
            'partialCounts': [{'sourceYear': source, 'targetYear': target,
                               'scope': scope, 'count': count}
                              for (source, target, scope), count in sorted(partial_counts.items())],
            'exclusionCounts': dict(sorted(Counter(reason for row in records
                                                  for reason in row['exclusionReasons']).items())),
            'correction': {'type': 'certified_unchanged_boundary_electorate_id_join',
                           'repairedSourceTargetPairs': [
                               {'sourceElectorateId': source_id,
                                'targetElectorateId': target_id,
                                'newPartialCandidateCount': count}
                               for (source_id, target_id), count in sorted(repaired.items())]}}
