"""Evaluation-only Stage27 metrics; no fitting or sample selection by outcomes."""
from collections import defaultdict
from math import sqrt
from statistics import mean

from scripts.checkpoints.stage22_evaluation import contest_error, score_rows, paired
from scripts.checkpoints.stage22_fit import SCENARIOS
from . import adapters as a
from .common import (DEST, METHODS, OLD_RESPONSE, cli, keyed, read, save_outputs,
                     verify_inputs, verify_outputs, phase_manifest)


def actuals(data, elections):
    seats = {s['id']: s for doc in elections.values() for s in doc['electorates']}
    candidate, response = [], []
    for row in data['shareRecords']:
        seat = seats[row['targetElectorateId']]
        valid = seat['candidateBallot']['validVotes']
        totals = {c['id']: c['votes'] for c in seat['candidates']}
        if valid <= 0 or valid != seat['validCandidateVotes'] or sum(totals.values()) != valid:
            raise ValueError('Evaluation candidate denominator does not reconcile')
        candidate.append({'targetElectorateId': seat['id'], 'validCandidateVotes': valid,
                          'winnerCandidateId': seat['winnerCandidateId'],
                          'candidateShares': {cid: v / valid for cid, v in totals.items()}})
    by_id = keyed(candidate, 'targetElectorateId')
    for row in data['responseRecords']:
        response.append({'id': row['id'], 'c1': by_id[row['electorateId']]['candidateShares'][row['targetOccurrenceId']]})
    return {'role': 'evaluation_only', 'candidateActuals': candidate, 'responseActuals': response}


def candidate_summary(rows):
    methods = (*METHODS, 'uniform')
    scores = {m: score_rows([r for r in rows if r['methods'][m] is not None], m) for m in methods}
    for m, s in scores.items():
        if s is not None:
            used = [r for r in rows if r['methods'][m] is not None]
            s['meanAbsoluteActualWinnerMarginErrorPP'] = mean(r['methods'][m]['marginErrorPP'] for r in used)
            s['abstainedContests'] = len(rows) - len(used)
    common = [r for r in rows if all(r['methods'][m] is not None for m in METHODS)]
    restricted = [r for r in common if r['methods']['restrictedZeroFloor'] is not None]
    parameter_free = [r for r in rows if r['methods']['restrictedZeroFloor'] is not None]
    return {'fullSampleContests': len(rows), 'methods': scores,
            'S_vs_baseline': paired(common, 'baseline_plus_S', 'baseline'),
            'restrictedZeroFloorContests': len(parameter_free),
            'parameterFreeRestricted': {m: score_rows(parameter_free, m) for m in ('uniform', 'restrictedZeroFloor')},
            'fittedRestrictedCommonContests': len(restricted),
            'restrictedCommon': {m: score_rows(restricted, m) for m in (*METHODS, 'restrictedZeroFloor')}}


def share_rows(case, scenario, inventory, outcomes):
    context = keyed(case['contextual'], 'targetElectorateId')
    prediction = {m: keyed(case['scenarios'][scenario]['predictions'][m], 'targetElectorateId') for m in METHODS}
    result = []
    for cid in case['evaluationIds']:
        row, actual = inventory[cid], outcomes[cid]
        sources = {m: prediction[m].get(cid, {}).get('candidateShares') for m in METHODS}
        sources.update({m: context[cid][m] for m in ('uniform', 'restrictedZeroFloor')})
        methods = {}
        for method, pred in sources.items():
            if pred is None:
                methods[method] = None
                continue
            score = contest_error(pred, actual, row['candidates'])
            for c in score['candidateErrors']:
                f = next(f for f in row['candidates'] if f['targetOccurrenceId'] == c['candidateOccurrenceId'])
                c['sourceFeatureStatus'] = 'supported_S' if f['s0Reported'] is not None else 'fallback'
            winner = actual['winnerCandidateId']
            observed = actual['candidateShares']
            am = observed[winner] - max(v for k, v in observed.items() if k != winner)
            pm = pred[winner] - max(v for k, v in pred.items() if k != winner)
            score['marginErrorPP'] = 100 * abs(pm - am)
            methods[method] = score
        result.append({'targetElectorateId': cid, 'targetYear': row['targetYear'],
                       'originalFrame': row['originalFrame'], 'methods': methods})
    return result


