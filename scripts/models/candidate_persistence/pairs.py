"""Construct auditable adjacent-election persistence pairs."""

from collections import Counter, defaultdict


ADJACENT = {2008: 2011, 2011: 2014, 2014: 2017, 2017: 2020, 2020: 2023}
PRIMARY = {(2008, 2011), (2014, 2017), (2020, 2023)}


def _reasons(source, target, source_link, target_link):
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
    if source_link['status'] != 'confirmed' or target_link['status'] != 'confirmed':
        reasons.append('identity_not_confirmed')
    return reasons


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
            reasons = _reasons(source, target, source_link, target_link)
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
                'primaryEligible': not reasons,
                'probableSensitivityEligible': not [r for r in reasons if r != 'identity_not_confirmed'],
                'exclusionReasons': reasons,
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
            'primaryGeneral': sum(pair['primaryEligible'] and pair['electorateType'] == 'general' for pair in subset),
            'primaryMaori': sum(pair['primaryEligible'] and pair['electorateType'] == 'maori' for pair in subset),
            'probableOrConfirmedComparable': sum(pair['probableSensitivityEligible'] for pair in subset),
        })
    return {'pairs': pairs, 'diagnostics': {'linkedAdjacentPairs': len(pairs),
            'primaryPairs': sum(pair['primaryEligible'] for pair in pairs),
            'probableOrConfirmedComparablePairs': sum(pair['probableSensitivityEligible'] for pair in pairs),
            'exclusionReasons': dict(sorted(counts.items())), 'byTransition': by_transition}}
