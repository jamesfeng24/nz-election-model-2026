"""Independent arithmetic and numerical verification of saved Stage27 companions."""
from math import exp, log, sqrt

import numpy as np
from scipy.optimize import minimize

from scripts.models.exact_geography_retests.common import DEST, METHODS, cli, keyed, read, save_outputs, verify_outputs, phase_manifest


def independent_objective(parameters, training, actual, mean_s, model):
    kappa = parameters[0]
    theta = parameters[1] if model == 'baseline_plus_S' else 0.0
    loss, dk, dt = 0.0, 0.0, 0.0
    for row in training:
        candidates = row['candidates']
        base = np.array([c['targetPartySupport'] for c in candidates])
        s = np.array([c['s0Reported'] - mean_s if c['s0Reported'] is not None else 0 for c in candidates])
        z = np.log(base + kappa) + theta * s
        q = np.exp(z - np.max(z)); q /= sum(q)
        y = np.array([actual[row['targetElectorateId']]['candidateShares'][c['targetOccurrenceId']] for c in candidates])
        loss += np.max(z) + log(sum(np.exp(z - np.max(z)))) - float(y @ z)
        dk += float((q - y) @ (1 / (base + kappa)))
        dt += float((q - y) @ s)
    gradient = np.array([dk, dt] if model == 'baseline_plus_S' else [dk]) / len(training)
    return loss / len(training), gradient


