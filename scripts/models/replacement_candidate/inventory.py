"""Inventory party-seat transitions without using target election outcomes."""

from collections import Counter, defaultdict

from scripts.models.freshman_incumbency.inventory import find_profile


ADJACENT = {2008: 2011, 2011: 2014, 2014: 2017, 2017: 2020, 2020: 2023}
UNCHANGED = {(2008, 2011), (2014, 2017), (2020, 2023)}


def _anchors(link, before_year):
    if not link or link.get('personExistenceStatus') != 'official_profile_corroborated':
        return []
    return sorted(anchor['candidateOccurrenceId'] for anchor in
                  link['evidence'].get('anchorOccurrences', [])
                  if anchor.get('electionDate') and
                  int(anchor['electionDate'][-4:]) < before_year)


def _identity(source, target, source_link, target_link):
    source_anchors = _anchors(source_link, target['year'])
    target_anchors = _anchors(target_link, target['year'])
    same_chain = (source['sourceCandidateName'] == target['sourceCandidateName'] and
                  source['candidateAffiliationKey'] == target['candidateAffiliationKey'] and
                  source['electorateName'] == target['electorateName'])
    same_person = (source_link and target_link and
                   source_link['personId'] == target_link['personId'])
    if same_person and same_chain and source_anchors:
        return 'supported_continuation', 'source_anchored_exact_chain', source_anchors, target_anchors
    if source_link and target_link and source_link['personId'] != target_link['personId']:
        if source_anchors and target_anchors:
            return 'supported_replacement', 'distinct_pre_target_official_people', source_anchors, target_anchors
        if source_link['personExistenceStatus'] == target_link['personExistenceStatus'] == 'official_profile_corroborated':
            return 'retrospective_distinct_people', 'distinct_official_people_target_or_later_anchor', source_anchors, target_anchors
    if same_person:
        return 'retrospective_or_ambiguous_continuation', 'same_person_link_without_source_anchored_exact_chain', source_anchors, target_anchors
    return 'unresolved_identity', 'name_contrast_alone_insufficient', source_anchors, target_anchors


def _indexed(occurrences):
    indexed = defaultdict(list)
    for row in occurrences:
        indexed[(row['year'], row['electorateType'], row['electorateName'], row['partyKey'])].append(row)
    return indexed


def _profile_for_anchors(anchor_ids, by_id, elected_ids, profiles):
    matches = {}
    for candidate_id in anchor_ids:
        if candidate_id not in elected_ids:
            continue
        for profile, _ in find_profile(by_id[candidate_id], profiles):
            matches[profile['sourceId']] = profile
    return next(iter(matches.values())) if len(matches) == 1 else None


def _prior_service(profile, target_year):
    if profile is None or profile['tenureEvidenceStatus'] != 'complete_dated_table':
        return {'status': 'unknown', 'priorElectorate': None, 'priorList': None}
    from scripts.models.freshman_incumbency.inventory import _source_date
    date = _source_date(target_year)
    return {'status': 'dated_profile',
            'priorElectorate': any(row['serviceKind'] == 'electorate' and row['startDate'] < date
                                    for row in profile['serviceRows']),
            'priorList': any(row['serviceKind'] == 'list' and row['startDate'] < date
                             for row in profile['serviceRows'])}


