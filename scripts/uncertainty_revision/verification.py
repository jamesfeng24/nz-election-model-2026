"""Independent Stage45 scalar moments, QR, quadrature and score audit."""
import math

import numpy as np
from scipy.linalg import helmert

from .common import OLD, PREFIX, arguments, read, save, verify
from .coordinates import mean_logit_location

EPSILON = 1e-6
TOLERANCE = 1e-10


def scalar_coordinates(row, field):
    values = [float(x)+EPSILON for x in row[field]]
    major = [i for i, g in enumerate(row['groups']) if g in ('national', 'labour')]
    minor = [i for i in range(len(values)) if i not in major]
    result = {'balance': None, 'mass': None, 'within': None}
    if row['groups'].count('national') == row['groups'].count('labour') == 1:
        n, l = row['groups'].index('national'), row['groups'].index('labour')
        result['balance'] = math.log(values[n])-math.log(values[l])
    if major and minor:
        result['mass'] = math.log(math.fsum(values[i] for i in major))-math.log(math.fsum(values[i] for i in minor))
    if len(minor) > 1:
        logs = [math.log(values[i]) for i in minor]
        center = math.fsum(logs)/len(logs)
        result['within'] = [v-center for v in logs]
    return result, minor


def independent_moments(rows):
    values, remainder = {'balance': [], 'mass': []}, []
    for row in rows:
        a, minor = scalar_coordinates(row, 'actual')
        b, _ = scalar_coordinates(row, 'mean')
        for coordinate in values:
            if a[coordinate] is not None:
                values[coordinate].append(a[coordinate]-b[coordinate])
        if a['within'] is not None:
            delta = np.array([x-y for x, y in zip(a['within'], b['within'])])
            tags = row['ballotGroupKeys'] if row['layer'] == 'local_party' else [f['group'] or 'no_group' for f in row['features']]
            remainder.append((delta, [tags[i] for i in minor]))
    moments = {}
    for coordinate, data in values.items():
        if not data:
            moments[coordinate] = {'shared': None, 'seat': None}
            continue
        center = math.fsum(data)/len(data)
        moments[coordinate] = {'shared': center**2,
            'seat': math.fsum((v-center)**2 for v in data)/len(data)}
    unique = sorted({tag for _, tags in remainder for tag in tags})
    if len(unique) < 2:
        seats = [math.fsum(float(v)**2 for v in residual)/(len(residual)-1) for residual, _ in remainder]
        moments['within'] = {'shared': None, 'seat': math.fsum(seats)/len(seats) if seats else None}
        return moments
    basis = helmert(len(unique), full=False).T
    matrices, responses = [], []
    for residual, tags in remainder:
        indicator = np.array([[float(tag == label) for label in unique] for tag in tags])
        indicator -= indicator.mean(axis=0)
        matrices.append(np.einsum('ij,jk->ik', indicator, basis)/math.sqrt(len(tags)-1))
        responses.append(residual/math.sqrt(len(tags)-1))
    x, y = np.concatenate(matrices), np.concatenate(responses)
    singular = np.linalg.svd(x, compute_uv=False)
    full = singular[-1] > max(1e-12, singular[0]*1e-10)
    if full:
        q, r = np.linalg.qr(x, mode='reduced')
        beta = np.linalg.solve(r, np.einsum('ij,i->j', q, y))
        effects = np.einsum('ij,j->i', basis, beta)
    else:
        effects = np.zeros(len(unique))
    seat = []
    for residual, tags in remainder:
        fitted = [float(effects[unique.index(t)]) for t in tags]
        center = math.fsum(fitted)/len(fitted)
        seat.append(math.fsum((float(e)-(v-center))**2 for e, v in zip(residual, fitted))/(len(residual)-1))
    moments['within'] = {'shared': math.fsum(float(e)**2 for e in effects)/(len(unique)-1) if full else None,
                         'seat': math.fsum(seat)/len(seat)}
    return moments


def close(actual, expected, label):
    if actual is None or expected is None:
        if actual is not expected:
            raise ValueError('Independent availability mismatch: '+label)
        return 0.
    difference = abs(actual-expected)
    if difference > TOLERANCE:
        raise ValueError(f'Independent calculation disagrees: {label} ({difference})')
    return difference


