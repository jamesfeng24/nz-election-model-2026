"""Sharp support functions for coupled, rounded source rows and target ballots."""

from math import isfinite


PROB_TOL = 1e-8
BALLOT_TOL = 1e-5
SHARE_TOL = 1e-9


class LedgerGeometryError(ValueError):
    """A source row or target ledger violates its mathematical contract."""


def row_maximum(cells, coefficients):
    """Maximize a linear objective on one bounded probability simplex."""
    if len(cells) != len(coefficients) or not cells:
        raise LedgerGeometryError('Missing or mismatched source cells')
    lower = [cell['bounds'][0] for cell in cells]
    upper = [cell['bounds'][1] for cell in cells]
    if any(not all(isfinite(value) for value in bounds) or
           not 0 <= bounds[0] <= bounds[1] <= 1
           for bounds in (cell['bounds'] for cell in cells)):
        raise LedgerGeometryError('Invalid source rounding bounds')
    if sum(lower) > 1 + PROB_TOL or sum(upper) < 1 - PROB_TOL:
        raise LedgerGeometryError('Infeasible coupled source row')
    remaining = 1 - sum(lower)
    value = sum(prob * coefficient for prob, coefficient in zip(lower, coefficients))
    for index in sorted(range(len(cells)), key=lambda i: (-coefficients[i], i)):
        added = min(max(0, upper[index] - lower[index]), max(0, remaining))
        value += added * coefficients[index]
        remaining -= added
    if abs(remaining) > PROB_TOL:
        raise LedgerGeometryError('Source row did not conserve probability')
    return value


def route_maximum(origin, destination_coefficients):
    """Exact support of one target ballot-origin route set."""
    mass = origin['mass']
    if not isfinite(mass) or mass < 0:
        raise LedgerGeometryError('Invalid target origin mass')
    if mass == 0:
        return 0.0
    if origin['routing'] == 'free':
        return mass * max(destination_coefficients.values())
    if origin['routing'] == 'diagonal':
        return mass * destination_coefficients[origin['destination']]
    if origin['routing'] not in ('primary', 'heterogeneity'):
        raise LedgerGeometryError('Unknown routing contract')
    pool = origin['pool']
    rows = pool['rows']
    if not rows or pool['totalMass'] <= 0:
        raise LedgerGeometryError('Empty source pool used as constrained routing')
    free_coefficient = max(destination_coefficients.values())
    row_values = []
    for row in rows:
        coefficients = [destination_coefficients.get(
            origin['sourceCategoryDestinations'].get(cell['category']), free_coefficient)
            for cell in row['cells']]
        row_values.append(row_maximum(row['cells'], coefficients))
    if origin['routing'] == 'heterogeneity':
        return mass * max(row_values)
    return mass * sum(row['mass'] * value for row, value in zip(rows, row_values)) / pool['totalMass']


def contest_maximum(origins, coefficients):
    return sum(route_maximum(origin, coefficients) for origin in origins)


def contest_minimum(origins, coefficients):
    return -contest_maximum(origins, {key: -value for key, value in coefficients.items()})


def linear_bounds(origins, coefficients):
    low = contest_minimum(origins, coefficients)
    high = contest_maximum(origins, coefficients)
    if low < -BALLOT_TOL or high < low - BALLOT_TOL:
        raise LedgerGeometryError('Impossible linear bound')
    return [max(0.0, low), max(0.0, high)]


def share_bounds(origins, candidate_id, destinations, candidate_ids, denominator):
    """Sharp ratio extrema from the same coupled contest support oracle."""
    if denominator[0] <= 1e-8:
        return {'status': 'undefined_zero_feasible_denominator', 'bounds': None}
    candidates = set(candidate_ids)
    def coefficients(ratio):
        return {destination: (1.0 if destination == candidate_id else 0.0) -
                (ratio if destination in candidates else 0.0)
                for destination in destinations}

    # On 0 < r < 1, candidate / noncandidate / other-candidate objective
    # ordering is fixed. Each source-row optimum is therefore one affine
    # line in r. Only the seat chosen by the heterogeneity hull can switch.
    def affine_line(origin, maximize):
        def value(ratio):
            objective = coefficients(ratio)
            if maximize:
                return route_maximum(origin, objective)
            return -route_maximum(origin, {key: -coefficient
                                           for key, coefficient in objective.items()})
        first, second = value(0.25), value(0.75)
        valid_candidate_votes = (first - second) / 0.5
        candidate_votes = first + 0.25 * valid_candidate_votes
        return candidate_votes, valid_candidate_votes

    def lines(maximize):
        result = []
        for origin in origins:
            if origin['routing'] == 'heterogeneity':
                row_lines = []
                for row in origin['pool']['rows']:
                    single = origin | {'routing': 'primary',
                                       'pool': {'totalMass': row['mass'],
                                                'rows': [row]}}
                    row_lines.append(affine_line(single, maximize))
                result.append((row_lines, True))
            else:
                result.append(([affine_line(origin, maximize)], False))
        return result

    maximum_lines, minimum_lines = lines(True), lines(False)

    def line_value(family, ratio, maximize):
        total = 0.0
        for row_lines, hull in family:
            values = [votes - ratio * valid for votes, valid in row_lines]
            total += (max(values) if maximize else min(values)) if hull else values[0]
        return total

    lower, upper = 0.0, 1.0
    for _ in range(42):
        middle = (lower + upper) / 2
        if line_value(maximum_lines, middle, True) >= 0:
            lower = middle
        else:
            upper = middle
    maximum = (lower + upper) / 2
    lower, upper = 0.0, 1.0
    for _ in range(42):
        middle = (lower + upper) / 2
        if line_value(minimum_lines, middle, False) <= 0:
            upper = middle
        else:
            lower = middle
    minimum = (lower + upper) / 2
    if maximum < minimum - SHARE_TOL:
        raise LedgerGeometryError('Impossible candidate-share bounds')
    if (abs(contest_maximum(origins, coefficients(maximum))) > BALLOT_TOL or
            abs(contest_minimum(origins, coefficients(minimum))) > BALLOT_TOL):
        raise LedgerGeometryError('Candidate-share root residual too large')
    return {'status': 'defined', 'bounds': [minimum, maximum]}
