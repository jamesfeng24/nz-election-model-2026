"""Evaluation-only Stage22 paired complete-share development diagnostics."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import sqrt
from statistics import mean

from scripts.checkpoints import stage22_prefit as prefit
from scripts.checkpoints.stage22_construction import DEST
from scripts.checkpoints.stage22_fit import METHODS, SCENARIOS


CONSTRUCTION = 'data/processed/checkpoints/stage22-shared-group-experiment/'
FEATURES = 'data/processed/checkpoints/stage22-shared-group-prefit/amended-features.json'
DIFFERENCES = 'data/processed/checkpoints/stage22-shared-group-prefit/coverage-differences.json'
PAIRS = (('baseline_plus_S', 'baseline'),
         ('baseline_plus_V', 'baseline'),
         ('baseline_plus_S_plus_V', 'baseline'),
         ('baseline_plus_S_plus_V', 'baseline_plus_S'),
         ('baseline_plus_S_plus_V', 'baseline_plus_V'))


def target_actuals(predictions, elections):
    seats = {seat['id']: seat for doc in elections.values()
             for seat in doc['electorates']}
    ids = [row['targetElectorateId'] for row in predictions['fullFrameStatus']
           if row['status'] == 'constructed']
    result = []
    for cid in ids:
        seat = seats[cid]
        valid = seat['candidateBallot']['validVotes']
        votes = {c['id']: c['votes'] for c in seat['candidates']}
        if (valid <= 0 or valid != seat['validCandidateVotes'] or
                sum(votes.values()) != valid or
                seat['winnerCandidateId'] not in votes):
            raise ValueError('Target candidate actuals do not reconcile')
        result.append({'targetElectorateId': cid,
                       'validCandidateVotes': valid,
                       'winnerCandidateId': seat['winnerCandidateId'],
                       'candidateShares': {key: value / valid for key, value in votes.items()}})
    return {'schemaVersion': 1, 'stage': 22,
            'role': 'target_evaluation_actuals_only', 'records': result}


def winner_set(shares):
    maximum = max(shares.values())
    return sorted(k for k, v in shares.items() if maximum - v <= 1e-12)


def contest_error(predicted, actual, candidates):
    if (set(predicted) != set(actual['candidateShares']) or
            set(predicted) != {c['targetOccurrenceId'] for c in candidates} or
            abs(sum(predicted.values()) - 1) > 1e-9 or
            abs(sum(actual['candidateShares'].values()) - 1) > 1e-9):
        raise ValueError('Incompatible complete valid-candidate slates')
    errors = []
    for candidate in candidates:
        cid = candidate['targetOccurrenceId']
        errors.append({'candidateOccurrenceId': cid,
                       'errorPP': 100 * (predicted[cid] - actual['candidateShares'][cid]),
                       'partyKey': candidate['targetPartyKey'],
                       'mappingStatus': candidate['mappingStatus'],
                       'sourceFeatureStatus': ('S_and_V' if candidate['s0Reported'] is not None and
                                               candidate['v0'] is not None else 'fallback'),
                       'slateSize': len(candidates)})
    winners = winner_set(predicted)
    return {'candidateErrors': errors,
            'contestMaePP': mean(abs(e['errorPP']) for e in errors),
            'contestMsePP2': mean(e['errorPP'] ** 2 for e in errors),
            'predictedWinnerSet': winners,
            'uniqueCorrect': len(winners) == 1 and winners[0] == actual['winnerCandidateId'],
            'tieContainsWinner': len(winners) > 1 and actual['winnerCandidateId'] in winners}


def score_rows(rows, method):
    if not rows:
        return None
    scores = [r['methods'][method] for r in rows]
    if any(score is None for score in scores):
        raise ValueError('Unsupported method in common sample')
    candidates = [c for score in scores for c in score['candidateErrors']]
    signed = sum(c['errorPP'] for c in candidates)
    if abs(signed) > 1e-6:
        raise ValueError('Full-slate signed bias failed conservation')
    grouped = defaultdict(list)
    for c in candidates:
        for label in (f"party:{c['partyKey']}",
                      f"mapping:{c['mappingStatus']}",
                      f"feature:{c['sourceFeatureStatus']}",
                      f"slate:{'2-5' if c['slateSize'] <= 5 else '6-8' if c['slateSize'] <= 8 else '9+'}"):
            grouped[label].append(c['errorPP'])
    return {'contests': len(rows), 'candidates': len(candidates),
            'contestEqualMaePP': mean(s['contestMaePP'] for s in scores),
            'contestEqualRmsePP': sqrt(mean(s['contestMsePP2'] for s in scores)),
            'candidateEqualMaePP': mean(abs(c['errorPP']) for c in candidates),
            'candidateEqualRmsePP': sqrt(mean(c['errorPP'] ** 2 for c in candidates)),
            'fullSlateSignedBiasPPAccountingCheck': signed / len(candidates),
            'uniquePredictedWinnerCount': sum(len(s['predictedWinnerSet']) == 1 for s in scores),
            'uniqueCorrectCount': sum(s['uniqueCorrect'] for s in scores),
            'uniqueWinnerAccuracyAllContests': sum(s['uniqueCorrect'] for s in scores) /
                                               len(rows),
            'predictedTieCount': sum(len(s['predictedWinnerSet']) > 1 for s in scores),
            'tieContainsWinnerCount': sum(s['tieContainsWinner'] for s in scores),
            'groupBias': {key: {'candidates': len(values),
                                'meanSignedBiasPP': mean(values),
                                'meanAbsoluteErrorPP': mean(abs(v) for v in values)}
                          for key, values in sorted(grouped.items())}}


def paired(rows, model, control):
    if not rows:
        return None
    changes = []
    for r in rows:
        a, b = r['methods'][model], r['methods'][control]
        if a is None or b is None:
            raise ValueError('Paired comparison has missing method')
        by_id = {c['candidateOccurrenceId']: c['errorPP']
                 for c in b['candidateErrors']}
        if set(by_id) != {c['candidateOccurrenceId'] for c in a['candidateErrors']}:
            raise ValueError('Unpaired candidate IDs')
        deltas_abs = [abs(c['errorPP']) - abs(by_id[c['candidateOccurrenceId']])
                      for c in a['candidateErrors']]
        deltas_sq = [c['errorPP'] ** 2 - by_id[c['candidateOccurrenceId']] ** 2
                     for c in a['candidateErrors']]
        changes.append({'targetElectorateId': r['targetElectorateId'],
                        'meanAbsoluteErrorDifferencePP': mean(deltas_abs),
                        'meanSquaredErrorDifferencePP2': mean(deltas_sq)})
    deltas = [r['meanAbsoluteErrorDifferencePP'] for r in changes]
    gain = -mean(deltas)
    loo_gains = [-((sum(deltas) - value) / (len(deltas) - 1))
                 for value in deltas] if len(deltas) > 1 else []
    return {'modelMinusControlMaePP': mean(deltas),
            'modelMinusControlMsePP2': mean(r['meanSquaredErrorDifferencePP2']
                                           for r in changes),
            'maeGainPP': gain,
            'leaveOneContestOutGainRangePP': [min(loo_gains), max(loo_gains)]
            if loo_gains else None,
            'fiveLargestAbsolutePairedChanges': sorted(changes,
                key=lambda r: (-abs(r['meanAbsoluteErrorDifferencePP']),
                               r['targetElectorateId']))[:5],
            'contestDifferences': changes}


def evaluate(predictions, actuals, features, changes):
    actual = {r['targetElectorateId']: r for r in actuals['records']}
    mapped = {r['targetElectorateId']: r for r in features['records']}
    common = set(changes['originalCommonContestIds'])
    new = set(changes['newlyAdmittedContestIds'])
    by_holdout = {}
    for fold in predictions['folds']:
        year = fold['targetYear']
        by_scenario = {}
        contextual = {r['targetElectorateId']: r for r in fold['contextual']}
        for scenario in SCENARIOS:
            indexed = {method: {r['targetElectorateId']: r['candidateShares']
                                for r in fold['scenarios'][scenario][method]}
                       for method in METHODS}
            rows = []
            for cid in fold['evaluationContestIds']:
                methods = {method: contest_error(indexed[method][cid], actual[cid],
                                                 mapped[cid]['candidates'])
                           for method in METHODS}
                methods['uniform'] = contest_error(contextual[cid]['uniform'], actual[cid],
                                                   mapped[cid]['candidates'])
                zero = contextual[cid]['restrictedZeroFloor']
                methods['restrictedZeroFloor'] = (
                    contest_error(zero, actual[cid], mapped[cid]['candidates'])
                    if zero is not None else None)
                rows.append({'targetElectorateId': cid, 'targetYear': year,
                             'subset': 'original_common' if cid in common else
                             'newly_admitted' if cid in new else 'unexpected',
                             'methods': methods})
            if any(r['subset'] == 'unexpected' for r in rows):
                raise ValueError('Amended evaluation sample not partitioned')
            groups = {'amendedFull': rows,
                      'originalCommon': [r for r in rows if r['subset'] == 'original_common'],
                      'newlyAdmitted': [r for r in rows if r['subset'] == 'newly_admitted']}
            summary = {}
            for label, subset in groups.items():
                restricted = [r for r in subset if r['methods']['restrictedZeroFloor'] is not None]
                summary[label] = {'allCommonMethods': {
                    method: score_rows(subset, method) for method in (*METHODS, 'uniform')},
                    'restrictedZeroFloorCommonContests': len(restricted),
                    'restrictedZeroFloorCommon': {
                        method: score_rows(restricted, method)
                        for method in (*METHODS, 'uniform', 'restrictedZeroFloor')},
                    'paired': {f'{model}_vs_{control}': paired(subset, model, control)
                               for model, control in PAIRS}}
            by_scenario[scenario] = {'summary': summary, 'records': rows}
        by_holdout[str(year)] = by_scenario
    earliest = {r['targetElectorateId']: r for r in predictions['earliest2011Contextual']}
    early_rows = []
    for cid, context in earliest.items():
        methods = {'uniform': contest_error(context['uniform'], actual[cid],
                                            mapped[cid]['candidates'])}
        zero = context['restrictedZeroFloor']
        methods['restrictedZeroFloor'] = (
            contest_error(zero, actual[cid], mapped[cid]['candidates'])
            if zero is not None else None)
        early_rows.append({'targetElectorateId': cid, 'methods': methods})
    coverage = dict(sorted(Counter(f"{r['targetYear']}:{r['reason'] or r['status']}"
                                   for r in predictions['fullFrameStatus']).items()))
    coverage_candidates = dict(sorted(Counter({
        f"{year}:{reason}": sum(r['candidateCount'] for r in predictions['fullFrameStatus']
                               if r['targetYear'] == year and (r['reason'] or r['status']) == reason)
        for year, reason in ((r['targetYear'], r['reason'] or r['status'])
                             for r in predictions['fullFrameStatus'])}).items()))
    early_restricted = [r for r in early_rows
                        if r['methods']['restrictedZeroFloor'] is not None]
    gates = {}
    for year in ('2017', '2023'):
        fold = by_holdout[year]
        printed = fold['printed']['summary']['amendedFull']
        pair = printed['paired']['baseline_plus_S_plus_V_vs_baseline']
        metrics = printed['allCommonMethods']
        rounding = [fold[s]['summary']['amendedFull']['paired']
                    ['baseline_plus_S_plus_V_vs_baseline']['maeGainPP']
                    for s in ('selected_lower', 'selected_upper')]
        gates[year] = {
            'maeGainPP': pair['maeGainPP'],
            'maeAtLeast025PP': pair['maeGainPP'] >= .25,
            'rmseRegressionPP': metrics['baseline_plus_S_plus_V']
                                ['contestEqualRmsePP'] - metrics['baseline']
                                ['contestEqualRmsePP'],
            'rmseRegressionBelow025PP': metrics['baseline_plus_S_plus_V']
                                        ['contestEqualRmsePP'] - metrics['baseline']
                                        ['contestEqualRmsePP'] < .25,
            'leaveOneOutGainPositive': pair['leaveOneContestOutGainRangePP'][0] > 0,
            'roundingGainPP': rounding,
            'noRoundingGainSignReversal': all(
                (value > 0) == (pair['maeGainPP'] > 0) and
                (value < 0) == (pair['maeGainPP'] < 0) for value in rounding),
            'identicalCoverageByConstruction': True}
    screen_pass = all(all(value for key, value in details.items()
                          if key in ('maeAtLeast025PP', 'rmseRegressionBelow025PP',
                                     'leaveOneOutGainPositive',
                                     'noRoundingGainSignReversal',
                                     'identicalCoverageByConstruction'))
                      for details in gates.values())
    return {'schemaVersion': 1, 'stage': 22,
            'role': 'development_holdout_evaluation_only',
            'fullFrameCoverage': coverage,
            'fullFrameCandidateOccurrencesByStatus': coverage_candidates,
            'earliest2011': {'uniform': score_rows(early_rows, 'uniform'),
                             'restrictedCommonContests': len(early_restricted),
                             'restrictedCommon': {
                                 method: score_rows(early_restricted, method)
                                 for method in ('uniform', 'restrictedZeroFloor')}},
            'holdouts': by_holdout,
            'developmentScreen': {'byFold': gates, 'allFrozenGatesPass': screen_pass,
                                  'interpretation': 'development_only_never_operational_selection'},
            'operationalSelection': None}


def build():
    manifest = prefit.read(CONSTRUCTION + 'construction-manifest.json')
    for name in ('fitted-parameters.json', 'predictions.json'):
        path = CONSTRUCTION + name
        if prefit.digest(path) != manifest['outputSha256'][name]:
            raise ValueError('Changed committed construction before scoring')
    predictions = prefit.read(CONSTRUCTION + 'predictions.json')
    elections = {year: prefit.read(prefit.ELECTIONS[year]) for year in (2011, 2017, 2023)}
    actuals = target_actuals(predictions, elections)
    differences = prefit.read(DIFFERENCES)['differences']
    diagnostics = evaluate(predictions, actuals, prefit.read(FEATURES), differences)
    result = {'actuals.json': actuals, 'diagnostics.json': diagnostics}
    inputs = (CONSTRUCTION + 'construction-manifest.json',
              CONSTRUCTION + 'predictions.json', FEATURES, DIFFERENCES,
              *(prefit.ELECTIONS[year] for year in (2011, 2017, 2023)))
    result['evaluation-manifest.json'] = {
        'schemaVersion': 1, 'stage': 22, 'phase': 'evaluation_after_committed_construction',
        'inputSha256': {path: prefit.digest(path) for path in inputs},
        'generatorSha256': prefit.digest('scripts/checkpoints/stage22_evaluation.py'),
        'outputSha256': {name: sha256(prefit.encode(doc)).hexdigest()
                         for name, doc in result.items()}}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build()
    for name, doc in result.items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != prefit.encode(doc):
                raise ValueError(f'Changed Stage22 evaluation {name}')
        else:
            path.write_bytes(prefit.encode(doc))
    print(json.dumps({year: {scenario: details['summary']['amendedFull']['paired']
        ['baseline_plus_S_plus_V_vs_baseline']['maeGainPP']
        for scenario, details in block.items()}
        for year, block in result['diagnostics.json']['holdouts'].items()}, sort_keys=True))


if __name__ == '__main__':
    main()