def response_metric(rows, method):
    selected = [r for r in rows if r['predictions'][method] is not None]
    if not selected:
        return None
    errors = [100 * (r['predictions'][method] - r['actual']) for r in selected]
    return {'records': len(errors), 'abstentions': len(rows) - len(errors),
            'maePP': mean(abs(x) for x in errors), 'rmsePP': sqrt(mean(x*x for x in errors)),
            'biasPP': mean(errors), 'outOfRangeCount': sum(not 0 <= r['predictions'][method] <= 1 for r in selected)}


def response_pair(rows, model, control):
    common = [r for r in rows if r['predictions'][model] is not None and r['predictions'][control] is not None]
    if not common:
        return None
    changes = []
    for r in common:
        em = 100 * (r['predictions'][model] - r['actual'])
        ec = 100 * (r['predictions'][control] - r['actual'])
        changes.append({'id': r['id'], 'modelMinusControlAbsoluteErrorPP': abs(em) - abs(ec),
                        'modelMinusControlSquaredErrorPP2': em*em - ec*ec})
    deltas = [r['modelMinusControlAbsoluteErrorPP'] for r in changes]
    loo = [-((sum(deltas) - d) / (len(deltas) - 1)) for d in deltas] if len(deltas) > 1 else []
    return {'records': len(common), 'modelMinusControlMaePP': mean(deltas), 'maeGainPP': -mean(deltas),
            'modelMinusControlMsePP2': mean(r['modelMinusControlSquaredErrorPP2'] for r in changes),
            'leaveOneRecordOutGainRangePP': [min(loo), max(loo)] if loo else None,
            'fiveLargestAbsolutePairedChanges': sorted(changes, key=lambda r: (-abs(r['modelMinusControlAbsoluteErrorPP']), r['id']))[:5],
            'recordDifferences': changes}


def response_summary(rows, definitions, comparisons):
    return {'records': len(rows), 'methods': {m: response_metric(rows, m) for m in definitions},
            'paired': {f'{m}_vs_{c}': response_pair(rows, m, c) for m, c in comparisons},
            'sourceVictoryStrata': {str(w): {m: response_metric([r for r in rows if r['sourceWon'] == w], m)
                                            for m in definitions} for w in (0, 1)}}


def evaluate(predictions, data, outcomes):
    candidate_data = keyed(data['shareRecords'], 'targetElectorateId')
    response_data = keyed(data['responseRecords'], 'id')
    candidate_actual = keyed(outcomes['candidateActuals'], 'targetElectorateId')
    response_actual = keyed(outcomes['responseActuals'], 'id')
    contract = read(OLD_RESPONSE + 'specification.json')
    comparisons = contract['primaryComparisons'] + contract['contextComparisons']
    candidate_cases, response_cases = [], []
    candidate_pools, response_pools = defaultdict(list), defaultdict(list)
    for case in predictions['candidateCases']:
        scenarios = {}
        for scenario in SCENARIOS:
            rows = share_rows(case, scenario, candidate_data, candidate_actual)
            subsets = {'expandedEvaluation': rows,
                       'originalCommon': [r for r in rows if r['originalFrame']],
                       'newlyAdmitted': [r for r in rows if not r['originalFrame']]}
            scenarios[scenario] = {'summary': {k: candidate_summary(v) for k, v in subsets.items()}, 'records': rows}
            candidate_pools[(case['chronologyProtocol'], case['trainingVariant'], scenario)].extend(
                r for r in rows if r['methods']['baseline'] is not None and r['methods']['baseline_plus_S'] is not None)
        candidate_cases.append({k: v for k, v in case.items() if k not in ('contextual', 'scenarios')} | {'scenarios': scenarios})
    for case in predictions['responseCases']:
        for party, methods in case['parties'].items():
            mapped = {m: keyed(d['predictions'], 'id') for m, d in methods.items()}
            rows = []
            for rid in case['evaluationIds']:
                r = response_data[rid]
                if r['party'] != party:
                    continue
                rows.append({'id': rid, 'actual': response_actual[rid]['c1'], 'sourceWon': r['sourceWon'],
                             'targetYear': r['targetYear'], 'originalFrame': r['originalFrame'],
                             'predictions': {m: d.get(rid, {}).get('point') for m, d in mapped.items()}})
            subsets = {'expandedEvaluation': rows, 'originalCommon': [r for r in rows if r['originalFrame']],
                       'newlyAdmitted': [r for r in rows if not r['originalFrame']]}
            response_cases.append({k: v for k, v in case.items() if k != 'parties'} | {
                'party': party, 'summary': {k: response_summary(v, methods, comparisons) for k, v in subsets.items()},
                'records': rows})
            response_pools[(case['chronologyProtocol'], case['trainingVariant'], party)].extend(
                r for r in rows if r['predictions']['source_victory'] is not None)
    pooled_candidates = [{'chronologyProtocol': k[0], 'trainingVariant': k[1], 'scenario': k[2],
                          'trainedFoldsOnly': candidate_summary(rows)} for k, rows in sorted(candidate_pools.items())]
    pooled_responses = [{'chronologyProtocol': k[0], 'trainingVariant': k[1], 'party': k[2],
                         'trainedFoldsOnly': response_summary(rows, contract['models'], comparisons)}
                        for k, rows in sorted(response_pools.items())]
    return {'stage': 27, 'role': 'development_evaluation_only', 'candidateCases': candidate_cases,
            'responseCases': response_cases, 'pooledCandidate': pooled_candidates,
            'pooledResponse': pooled_responses, 'operationalSelection': None}


