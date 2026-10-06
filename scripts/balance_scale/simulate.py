"""Common-stream restriction banks: only the candidate N/L balance seat scale differs."""
from copy import deepcopy
import numpy as np
from scripts.uncertainty.construction import national_case
from scripts.uncertainty.metrics import crps
from scripts.uncertainty_revision.coordinates import binary_draw, partition
from scripts.uncertainty_tails.metrics import record
from scripts.uncertainty_tails.streams import noise, permutation
from scripts.uncertainty_expectation.simulation import component, upstream, invert
from .common import RESTRICTIONS

LEVELS = (50, 80, 90)
INTERVAL_KEYS = ('covered', 'widths', 'scores')


def scaled(fit, multiplier):
    result = deepcopy(fit)
    result['balance']['seat'] = fit['balance']['seat'] * float(multiplier)
    return result


def compact(rec, extra=None):
    """The fields every Stage48 summary and the Stage47 width helpers read."""
    pair = rec['ranking']['predictionTimePair']
    pack = lambda x: {k: [bool(v) if k == 'covered' else float(v) for v in x[k]] for k in INTERVAL_KEYS}
    result = {'id': rec['id'], 'year': rec['year'], 'ids': rec['ids'], 'groups': rec['groups'],
              'crpsPP': [float(v) for v in rec['crpsPP']], 'energyPP': float(rec['energyPP']), 'maePP': float(rec['maePP']),
              'simulatedMean': [float(v) for v in rec['simulatedMean']],
              **{f'interval{l}': pack(rec[f'interval{l}']) for l in LEVELS},
              'ranking': {'predictionTimePair': {'ids': pair['ids'], 'crpsPP': float(pair['crpsPP']),
                                                 **{f'interval{l}': pack(pair[f'interval{l}']) for l in LEVELS}}}}
    result.update(extra or {})
    return result


def major_columns(row):
    n, l, _ = partition(row['groups'])
    return n + l


def draw_gaps(row, q_by_restriction):
    """Non-balance coordinates and the National+Labour mass must be identical across restrictions."""
    n, l, other = partition(row['groups'])
    control = q_by_restriction['control']
    mass = control[:, n[0]] + control[:, l[0]]
    return {r: {'otherMaxAbs': float(np.max(np.abs(q[:, other] - control[:, other]))) if other else 0.,
                'majorMassMaxAbs': float(np.max(np.abs(q[:, n[0]] + q[:, l[0]] - mass)))}
            for r, q in q_by_restriction.items() if r != 'control'}


def prefix_metrics(row, q, point, counts):
    out = {}
    for count in counts:
        rec = record(row, q[:count], point)
        out[str(count)] = {'meansPP': (100 * np.asarray(rec['simulatedMean'])).tolist(), 'crps': rec['crpsPP'],
                           'energy': rec['energyPP'], **{f'width{l}': rec[f'interval{l}']['widths'] for l in LEVELS}}
    return out


def component_seat(row, fit, multipliers, count, resolution, doubling=None):
    banks, records = {}, {}
    point = np.asarray(row['mean'])
    major = major_columns(row)
    actual = 100 * np.asarray(row['actual'])
    for r in RESTRICTIONS:
        q, _ = component(row, scaled(fit, multipliers[r]), count)
        banks[r] = q
        extra = {'multiplier': float(multipliers[r]),
                 'majorCRPSPrefix': float(np.mean(crps(100 * q[:resolution][:, major], actual[major]))),
                 'finiteMeanDeviationPP': float(np.max(np.abs(100 * (q.mean(axis=0) - point))))}
        if doubling:
            extra['doubling'] = prefix_metrics(row, q, point, doubling)
        records[r] = compact(record(row, q, point), extra)
    return records, draw_gaps(row, banks)


def national_inputs(year, party, count):
    base, ids, _ = national_case(year, party['ids'], 4096)
    order = permutation(4096, f'national:{year}')[:count]
    return base[order]


def rebalance(control, conditional, row, scales, count):
    """Recompute only the N/L split from the same shared noise; the remainder block is reused."""
    n, l, other = partition(row['groups'])
    major = n + l
    eta, total = noise(row, scales, count)
    original = conditional[:, major].sum(axis=1)
    mass = binary_draw(original, eta['mass'], total['mass']) if other else np.ones(count)
    ratio = binary_draw(np.divide(conditional[:, n[0]], original, out=np.zeros(count), where=original > 0),
                        eta['balance'], total['balance'])
    q = control.copy()
    q[:, n[0]], q[:, l[0]] = mass * ratio, mass * (1 - ratio)
    return q


def composed_seat(row, party, national, party_scales, fit, multipliers, resolution, doubling=None, check_full=False):
    local, conditional, control_input, meta = upstream(party, row, national, party_scales)
    count = len(national)
    base, _ = invert(conditional, row, fit, count)
    point = np.asarray(control_input.mean(axis=0))
    actual = 100 * np.asarray(row['actual'])
    major = major_columns(row)
    banks, records, checks = {'control': base}, {}, {}
    again = rebalance(base, conditional, row, fit, count)
    checks['controlRebalanceMaxAbs'] = float(np.max(np.abs(again - base)))
    for r in RESTRICTIONS[1:]:
        banks[r] = rebalance(base, conditional, row, scaled(fit, multipliers[r]), count)
        if check_full:
            full, _ = invert(conditional, row, scaled(fit, multipliers[r]), count)
            checks[r + 'FullInvertMaxAbs'] = float(np.max(np.abs(full - banks[r])))
    for r in RESTRICTIONS:
        q = banks[r]
        extra = {'multiplier': float(multipliers[r]),
                 'majorCRPSPrefix': float(np.mean(crps(100 * q[:resolution][:, major], actual[major])))}
        if doubling:
            extra['doubling'] = prefix_metrics(row, q, point, doubling)
        records[r] = compact(record(row, q, point), extra)
    return records, {**checks, **draw_gaps(row, banks)}
