"""Evaluation-only actuals and common-sample candidate-share diagnostics."""

from collections import Counter, defaultdict
from math import sqrt
from statistics import mean

from scripts.models.conditional_candidate_share.model import METHODS


def actuals(construction, elections):
    seats = {year: {seat['id']: seat for seat in doc['electorates']}
             for year, doc in elections.items()}
    rows = []
    for holdout in construction['holdouts']:
        for record in holdout['records']:
            if record['status'] != 'constructed':
                continue
            seat = seats[holdout['targetYear']][record['targetElectorateId']]
            valid = seat['candidateBallot']['validVotes']
            votes = {candidate['id']: candidate['votes'] for candidate in seat['candidates']}
            ids = {candidate['candidateOccurrenceId'] for candidate in record['candidates']}
            if (valid <= 0 or valid != seat['validCandidateVotes'] or
                    sum(votes.values()) != valid or set(votes) != ids or
                    seat['winnerCandidateId'] not in votes):
                raise ValueError('Candidate evaluation totals do not reconcile')
            rows.append({'targetYear': holdout['targetYear'],
                         'targetElectorateId': record['targetElectorateId'],
                         'validCandidateVotes': valid,
                         'winnerCandidateId': seat['winnerCandidateId'],
                         'candidateShares': {key: value / valid for key, value in votes.items()}})
    return {'schemaVersion': 1, 'stage': 18, 'role': 'evaluation_only_target_outcomes',
            'records': rows}


def _round(value):
    return round(float(value), 10)


def _slate_stratum(n):
    return '2-5' if n <= 5 else '6-8' if n <= 8 else '9+'


def _metrics(records, method):
    if not records:
        return None
    candidate_rows = []
    contest_mae = []
    contest_mse = []
    unique_correct = 0
    unique_predictions = 0
    tied_predictions = 0
    tied_contains = 0
    for record in records:
        errors = record['methods'][method]['candidateErrors']
        contest_mae.append(mean(abs(row['errorPP']) for row in errors))
        contest_mse.append(mean(row['errorPP'] ** 2 for row in errors))
        candidate_rows.extend(errors)
        predicted = record['methods'][method]['predictedWinnerSet']
        if len(predicted) == 1:
            unique_predictions += 1
            unique_correct += predicted[0] == record['actualWinnerCandidateId']
        else:
            tied_predictions += 1
            tied_contains += record['actualWinnerCandidateId'] in predicted
    groups = defaultdict(list)
    for row in candidate_rows:
        groups[f"category:{row['sourcePartyKey']}"].append(row['errorPP'])
        groups[f"mapping:{row['mappingStatus']}"].append(row['errorPP'])
        groups[f"slateSize:{row['slateSizeStratum']}"].append(row['errorPP'])
    total_bias = sum(row['errorPP'] for row in candidate_rows)
    if abs(total_bias) > 1e-6:
        raise ValueError('Predicted or actual contest shares do not conserve one')
    return {'contests': len(records), 'candidates': len(candidate_rows),
            'contestEqualMaePP': _round(mean(contest_mae)),
            'contestEqualRmsePP': _round(sqrt(mean(contest_mse))),
            'candidateEqualMaePP': _round(mean(abs(row['errorPP']) for row in candidate_rows)),
            'candidateEqualRmsePP': _round(sqrt(mean(row['errorPP'] ** 2
                                                   for row in candidate_rows))),
            'overallSignedBiasPPAccountingCheck': _round(total_bias / len(candidate_rows)),
            'uniquePredictedWinnerCount': unique_predictions,
            'uniqueWinnerCorrectCount': unique_correct,
            'uniqueWinnerAccuracyAllContests': _round(unique_correct / len(records)),
            'predictedTieCount': tied_predictions,
            'tiedSetContainsActualCount': tied_contains,
            'errorByGroupPP': {key: {'candidates': len(values),
                                    'meanSignedBiasPP': _round(mean(values)),
                                    'meanAbsoluteErrorPP': _round(mean(abs(v) for v in values)),
                                    'rmsePP': _round(sqrt(mean(v * v for v in values)))}
                               for key, values in sorted(groups.items())}}