def build_inventory(occurrences, links, continuity, elected_ids, profiles=()):
    """Pair all observed same-party seats; retain unresolved and excluded records."""
    by_seat = _indexed(occurrences)
    by_link = {row['candidateOccurrenceId']: row for row in links}
    if len(by_link) != len(links):
        raise ValueError('Duplicate occurrence identity link')
    by_id = {row['candidateOccurrenceId']: row for row in occurrences}
    if len(by_id) != len(occurrences) or not set(by_link) <= set(by_id):
        raise ValueError('Duplicate occurrence or dangling identity link')
    parties = defaultdict(list)
    for row in continuity:
        parties[(row['sourceYear'], row['targetYear'])].append(row)
    records = []
    for source_year, target_year in ADJACENT.items():
        for party in parties[source_year, target_year]:
            if party['status'] != 'eligible':
                continue
            source_key = party['source']['sourceKey']
            target_key = party['target']['sourceKey']
            for (year, scope, seat, key), source_rows in sorted(
                    by_seat.items(), key=lambda item: tuple(str(value) for value in item[0])):
                if year != source_year or key != source_key:
                    continue
                target_rows = by_seat.get((target_year, scope, seat, target_key), [])
                if not target_rows:
                    continue
                reasons = []
                if len(source_rows) != 1 or len(target_rows) != 1:
                    reasons.append('ambiguous_party_seat_candidate_multiplicity')
                if (source_year, target_year) not in UNCHANGED:
                    reasons.append('changed_boundary_transition')
                source, target = source_rows[0], target_rows[0]
                if source['boundaryRegime'] != target['boundaryRegime']:
                    reasons.append('different_boundary_regime')
                if source['candidateContestStatus'] != 'held' or target['candidateContestStatus'] != 'held':
                    reasons.append('cancelled_contest')
                if not source['eligible'] or not target['eligible']:
                    reasons.append('missing_exact_party_counterpart')
                if source['normalizedPremium'] is None or target['normalizedPremium'] is None:
                    reasons.append('missing_normalized_premium')
                source_id, target_id = source['candidateOccurrenceId'], target['candidateOccurrenceId']
                source_link, target_link = by_link.get(source_id), by_link.get(target_id)
                identity, method, source_anchors, target_anchors = _identity(
                    source, target, source_link, target_link)
                source_winner = source_id in elected_ids if scope == 'general' else None
                source_profile = _profile_for_anchors([source_id] if source_winner else [],
                                                      by_id, elected_ids, profiles)
                incoming_profile = _profile_for_anchors(target_anchors, by_id,
                                                        elected_ids, profiles)
                if identity not in ('supported_continuation', 'supported_replacement'):
                    reasons.append('identity_not_pre_target_supported')
                if source_winner is None:
                    reasons.append('maori_winner_status_unavailable')
                elif not source_winner:
                    reasons.append('outgoing_challenger_separate_diagnostic')
                records.append({
                    'eventId': source_id + '->' + target_id,
                    'sourceOccurrenceId': source_id, 'targetOccurrenceId': target_id,
                    'sourceYear': source_year, 'targetYear': target_year,
                    'electorateType': scope, 'electorateName': seat,
                    'partyKey': party['canonicalPartyId'],
                    'sourceName': source['sourceCandidateName'],
                    'targetName': target['sourceCandidateName'],
                    'nameContrast': source['sourceCandidateName'] != target['sourceCandidateName'],
                    'sourceWasElected': source_winner,
                    'outgoingStatus': ('source_winner' if source_winner else
                                       'source_challenger' if source_winner is False else
                                       'source_winner_unknown'),
                    'departureReason': 'unknown',
                    'sourceProfileId': source_profile['sourceId'] if source_profile else None,
                    'sourceCareerHistory': _prior_service(source_profile, source_year),
                    'incomingProfileId': incoming_profile['sourceId'] if incoming_profile else None,
                    'incomingCareerHistory': _prior_service(incoming_profile, target_year),
                    'sourceIdentityStatus': source_link['status'] if source_link else 'unresolved',
                    'targetIdentityStatus': target_link['status'] if target_link else 'unresolved',
                    'sourcePersonId': source_link['personId'] if source_link else None,
                    'targetPersonId': target_link['personId'] if target_link else None,
                    'sourceIdentityEvidence': source_link['evidence'] if source_link else None,
                    'targetIdentityEvidence': target_link['evidence'] if target_link else None,
                    'sourcePreTargetAnchors': source_anchors,
                    'targetPreTargetAnchors': target_anchors,
                    'identityClass': identity, 'identityMethod': method,
                    'sourceBoundaryRegime': source['boundaryRegime'],
                    'targetBoundaryRegime': target['boundaryRegime'],
                    'primaryEligible': not reasons,
                    'exclusionReasons': sorted(set(reasons)),
                    'priorResidual': source['normalizedPremium'],
                    'targetResidual': target['normalizedPremium'],
                    'scaleResiduals': {scale: {
                        'prior': source.get('methods', {}).get(scale, {}).get('residual'),
                        'target': target.get('methods', {}).get(scale, {}).get('residual')}
                        for scale in ('proportional', 'log_odds')},
                })
    records.sort(key=lambda row: (row['targetYear'], row['eventId']))
    counts = Counter((row['sourceYear'], row['targetYear'], row['electorateType'],
                      row['outgoingStatus'], row['identityClass']) for row in records)
    return {'schemaVersion': 1, 'records': records,
            'counts': [{'sourceYear': s, 'targetYear': t, 'electorateType': scope,
                        'outgoingStatus': status, 'identityClass': identity, 'count': count}
                       for (s, t, scope, status, identity), count in sorted(counts.items())],
            'primaryEligible': sum(row['primaryEligible'] for row in records),
            'interpretation': 'All same-party party-seat candidate comparisons under Stage 5 continuity. Pre-target identity evidence is separate from retrospective links. Unknown departure and incoming careers remain unknown; target results are never used for identity or eligibility.'}
