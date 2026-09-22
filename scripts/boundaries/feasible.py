"""Exact bounds for disjoint integer population groups with destination controls.

No statistical model, nominal allocation or recovery of suppressed observations.
Each destination has a fixed published total and independent bounded cells.
"""
from fractions import Fraction


def bounded_sum_component(lower, upper, other_lower, other_upper, total):
    values = (lower, upper, other_lower, other_upper, total)
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError('Expected nonnegative integer bounds/control')
    if lower > upper or other_lower > other_upper:
        raise ValueError('Reversed population bounds')
    lo, hi = max(lower, total - other_upper), min(upper, total - other_lower)
    if lo > hi:
        raise ValueError('Population bounds incompatible with destination control')
    return lo, hi


def tighten_destinations(edges, controls):
    """Sharp marginal edge bounds; all original destination equations still apply."""
    totals = {}
    seen = set()
    for edge in edges:
        key = edge['source'], edge['target']
        if key in seen:
            raise ValueError('Duplicate population edge')
        seen.add(key)
        lo, hi = edge['lower'], edge['upper']
        if type(lo) is not int or type(hi) is not int or lo < 0 or lo > hi:
            raise ValueError('Invalid edge population bounds')
        values = totals.setdefault(edge['target'], [0, 0])
        values[0] += lo
        values[1] += hi
    if totals.keys() != controls.keys():
        raise ValueError('Destination control coverage mismatch')
    result = []
    for edge in edges:
        lower, upper = totals[edge['target']]
        lo, hi = bounded_sum_component(edge['lower'], edge['upper'],
                                      lower - edge['lower'], upper - edge['upper'],
                                      controls[edge['target']])
        result.append({**edge, 'lower': lo, 'upper': hi})
    return result


def ratio_interval(lower, upper, other_lower, other_upper):
    """Sharp component/sum bounds when component and other sums are independent."""
    if min(lower, upper, other_lower, other_upper) < 0 or lower > upper or other_lower > other_upper:
        raise ValueError('Invalid ratio population bounds')
    if lower + other_lower <= 0:
        raise ValueError('Source population can be zero; weight undefined')
    return Fraction(lower, lower + other_upper), Fraction(upper, upper + other_lower)


def fraction_json(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


def outgoing_weight_bounds(edges):
    """Each source edge is in a different controlled destination: independence holds.

    Bounds for different weights are not independent. Every feasible joint
    allocation must retain the population variables and sum constraints.
    """
    totals = {}
    for edge in edges:
        total = totals.setdefault(edge['source'], [0, 0])
        total[0] += edge['lower']
        total[1] += edge['upper']
    result = []
    for edge in edges:
        lo, hi = totals[edge['source']]
        lower, upper = ratio_interval(edge['lower'], edge['upper'],
                                      lo - edge['lower'], hi - edge['upper'])
        result.append({**edge, 'sourcePopulationLower': lo, 'sourcePopulationUpper': hi,
                       'weightLower': fraction_json(lower), 'weightUpper': fraction_json(upper),
                       'weight': float(lower) if lower == upper else None,
                       'uniquelyIdentified': lower == upper})
    return result


def aggregate(cells):
    edges = {}
    for cell in cells:
        key = cell['source'], cell['target']
        edge = edges.setdefault(key, {'source': key[0], 'target': key[1], 'lower': 0,
                                     'upper': 0, 'meshblockCount': 0, 'suppressedCount': 0})
        edge['lower'] += cell['population']['lower']
        edge['upper'] += cell['population']['upper']
        edge['meshblockCount'] += 1
        edge['suppressedCount'] += cell['population']['status'] == 'suppressed'
    return [edges[k] for k in sorted(edges)]
