"""Evaluate saved conditional ledgers against separate observed candidate results."""

from collections import Counter, defaultdict
from statistics import mean, median

from scripts.models.conditional_candidate_ledger.construct import METHODS
from scripts.models.conditional_candidate_ledger.feasibility import joint_feasibility
from scripts.models.conditional_candidate_ledger.geometry import BALLOT_TOL


def observed_results(ledgers, elections):
    """Read outcome fields only after construction is frozen on disk."""
    seats = {year: {seat['id']: seat for seat in election['electorates']}
             for year, election in elections.items()}
    records = []
    for ledger in ledgers['records']:
        if ledger['status'] != 'constructed':
            continue
        seat = seats[ledger['targetYear']][ledger['targetElectorateId']]
        candidates = seat['candidates']
        valid = seat['validCandidateVotes']
        if (valid <= 0 or valid != seat['candidateBallot']['validVotes'] or
                sum(candidate['votes'] for candidate in candidates) != valid or
                {candidate['id'] for candidate in candidates} !=
                set(ledger['candidateOccurrenceIds'])):
            raise ValueError('Published candidate outcome cannot be reconciled')
        records.append({'targetElectorateId': ledger['targetElectorateId'],
                        'targetYear': ledger['targetYear'],
                        'actualValidCandidateVotes': valid,
                        'winnerCandidateId': seat['winnerCandidateId'],
                        'candidates': [{'candidateOccurrenceId': candidate['id'],
                                        'actualCandidateVotes': candidate['votes'],
                                        'actualCandidateShare': candidate['votes'] / valid,
                                        'elected': candidate['elected']}
                                       for candidate in candidates]})
    return {'schemaVersion': 1, 'stage': 15, 'role': 'evaluation_only',
            'records': records}


def _candidate_diagnostics(predicted, actual, unrestricted, method_record):
    votes = actual['actualCandidateVotes']
    vote_bounds = predicted['candidateVotes']
    share = predicted['candidateShare']
    share_bounds = share['bounds']
    actual_share = actual['actualCandidateShare']
    return {'candidateOccurrenceId': actual['candidateOccurrenceId'],
            'partyKey': method_record['candidateParties'][actual['candidateOccurrenceId']],
            'elected': actual['elected'],
            'voteWidth': vote_bounds[1] - vote_bounds[0],
            'voteContainsActual': vote_bounds[0] - BALLOT_TOL <= votes <= vote_bounds[1] + BALLOT_TOL,
            'informativeVsUnrestricted': (
                vote_bounds[0] > unrestricted['candidateVotes'][0] + BALLOT_TOL or
                vote_bounds[1] < unrestricted['candidateVotes'][1] - BALLOT_TOL),
            'shareStatus': share['status'],
            'shareWidthPP': (100 * (share_bounds[1] - share_bounds[0])
                             if share_bounds is not None else None),
            'shareContainsActual': (share_bounds[0] - 1e-8 <= actual_share <= share_bounds[1] + 1e-8
                                    if share_bounds is not None else None),
            'pointCandidateVotes': predicted['pointCandidateVotes']}


def evaluate(ledgers, actuals, source_pools, solver=None):
    """Compare all frozen methods on identical contests; never refit routing."""
    by_actual = {row['targetElectorateId']: row for row in actuals['records']}
    pool_index = {pool['id']: pool for year in source_pools['sourceYears'].values()
                  for pool in year['pools'].values()}
    if len(by_actual) != len(actuals['records']):
        raise ValueError('Duplicate actual contest')
    records = []
    for ledger in ledgers['records']:
        if ledger['status'] != 'constructed':
            continue
        actual = by_actual.get(ledger['targetElectorateId'])
        if actual is None:
            raise ValueError('Missing actual contest')
        by_candidate = {row['candidateOccurrenceId']: row for row in actual['candidates']}
        if len(by_candidate) != len(actual['candidates']):
            raise ValueError('Duplicate actual candidate')
        actual_votes = {key: row['actualCandidateVotes'] for key, row in by_candidate.items()}
        methods = {}
        unrestricted = {row['candidateOccurrenceId']: row for row in
                        ledger['methods']['unrestricted']['candidates']}
        for method in METHODS:
            predicted = ledger['methods'][method]
            predictions = {row['candidateOccurrenceId']: row for row in predicted['candidates']}
            if set(predictions) != set(actual_votes):
                raise ValueError('Evaluated candidate set differs from construction')
            joint = (joint_feasibility(predicted, pool_index, actual_votes, solver)
                     if solver is not None else
                     joint_feasibility(predicted, pool_index, actual_votes))
            candidate_rows = [_candidate_diagnostics(predictions[cid], by_candidate[cid],
                                                     unrestricted[cid], ledger)
                              for cid in ledger['candidateOccurrenceIds']]
            denominator = predicted['validCandidateDenominator']
            methods[method] = {
                'jointObservedCandidateVector': joint,
                'denominatorContainsActual': (denominator[0] - BALLOT_TOL <=
                                              actual['actualValidCandidateVotes'] <=
                                              denominator[1] + BALLOT_TOL),
                'candidates': candidate_rows}
        records.append({'targetElectorateId': ledger['targetElectorateId'],
                        'sourceYear': ledger['sourceYear'], 'targetYear': ledger['targetYear'],
                        'scope': ledger['scope'], 'candidateCount': len(actual_votes),
                        'votesCast': ledger['votesCast'],
                        'methods': methods})
    if len(records) != 191:
        raise ValueError('Changed common conditional evaluation frame')
    return {'schemaVersion': 1, 'stage': 15,
            'role': 'evaluation_only_conditional_not_forecast',
            'records': records, 'summary': summarize(records, ledgers),
            'selectedOperationalCandidateLedger': None}