def screens(result):
    output = {'candidate': [], 'response': []}
    for protocol in ('expanding_window', 'more_separated'):
        cs = [c for c in result['candidateCases'] if c['chronologyProtocol'] == protocol and c['trainingVariant'] == 'expanded'
              and c['scenarios']['printed']['summary']['expandedEvaluation']['S_vs_baseline'] is not None]
        folds = []
        for c in cs:
            summary = c['scenarios']['printed']['summary']['expandedEvaluation']
            pair, scores = summary['S_vs_baseline'], summary['methods']
            rmse_regression = scores['baseline_plus_S']['contestEqualRmsePP'] - scores['baseline']['contestEqualRmsePP']
            rounding = [c['scenarios'][s]['summary']['expandedEvaluation']['S_vs_baseline']['maeGainPP'] for s in SCENARIOS]
            passes = (pair['maeGainPP'] >= .25 and rmse_regression < .25 and
                      pair['leaveOneContestOutGainRangePP'][0] > 0 and min(rounding) > 0)
            folds.append({'targetYear': c['targetYear'], 'maeGainPP': pair['maeGainPP'],
                          'rmseRegressionPP': rmse_regression, 'roundingGainRangePP': [min(rounding), max(rounding)], 'passes': passes})
        output['candidate'].append({'chronologyProtocol': protocol, 'folds': folds,
                                    'allTrainedFoldsPass': bool(folds) and all(f['passes'] for f in folds),
                                    'original2017And2023Pass': all(f['passes'] for f in folds if f['targetYear'] in (2017, 2023))})
        for party in ('nationalparty', 'labourparty'):
            rs = [r for r in result['responseCases'] if r['chronologyProtocol'] == protocol and
                  r['trainingVariant'] == 'expanded' and r['party'] == party and
                  r['summary']['expandedEvaluation']['paired']['source_victory_vs_common_intercept'] is not None]
            pooled = next(r for r in result['pooledResponse'] if r['chronologyProtocol'] == protocol and
                          r['trainingVariant'] == 'expanded' and r['party'] == party)['trainedFoldsOnly']
            gains = [{'targetYear': r['targetYear'], 'maeGainPP': r['summary']['expandedEvaluation']['paired']
                      ['source_victory_vs_common_intercept']['maeGainPP']} for r in rs]
            gain = pooled['paired']['source_victory_vs_common_intercept']['maeGainPP']
            output['response'].append({'chronologyProtocol': protocol, 'party': party, 'foldGains': gains,
                'pooledMaeGainPP': gain, 'passes': gain >= .25 and all(g['maeGainPP'] > 0 for g in gains),
                'worstFoldRmseRegressionPP': max(r['summary']['expandedEvaluation']['methods']['source_victory']['rmsePP'] -
                    r['summary']['expandedEvaluation']['methods']['common_intercept']['rmsePP'] for r in rs)})
    return output


def main():
    check = cli()
    verify_inputs()
    verify_outputs(DEST + 'construction-manifest.json')
    data, predictions = read(DEST + 'inventory.json'), read(DEST + 'predictions.json')
    elections, _ = a.datasets()
    observed = actuals(data, elections)
    result = evaluate(predictions, data, observed)
    result['developmentScreens'] = screens(result)
    from .training_comparison import compare
    result['trainingComparison'] = compare(result)
    outputs = {'evaluation-actuals.json': observed, 'results.json': result}
    outputs['evaluation-manifest.json'] = phase_manifest([DEST + p for p in (
        'inventory.json', 'predictions.json', 'construction-manifest.json')], outputs)
    save_outputs(outputs, check)
    print(result['developmentScreens'])


if __name__ == '__main__':
    main()
