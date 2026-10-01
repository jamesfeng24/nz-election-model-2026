"""Supplemental, election-local shared ballot group mapping for Stage 22."""

from copy import deepcopy
from collections import Counter


SHARED_STATUS = 'mapped_shared_group_single_local_destination'
MULTIPLE_STATUS = 'ambiguous_shared_group_multiple_local_destinations'


def apply_group(training, seat, evidence):
    """Route one official group once; preserve source affiliation independently."""
    group = evidence['sharedPartyKey']
    if evidence['year'] != training['year'] or evidence['electorateId'] != seat['id']:
        raise ValueError('Shared-group evidence joins wrong contest')
    party_rows = [row for row in seat['parties'] if row['partyKey'] == group]
    if len(party_rows) != 1 or party_rows[0]['votes'] != evidence['sharedPartyVotes']:
        raise ValueError('Missing, duplicate or changed shared party-ballot group')
    ids = [row['candidateOccurrenceId'] for row in evidence['candidates']]
    if len(ids) != evidence['candidateCountInGroup'] or len(ids) != len(set(ids)):
        raise ValueError('Duplicate or incomplete shared-group destination evidence')
    official = {row['id']: row for row in seat['candidates']}
    if len(official) != len(seat['candidates']):
        raise ValueError('Duplicate election-local candidate ID')
    mapped = {row['candidateOccurrenceId']: row for row in training['candidates']}
    if len(mapped) != len(training['candidates']):
        raise ValueError('Duplicate mapped candidate ID')
    for detail in evidence['candidates']:
        cid = detail['candidateOccurrenceId']
        if cid not in official or cid not in mapped:
            raise ValueError('Shared-group candidate not standing')
        if (mapped[cid]['sourcePartyKey'] != detail['sourcePartyKey'] or
                official[cid]['partyKey'] != detail['sourcePartyKey'] or
                mapped[cid]['sourceAffiliation'] != detail['sourceAffiliation']):
            raise ValueError('Shared-group source affiliation changed')
        if mapped[cid]['partyKey'] is not None:
            raise ValueError('Shared-group candidate already assigned party support')
    if not ids:
        return 'no_local_destination'
    if len(ids) > 1:
        for cid in ids:
            mapped[cid].update(mappingStatus=MULTIPLE_STATUS, partyKey=None,
                               noRegisteredPartyGroup=False,
                               sharedPartyGroupEvidence=evidence['electorateId'])
        training['status'] = 'ambiguous_mapping'
        return 'multiple_destinations_abstain'
    candidate = mapped[ids[0]]
    candidate.update(mappingStatus=SHARED_STATUS, partyKey=group,
                     noRegisteredPartyGroup=False,
                     sharedPartyGroupEvidence=evidence['electorateId'])
    assigned = [row for row in training['candidates'] if row['partyKey'] == group]
    if len(assigned) != 1:
        raise ValueError('Shared group assigned more than once')
    if training['status'] == 'ambiguous_mapping' and not any(
            row['mappingStatus'].startswith(('ambiguous_', 'missing_'))
            for row in training['candidates']):
        training['status'] = 'complete'
    return 'single_local_destination'


def amend_inventory(original, overlay, elections):
    """Copy Stage18's mapping; never rewrite the historical checkpoint."""
    mapping = deepcopy(original)
    training = {(r['year'], r['electorateId']): r
                for r in mapping['trainingGeneralContests']}
    frame = {(r['targetYear'], r['targetElectorateId']): r
             for r in mapping['frame']}
    seats = {(year, seat['id']): seat for year, doc in elections.items()
             for seat in doc['electorates']}
    if len(training) != len(mapping['trainingGeneralContests']) or len(frame) != len(mapping['frame']):
        raise ValueError('Duplicate mapping contest')
    decisions = []
    seen = set()
    for evidence in overlay['records']:
        key = (evidence['year'], evidence['electorateId'])
        if key in seen or key not in training or key not in seats:
            raise ValueError('Duplicate or unmatched shared-group contest')
        seen.add(key)
        if not evidence['held']:
            if training[key]['status'] != 'cancelled_or_unheld':
                raise ValueError('Cancelled shared-group contest changed status')
            decisions.append({'year': key[0], 'electorateId': key[1],
                              'decision': 'cancelled_unchanged', 'candidateOccurrenceIds': []})
            continue
        old_status = training[key]['status']
        old_candidates = deepcopy(training[key]['candidates'])
        outcome = apply_group(training[key], seats[key], evidence)
        if key in frame:
            framed = frame[key]
            framed['status'] = training[key]['status']
            framed['candidates'] = deepcopy(training[key]['candidates'])
        decisions.append({'year': key[0], 'electorateId': key[1],
                          'decision': outcome, 'oldStatus': old_status,
                          'newStatus': training[key]['status'],
                          'candidateOccurrenceIds': [r['candidateOccurrenceId']
                                                     for r in evidence['candidates']],
                          'candidateMappingChanges': [
                              {'candidateOccurrenceId': old['candidateOccurrenceId'],
                               'oldStatus': old['mappingStatus'],
                               'oldPartyKey': old['partyKey'],
                               'newStatus': new['mappingStatus'],
                               'newPartyKey': new['partyKey']}
                              for old, new in zip(old_candidates, training[key]['candidates'])
                              if old != new]})
    mapping['stage'] = 22
    mapping['role'] = 'supplemental_shared_group_mapping_no_target_outcomes'
    mapping['summary'] = {
        'frameContests': len(mapping['frame']),
        'heldGeneralCandidates': sum(r['candidateCount'] for r in mapping['frame']
                                     if r['scope'] == 'general' and
                                     r['status'] != 'cancelled_or_unheld'),
        'byTargetYearStatus': {f'{year}:{status}': n for (year, status), n in sorted(
            Counter((r['targetYear'], r['status']) for r in mapping['frame']).items())},
        'trainingByYearStatus': {f'{year}:{status}': n for (year, status), n in sorted(
            Counter((r['year'], r['status'])
                    for r in mapping['trainingGeneralContests']).items())}}
    return mapping, decisions
