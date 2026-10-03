"""Saved-prediction paired errors, finite associations and environment robustness."""
import argparse
from math import sqrt
from statistics import mean, pstdev
from .common import *
from .statistics import association, centered_association, dispersion


def verify_actual_denominators(actuals):
    for year in sorted({int(cid.split('-')[2]) for cid in actuals}):
        seats = keyed(read(f'data/processed/elections/{year}.json')['electorates'], 'id')
        for cid, a in actuals.items():
            if cid not in seats:
                continue
            s = seats[cid]; total = s['validCandidateVotes']; votes = {c['id']: c['votes'] for c in s['candidates']}
            if total <= 0 or sum(votes.values()) != total or total != s['candidateBallot']['validVotes']:
                raise ValueError('Actual valid-candidate denominator mismatch')
            if {c: v/total for c, v in votes.items()} != a['candidateShares']:
                raise ValueError('Saved actuals disagree with preserved candidate counts')


def errors_for(predictions, actual, ids):
    a = actual['candidateShares']; results = {}
    if set(a) != set(ids) or abs(sum(a.values())-1) > 1e-12 or any(v < 0 for v in a.values()):
        raise ValueError('Evaluation actual slate/denominator mismatch')
    for method, p in predictions.items():
        q = p['candidateShares']
        if set(q) != set(ids) or abs(sum(q.values())-1) > 1e-12 or any(v < 0 for v in q.values()):
            raise ValueError('Evaluation prediction slate/denominator mismatch')
        errors = {cid: 100*(q[cid]-a[cid]) for cid in ids}
        results[method] = {'maePP': mean(abs(v) for v in errors.values()),
            'msePP2': mean(v*v for v in errors.values()), 'candidateErrorPP': errors}
    return results


def paired(values):
    return {'Gpp': values[R]['maePP']-values[S]['maePP'],
        'Jpp': values[S]['maePP']-values[JOINT]['maePP'],
        'improvementsOverBaselinePP': {m: values['baseline']['maePP']-s['maePP'] for m, s in values.items()}}


def feature_groups(rows, features, view):
    result = {}
    for supported in (True, False):
        blocks = []
        for r in rows:
            ids = [c['targetOccurrenceId'] for c in features[r['targetElectorateId']]['candidates']
                if (c['R'][view]['status']=='supported') == supported]
            if ids:
                blocks.append({m: [r['errors'][m]['candidateErrorPP'][cid] for cid in ids] for m in METHODS})
        methods = {}
        for m in METHODS:
            values = [e for b in blocks for e in b[m]]
            methods[m] = None if not values else {'candidateEqualMaePP': mean(abs(v) for v in values),
                'candidateEqualRmsePP': sqrt(mean(v*v for v in values)), 'signedBiasPP': mean(values),
                'presentContestEqualMaePP': mean(mean(abs(v) for v in b[m]) for b in blocks)}
        key = 'R_supported' if supported else 'R_unsupported'
        result[key] = {'candidates': sum(len(b['baseline']) for b in blocks), 'presentContests': len(blocks),
            'weighting': 'candidate_equal_primary; contest_sensitivity_only_contests_with_group', 'methods': methods,
            'Gpp': None if not blocks else methods[R]['candidateEqualMaePP']-methods[S]['candidateEqualMaePP'],
            'Jpp': None if not blocks else methods[S]['candidateEqualMaePP']-methods[JOINT]['candidateEqualMaePP']}
    return result


