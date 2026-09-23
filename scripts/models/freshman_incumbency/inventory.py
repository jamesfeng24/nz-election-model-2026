"""Build pre-fit, outcome-independent tenure classifications for linked recontesters."""

from collections import Counter
from datetime import datetime, timedelta
import unicodedata

from scripts.models.candidate_persistence.official import ELECTION_DATES
from scripts.transform.historical import key


def _fold(value):
    plain = unicodedata.normalize('NFKD', value.casefold())
    return ''.join(char for char in plain if not unicodedata.combining(char))


def _source_date(year):
    return datetime.strptime(ELECTION_DATES[year], '%d %B %Y').date().isoformat()


def _surname(name):
    return _fold(name.split(',', 1)[0].strip()) if ',' in name else None


def _at_date(row, date):
    return row['startDate'] <= date and (row['endDate'] is None or row['endDate'] >= date)


def _interrupted_electorate_history(rows, through_date):
    prior = sorted((r for r in rows if r['startDate'] <= through_date),
                   key=lambda r: r['startDate'])
    if len(prior) < 2:
        return False
    latest_end = prior[0]['endDate']
    for row in prior[1:]:
        if latest_end and datetime.fromisoformat(row['startDate']).date() > (
                datetime.fromisoformat(latest_end).date() + timedelta(days=1)):
            return True
        if latest_end is None or row['endDate'] is None:
            latest_end = None
        else:
            latest_end = max(latest_end, row['endDate'])
    return False


def find_profile(source, profiles):
    """Require a unique same-surname, seat/date service match to an elected occurrence."""
    date = _source_date(source['year'])
    candidates = []
    for profile in profiles:
        if _surname(profile['displayName'] or '') != _surname(source['sourceCandidateName']):
            continue
        rows = [row for row in profile['serviceRows'] if row['serviceKind'] == 'electorate'
                and _fold(row['electorateName']) == _fold(source['electorateName'])
                and _at_date(row, date)]
        if rows:
            candidates.append((profile, rows))
    return candidates


def classify_tenure(source, target_year, profile):
    """Classify at target candidacy using source win and service facts, never target result."""
    if profile['tenureEvidenceStatus'] != 'complete_dated_table':
        return 'uncertain', 'incomplete_tenure_table', None
    source_date, target_date = _source_date(source['year']), _source_date(target_year)
    rows = profile['serviceRows']
    if not rows or profile['firstParliamentElectedDate'] != min(r['startDate'] for r in rows):
        return 'uncertain', 'career_start_not_reconciled', None
    electorate = sorted((r for r in rows if r['serviceKind'] == 'electorate'),
                        key=lambda r: r['startDate'])
    source_rows = [r for r in electorate if _fold(r['electorateName']) == _fold(source['electorateName'])
                   and _at_date(r, source_date)]
    if len(source_rows) != 1:
        return 'uncertain', 'source_service_not_unique', None
    source_row = source_rows[0]
    # Ending on election day is compatible with an incumbent who loses that election.
    if source_row['endDate'] is not None and source_row['endDate'] < target_date:
        return 'excluded', 'service_interrupted_before_target', source_row
    if source_row['startDate'] == source_date and electorate[0] == source_row:
        return 'first_term', 'first_ever_electorate_win_at_source_general_election', source_row
    if source_row['startDate'] == source_date and electorate[0] != source_row:
        prior = [r for r in electorate if r != source_row and r['startDate'] < source_date]
        latest_end = max((r['endDate'] for r in prior if r['endDate'] is not None), default=None)
        if latest_end and datetime.fromisoformat(latest_end).date() >= (
                datetime.fromisoformat(source_date).date() - timedelta(days=1)):
            return 'excluded', 'continuing_incumbent_seat_switch', source_row
        return 'excluded', 'returning_former_electorate_mp', source_row
    if source_row['startDate'] < source_date:
        if _interrupted_electorate_history(electorate, source_date):
            return 'excluded', 'returning_former_electorate_mp', source_row
        if (source_row['startDate'] > _source_date(2008) and
                source_row['startDate'] not in {_source_date(y) for y in ELECTION_DATES}):
            return 'experienced', 'off_cycle_electorate_entry', source_row
        if source_row['startDate'] < _source_date(2008):
            return 'experienced', 'documented_pre_panel_electorate_service', source_row
        return 'experienced', 'prior_continuing_electorate_service', source_row
    return 'uncertain', 'unclassified_service_sequence', source_row