def check_scales(inventory, scales, specification):
    checks, maximum = [], 0.
    for layer, key in [('local_party', 'partyRecords'), ('candidate', 'candidateRecords')]:
        rows = inventory[key]
        moments = {year: independent_moments([r for r in rows if r['targetYear'] == year])
                   for year in sorted({r['targetYear'] for r in rows})}
        for fit in scales['folds'][layer]+[scales['descriptive'][layer]]:
            expected_rows = [r for r in rows if fit['targetYear'] is None or r['targetYear'] < fit['targetYear']]
            expected_years = sorted({r['targetYear'] for r in expected_rows})
            if fit['trainingYears'] != expected_years or fit['trainingIds'] != [r['targetElectorateId'] for r in expected_rows]:
                raise ValueError('Independent exact training membership mismatch')
            if fit['targetYear'] is not None and any(y >= fit['targetYear'] for y in fit['trainingYears']):
                raise ValueError('Nonchronological residual scales')
            for m in fit['moments']:
                for coordinate in ('balance', 'mass', 'within'):
                    for kind in ('shared', 'seat'):
                        maximum = max(maximum, close(moments[m['year']][coordinate][kind], m['moments'][coordinate][kind], 'environment moment'))
            for coordinate in ('balance', 'mass', 'within'):
                for kind in ('shared', 'seat'):
                    historical = [moments[y][coordinate][kind] for y in fit['trainingYears'] if moments[y][coordinate][kind] is not None]
                    pseudo = specification['priorPseudoEnvironments']
                    prior = specification['priors'][layer][coordinate][kind]
                    variance = (math.fsum(historical)+pseudo*prior**2)/(len(historical)+pseudo)
                    maximum = max(maximum, close(math.sqrt(variance), fit['scales'][coordinate][kind], 'pooled scale'))
                    contribution = fit['contributions'][coordinate][kind]
                    maximum = max(maximum, close(pseudo*prior**2/(len(historical)+pseudo), contribution['priorVarianceContribution'], 'prior variance contribution'))
                    maximum = max(maximum, close(math.fsum(historical)/(len(historical)+pseudo), contribution['historicalVarianceContribution'], 'history variance contribution'))
            checks.append({'layer': layer, 'targetYear': fit['targetYear'], 'trainingYears': fit['trainingYears'],
                           'scalarDirections': 2, 'remainderFit': 'independent QR, no normal-equation reuse'})
    return {'fits': checks, 'maximumAbsoluteDifference': maximum,
            'methods': 'math.log/fsum scalar odds and independent QR; equal-election shrinkage reconstructed'}


def logistic(value):
    if value >= 0:
        return 1/(1+math.exp(-value))
    e = math.exp(value)
    return e/(1+e)


def independent_expectation(location, sd, order=81):
    nodes, weights = np.polynomial.hermite.hermgauss(order)
    return math.fsum(float(w)*logistic(location+math.sqrt(2)*sd*float(z)) for z, w in zip(nodes, weights))/math.sqrt(math.pi)