def verify():
    verify_outputs(DEST + 'construction-manifest.json')
    verify_outputs(DEST + 'evaluation-manifest.json')
    inventory = read(DEST + 'inventory.json')
    saved = read(DEST + 'predictions.json')
    actuals = read(DEST + 'evaluation-actuals.json')
    results = read(DEST + 'results.json')
    actual = keyed(actuals['candidateActuals'], 'targetElectorateId')
    response_actual = keyed(actuals['responseActuals'], 'id')
    features = keyed(inventory['shareRecords'], 'targetElectorateId')
    response_features = keyed(inventory['responseRecords'], 'id')
    checks = []
    seen = set()
    for case in saved['candidateCases']:
        training = [features[cid] for cid in case['trainingIds']]
        scenario = case['scenarios']['printed']
        if not training:
            continue
        if tuple(case['trainingIds']) not in seen:
            seen.add(tuple(case['trainingIds']))
            den = sum(sum(c['s0Reported'] is not None for c in r['candidates']) / len(r['candidates']) for r in training)
            mu = sum(sum(c['s0Reported'] for c in r['candidates'] if c['s0Reported'] is not None) / len(r['candidates']) for r in training) / den
            if abs(mu - scenario['trainingOnlyMeans']['S']) > 1e-12:
                raise ValueError('Independent S mean disagrees')
            for method in METHODS:
                fits = []
                for k in (.001, .01, .09):
                    initial = [k, 0] if method == 'baseline_plus_S' else [k]
                    fitted = minimize(lambda p: independent_objective(p, training, actual, mu, method), initial,
                        jac=True, method='L-BFGS-B', bounds=[(.0001, .1)] + ([(-4, 4)] if len(initial) == 2 else []),
                        options={'gtol': 1e-10, 'ftol': 1e-15, 'maxiter': 2000, 'maxls': 50})
                    fits.append(fitted)
                best = min(fits, key=lambda r: r.fun)
                reference = scenario['fits'][method]
                gap = abs(best.fun - reference['objective'])
                if gap > 1e-8 or abs(best.x[0] - reference['kappa']) > 1e-4:
                    raise ValueError('Independent joint fit disagrees')
                checks.append({'kind': 'independent_direct_joint_fit', 'method': method,
                               'trainingContests': len(training), 'objectiveWithinFrozenTolerance': True,
                               'kappaWithinFrozenTolerance': True})
        reported = next(r for r in results['candidateCases'] if r['foldId'] == case['foldId'] and r['trainingVariant'] == case['trainingVariant'])
        for method in METHODS:
            params = scenario['fits'][method]
            errors_by_slate = []
            discrepancy = 0.0
            for prediction in scenario['predictions'][method]:
                row = features[prediction['targetElectorateId']]
                mu = scenario['trainingOnlyMeans']['S']
                theta = params['theta'][0] if params['theta'] else 0
                weights = [(c['targetPartySupport'] + params['kappa']) * exp(theta * (c['s0Reported'] - mu)
                    if c['s0Reported'] is not None else 0) for c in row['candidates']]
                vector = {c['targetOccurrenceId']: w / sum(weights) for c, w in zip(row['candidates'], weights)}
                discrepancy = max(discrepancy, max(abs(vector[k] - v) for k, v in prediction['candidateShares'].items()))
                outcome = actual[row['targetElectorateId']]['candidateShares']
                errors_by_slate.append([100 * (vector[k] - outcome[k]) for k in vector])
            mae = sum(sum(abs(x) for x in block) / len(block) for block in errors_by_slate) / len(errors_by_slate)
            rmse = sqrt(sum(sum(x*x for x in block) / len(block) for block in errors_by_slate) / len(errors_by_slate))
            summary = reported['scenarios']['printed']['summary']['expandedEvaluation']['methods'][method]
            if discrepancy > 1e-12 or abs(mae - summary['contestEqualMaePP']) > 1e-10 or abs(rmse - summary['contestEqualRmsePP']) > 1e-10:
                raise ValueError('Independent candidate shares or metrics disagree')
            checks.append({'kind': 'candidate_arithmetic', 'foldId': case['foldId'], 'trainingVariant': case['trainingVariant'],
                           'method': method, 'maePP': round(mae, 6), 'rmsePP': round(rmse, 6), 'shareArithmeticWithin1e12': True})
    for case in saved['responseCases']:
        for party, methods in case['parties'].items():
            training = [response_features[rid] for rid in case['trainingIds'] if response_features[rid]['party'] == party]
            reported = next(r for r in results['responseCases'] if r['foldId'] == case['foldId'] and r['trainingVariant'] == case['trainingVariant'] and r['party'] == party)
            for method, record in methods.items():
                fit = record['fit']
                if fit['status'] != 'available':
                    continue
                if training and method in ('stage6_zero_intercept', 'common_intercept', 'source_victory'):
                    columns = read(DEST + 'input-contract.json')['responseModels'][method]['columns']
                    x = np.array([[{'intercept': 1, 'x': r['x'], 'sourceWon': r['sourceWon']}[k] for k in columns] for r in training])
                    y = np.array([response_actual[r['id']]['c1'] - r['c0'] for r in training])
                    independent = np.linalg.lstsq(x, y, rcond=None)[0]
                    expected = [fit[{'intercept': 'alpha', 'x': 'beta', 'sourceWon': 'gamma'}[k]] for k in columns]
                    if np.max(np.abs(independent - expected)) > 1e-10:
                        raise ValueError('Independent OLS disagrees')
                errors = [100 * (p['point'] - response_actual[p['id']]['c1']) for p in record['predictions']]
                metrics = reported['summary']['expandedEvaluation']['methods'][method]
                mae = sum(abs(e) for e in errors) / len(errors)
                rmse = sqrt(sum(e*e for e in errors) / len(errors))
                if abs(mae - metrics['maePP']) > 1e-10 or abs(rmse - metrics['rmsePP']) > 1e-10:
                    raise ValueError('Independent response scores disagree')
                checks.append({'kind': 'response_arithmetic', 'foldId': case['foldId'], 'trainingVariant': case['trainingVariant'],
                               'party': party, 'method': method, 'maePP': round(mae, 6), 'rmsePP': round(rmse, 6)})
    return {'stage': 27, 'checks': checks, 'allPassed': True,
            'interpretation': 'Independent numerical/arithmetic verification, not a new predictive formulation or uncertainty estimate'}


if __name__ == '__main__':
    output = verify()
    outputs = {'independent-verification.json': output}
    outputs['independent-manifest.json'] = phase_manifest(
        [DEST + p for p in ('inventory.json', 'predictions.json', 'evaluation-actuals.json', 'results.json')] +
        ['scripts/validate/stage27_independent.py'], outputs)
    save_outputs(outputs, cli())
    print({'independentChecks': len(output['checks']), 'allPassed': output['allPassed']})
