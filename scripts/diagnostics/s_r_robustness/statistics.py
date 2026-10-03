"""Finite descriptive associations and environment dispersion; no model fitting."""
from math import fsum, sqrt
from statistics import mean, pstdev


def correlation(x, y, weights=None):
    if len(x) != len(y) or len(x) < 2:
        return None
    w = [1.0]*len(x) if weights is None else weights
    if len(w) != len(x) or any(v <= 0 for v in w):
        raise ValueError('Invalid descriptive weights')
    total = fsum(w); a = fsum(v*z for v, z in zip(w, x))/total; b = fsum(v*z for v, z in zip(w, y))/total
    xx = fsum(v*(z-a)**2 for v, z in zip(w, x)); yy = fsum(v*(z-b)**2 for v, z in zip(w, y))
    xy = fsum(v*(z-a)*(t-b) for v, z, t in zip(w, x, y))
    if xx == 0 or yy == 0:
        return None
    return xy/sqrt(xx*yy)


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i]); result = [0.0]*len(values); i = 0
    while i < len(order):
        j = i+1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for k in order[i:j]:
            result[k] = (i+1+j)/2
        i = j
    return result


def slope(x, y, weights=None):
    if len(x) != len(y) or len(x) < 2:
        return None
    w = [1.0]*len(x) if weights is None else weights
    total = fsum(w); a = fsum(v*z for v, z in zip(w, x))/total; b = fsum(v*z for v, z in zip(w, y))/total
    xx = fsum(v*(z-a)**2 for v, z in zip(w, x))
    return None if xx == 0 else fsum(v*(z-a)*(t-b) for v, z, t in zip(w, x, y))/xx


def association(rows, field):
    selected = [r for r in rows if r['movementStatus'] == 'available']; x = [r[field] for r in selected]; y = [r['Gpp'] for r in selected]
    beta = slope(x, y)
    rho = correlation(ranks(x), ranks(y))
    return {'availableContests': len(selected), 'excludedContests': len(rows)-len(selected),
        'slopeGainPPPer10ppMovement': None if beta is None else .1*beta,
        'spearman': rho, 'slopeUnavailableReason': 'insufficient_observations_or_no_distance_variation' if beta is None else None,
        'spearmanUnavailableReason': 'insufficient_observations_or_constant_rank' if rho is None else None}


def centered_association(rows, field):
    blocks = [[r for r in rows if r['targetYear']==y and r['movementStatus']=='available'] for y in sorted({r['targetYear'] for r in rows})]
    blocks = [b for b in blocks if b]; x, g, weights = [], [], []
    for block in blocks:
        mx = mean(r[field] for r in block); mg = mean(r['Gpp'] for r in block)
        x.extend(r[field]-mx for r in block); g.extend(r['Gpp']-mg for r in block)
        weights.extend([1/(len(blocks)*len(block))]*len(block))
    beta = slope(x, g, weights) if weights else None
    rho = correlation(x, g, weights) if weights else None
    return {'elections': len(blocks), 'contests': len(x), 'weighting': 'equal_total_per_election; centered_within_election',
        'slopeGainPPPer10ppMovement': None if beta is None else .1*beta, 'pearson': rho,
        'unavailableReason': 'insufficient_observations_or_zero_within_variation' if beta is None or rho is None else None}


def dispersion(values, years):
    if not values:
        return None
    worst = max(values)
    return {'equalElectionMeanPP': mean(values), 'populationSDPP': pstdev(values),
        'rangePP': max(values)-min(values), 'minimumPP': min(values), 'maximumPP': worst,
        'worstTargetYears': [y for y, v in zip(years, values) if v == worst], 'elections': len(values)}
