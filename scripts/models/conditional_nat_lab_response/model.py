"""One deterministic OLS family with explicit training and uncertainty contracts."""
from fractions import Fraction
from math import isfinite, sqrt


MODES = ('actual_observed_local_party', 'additive', 'proportional', 'log_odds')


def solve_normal_equations(design, outcome):
    """Small rational elimination; detect deficient/near-deficient Gram systems."""
    size = len(design[0])
    x = [[Fraction(str(v)) for v in row] for row in design]
    y = [Fraction(str(v)) for v in outcome]
    matrix = [[sum(row[i] * row[j] for row in x) for j in range(size)] +
              [sum(row[i] * value for row, value in zip(x, y))] for i in range(size)]
    scale = max(Fraction(1), max(abs(v) for row in matrix for v in row[:size]))
    for column in range(size):
        pivot = max(range(column, size), key=lambda i: abs(matrix[i][column]))
        if abs(matrix[pivot][column]) <= scale * Fraction(1, 10**12):
            return None
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        divisor = matrix[column][column]
        matrix[column] = [v / divisor for v in matrix[column]]
        for i in range(size):
            if i == column:
                continue
            multiplier = matrix[i][column]
            matrix[i] = [v - multiplier * p for v, p in zip(matrix[i], matrix[column])]
    return [float(row[-1]) for row in matrix]


def fit(rows, definition):
    columns, fixed = definition['columns'], definition['fixedBeta']
    if not columns:
        return {'status': 'available', 'alpha': 0.0, 'beta': float(fixed),
                'gamma': 0.0, 'n': 0, 'trainingRecordIds': [], 'trainingTargetYears': []}
    unavailable = lambda reason: {'status': 'abstain', 'reason': reason, 'n': len(rows)}
    if not rows:
        return unavailable('no_earlier_training_transition')
    if len({r['party'] for r in rows}) != 1:
        raise ValueError('Separate-party fit required')
    if len(rows) < 5 * len(columns):
        return unavailable('too_few_training_records')
    if 'sourceWon' in columns:
        if any(r['sourceWon'] not in (0, 1) for r in rows):
            return unavailable('unknown_source_victory')
        if min(sum(r['sourceWon'] == value for r in rows) for value in (0, 1)) < 5:
            return unavailable('insufficient_source_status_groups')
    design, outcome = [], []
    for row in rows:
        values = {'intercept': 1.0, 'x': row['x'], 'sourceWon': row['sourceWon']}
        design.append([values[c] for c in columns])
        outcome.append(row['y'] - (fixed * row['x'] if fixed is not None else 0))
    if not all(isfinite(v) for row in design for v in row) or not all(isfinite(v) for v in outcome):
        raise ValueError('Nonfinite regression input')
    coefficients = solve_normal_equations(design, outcome)
    if coefficients is None:
        return unavailable('rank_deficient_or_near_singular')
    by_column = dict(zip(columns, coefficients))
    return {'status': 'available', 'alpha': by_column.get('intercept', 0.0),
            'beta': by_column.get('x', float(fixed) if fixed is not None else 0.0),
            'gamma': by_column.get('sourceWon', 0.0), 'n': len(rows),
            'trainingRecordIds': [r['id'] for r in rows],
            'trainingTargetYears': sorted({r['targetYear'] for r in rows})}


def training_rows(rows, test):
    if not test:
        raise ValueError('Empty holdout')
    source_years = {r['sourceYear'] for r in test}
    if len(source_years) != 1:
        raise ValueError('Mixed holdout transitions')
    cutoff = next(iter(source_years))
    train = [r for r in rows if r['targetYear'] < cutoff]
    if set(r['id'] for r in train) & set(r['id'] for r in test):
        raise ValueError('Training/holdout overlap')
    return train


def predict(row, fitted, mode):
    """Read covariates only; target candidate outcome is intentionally unused."""
    if fitted['status'] != 'available':
        return None
    bounds = row['partyInputs'][mode]
    if (len(bounds) != 2 or not all(isfinite(v) for v in bounds)
            or not 0 <= bounds[0] <= bounds[1] <= 1):
        raise ValueError('Invalid target party-share bounds')
    if fitted['gamma'] != 0 and row['sourceWon'] not in (0, 1):
        return None
    intercept = row['c0'] + fitted['alpha'] + fitted['gamma'] * (row['sourceWon'] or 0)
    endpoints = sorted(intercept + fitted['beta'] * (p - row['p0']) for p in bounds)
    return {'id': row['id'], 'bounds': endpoints,
            'point': endpoints[0] if endpoints[0] == endpoints[1] else None,
            'outOfRangePossible': endpoints[0] < 0 or endpoints[1] > 1,
            'outOfRangeCertain': endpoints[1] < 0 or endpoints[0] > 1}


def score(predictions, rows):
    actual = {r['id']: r['c1'] for r in rows}
    if len(actual) != len(rows) or len(predictions) != len(rows):
        raise ValueError('Scoring sample mismatch')
    lows, highs, signed_lows, signed_highs = [], [], [], []
    for prediction in predictions:
        a, b = prediction['bounds']
        y = actual[prediction['id']]
        lows.append(max(0.0, a - y, y - b))
        highs.append(max(abs(a - y), abs(b - y)))
        signed_lows.append(a - y)
        signed_highs.append(b - y)
    n = len(rows)
    if not n:
        return None
    result = {'n': n, 'recordIds': [p['id'] for p in predictions],
              'maePP': [100 * sum(v) / n for v in (lows, highs)],
              'rmsePP': [100 * sqrt(sum(x*x for x in v) / n) for v in (lows, highs)],
              'biasPP': [100 * sum(v) / n for v in (signed_lows, signed_highs)],
              'outOfRangePossible': sum(p['outOfRangePossible'] for p in predictions),
              'outOfRangeCertain': sum(p['outOfRangeCertain'] for p in predictions),
              'pointCount': sum(p['point'] is not None for p in predictions)}
    return result
