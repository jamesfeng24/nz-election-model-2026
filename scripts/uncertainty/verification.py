"""Independent scalar log coordinates and QR-based uncertainty arithmetic audit."""
from math import fsum, log, sqrt

import numpy as np

from .common import PREFIX, YEARS, arguments, read, save, verify

TOLERANCE = 1e-10


def coordinates(values, epsilon):
    """Compute CLR directly; its common zero-replacement denominator cancels."""
    if not values or any(not np.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid independent residual vector')
    logs = [log(v + epsilon) for v in values]
    center = fsum(logs) / len(logs)
    return np.array([v - center for v in logs])


def residual(row, epsilon):
    return coordinates(row['actual'], epsilon) - coordinates(row['mean'], epsilon)


def contrasts(count):
    """Construct orthonormal Helmert columns explicitly, without scipy helper."""
    result = np.zeros((count, count - 1))
    for column in range(count - 1):
        denominator = sqrt((column + 1) * (column + 2))
        result[:column + 1, column] = 1 / denominator
        result[column + 1, column] = -(column + 1) / denominator
    return result


def category_design(groups, labels):
    matrix = np.array([[float(group == label) for label in labels] for group in groups])
    return matrix - np.sum(matrix, axis=0) / len(groups)


def environment(rows, labels, epsilon):
    contrast = contrasts(len(labels))
    x, y = [], []
    for row in rows:
        weight = sqrt(len(row['ids']))
        x.extend(category_design(row['groups'], labels) @ contrast / weight)
        y.extend(residual(row, epsilon) / weight)
    x, y = np.asarray(x), np.asarray(y)
    singular = np.linalg.svd(x, compute_uv=False)
    rank = int(np.sum(singular > max(1e-12, singular[0] * 1e-10)))
    identifiable = singular[-1] > singular[0] * 1e-10 and singular[-1] > 1e-12
    if identifiable:
        orthogonal, triangular = np.linalg.qr(x, mode='reduced')
        coefficients = np.linalg.solve(triangular, orthogonal.T @ y)
        effects = contrast @ coefficients
        shared = fsum(float(v) ** 2 for v in effects) / (len(labels) - 1)
    else:
        effects = np.zeros(len(labels))
        shared = None
    seat = []
    for row in rows:
        remainder = residual(row, epsilon) - category_design(row['groups'], labels) @ effects
        seat.append(fsum(float(v) ** 2 for v in remainder) / (len(remainder) - 1))
    return {'rank': rank, 'identifiable': bool(identifiable), 'effects': effects,
            'shared': shared, 'seat': fsum(seat) / len(seat)}


def verify_fit(rows, layer, target_year, saved, spec):
    eligible = [r for r in rows if target_year is None or r['targetYear'] < target_year]
    years = sorted({r['targetYear'] for r in eligible})
    if saved['trainingYears'] != years or saved['trainingIds'] != [r['targetElectorateId'] for r in eligible]:
        raise ValueError('Independent chronology membership mismatch')
    moments = []
    gap, identities = 0., 0
    for year in years:
        rows_year = [r for r in eligible if r['targetYear'] == year]
        calculated = environment(rows_year, spec['sharedClasses'][layer], spec['zeroReplacement'])
        recorded = next(m for m in saved['moments'] if m['targetYear'] == year)
        if calculated['rank'] != recorded['sharedRank'] or calculated['identifiable'] != recorded['sharedIdentifiable']:
            raise ValueError('Independent rank audit mismatch')
        for name, value in zip(spec['sharedClasses'][layer], calculated['effects']):
            gap = max(gap, abs(float(value) - recorded['classEffects'][name]))
            identities += 1
        for name, key in (('shared', 'sharedSecondMoment'), ('seat', 'seatSecondMoment')):
            value = calculated[name]
            if (value is None) != (recorded[key] is None):
                raise ValueError('Independent missing shared moment mismatch')
            if value is not None:
                gap = max(gap, abs(value - recorded[key]))
                identities += 1
        moments.append(calculated)
    for name in ('shared', 'seat'):
        values = [m[name] for m in moments if m[name] is not None]
        weight = spec['priorPseudoEnvironments']
        scale = sqrt((fsum(values) + weight * spec['priorScales'][layer][name] ** 2) / (len(values) + weight))
        gap = max(gap, abs(scale - saved['scales'][name]))
        identities += 1
    if gap > TOLERANCE:
        raise ValueError('Independent moment/scale disagreement')
    return identities, gap


def build():
    inventory = read(PREFIX + '/inventory.json')
    scales = read(PREFIX + '/scales.json')
    spec = read(PREFIX + '/specification.json')
    identities, gap, fits = 0, 0., 0
    residual_coordinates = 0
    for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords')):
        rows = inventory[key]
        for row in rows:
            value = residual(row, spec['zeroReplacement'])
            if abs(fsum(float(v) for v in value)) > TOLERANCE:
                raise ValueError('Independent CLR conservation mismatch')
            residual_coordinates += len(value)
        for saved in scales['folds'][layer] + [scales['descriptive'][layer]]:
            n, difference = verify_fit(rows, layer, saved['targetYear'], saved, spec)
            identities += n
            gap = max(gap, difference)
            fits += 1
    return {'stage': 44, 'independentMethods': ['scalar CLR logs with fsum',
                'explicit Helmert coordinates', 'QR rather than normal-equation solve',
                'equal-election prior-shrunk second moments'],
            'residualVectors': len(inventory['partyRecords']) + len(inventory['candidateRecords']),
            'residualCoordinates': residual_coordinates, 'chronologicalAndDescriptiveFits': fits,
            'momentAndScaleIdentities': identities, 'tolerance': TOLERANCE,
            'maximumDifferenceRounded12Decimals': round(gap, 12),
            'allChecksPassed': True, 'historicalMeanFittingPerformed': False,
            'simulationAndScoreChecks': 'pending construction/evaluation archives'}


def main():
    args = arguments()
    verify()
    value = build()
    save('independent-verification.json', value, args.check)
    print('Stage44 independent moments/scales verified', value['momentAndScaleIdentities'])


if __name__ == '__main__':
    main()