def build_inventory(pairs, occurrences, profiles, elected_ids):
    """Inventory comparable linked recontesters and explicit exclusions before fitting."""
    by_id = {row['candidateOccurrenceId']: row for row in occurrences}
    if len(by_id) != len(occurrences):
        raise ValueError('Duplicate candidate occurrence')
    result = []
    for pair in pairs:
        source_id, target_id = pair['sourceOccurrenceId'], pair['targetOccurrenceId']
        if source_id not in by_id or target_id not in by_id:
            raise ValueError(f'Dangling pair occurrence: {pair["pairId"]}')
        source = by_id[source_id]
        reasons = []
        if not pair['probableSensitivityEligible']:
            reasons.append('not_comparable_stage8_pair')
        if source_id not in elected_ids:
            reasons.append('source_candidate_not_elected')
        matches = find_profile(source, profiles) if source_id in elected_ids else []
        if len(matches) != 1:
            reasons.append('no_unique_dated_source_service' if not matches else 'ambiguous_source_service')
        profile = matches[0][0] if len(matches) == 1 else None
        status, reason, source_row = (classify_tenure(source, pair['targetYear'], profile)
                                      if profile else ('uncertain', 'source_tenure_unresolved', None))
        if status not in ('first_term', 'experienced'):
            reasons.append(reason)
        # Exact-chain Stage 8 pairing may be probable at the target. Retain that uncertainty.
        if pair['sourceIdentityStatus'] == 'unresolved' or pair['targetIdentityStatus'] == 'unresolved':
            reasons.append('unresolved_occurrence_identity')
        source_date = _source_date(pair['sourceYear'])
        prior_list = (any(r['serviceKind'] == 'list' and r['startDate'] < source_date
                          for r in profile['serviceRows']) if profile else None)
        if status == 'first_term' and prior_list:
            reasons.append('prior_list_service_primary_exclusion')
        if reason == 'off_cycle_electorate_entry':
            reasons.append('off_cycle_entrant_primary_exclusion')
        if profile and source_row and key(source_row['party']) != source['candidateAffiliationKey']:
            # Party labels can differ across sources; record rather than silently normalize.
            party_match = False
        else:
            party_match = bool(profile)
        result.append({
            'pairId': pair['pairId'], 'personId': pair['personId'],
            'sourceOccurrenceId': source_id, 'targetOccurrenceId': target_id,
            'sourceYear': pair['sourceYear'], 'targetYear': pair['targetYear'],
            'electorateType': pair['electorateType'], 'electorateName': pair['sourceElectorate'],
            'sourceIdentityStatus': pair['sourceIdentityStatus'],
            'targetIdentityStatus': pair['targetIdentityStatus'],
            'sourceWasElected': source_id in elected_ids,
            'tenureCategory': status, 'tenureReason': reason,
            'sourceProfileId': profile['sourceId'] if profile else None,
            'sourceProfileUrl': profile['sourceUrl'] if profile else None,
            'profilePublishedDate': profile['publishedDate'] if profile else None,
            'profileRetrievedAt': profile['retrievedAt'] if profile else None,
            'tenureEvidenceStatus': profile['tenureEvidenceStatus'] if profile else 'unresolved',
            'firstParliamentElectedDate': profile['firstParliamentElectedDate'] if profile else None,
            'serviceRows': profile['serviceRows'] if profile else [],
            'sourceServiceStartDate': source_row['startDate'] if source_row else None,
            'sourceServiceEndDate': source_row['endDate'] if source_row else None,
            'priorListService': prior_list,
            'partyLabelAgrees': party_match,
            'primaryEligible': not reasons,
            'exclusionReasons': sorted(set(reasons)),
        })
    result.sort(key=lambda row: (row['targetYear'], row['pairId']))
    counts = Counter((row['sourceYear'], row['targetYear'], row['electorateType'], row['tenureCategory'])
                     for row in result if row['sourceWasElected'] and
                     'not_comparable_stage8_pair' not in row['exclusionReasons'])
    eligible = Counter((row['sourceYear'], row['targetYear'], row['electorateType'], row['tenureCategory'])
                       for row in result if row['primaryEligible'])
    return {'schemaVersion': 1, 'records': result,
            'counts': [{'sourceYear': a, 'targetYear': b, 'electorateType': c, 'tenureCategory': d,
                        'sourceWinnerComparable': n, 'primaryEligible': eligible[(a, b, c, d)]}
                       for (a, b, c, d), n in sorted(counts.items())],
            'interpretation': 'Retrospective source-winner and known-target-candidacy inventory. No target winner flag or target residual participates in classification.'}
