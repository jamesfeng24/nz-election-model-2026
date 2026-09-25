"""Audit preserved split-table populations and pre-result candidate applicability."""

from collections import Counter

from scripts.transform.historical import key
from scripts.validate.source_files import verify_source_files


YEARS = (2008, 2011, 2014, 2017, 2020, 2023)
TRANSITIONS = ((2008, 2011), (2011, 2014), (2014, 2017),
               (2017, 2020), (2020, 2023))
UNCHANGED = {(2008, 2011), (2014, 2017), (2020, 2023)}


def verify_snapshot(root, registry, snapshot, splits):
    """Pin consumed local source records and bytes without pinning the registry."""
    if snapshot['stage'] != 11:
        raise ValueError('Wrong split source snapshot stage')
    live = registry['sources']
    if len(live) != len({row['id'] for row in live}):
        raise ValueError('Ambiguous live source ID')
    required = snapshot['sources']
    if len(required) != len({row['id'] for row in required}):
        raise ValueError('Ambiguous pinned source ID')
    consumed = {sid for year in YEARS for matrix in splits[year]['matrices']
                for sid in matrix['sourceIds']}
    if consumed != {row['id'] for row in required}:
        raise ValueError('Missing or extra pinned local split dependency')
    by_id = {row['id']: row for row in live}
    if any(by_id.get(row['id']) != row for row in required):
        raise ValueError('Changed or deleted required split source record')
    verify_source_files(root, {'schemaVersion': 1, 'sources': required})


def table_coverage(elections, splits):
    """Check local orientation, controls, precision and scope without fitting."""
    result = []
    for year in YEARS:
        election = {seat['id']: seat for seat in elections[year]['electorates']}
        matrices = splits[year]['matrices']
        seen = set()
        counts = Counter()
        for matrix in matrices:
            seat_id = matrix['electorateId']
            if seat_id in seen or seat_id not in election:
                raise ValueError('Duplicate or dangling local matrix electorate')
            seen.add(seat_id)
            seat = election[seat_id]
            if seat['kind'] != 'general' or matrix['year'] != year:
                raise ValueError('Local split matrix scope/year mismatch')
            rows = matrix['rows']
            if not rows or rows[-1]['partyLabel'] != 'Total Party Votes and Percentages':
                raise ValueError('Missing local split total row')
            by_party = {p['partyKey']: p['votes'] for p in seat['parties']}
            by_party['informalpartyvotes'] = seat['partyBallot']['informalVotes']
            row_keys = [key(row['partyLabel']) for row in rows[:-1]]
            if len(set(row_keys)) != len(row_keys) or set(row_keys) != set(by_party):
                raise ValueError('Local split row identities do not match party ballot')
            if any(row['totalPartyVotes'] != by_party[key(row['partyLabel'])]
                   for row in rows[:-1]):
                raise ValueError('Local split row denominator differs from party count')
            total = seat['validPartyVotes'] + seat['partyBallot']['informalVotes']
            if sum(row['totalPartyVotes'] for row in rows[:-1]) != total or rows[-1]['totalPartyVotes'] != total:
                raise ValueError('Local split total denominator mismatch')
            candidates = {candidate['id']: candidate for candidate in seat['candidates']}
            categories = [cell['category'] for cell in rows[0]['cells']]
            if categories.count('informal') != 1 or categories.count('party-vote-only') != 1:
                raise ValueError('Missing non-candidate destination')
            if {cell['candidateId'] for cell in rows[0]['cells'] if cell['category'] == 'candidate'} != set(candidates):
                raise ValueError('Local split candidate columns do not match election')
            for row in rows:
                if len(row['cells']) != len(categories) or any(cell['count'] is not None for cell in row['cells']):
                    raise ValueError('Joint split counts invented or destination missing')
                if row['totalPartyVotes'] and matrix.get('behaviouralEvidence') is not False and any(
                        cell['reportedPercent'] is None for cell in row['cells']):
                    raise ValueError('Missing positive-denominator split percentage')
            counts['roundedLocalMatrices'] += 1
            counts['partyVoteRows'] += len(rows) - 2
            counts['candidateColumns'] += len(candidates)
            counts['cancelledOrNonbehavioural'] += matrix.get('behaviouralEvidence') is False
        expected = {seat['id'] for seat in election.values() if seat['kind'] == 'general'}
        if seen != expected:
            raise ValueError('Incomplete general local split coverage')
        counts['supportingMaoriLocalMatrices'] = len(splits[year].get('supportingMatrices', []))
        counts['maoriElectoratesWithoutLocalMatrix'] = 7 - counts['supportingMaoriLocalMatrices']
        counts['officialSourceDiscrepancies'] = len(splits[year].get('sourceDiscrepancies', []))
        result.append({'year': year, **dict(sorted(counts.items()))})
    return result


