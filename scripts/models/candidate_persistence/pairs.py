"""Construct auditable adjacent-election persistence pairs."""

from collections import Counter, defaultdict


ADJACENT = {2008: 2011, 2011: 2014, 2014: 2017, 2017: 2020, 2020: 2023}
PRIMARY = {(2008, 2011), (2014, 2017), (2020, 2023)}


def _reasons(source, target):
    reasons = []
    if (source['year'], target['year']) not in PRIMARY:
        reasons.append('changed_boundary_transition')
    if source['boundaryRegime'] != target['boundaryRegime']:
        reasons.append('different_boundary_regime')
    if source['electorateName'] != target['electorateName'] or source['electorateType'] != target['electorateType']:
        reasons.append('different_electorate_or_scope')
    if source['candidateContestStatus'] != 'held' or target['candidateContestStatus'] != 'held':
        reasons.append('cancelled_contest')
    if not source['eligible'] or not target['eligible']:
        reasons.append('missing_exact_party_counterpart')
    if source['normalizedPremium'] is None or target['normalizedPremium'] is None:
        reasons.append('missing_normalized_premium')
    return reasons


def _anchor_roles(source, target, source_link, target_link, rows):
    anchor_ids = set(source_link['evidence'].get('winnerOccurrenceIds', []))
    anchor_ids.update(target_link['evidence'].get('winnerOccurrenceIds', []))
    dates = {anchor['candidateOccurrenceId']: anchor.get('electionDate')
             for link in (source_link, target_link)
             for anchor in link['evidence'].get('anchorOccurrences', [])}
    result = []
    for candidate_id in sorted(anchor_ids):
        year = rows[candidate_id]['year']
        role = ('source' if candidate_id == source['candidateOccurrenceId'] else
                'target' if candidate_id == target['candidateOccurrenceId'] else
                'earlier' if year < source['year'] else
                'later' if year > target['year'] else 'other')
        result.append({'candidateOccurrenceId': candidate_id, 'year': year,
                       'electionDate': dates.get(candidate_id), 'role': role})
    return result


