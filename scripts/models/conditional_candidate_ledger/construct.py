"""Construct outcome-independent conditional candidate ballot ledgers."""

from collections import Counter

from scripts.models.conditional_candidate_ledger.geometry import (
    BALLOT_TOL, LedgerGeometryError, linear_bounds, share_bounds)
from scripts.models.conditional_candidate_ledger.pool import (
    DISALLOWED_DESTINATION, INFORMAL_DESTINATION, INFORMAL_ORIGIN,
    NONCANDIDATE_DESTINATIONS, PARTY_ONLY_DESTINATION)


METHODS = ('primary', 'heterogeneity', 'party_diagonal', 'unrestricted')


def continuity_maps(records, source_year, target_year):
    source_to_target = {}
    target_to_source = {}
    for row in records:
        if ((row['sourceYear'], row['targetYear']) != (source_year, target_year)
                or row['status'] != 'eligible'):
            continue
        source = row['source']['sourceKey']
        target = row['target']['sourceKey']
        if source in source_to_target or target in target_to_source:
            raise LedgerGeometryError('Ambiguous eligible party continuity')
        source_to_target[source] = target
        target_to_source[target] = source
    return source_to_target, target_to_source


def target_inputs(seat):
    """Only permitted party/turnout and candidature fields are read here."""
    ballot = seat['partyBallot']
    parties = seat['parties']
    candidates = seat['candidates']
    if (len({party['partyKey'] for party in parties}) != len(parties) or
            len({candidate['id'] for candidate in candidates}) != len(candidates)):
        raise LedgerGeometryError('Duplicate target party or candidate')
    valid = sum(party['votes'] for party in parties)
    disallowed = ballot['ordinaryDisallowed'] + ballot['specialDisallowed']
    if (valid != ballot['validVotes'] or min(valid, ballot['informalVotes'],
                                            disallowed) < 0 or
            valid + ballot['informalVotes'] + disallowed != ballot['votesCast']):
        raise LedgerGeometryError('Incompatible target party ballot population')
    candidate_ids = [candidate['id'] for candidate in candidates]
    destinations = candidate_ids + list(NONCANDIDATE_DESTINATIONS)
    if len(destinations) != len(set(destinations)):
        raise LedgerGeometryError('Candidate/noncandidate destination collision')
    groups = [{'id': party['partyKey'], 'kind': 'valid_party', 'mass': party['votes']}
              for party in sorted(parties, key=lambda item: item['partyKey'])]
    groups.extend(({'id': INFORMAL_ORIGIN, 'kind': 'informal_party',
                    'mass': ballot['informalVotes']},
                   {'id': 'party_disallowed_unrepresented', 'kind': 'party_disallowed',
                    'mass': disallowed}))
    return {'candidateIds': candidate_ids, 'destinations': destinations,
            'candidateParties': {candidate['id']: candidate['partyKey']
                                 for candidate in candidates},
            'groups': groups, 'votesCast': ballot['votesCast']}


def _candidate_by_party(candidate_parties):
    grouped = {}
    for candidate_id, party in candidate_parties.items():
        grouped.setdefault(party, []).append(candidate_id)
    return grouped


def _pooled_origin(group, pool, candidate_parties, source_to_target,
                   target_to_source, method):
    target_origin = group['id']
    source_origin = (INFORMAL_ORIGIN if target_origin == INFORMAL_ORIGIN else
                     target_to_source.get(target_origin))
    if group['kind'] == 'party_disallowed':
        return {'mass': group['mass'], 'routing': 'free',
                'reason': 'disallowed_party_origin', 'group': group}
    if source_origin is None:
        return {'mass': group['mass'], 'routing': 'free',
                'reason': 'unmapped_party_origin', 'group': group}
    source_pool = pool['pools'].get(source_origin)
    if source_pool is None:
        return {'mass': group['mass'], 'routing': 'free',
                'reason': 'no_positive_complete_source_rows', 'group': group}
    by_party = _candidate_by_party(candidate_parties)
    support = set(source_pool['supportedDestinations'])
    for party, ids in by_party.items():
        source_party = target_to_source.get(party)
        if party == 'independent' or len(ids) != 1 or source_party is None or (
                f'party:{source_party}' not in support):
            return {'mass': group['mass'], 'routing': 'free',
                    'reason': 'unsupported_or_ambiguous_target_destination',
                    'group': group, 'sourcePoolId': source_pool['id']}
    mapped = {INFORMAL_DESTINATION: INFORMAL_DESTINATION,
              PARTY_ONLY_DESTINATION: PARTY_ONLY_DESTINATION}
    for source_category in sorted(support):
        source_party = source_category.removeprefix('party:')
        target_party = source_to_target.get(source_party)
        if target_party and len(by_party.get(target_party, [])) == 1:
            mapped[source_category] = by_party[target_party][0]
    return {'mass': group['mass'], 'routing': method,
            'reason': 'source_pool_transport', 'group': group,
            'sourcePoolId': source_pool['id'], 'pool': source_pool,
            'sourceCategoryDestinations': mapped}


