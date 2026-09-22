"""Composition summaries for a controlled integer population partition."""
import itertools
from fractions import Fraction
from scripts.boundaries.feasible import fraction_json


def _minimum_squares(lower, upper, total):
    # Discrete water filling minimizes convex sum of squares; no cells estimated.
    lo, hi = min(lower), max(upper)
    while lo < hi:
        level = (lo + hi + 1) // 2
        if sum(max(a, min(b, level)) for a, b in zip(lower, upper)) <= total:
            lo = level
        else:
            hi = level - 1
    allocation = [max(a, min(b, lo)) for a, b in zip(lower, upper)]
    residual = total - sum(allocation)
    for i in sorted(range(len(lower)), key=lambda j: (allocation[j], j)):
        if residual and allocation[i] < upper[i]:
            allocation[i] += 1
            residual -= 1
    if residual:
        raise ValueError('Unresolved discrete convex minimum')
    return sum(v * v for v in allocation)


def _maximum_squares(lower, upper, total):
    # A convex maximum lies at a box/hyperplane vertex. Integer bounds and
    # integer total make each vertex integral. Small predecessor inventories.
    if len(lower) > 16:
        raise ValueError('Too many predecessors for exact vertex enumeration')
    maximum = None
    for pivot in range(len(lower)):
        others = [i for i in range(len(lower)) if i != pivot]
        for values in itertools.product(*[(lower[i], upper[i]) for i in others]):
            remainder = total - sum(values)
            if lower[pivot] <= remainder <= upper[pivot]:
                score = sum(v * v for v in values) + remainder * remainder
                maximum = score if maximum is None else max(maximum, score)
    if maximum is None:
        raise ValueError('No feasible population partition')
    return maximum


def summarize(edges, total):
    lower = [e['lower'] for e in edges]
    upper = [e['upper'] for e in edges]
    if not lower or sum(lower) > total or sum(upper) < total or total <= 0:
        raise ValueError('Invalid controlled composition')
    lo, hi = max(lower), max(upper)
    while lo < hi:
        middle = (lo + hi) // 2
        if sum(min(v, middle) for v in upper) >= total:
            hi = middle
        else:
            lo = middle + 1
    dominant_lower, dominant_upper = Fraction(lo, total), Fraction(max(upper), total)
    guaranteed = [e['source'] for i,e in enumerate(edges)
                  if e['lower'] > max((other['upper'] for j,other in enumerate(edges) if j != i), default=-1)]
    positive = [i for i, v in enumerate(lower) if v > 0]
    optional = [i for i, v in enumerate(lower) if v == 0 and upper[i] > 0]
    capacity = sum(upper[i] for i in positive)
    minimum_count = len(positive)
    for i in sorted(optional, key=lambda j: upper[j], reverse=True):
        if capacity >= total:
            break
        capacity += upper[i]
        minimum_count += 1
    maximum_count = len(positive) + min(len(optional), total - sum(lower))
    min_squares = _minimum_squares(lower, upper, total)
    max_squares = _maximum_squares(lower, upper, total)
    return {'dominantPredecessor': guaranteed[0] if len(guaranteed) == 1 else None,
            'dominantPredecessorShareLower': fraction_json(dominant_lower),
            'dominantPredecessorShareUpper': fraction_json(dominant_upper),
            'nonDominantPopulationShareLower': fraction_json(1 - dominant_upper),
            'nonDominantPopulationShareUpper': fraction_json(1 - dominant_lower),
            'positivePredecessorCountLower': minimum_count, 'positivePredecessorCountUpper': maximum_count,
            'effectivePredecessorCountLower': fraction_json(Fraction(total * total, max_squares)),
            'effectivePredecessorCountUpper': fraction_json(Fraction(total * total, min_squares))}
