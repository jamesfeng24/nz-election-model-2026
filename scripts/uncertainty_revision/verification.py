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
        moments['within'] = {'shared': None, 'seat': None}
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


def build():
    inventory, scales, spec = read(OLD+'/inventory.json'), read(PREFIX+'/scales.json'), read(PREFIX+'/specification.json')
    return {'stage': 45, 'scaleAudit': check_scales(inventory, scales, spec),
            'conditionalLocationAudit': check_locations(inventory, scales),
            'majorCategorySplitAudit': check_category_splitting(spec),
            'drawScoreAudit': {'status': 'pending sealed construction/evaluation', 'newScoring': False},
            'operationalSelection': None}


def main():
    args = arguments();verify();value = build();save('independent-verification.json', value, args.check)
    print('Stage45 independent scales/conditional locations verified', value['scaleAudit']['maximumAbsoluteDifference'], value['conditionalLocationAudit']['maximumAbsoluteGap'])


if __name__ == '__main__':
    main()