def candidate_inventory(elections, splits, continuity):
    """Inventory every target candidature; never inspect target votes or winner flags."""
    party_map = {(row['sourceYear'], row['targetYear'], row['target']['sourceKey']):
                 row['source']['sourceKey'] for row in continuity
                 if row['status'] == 'eligible'}
    records = []
    for source_year, target_year in TRANSITIONS:
        source_seats = {(seat['kind'], seat['name']): seat
                        for seat in elections[source_year]['electorates']}
        source_matrices = {matrix['electorateId']: matrix
                           for matrix in splits[source_year]['matrices']}
        for target in elections[target_year]['electorates']:
            source = source_seats.get((target['kind'], target['name']))
            matrix = source_matrices.get(source['id']) if source else None
            target_rows = {p['partyKey'] for p in target['parties']}
            target_rows.add('informalpartyvotes')
            source_rows = ({key(row['partyLabel']) for row in matrix['rows'][:-1]}
                           if matrix else set())
            source_candidates = source['candidates'] if source else []
            for candidate in target['candidates']:
                source_party = party_map.get((source_year, target_year, candidate['partyKey']))
                prior = [row for row in source_candidates if row['partyKey'] == source_party] if source_party else []
                exact = [row for row in prior if row['name'] == candidate['name']]
                if len(exact) == 1 and len(prior) == 1:
                    identity = 'probable_exact_name_party_seat_chain'
                elif prior:
                    identity = 'unresolved_same_party_predecessor'
                else:
                    identity = 'no_same_party_source_candidacy'
                reasons = []
                if (source_year, target_year) not in UNCHANGED:
                    reasons.append('changed_boundary_transition')
                if target['kind'] != 'general':
                    reasons.append('maori_local_split_unavailable_or_sparse')
                if not source or not matrix:
                    reasons.append('missing_comparable_source_seat_or_local_matrix')
                if matrix and matrix.get('behaviouralEvidence') is False:
                    reasons.append('cancelled_source_contest')
                if target.get('candidateContestStatus', 'held') != 'held':
                    reasons.append('cancelled_target_contest')
                if not source_party:
                    reasons.append('no_supported_cross_election_party_continuity')
                if source_party and source_party not in {p['partyKey'] for p in source_candidates}:
                    reasons.append('source_candidate_party_absent')
                missing_rows = sorted(
                    party for party in target_rows
                    if (party if party == 'informalpartyvotes' else
                        party_map.get((source_year, target_year, party))) not in source_rows)
                partial_reasons = list(reasons)
                if missing_rows:
                    reasons.append('target_party_group_absent_in_source_local_split')
                records.append({
                    'targetOccurrenceId': candidate['id'], 'targetYear': target_year,
                    'sourceYear': source_year, 'electorateName': target['name'],
                    'electorateType': target['kind'], 'targetPartyKey': candidate['partyKey'],
                    'sourcePartyKey': source_party,
                    'sourceCandidateIds': [row['id'] for row in prior],
                    'candidateMapping': identity, 'sourceMatrixId': matrix['id'] if matrix else None,
                    'targetPartyGroupCount': len(target_rows), 'missingSourcePartyGroups': missing_rows,
                    'geography': 'same_verified_boundary_regime' if (source_year, target_year) in UNCHANGED and source else 'not_comparable',
                    'conditionalPartialApplicability': not partial_reasons,
                    'conditionalLocalApplicability': not reasons,
                    'exclusionReasons': reasons})
    records.sort(key=lambda row: row['targetOccurrenceId'])
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
                                                  for reason in row['exclusionReasons']).items()))}