def check_locations(inventory, scales):
    checks = []
    for layer, key in [('local_party', 'partyRecords'), ('candidate', 'candidateRecords')]:
        for fit in scales['folds'][layer]:
            rows = sorted([r for r in inventory[key] if r['targetYear'] == fit['targetYear']], key=lambda r: r['targetElectorateId'])
            for index in sorted({0, len(rows)//2, len(rows)-1}):
                row = rows[index];groups = row['groups'];mean = row['mean']
                major = [i for i, g in enumerate(groups) if g in ('national', 'labour')]
                mass = math.fsum(mean[i] for i in major)
                probabilities = {'mass': mass}
                if groups.count('national') == groups.count('labour') == 1 and mass > 0:
                    probabilities['balance'] = mean[groups.index('national')]/mass
                for name, probability in probabilities.items():
                    if not 0 < probability < 1:
                        continue
                    sd = math.sqrt(math.fsum(v*v for v in fit['scales'][name].values()))
                    location = float(mean_logit_location(np.array([probability]), sd)[0])
                    expectation = independent_expectation(location, sd)
                    gap = abs(expectation-probability)
                    if gap > TOLERANCE:
                        raise ValueError(f'GH81 conditional expectation differs: {layer}/{row["targetYear"]}/{name}/{gap}')
                    checks.append({'layer': layer, 'year': row['targetYear'], 'seatId': row['targetElectorateId'],
                        'direction': name, 'sd': sd, 'target': probability, 'GH81Expectation': expectation,
                        'absoluteGap': gap})
    return {'records': checks, 'maximumAbsoluteGap': max(c['absoluteGap'] for c in checks),
            'method': 'independent physicists Hermite81 rule, scalar logistic versus production normal-Hermite41 location'}


def major_delta_covariance(mean, groups, scales):
    n, l = groups.index('national'), groups.index('labour')
    mass = mean[n]+mean[l];ratio = mean[n]/mass
    d_balance = mass*ratio*(1-ratio)
    d_n = ratio*mass*(1-mass);d_l = (1-ratio)*mass*(1-mass)
    variance_b = math.fsum(v*v for v in scales['balance'].values())
    variance_m = math.fsum(v*v for v in scales['mass'].values())
    return {'NATVariance': d_balance*d_balance*variance_b+d_n*d_n*variance_m,
            'LABVariance': d_balance*d_balance*variance_b+d_l*d_l*variance_m,
            'NATLABCovariance': -d_balance*d_balance*variance_b+d_n*d_l*variance_m,
            'NLLogRatioVariance': variance_b}


def check_category_splitting(spec):
    examples = []
    for layer in ('local_party', 'candidate'):
        scales = spec['priors'][layer]
        original = major_delta_covariance([.45, .4, .15], ['national', 'labour', 'other'], scales)
        for count in (2, 10, 100):
            mean = [.45, .4]+[.15/count]*count
            actual = major_delta_covariance(mean, ['national', 'labour']+['other']*count, scales)
            if actual != original:
                raise ValueError('Splitting remainder changes major contrast covariance')
            examples.append({'layer': layer, 'remainderOptions': count, 'majorCovariance': actual})
    return {'examples': examples, 'interpretation': 'Delta covariance for arithmetic aggregate balances; within-remainder uncertainty cannot affect major mass/balance.'}


def scalar_quantile(values, probability):
    ordered = sorted(map(float, values))
    position = (len(ordered)-1)*probability
    lower = int(position);upper = min(lower+1, len(ordered)-1)
    return ordered[lower]+(position-lower)*(ordered[upper]-ordered[lower])


def cdf_crps(values, outcome):
    """Integrate squared empirical CDF error, independently of rank shortcut."""
    ordered = sorted(map(float, values));n = len(ordered)
    cuts = sorted(set(ordered+[float(outcome)]))
    count, areas = 0, []
    for lower, upper in zip(cuts, cuts[1:]):
        while count < n and ordered[count] <= lower:
            count += 1
        cdf = count/n
        truth = float(lower >= outcome)
        areas.append((upper-lower)*(cdf-truth)**2)
    return math.fsum(areas)


def scalar_energy(draws, actual, limit):
    selected = draws[:limit]
    def distance(a, b):
        return math.sqrt(math.fsum((float(v)-float(w))**2 for v, w in zip(a, b)))
    first = math.fsum(distance(row, actual) for row in selected)/len(selected)
    second = math.fsum(distance(a, b) for a in selected for b in selected)/(2*len(selected)**2)
    return first-second


def check_record(row, q, recorded, energy_limit):
    means = [math.fsum(map(float, q[:, i]))/len(q) for i in range(q.shape[1])]
    errors = [100*(m-a) for m, a in zip(means, row['actual'])]
    gaps = [close(m, v, 'arithmetic mean') for m, v in zip(means, recorded['simulatedMean'])]
    gaps += [close(e, v, 'share error') for e, v in zip(errors, recorded['errorPP'])]
    gaps += [close(math.fsum(map(abs, errors))/len(errors), recorded['maePP'], 'MAE'),
             close(math.fsum(e*e for e in errors)/len(errors), recorded['msePP2'], 'MSE'),
             close(math.fsum(errors)/len(errors), recorded['biasPP'], 'bias')]
    for i, truth in enumerate(row['actual']):
        values = 100*q[:, i];outcome = 100*truth
        gaps.append(close(cdf_crps(values, outcome), recorded['crpsPP'][i], 'CDF-integral CRPS'))
        for level, key in ((.5, 'interval50'), (.9, 'interval90')):
            alpha = 1-level
            lower, upper = scalar_quantile(values, alpha/2), scalar_quantile(values, 1-alpha/2)
            score = upper-lower+2/alpha*(max(lower-outcome, 0)+max(outcome-upper, 0))
            for name, value in [('lower', lower), ('upper', upper), ('widths', upper-lower), ('scores', score)]:
                gaps.append(close(value, recorded[key][name][i], 'proper interval '+name))
            if (lower <= outcome <= upper) != recorded[key]['covered'][i]:
                raise ValueError('Independent interval coverage disagreement')
    energy = scalar_energy(100*q, [100*a for a in row['actual']], energy_limit)
    gaps.append(close(energy, recorded['energyPP'], 'scalar energy'))
    if 'ranking' in recorded:
        ranking = recorded['ranking'];counts = [0.]*q.shape[1]
        for draw in q:
            maximum = max(draw);tied = [i for i, v in enumerate(draw) if abs(v-maximum) <= 1e-12]
            for i in tied:
                counts[i] += 1/len(tied)
        probabilities = [c/len(q) for c in counts]
        gaps += [close(p, v, 'fractional winner probability') for p, v in zip(probabilities, ranking['winnerProbabilities'])]
        actual = row['actual'];winners = [i for i, v in enumerate(actual) if abs(v-max(actual)) <= 1e-12]
        if len(winners) == 1:
            winner = winners[0]
            brier = math.fsum((p-float(i == winner))**2 for i, p in enumerate(probabilities))
            gaps.append(close(brier, ranking['winnerBrier'], 'winner Brier'))
            logloss = -math.log(probabilities[winner]) if probabilities[winner] else None
            gaps.append(close(logloss, ranking['winnerLogLoss'], 'winner log loss'))
        pair = ranking['predictionTimePair'];a, b = [row['ids'].index(i) for i in pair['ids']]
        margins = 100*(q[:, a]-q[:, b]);truth = 100*(actual[a]-actual[b])
        gaps.append(close(cdf_crps(margins, truth), pair['crpsPP'], 'competitive pair CRPS'))
        gaps.append(close(math.fsum(map(float, margins))/len(q), pair['meanSignedMarginPP'], 'competitive pair mean'))
    return max(gaps)


def scalar_summary(rows):
    average = lambda values: math.fsum(values)/len(values)
    result = {'contests': len(rows), 'coordinates': sum(len(r['ids']) for r in rows),
        'contestEqualMAEPP': average([r['maePP'] for r in rows]),
        'contestEqualRMSEPP': math.sqrt(average([r['msePP2'] for r in rows])),
        'contestEqualCRPSPP': average([average(r['crpsPP']) for r in rows]),
        'candidateCategoryEqualMAEPP': average([abs(e) for r in rows for e in r['errorPP']]),
        'candidateCategoryEqualRMSEPP': math.sqrt(average([e*e for r in rows for e in r['errorPP']])),
        'fullSlateBiasAccountingPP': average([r['biasPP'] for r in rows]),
        'energyPP': average([r['energyPP'] for r in rows])}
    for key in ('interval50', 'interval90'):
        covers = [v for r in rows for v in r[key]['covered']]
        result[key] = {'covered': sum(covers), 'total': len(covers), 'coverage': sum(covers)/len(covers),
            'contestEqualWidthPP': average([average(r[key]['widths']) for r in rows]),
            'contestEqualScorePP': average([average(r[key]['scores']) for r in rows])}
    result['groups'] = {}
    for group in sorted({g for r in rows for g in r['groups']}):
        selected = [(r, i) for r in rows for i, g in enumerate(r['groups']) if g == group]
        errors = [r['errorPP'][i] for r, i in selected]
        value = {'coordinates': len(selected), 'containingContests': len({r['id'] for r, _ in selected}),
                 'maePP': average(list(map(abs, errors))), 'rmsePP': math.sqrt(average([e*e for e in errors])),
                 'biasPP': average(errors), 'crpsPP': average([r['crpsPP'][i] for r, i in selected])}
        for key in ('interval50', 'interval90'):
            covers = [r[key]['covered'][i] for r, i in selected]
            value[key] = {'covered': sum(covers), 'total': len(covers), 'coverage': sum(covers)/len(covers),
                          'widthPP': average([r[key]['widths'][i] for r, i in selected]),
                          'scorePP': average([r[key]['scores'][i] for r, i in selected])}
        result['groups'][group] = value
    return result


def compare_subset(value, recorded, label='summary'):
    if isinstance(value, dict):
        return max([compare_subset(v, recorded[k], label+'.'+k) for k, v in value.items()], default=0)
    if isinstance(value, int):
        if value != recorded:
            raise ValueError('Independent denominator mismatch: '+label)
        return 0.
    return close(value, recorded, label)


def check_draw_scores(inventory, specification):
    from .construction import arrays
    construction, evaluation = read(PREFIX+'/construction.json'), read(PREFIX+'/evaluation.json')
    evaluated = {c['id']: c for c in evaluation['cases']}
    party = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    candidate = {r['targetElectorateId']: r for r in inventory['candidateRecords']}
    gap, vectors, selected, energy_changes, point_count = 0., 0, [], [], 0
    for case in construction['cases']:
        records = sorted(case['records'], key=lambda r: r['id'])
        choices = [records[i] for i in sorted({0, len(records)//2, len(records)-1})]
        lookup = party if case['layer'] == 'local_party' else candidate
        with arrays(case) as bank:
            for item in records:
                for policy in ('revised', 'unchanged_stage44'):
                    q = bank[policy+':'+item['id']]
                    if q.shape != (case['draws'], len(lookup[item['id']]['ids'])) or not np.isfinite(q).all() or np.any(q < 0) or np.max(abs(q.sum(axis=1)-1)) > 1e-12:
                        raise ValueError('Independent cached simplex failure')
                    vectors += len(q)
            for policy in ('revised', 'unchanged_stage44'):
                scored = {r['id']: r for r in evaluated[case['id']]['methods'][policy]['records']}
                for item in choices:
                    row = lookup[item['id']];q = bank[policy+':'+item['id']]
                    gap = max(gap, check_record(row, q, scored[item['id']], specification['energyDraws']))
                    energy128 = scored[item['id']]['energyPP']
                    energy256 = scalar_energy(100*q, [100*a for a in row['actual']], 256)
                    energy_changes.append({'case': case['id'], 'seatId': item['id'], 'policy': policy,
                                          'energy128PP': energy128, 'energy256PP': energy256,
                                          'changePP': energy256-energy128})
                    selected.append({'case': case['id'], 'seatId': item['id'], 'policy': policy})
            point_records = {r['id']: r for r in evaluated[case['id']]['methods']['point']['records']}
            for item in choices:
                row = lookup[item['id']]
                metadata = item['metadata']['unchanged_stage44']
                point = metadata.get('deterministicNationalOnlyMean', row['mean'])
                q = np.broadcast_to(np.array(point), (128, len(point)))
                gap = max(gap, check_record(row, q, point_records[item['id']], specification['energyDraws']))
                point_count += 1
        for policy in ('revised', 'unchanged_stage44', 'point'):
            result = evaluated[case['id']]['methods'][policy]
            gap = max(gap, compare_subset(scalar_summary(result['records']), result['summary']))
        r = evaluated[case['id']]['methods']['revised']['records']
        for policy in ('unchanged_stage44', 'point'):
            c = evaluated[case['id']]['methods'][policy]['records']
            paired = math.fsum(math.fsum(a-b for a, b in zip(x['crpsPP'], y['crpsPP']))/len(x['ids']) for x, y in zip(r, c))/len(r)
            gap = max(gap, close(paired, evaluated[case['id']]['revisedMinusComparatorCRPSPP'][policy], 'paired CRPS'))
    for layer in ('local_party', 'candidate', 'composed'):
        subset = [c for c in evaluation['cases'] if c['layer'] == layer]
        for policy in ('revised', 'unchanged_stage44', 'point'):
            rows = [r for c in subset for r in c['methods'][policy]['records']]
            pooled = evaluation['pooled'][layer][policy]
            gap = max(gap, compare_subset(scalar_summary(rows), pooled['contestWeighted']))
            equal = math.fsum(c['methods'][policy]['summary']['contestEqualCRPSPP'] for c in subset)/len(subset)
            gap = max(gap, close(equal, pooled['equalElectionCRPSPP'], 'equal-election weighting'))
    convergence = read(PREFIX+'/convergence.json')
    if construction['draws'] != convergence['selectedDraws'] or construction['precisionStatus'] != convergence['status']:
        raise ValueError('Independent integration status mismatch')
    return {'status': 'sealed outputs independently verified', 'simplexDrawVectors': vectors,
            'pointReferenceRecords': point_count,
            'representativeRecords': selected, 'maximumAbsoluteDifference': gap,
            'integrationPrecision': {'draws': construction['draws'], 'frozenConvergencePassed': convergence['converged'],
                'status': construction['precisionStatus'],
                'interpretation': 'Numerically audited arithmetic does not overturn failed finite-integration precision gates.'},
            'methods': 'scalar empirical-CDF CRPS integral, quantiles, interval scores, Euclidean energy, winner probabilities, fsum group/pool arithmetic',
            'energyNumericalSensitivity': {'estimatorUnchanged': True, 'energy128Versus256': energy_changes,
                'maximumAbsoluteChangePP': max(abs(r['changePP']) for r in energy_changes)}}


def build():
    inventory, scales, spec = read(OLD+'/inventory.json'), read(PREFIX+'/scales.json'), read(PREFIX+'/specification.json')
    return {'stage': 45, 'scaleAudit': check_scales(inventory, scales, spec),
            'conditionalLocationAudit': check_locations(inventory, scales),
            'majorCategorySplitAudit': check_category_splitting(spec),
            'drawScoreAudit': check_draw_scores(inventory, spec),
            'operationalSelection': None}


def main():
    args = arguments();verify();value = build();save('independent-verification.json', value, args.check)
    print('Stage45 independent scales/conditional locations verified', value['scaleAudit']['maximumAbsoluteDifference'], value['conditionalLocationAudit']['maximumAbsoluteGap'])


if __name__ == '__main__':
    main()