def build_origins(inputs, pool, continuity, source_year, target_year, method):
    source_to_target, target_to_source = continuity_maps(
        continuity, source_year, target_year)
    by_party = _candidate_by_party(inputs['candidateParties'])
    origins = []
    for group in inputs['groups']:
        if method in ('primary', 'heterogeneity'):
            origin = _pooled_origin(group, pool, inputs['candidateParties'],
                                    source_to_target, target_to_source, method)
        elif method == 'party_diagonal' and group['kind'] == 'valid_party' and len(
                by_party.get(group['id'], [])) == 1:
            origin = {'mass': group['mass'], 'routing': 'diagonal',
                      'destination': by_party[group['id']][0],
                      'reason': 'same_party_diagonal', 'group': group}
        else:
            reason = ('unrestricted_comparator' if method == 'unrestricted' else
                      'no_unique_same_party_candidate')
            origin = {'mass': group['mass'], 'routing': 'free',
                      'reason': reason, 'group': group}
        origins.append(origin)
    if sum(item['mass'] for item in origins) != inputs['votesCast']:
        raise LedgerGeometryError('Target origins do not conserve votes cast')
    return origins


def method_bounds(inputs, origins):
    candidates = inputs['candidateIds']
    destinations = inputs['destinations']
    denominator = linear_bounds(origins, {
        destination: float(destination in candidates) for destination in destinations})
    if denominator[1] > inputs['votesCast'] + BALLOT_TOL:
        raise LedgerGeometryError('Candidate denominator exceeds cast ballots')
    bounds = []
    for candidate_id in candidates:
        votes = linear_bounds(origins, {destination: float(destination == candidate_id)
                                        for destination in destinations})
        share = share_bounds(origins, candidate_id, destinations, candidates, denominator)
        bounds.append({'candidateOccurrenceId': candidate_id,
                       'candidateVotes': votes, 'candidateShare': share,
                       'pointCandidateVotes': (votes[0]
                                               if abs(votes[1] - votes[0]) <= 1e-8 else None),
                       'pointAbstentionReason': (None if abs(votes[1] - votes[0]) <= 1e-8
                                                  else 'nondegenerate_joint_feasible_range')})
    metadata = [{key: value for key, value in origin.items()
                 if key not in ('pool', 'sourceCategoryDestinations')}
                | {'mappedSourceCategories': origin.get('sourceCategoryDestinations', {})}
                for origin in origins]
    fully_free = [item for item in origins if item['routing'] == 'free' and item['mass'] > 0]
    return {'status': 'constructed', 'validCandidateDenominator': denominator,
            'candidates': bounds, 'origins': metadata,
            'fullyFreeOriginCount': len(fully_free),
            'fullyFreeOriginMass': sum(item['mass'] for item in fully_free),
            'allPositiveOriginsFree': len(fully_free) == sum(item['mass'] > 0 for item in origins),
            'pointAbstentionCount': sum(row['pointCandidateVotes'] is None for row in bounds)}


def construct(frame, elections, source_pools, continuity):
    targets = {year: {seat['id']: seat for seat in election['electorates']}
               for year, election in elections.items()}
    records = []
    for frame_row in frame:
        source_year, target_year = frame_row['sourceYear'], frame_row['targetYear']
        basic = {'sourceYear': source_year, 'targetYear': target_year,
                 'scope': frame_row['scope'], 'contestStatus': frame_row['contestStatus'],
                 'sourceElectorateId': frame_row['sourceElectorateId'],
                 'targetElectorateId': frame_row['targetElectorateId'],
                 'candidateOccurrenceIds': frame_row['targetOccurrenceIds'],
                 'inputMode': 'conditional_observed_party_retrospective_candidature'}
        if not frame_row['conditionalObservedInputEligible']:
            reason = ('cancelled_or_unheld' if frame_row['contestStatus'] != 'held_both'
                      else 'maori_comparable_local_source_and_party_inputs_unavailable')
            records.append(basic | {'status': 'coverage_only', 'reason': reason})
            continue
        seat = targets[target_year].get(frame_row['targetElectorateId'])
        if seat is None:
            raise LedgerGeometryError('Missing eligible target contest')
        inputs = target_inputs(seat)
        if set(inputs['candidateIds']) != set(frame_row['targetOccurrenceIds']):
            raise LedgerGeometryError('Changed fixed target candidature')
        methods = {}
        for method in METHODS:
            origins = build_origins(inputs, source_pools[source_year], continuity,
                                    source_year, target_year, method)
            methods[method] = method_bounds(inputs, origins)
        records.append(basic | {'status': 'constructed', 'votesCast': inputs['votesCast'],
                                'candidateParties': inputs['candidateParties'],
                                'destinations': inputs['destinations'],
                                'methods': methods})
    if len(records) != 213 or sum(row['status'] == 'constructed' for row in records) != 191:
        raise LedgerGeometryError('Changed conditional contest frame')
    summary = {'frameContests': len(records), 'constructedContests': 191,
               'coverageOnly': dict(sorted(Counter(row['reason'] for row in records
                                                   if row['status'] == 'coverage_only').items())),
               'allPositiveOriginsFreeByMethod': {method: sum(
                   row['methods'][method]['allPositiveOriginsFree'] for row in records
                   if row['status'] == 'constructed') for method in METHODS}}
    return {'schemaVersion': 1, 'stage': 15,
            'mode': 'conditional_observed_party_not_pre_election_forecast',
            'outcomeFieldsUsed': [], 'records': records, 'summary': summary,
            'selectedOperationalCandidateLedger': None}