def evaluate(construction, actual_doc):
    actual_index = {(row['targetYear'], row['targetElectorateId']): row
                    for row in actual_doc['records']}
    if len(actual_index) != len(actual_doc['records']):
        raise ValueError('Duplicate evaluation contest')
    rows = []
    for holdout in construction['holdouts']:
        for record in holdout['records']:
            if record['status'] != 'constructed':
                continue
            actual = actual_index[(holdout['targetYear'], record['targetElectorateId'])]
            methods = {}
            for method in METHODS:
                predicted = record['methods'][method]
                if predicted is None:
                    methods[method] = None
                    continue
                shares = predicted['shares']
                if (set(shares) != set(actual['candidateShares']) or
                        abs(sum(shares.values()) - 1) > 1e-9 or
                        abs(sum(actual['candidateShares'].values()) - 1) > 1e-9):
                    raise ValueError('Incompatible candidate-share destination or denominator')
                errors = []
                for candidate in record['candidates']:
                    cid = candidate['candidateOccurrenceId']
                    errors.append({'candidateOccurrenceId': cid,
                                   'sourcePartyKey': candidate['sourcePartyKey'],
                                   'mappingStatus': candidate['mappingStatus'],
                                   'slateSizeStratum': _slate_stratum(len(record['candidates'])),
                                   'errorPP': _round(100 * (shares[cid] - actual['candidateShares'][cid]))})
                methods[method] = {'predictedWinnerSet': predicted['predictedWinnerSet'],
                                   'candidateErrors': errors}
            rows.append({'targetYear': holdout['targetYear'],
                         'targetElectorateId': record['targetElectorateId'],
                         'actualWinnerCandidateId': actual['winnerCandidateId'],
                         'candidateCount': len(record['candidates']), 'methods': methods})
    by_year = {}
    for year in (2011, 2017, 2023):
        year_rows = [row for row in rows if row['targetYear'] == year]
        common = [row for row in year_rows if row['methods']['restricted_zero_floor'] is not None]
        by_year[str(year)] = {'allSupported': {method: _metrics(year_rows, method)
                                               for method in METHODS[:2]},
                              'restrictedCommon': {method: _metrics(common, method)
                                                   for method in METHODS},
                              'restrictedComparatorAbstainedContests': len(year_rows) - len(common)}
    pooled = [row for row in rows if row['targetYear'] in (2017, 2023)]
    pooled_common = [row for row in pooled if row['methods']['restricted_zero_floor'] is not None]
    status = Counter((row['targetYear'], row['status'] if row['status'] == 'constructed'
                      else row['reason']) for h in construction['holdouts'] for row in h['records'])
    sensitivities = {}
    for year in (2011, 2017, 2023):
        records = next(h['records'] for h in construction['holdouts'] if h['targetYear'] == year)
        sensitivities[str(year)] = {method: dict(sorted(Counter(
            r['stage5ConditionalObservedNationalSensitivity'][method]['status'] if
            r['stage5ConditionalObservedNationalSensitivity'][method]['status'] == 'constructed'
            else r['stage5ConditionalObservedNationalSensitivity'][method]['reason']
            for r in records if r['status'] == 'constructed').items()))
            for method in ('additive', 'proportional', 'log_odds')}
    return {'schemaVersion': 1, 'stage': 18,
            'role': 'conditional_development_holdout_evaluation_only',
            'records': rows,
            'summary': {'fullFrameContests': 213,
                        'heldGeneralFrameCandidates': 1313,
                        'statusByYear': {f'{year}:{label}': n
                                         for (year, label), n in sorted(status.items())},
                        'byHoldout': by_year,
                        'pooledTrainedFolds': {
                            'allSupported': {method: _metrics(pooled, method)
                                             for method in METHODS[:2]},
                            'restrictedCommon': {method: _metrics(pooled_common, method)
                                                 for method in METHODS}},
                        'stage5InputSensitivity': sensitivities},
            'selectedOperationalCandidateBaseline': None}