def describe_fold(fold, scores, actuals, features, movements, check_saved):
    predictions = {m: keyed(fold['predictions'][m], 'targetElectorateId') for m in METHODS}
    sets = [set(v) for v in predictions.values()]
    if any(v != sets[0] for v in sets) or sets[0] not in (set(), set(fold['evaluationIds'])):
        raise ValueError('Four restrictions have different samples')
    saved = keyed(scores['records'], 'targetElectorateId'); rows = []
    for cid in sorted(sets[0]):
        feature = features[cid]; ids = [c['targetOccurrenceId'] for c in feature['candidates']]
        values = errors_for({m: p[cid] for m, p in predictions.items()}, actuals[cid], ids)
        if check_saved:
            for m in METHODS:
                old = saved[cid]['scores'][m]
                if abs(values[m]['maePP']-old['contestMaePP']) > 1e-9 or abs(values[m]['msePP2']-old['contestMsePP2']) > 1e-9:
                    raise ValueError('Stage33 saved score reproduction mismatch')
                if values[m]['candidateErrorPP'] != {c['candidateOccurrenceId']: c['errorPP'] for c in old['candidateErrors']}:
                    raise ValueError('Stage33 saved candidate error mismatch')
        move = movements[cid]; candidates = feature['candidates']
        coverage = {v: sum(c['R'][v]['status']=='supported' for c in candidates) for v in ('broad', 'strict')}
        rows.append({'targetYear': fold['targetYear'], 'targetElectorateId': cid, 'candidateIds': ids,
            'sourceElectorateId': feature['sourceElectorateId'], 'targetSeatName': move.get('targetSeatName'), 'slateSize': len(ids),
            'RSupportedCounts': coverage, 'RSupportedFractions': {v: n/len(ids) for v, n in coverage.items()},
            'SCount': sum(c['s0Reported'] is not None for c in candidates),
            'movementStatus': move['status'], 'movementExclusion': move.get('diagnosticExclusion'),
            'constructedLocalDistance': move.get('constructedLocalDistance'), 'observedLocalDistance': move.get('observedLocalDistance'),
            'constructedPartyInputErrorEvaluationOnly': move.get('partyInputError'), 'errors': values, **paired(values)})
    methods = {m: {'contestEqualMaePP': mean(r['errors'][m]['maePP'] for r in rows),
        'contestEqualRmsePP': sqrt(mean(r['errors'][m]['msePP2'] for r in rows))} for m in METHODS} if rows else None
    rfit = fold['fits'][R]['parameters']
    return {'branch': fold['branch'], 'targetYear': fold['targetYear'], 'sourceYear': fold['sourceYear'],
        'foldId': fold['id'], 'records': rows, 'contests': len(rows), 'candidates': sum(r['slateSize'] for r in rows),
        'expectedContests': len(fold['evaluationIds']), 'noFitIds': sorted(set(fold['evaluationIds'])-sets[0]),
        'trainingContests': len(fold['trainingIds']), 'trainingEnvironments': fold['trainingTransitionEnvironments'],
        'savedRFit': {'status': rfit['status'], 'coefficient': rfit.get('coefficients', {}).get('R'),
            'thetaAtBoundary': rfit.get('thetaAtBoundary'), 'fitId': fold['fits'][R]['fitId']},
        'methods': methods, 'meanGpp': mean(r['Gpp'] for r in rows) if rows else None,
        'meanJpp': mean(r['Jpp'] for r in rows) if rows else None,
        'Rgroups': feature_groups(rows, features, fold['view']),
        'associations': {k: association(rows, k) for k in ('constructedLocalDistance', 'observedLocalDistance')}}


def robust(folds):
    cases = [f for f in folds if f['records']]; years = [f['targetYear'] for f in cases]
    records = [r for f in cases for r in f['records']]; result = {}
    for m in METHODS:
        values = [f['methods'][m]['contestEqualMaePP'] for f in cases]
        gains = [f['methods']['baseline']['contestEqualMaePP']-v for f, v in zip(cases, values)]
        d = dispersion(gains, years)
        if d:
            d['worstImprovementTargetYears'] = [y for y, v in zip(years, gains) if v==min(gains)]
            d.pop('worstTargetYears')
        result[m] = {'originalContestEqualPooledMaePP': mean(r['errors'][m]['maePP'] for r in records) if records else None,
            'originalContestEqualPooledRmsePP': sqrt(mean(r['errors'][m]['msePP2'] for r in records)) if records else None,
            'electionMaeDispersion': dispersion(values, years), 'baselineRelativeImprovementDispersion': d,
            'byElection': [{'targetYear': y, 'maePP': v, 'improvementOverBaselinePP': g} for y, v, g in zip(years, values, gains)]}
    return {'availableTargetYears': years, 'contests': len(records), 'methods': result,
        'warning': 'error_environment_dispersion_not_predictive_uncertainty; selected_partial_samples'}