def _method_summary(rows, method):
    contests = [row['methods'][method] for row in rows]
    candidates = [candidate for contest in contests for candidate in contest['candidates']]
    shares = [candidate for candidate in candidates if candidate['shareWidthPP'] is not None]
    point = [candidate for candidate in candidates if candidate['pointCandidateVotes'] is not None]
    joint = Counter(contest['jointObservedCandidateVector']['status'] for contest in contests)
    return {'contestCount': len(contests), 'candidateCount': len(candidates),
            'informativeCandidateCount': sum(row['informativeVsUnrestricted'] for row in candidates),
            'voteContainsActualCount': sum(row['voteContainsActual'] for row in candidates),
            'meanVoteWidth': mean(row['voteWidth'] for row in candidates),
            'medianVoteWidth': median(row['voteWidth'] for row in candidates),
            'definedShareCount': len(shares),
            'undefinedShareCount': len(candidates) - len(shares),
            'shareContainsActualCount': sum(row['shareContainsActual'] for row in shares),
            'meanShareWidthPP': mean(row['shareWidthPP'] for row in shares) if shares else None,
            'medianShareWidthPP': median(row['shareWidthPP'] for row in shares) if shares else None,
            'denominatorContainsActualCount': sum(row['denominatorContainsActual'] for row in contests),
            'jointVectorStatus': dict(sorted(joint.items())),
            'pointCandidateCount': len(point),
            'pointAbstentionCount': len(candidates) - len(point),
            'numericalFailureContests': joint['numerical_or_solver_failure']}


def _common_share_summary(rows):
    common = []
    methods = ('primary', 'heterogeneity', 'party_diagonal')
    for row in rows:
        for index in range(row['candidateCount']):
            candidates = {method: row['methods'][method]['candidates'][index]
                          for method in methods}
            if all(candidate['shareStatus'] == 'defined' for candidate in candidates.values()):
                common.append(candidates)
    return {'candidateCount': len(common),
            'methods': {method: {
                'shareContainsActualCount': sum(item[method]['shareContainsActual']
                                                for item in common),
                'meanShareWidthPP': (mean(item[method]['shareWidthPP'] for item in common)
                                     if common else None)}
                for method in methods}}


def summarize(records, ledgers):
    result = {'frameContests': len(ledgers['records']),
              'evaluatedContests': len(records),
              'coverageOnly': ledgers['summary']['coverageOnly'],
              'coverageByTransitionScopeStatus': dict(sorted(Counter(
                  f"{row['sourceYear']}->{row['targetYear']}:{row['scope']}:{row['status']}"
                  for row in ledgers['records']).items())),
              'conservedConstructedContests': len(records),
              'byHoldout': []}
    construction = {row['targetElectorateId']: row for row in ledgers['records']
                    if row['status'] == 'constructed'}
    for year in (2011, 2017, 2023):
        rows = [row for row in records if row['targetYear'] == year]
        year_summary = {'targetYear': year, 'contests': len(rows),
                        'candidates': sum(row['candidateCount'] for row in rows),
                        'methods': {method: _method_summary(rows, method)
                                    for method in METHODS},
                        'commonDefinedShare': _common_share_summary(rows),
                        'fullyFreePrimaryContests': sum(construction[row['targetElectorateId']]
                                                        ['methods']['primary']['allPositiveOriginsFree']
                                                        for row in rows),
                        'partyCoverageAtLeastFive': []}
        year_summary['partiallyConstrainedPrimaryContests'] = (
            len(rows) - year_summary['fullyFreePrimaryContests'])
        party_rows = defaultdict(list)
        for row in rows:
            for candidate in row['methods']['primary']['candidates']:
                party_rows[candidate['partyKey']].append(candidate)
        for party, candidates in sorted(party_rows.items()):
            if len(candidates) >= 5:
                year_summary['partyCoverageAtLeastFive'].append({
                    'partyKey': party, 'candidateCount': len(candidates),
                    'informativePrimaryCount': sum(row['informativeVsUnrestricted']
                                                   for row in candidates),
                    'primaryVoteContainsActual': sum(row['voteContainsActual']
                                                     for row in candidates)})
        result['byHoldout'].append(year_summary)
    result['commonVoteCandidateCount'] = sum(row['candidateCount'] for row in records)
    result['commonPointCandidateCount'] = sum(all(
        row['methods'][method]['candidates'][index]['pointCandidateVotes'] is not None
        for method in METHODS)
        for row in records for index in range(row['candidateCount']))
    result['pointMetricsOnCommonSample'] = None
    result['reasonNoPointMetrics'] = ('no_common_frozen_point_prediction'
                                      if result['commonPointCandidateCount'] == 0 else None)
    result['commonDefinedSharePrimaryHeterogeneityDiagonal'] = sum(all(
        row['methods'][method]['candidates'][index]['shareStatus'] == 'defined'
        for method in ('primary', 'heterogeneity', 'party_diagonal'))
        for row in records for index in range(row['candidateCount']))
    return result
