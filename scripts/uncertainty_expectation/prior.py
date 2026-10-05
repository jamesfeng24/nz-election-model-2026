"""Saved-scale attribution and exact major-product variance identities, not fits."""
import math
import numpy as np
from scipy.special import expit, roots_hermitenorm

from scripts.uncertainty_revision.coordinates import mean_logit_location, partition
from .common import INVENTORY, SCALES, arguments, read, save, verify


def moment_definition(coordinate, kind):
    if coordinate != 'within':
        return ('squared equal-seat election residual mean; one scalar df' if kind == 'shared'
                else 'equal-seat population variance about election mean; no Bessel correction')
    return ('squared centered ballot-label effects / (distinct labels - 1); full-rank only'
            if kind == 'shared' else
            'equal-seat squared projected leftover / (remainder options - 1); '
            'unprojected residual retained when shared-label fit is rank deficient')


def scale_entry(fold, coordinate, kind, prior_sd, pseudo):
    """Independently decompose a saved variance without re-estimating residuals."""
    if (not math.isfinite(prior_sd) or prior_sd < 0 or pseudo <= 0
            or any(year >= fold['targetYear'] for year in fold['trainingYears'])):
        raise ValueError('Invalid prior or non-earlier scale environment')
    moments = []
    for environment in fold['moments']:
        if environment['year'] not in fold['trainingYears']:
            raise ValueError('Moment year differs from permitted earlier scale environments')
        value = environment['moments'][coordinate]
        moments.append({'year': environment['year'], 'secondMoment': value[kind],
                        'records': value['records'], 'rank': value.get('rank'),
                        'columns': value.get('columns')})
    available = [m for m in moments if m['secondMoment'] is not None]
    unavailable = [m['year'] for m in moments if m['secondMoment'] is None]
    values = [float(m['secondMoment']) for m in available]
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid saved second moment')
    denominator = len(values) + pseudo
    historical = math.fsum(values) / denominator
    prior = pseudo * prior_sd ** 2 / denominator
    variance = historical + prior
    saved_sd = fold['scales'][coordinate][kind]
    saved = fold['contributions'][coordinate][kind]
    checks = ((saved_sd ** 2, variance),
              (saved['historicalVarianceContribution'], historical),
              (saved['priorVarianceContribution'], prior))
    if saved['environments'] != len(values) or any(
            not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14) for a, b in checks):
        raise ValueError('Saved-scale decomposition differs from frozen moments')
    return {'layer': fold['layer'], 'targetYear': fold['targetYear'],
            'coordinate': coordinate, 'kind': kind, 'trainingYears': fold['trainingYears'],
            'availableYears': [m['year'] for m in available], 'unavailableYears': unavailable,
            'earlierEnvironments': len(values), 'priorElectionEquivalents': pseudo,
            'priorWeight': pseudo / denominator,
            'priorSD': prior_sd, 'historicalMomentSum': math.fsum(values),
            'historicalVarianceContribution': historical, 'priorVarianceContribution': prior,
            'actualPriorVarianceFraction': prior / variance if variance else None,
            'resultingVariance': variance, 'resultingSD': saved_sd,
            'empiricalOnlySD': math.sqrt(math.fsum(values) / len(values)) if values else None,
            'moments': moments, 'momentDefinition': moment_definition(coordinate, kind),
            'units': 'dimensionless log odds' if coordinate != 'within' else
                     'unprojected exchangeable log-intensity scale; not each CLR coordinate SD',
            'rankFailureDoesNotBecomeZero': True, 'momentClippingOrTruncation': False}


def logistic_moments(probability, sd, order):
    """Independent GH moments at the original frozen GH41 location."""
    if not 0 <= probability <= 1 or not math.isfinite(sd) or sd < 0:
        raise ValueError('Invalid logistic probability or scale')
    if probability in (0., 1.):
        return {'mean': probability, 'secondMoment': probability, 'variance': 0.,
                'frozenLocation': None, 'zeroFace': True}
    location = float(mean_logit_location(np.array([probability]), sd)[0])
    nodes, weights = roots_hermitenorm(order)
    values = expit(location + sd * nodes)
    mean = float(math.fsum((values * weights).tolist()) / math.sqrt(2 * math.pi))
    second = float(math.fsum((values ** 2 * weights).tolist()) / math.sqrt(2 * math.pi))
    return {'mean': mean, 'secondMoment': second, 'variance': max(0., second - mean ** 2),
            'frozenLocation': location, 'zeroFace': False}