def pooled_diagnostic(folds, features, view):
    rows = [r for f in folds for r in f['records']]; fields = ('constructedLocalDistance', 'observedLocalDistance')
    return {'records': len(rows), 'withinElectionCentered': {k: centered_association(rows, k) for k in fields},
        'fixedPredictionDeleteOneElection': [{'deletedTargetYear': y, 'associations': {
            k: centered_association([r for r in rows if r['targetYear']!=y], k) for k in fields}}
            for y in sorted({r['targetYear'] for r in rows})],
        'Rgroups': feature_groups(rows, features, view),
        'jointVsS': {'improvedContests': sum(r['Jpp']>0 for r in rows), 'worsenedContests': sum(r['Jpp']<0 for r in rows),
            'ties': sum(r['Jpp']==0 for r in rows),
            'fiveLargestGains': [{'targetElectorateId': r['targetElectorateId'], 'targetSeatName': r['targetSeatName'], 'Jpp': r['Jpp']} for r in sorted([r for r in rows if r['Jpp']>0], key=lambda r: (-r['Jpp'], r['targetElectorateId']))[:5]],
            'fiveLargestLosses': [{'targetElectorateId': r['targetElectorateId'], 'targetSeatName': r['targetSeatName'], 'Jpp': r['Jpp']} for r in sorted([r for r in rows if r['Jpp']<0], key=lambda r: (r['Jpp'], r['targetElectorateId']))[:5]]}}


def available_mean(rows, value):
    values = [value(r) for r in rows if r['movementStatus']=='available']
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def build(construction=None, evaluation=None, features=None, movement=None, actuals=None):
    construction = read(S33+'construction.json') if construction is None else construction
    evaluation = read(S33+'evaluation.json') if evaluation is None else evaluation
    features = read(S32+'inventory.json') if features is None else features
    movement = local('movement.json') if movement is None else movement
    check_saved = actuals is None
    if check_saved:
        actuals = evaluation['evaluationOnlyActuals']; verify_actual_denominators(actuals)
    feature = keyed(features['contestRecords'], 'targetElectorateId'); moves = keyed(movement['records'], 'targetElectorateId')
    saved = keyed(evaluation['folds'], 'id')
    folds = [describe_fold(f, saved[f['id']], actuals, feature, moves, check_saved) for f in construction['folds'] if f['branch'] in BRANCHES]
    branches = []; national = keyed(movement['national'], 'targetYear')
    for branch in BRANCHES:
        cases = [f for f in folds if f['branch']==branch]; view = 'strict' if branch=='strict' else 'broad'
        block = {'branch': branch, **pooled_diagnostic(cases, feature, view)}
        if branch in ('primary', 'strict', 'separated'):
            block['robustness'] = robust(cases)
        block['environmentRows'] = [{'targetYear': f['targetYear'], 'nationalDistance': national[f['targetYear']]['totalVariationFraction'],
            'contests': f['contests'], 'meanGpp': f['meanGpp'], 'meanJpp': f['meanJpp'],
            'RSupported': {v: sum(r['RSupportedCounts'][v] for r in f['records']) for v in ('broad', 'strict')},
            'candidates': f['candidates'], 'trainingContests': f['trainingContests'],
            'trainingEnvironments': f['trainingEnvironments'], 'savedRFit': f['savedRFit'],
            'meanPartyInputMAEpp': available_mean(f['records'], lambda r: r['constructedPartyInputErrorEvaluationOnly']['completeVectorMaePP']),
            'majorPartyInputMAEpp': {k: available_mean(f['records'], lambda r: r['constructedPartyInputErrorEvaluationOnly']['majorParty'][k]['absoluteErrorPP'] if r['constructedPartyInputErrorEvaluationOnly']['majorParty'][k] else None) for k in ('nationalparty', 'labourparty')}} for f in cases if f['records']]
        branches.append(block)
    return {'stage': 34, 'role': 'post_result_saved_prediction_diagnostic_no_fits', 'folds': folds, 'branches': branches,
        'operationalSelection': None, 'predictionsRegenerated': False}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    verify_inputs(); verify_phase('movement'); result = build(); save('analysis.json', result, a.check)
    phase('analysis', ['analysis.json'], ['statistics', 'analysis'], a.check)
    print('Stage34 diagnostic folds', len(result['folds']), 'prior preserved', preserve())


if __name__ == '__main__':
    main()