def build_pairs(occurrences, links):
    """Return all adjacent linked histories, with explicit primary exclusions."""
    rows = {row['candidateOccurrenceId']: row for row in occurrences}
    if len(rows) != len(occurrences):
        raise ValueError('Duplicate occurrence ID')
    by_person = defaultdict(dict)
    for link in links:
        candidate_id = link['candidateOccurrenceId']
        if candidate_id not in rows:
            raise ValueError(f'Dangling identity link: {candidate_id}')
        row = rows[candidate_id]
        if row['year'] in by_person[link['personId']]:
            raise ValueError('Person has two occurrences in one election')
        by_person[link['personId']][row['year']] = (row, link)
    pairs = []
    for person_id, by_year in sorted(by_person.items()):
        for year, later in ADJACENT.items():
            if year not in by_year or later not in by_year:
                continue
            source, source_link = by_year[year]
            target, target_link = by_year[later]
            base_reasons = _reasons(source, target)
            same_chain = (source['sourceCandidateName'] == target['sourceCandidateName'] and
                          source['candidateAffiliationKey'] == target['candidateAffiliationKey'] and
                          source['electorateName'] == target['electorateName'] and
                          source['electorateType'] == target['electorateType'])
            source_direct = (source_link['status'] == 'confirmed' and
                             source_link['evidence'].get('directOccurrenceEvidence') is True)
            target_direct = (target_link['status'] == 'confirmed' and
                             target_link['evidence'].get('directOccurrenceEvidence') is True)
            validation_reasons = base_reasons.copy()
            if not source_direct:
                validation_reasons.append('source_occurrence_not_directly_corroborated')
            if not same_chain:
                validation_reasons.append('target_not_in_exact_source_chain')
            retrospective_reasons = base_reasons.copy()
            if not source_direct or not target_direct:
                retrospective_reasons.append('identity_not_confirmed_at_both_occurrences')
            anchor_roles = _anchor_roles(source, target, source_link, target_link, rows)
            pair = {
                'pairId': source['candidateOccurrenceId'] + '->' + target['candidateOccurrenceId'],
                'personId': person_id,
                'sourceOccurrenceId': source['candidateOccurrenceId'],
                'targetOccurrenceId': target['candidateOccurrenceId'],
                'sourceYear': year, 'targetYear': later,
                'electorateType': target['electorateType'],
                'sourceElectorate': source['electorateName'],
                'targetElectorate': target['electorateName'],
                'sourceBoundaryRegime': source['boundaryRegime'],
                'targetBoundaryRegime': target['boundaryRegime'],
                'sourcePartyKey': source['partyKey'],
                'targetPartyKey': target['partyKey'],
                'sourceIdentityStatus': source_link['status'],
                'targetIdentityStatus': target_link['status'],
                'sourceIdentityMethod': source_link['method'],
                'targetIdentityMethod': target_link['method'],
                'sourceIdentityEvidence': source_link['evidence'],
                'targetIdentityEvidence': target_link['evidence'],
                'anchorOutcomeRoles': anchor_roles,
                'outcomeDependencies': {
                    'identityAdjudication': {
                        'sourceElection': any(anchor['role'] == 'source' for anchor in anchor_roles),
                        'targetElection': any(anchor['role'] == 'target' for anchor in anchor_roles),
                        'laterElection': any(anchor['role'] == 'later' for anchor in anchor_roles)},
                    'validation': {'sourceElection': source_direct,
                                   'targetElection': False, 'laterElection': False},
                    'retrospectiveConfirmed': {'sourceElection': source_direct,
                                               'targetElection': target_direct,
                                               'laterElection': False}},
                'validationEligible': not validation_reasons,
                'validationExclusionReasons': validation_reasons,
                'retrospectiveConfirmedEligible': not retrospective_reasons,
                'probableSensitivityEligible': not base_reasons,
                'exclusionReasons': retrospective_reasons,
                'cohortInclusion': {
                    'outcomeIndependentValidation': {'included': not validation_reasons,
                                                     'exclusionReasons': validation_reasons},
                    'retrospectiveConfirmed': {'included': not retrospective_reasons,
                                               'exclusionReasons': retrospective_reasons},
                    'allComparableLinked': {'included': not base_reasons,
                                            'exclusionReasons': base_reasons}},
                'priorResidual': source['normalizedPremium'],
                'targetResidual': target['normalizedPremium'],
                'scaleResiduals': {
                    scale: {'prior': source.get('methods', {}).get(scale, {}).get('residual'),
                            'target': target.get('methods', {}).get(scale, {}).get('residual')}
                    for scale in ('proportional', 'log_odds')},
            }
            pairs.append(pair)
    pairs.sort(key=lambda pair: (pair['targetYear'], pair['pairId']))
    counts = Counter(reason for pair in pairs for reason in pair['exclusionReasons'])
    by_transition = []
    for source_year, target_year in ADJACENT.items():
        subset = [pair for pair in pairs if pair['sourceYear'] == source_year]
        by_transition.append({
            'transition': f'{source_year}->{target_year}',
            'linkedPairs': len(subset),
            'retrospectiveConfirmedGeneral': sum(pair['retrospectiveConfirmedEligible'] and pair['electorateType'] == 'general' for pair in subset),
            'retrospectiveConfirmedMaori': sum(pair['retrospectiveConfirmedEligible'] and pair['electorateType'] == 'maori' for pair in subset),
            'validationGeneral': sum(pair['validationEligible'] and pair['electorateType'] == 'general' for pair in subset),
            'validationMaori': sum(pair['validationEligible'] and pair['electorateType'] == 'maori' for pair in subset),
            'probableOrConfirmedComparable': sum(pair['probableSensitivityEligible'] for pair in subset),
        })
    return {'pairs': pairs, 'diagnostics': {'linkedAdjacentPairs': len(pairs),
            'retrospectiveConfirmedPairs': sum(pair['retrospectiveConfirmedEligible'] for pair in pairs),
            'outcomeIndependentValidationPairs': sum(pair['validationEligible'] for pair in pairs),
            'probableOrConfirmedComparablePairs': sum(pair['probableSensitivityEligible'] for pair in pairs),
            'exclusionReasons': dict(sorted(counts.items())), 'byTransition': by_transition}}