def product_variance(mass, ratio):
    """Exact Var(MR) for independent mass and balance; interaction is explicit."""
    vm, vr = mass['variance'], ratio['variance']
    m, r = mass['mean'], ratio['mean']
    mass_term, balance_term, interaction = r * r * vm, m * m * vr, vm * vr
    total = mass_term + balance_term + interaction
    direct = mass['secondMoment'] * ratio['secondMoment'] - (m * r) ** 2
    if not math.isclose(total, direct, rel_tol=1e-10, abs_tol=1e-14):
        raise ValueError('Major-product variance identity failed')
    return {'massContribution': mass_term, 'balanceContribution': balance_term,
            'nonlinearInteraction': interaction, 'nationalVariance': total,
            'nationalLabourCovariance': vm * r * (1 - r) - mass['secondMoment'] * vr,
            'units': 'share squared', 'quantileWidthsAreNotAdditive': True}


def major_variance(row, scales):
    """Audit conditional major variance; candidate outcomes are never accessed."""
    n, l, other = partition(row['groups'])
    if not n or not l:
        return {'layer': row['layer'], 'targetYear': row['targetYear'],
                'targetElectorateId': row['targetElectorateId'], 'status': 'major_balance_absent'}
    base = np.asarray(row['mean'], float)
    mass = float(base[n[0]] + base[l[0]])
    ratio = float(base[n[0]] / mass) if mass else 0.
    mass_sd = math.hypot(scales['mass']['shared'], scales['mass']['seat']) if other else 0.
    balance_sd = math.hypot(scales['balance']['shared'], scales['balance']['seat'])
    checks = {}
    for order in (81, 161):
        m = logistic_moments(mass, mass_sd, order)
        r = logistic_moments(ratio, balance_sd, order)
        checks[str(order)] = {'mass': m, 'balance': r, 'product': product_variance(m, r)}
    reference = checks['161']
    gap = max(abs(checks['81'][name][key] - reference[name][key])
              for name in ('mass', 'balance') for key in ('mean', 'secondMoment'))
    mean_gap = max(abs(reference['mass']['mean'] - mass),
                   abs(reference['balance']['mean'] - ratio))
    return {'layer': row['layer'], 'targetYear': row['targetYear'],
            'targetElectorateId': row['targetElectorateId'], 'status': 'defined',
            'frozenDeterministicMass': mass, 'frozenDeterministicRatio': ratio,
            'massSD': mass_sd, 'balanceSD': balance_sd, 'integrationOrders': checks,
            'maximum81To161MomentDifferencePP': 100 * gap,
            'maximumFrozenLocationConditionalMeanGapPP': 100 * mean_gap,
            'independentOrderAgreementAt005PP': 100 * gap <= .05,
            'conditionalMeanAt005PP': 100 * mean_gap <= .05,
            'samplingLaw': 'independent Gaussian aggregate mass and NL balance',
            'withinRemainderDoesNotEnterMajorVariance': True,
            'outcomesUsed': False}


def build():
    saved = read(SCALES)
    specification = read('data/processed/uncertainty-revision/specification.json')
    inventory = read(INVENTORY)
    entries, major = [], []
    for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords')):
        for fold in saved['folds'][layer]:
            for coordinate in ('balance', 'mass', 'within'):
                for kind in ('shared', 'seat'):
                    entries.append(scale_entry(fold, coordinate, kind,
                                   specification['priors'][layer][coordinate][kind],
                                   specification['priorPseudoEnvironments']))
            for row in inventory[key]:
                if row['targetYear'] == fold['targetYear']:
                    major.append(major_variance(row, fold['scales']))
    return {'stage': 47, 'sourceScales': SCALES, 'sourceInventory': INVENTORY,
            'refitted': False, 'heldOutScoresCalculated': False,
            'varianceUnits': 'dimensionless log units squared; analytic share variance explicitly labelled',
            'scaleAttribution': entries, 'conditionalMajorVariance': major,
            'cautions': ['prior weight differs from prior contribution to actual variance',
                         'remainder projected covariance depends on repeated ballot labels',
                         'empirical-only scales are descriptive, not replacement forecasts',
                         'product variance interaction is not additive interval-width attribution']}


def main():
    args = arguments()
    verify()
    value = build()
    save('prior-audit.json', value, args.check)
    print('Stage47 saved-scale prior attribution and independent aggregate-moment audit reproduced')


if __name__ == '__main__':
    main()
