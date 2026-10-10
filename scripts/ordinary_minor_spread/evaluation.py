"""Score the Stage83 arms on the Stage44 candidate records with common streams; only the within and mass multipliers differ.

Every arm carries the D107 balance multiplier (0.60 in seats outside the Stage67 primary flag set, 1.00 inside it); the
arms differ only in the ordinary-seat multipliers on the candidate within-remainder noise and the major-mass noise.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import numpy as np
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty.metrics import crps
from scripts.uncertainty_expectation.simulation import component
from scripts.balance_shrink.evaluation import candidate_rows
from .common import PREFIX, SCALES, YEARS, LEVELS, ARMS, read, save, verify, arguments, design, arms, is_flagged

GROUPS = ('national', 'labour', 'other', 'no_group')
BALANCE = {'ordinary': 0.60, 'exceptional': 1.00}


def arm_scales(fit, balance, within, mass):
    result = deepcopy(fit)
    result['balance']['seat'] = fit['balance']['seat'] * balance
    for component_name, factor in (('within', within), ('mass', mass)):
        result[component_name]['seat'] = fit[component_name]['seat'] * factor
        result[component_name]['shared'] = fit[component_name]['shared'] * factor
    return result


def r6(value):
    return round(float(value), 6)


def intervals(q, y, level):
    """Per-column covered flag, width and interval score at a central `level`% interval, in percentage points."""
    alpha = 1 - level / 100
    lower, upper = np.quantile(q, [alpha / 2, 1 - alpha / 2], axis=0)
    score = upper - lower + 2 / alpha * (np.maximum(lower - y, 0) + np.maximum(y - upper, 0))
    return (y >= lower) & (y <= upper), upper - lower, score


def seat_record(row, q, multipliers, narrowed, prefix):
    """Lean per-seat record for one arm: per-group candidate scores, major mass, winner probabilities."""
    groups = np.asarray(row['groups'])
    y = 100 * np.asarray(row['actual'])
    x = 100 * q
    crps_all = crps(x, y)
    out = {'id': row['targetElectorateId'], 'year': row['targetYear'], 'name': row['name'], 'multipliers': multipliers,
           'narrowed': bool(narrowed), 'groups': {}}
    per = {level: intervals(x, y, level) for level in LEVELS}
    short = intervals(x[:prefix], y, 80)
    for g in GROUPS:
        cols = np.flatnonzero(groups == g)
        if not len(cols):
            continue
        out['groups'][g] = {'candidates': len(cols), 'crpsPP': r6(np.mean(crps_all[cols])),
                            'meanPP': [r6(v) for v in x[:, cols].mean(axis=0)], 'actualPP': [r6(v) for v in y[cols]],
                            **{f'covered{l}': [bool(v) for v in per[l][0][cols]] for l in LEVELS},
                            **{f'width{l}': [r6(v) for v in per[l][1][cols]] for l in LEVELS},
                            'score80': [r6(v) for v in per[80][2][cols]],
                            'covered80Prefix': [bool(v) for v in short[0][cols]]}
    major = np.flatnonzero(np.isin(groups, ('national', 'labour')))
    if len(major):
        mass_q, mass_y = x[:, major].sum(axis=1)[:, None], np.array([y[major].sum()])
        out['mass'] = {'crpsPP': r6(crps(mass_q, mass_y)[0]),
                       **{f'covered{l}': bool(intervals(mass_q, mass_y, l)[0][0]) for l in LEVELS}}
    tied = np.abs(q - q.max(axis=1, keepdims=True)) <= 1e-12
    probabilities = (tied / tied.sum(axis=1, keepdims=True)).mean(axis=0)
    observed = np.flatnonzero(np.abs(y - y.max()) <= 1e-12)
    minor = np.isin(groups, ('other', 'no_group'))
    out['ranking'] = {'uniqueWinner': bool(len(observed) == 1),
                      'actualWinnerProbability': r6(probabilities[observed[0]]) if len(observed) == 1 else None,
                      'actualWinnerIsMinor': bool(minor[observed[0]]) if len(observed) == 1 else None,
                      'minorWinMass': r6(probabilities[minor].sum())}
    return out


def year_task(year, part=0, parts=1):
    spec = design()
    fold = read(PREFIX + '/fit.json')['folds'][str(year)]
    fit = scale_for(read(SCALES), 'candidate', year)['scales']
    rows = candidate_rows(year)[part::parts]
    order = arms()
    count, prefix = spec['components']['draws'], spec['components']['prefixDraws']
    records, identity = {a: [] for a in order}, {a: 0.0 for a in order}
    for row in rows:
        primary = is_flagged(row, 'primary')
        balance = BALANCE['exceptional' if primary else 'ordinary']
        control, _ = component(row, arm_scales(fit, balance, 1.0, 1.0), count)
        records['control'].append(seat_record(row, control, {'balance': balance, 'within': 1.0, 'mass': 1.0}, False, prefix))
        for arm in order[1:]:
            kind, estimator, uses_mass = ARMS[arm]
            flagged = is_flagged(row, kind)
            within = 1.0 if flagged else fold[kind]['within'][estimator]['multiplier']
            mass = 1.0 if flagged or not uses_mass else fold[kind]['mass'][estimator]['multiplier']
            q = control
            if within != 1.0 or mass != 1.0:
                q, _ = component(row, arm_scales(fit, balance, within, mass), count)
            if flagged:
                identity[arm] = max(identity[arm], float(np.max(np.abs(q - control))))
            records[arm].append(seat_record(row, q, {'balance': balance, 'within': within, 'mass': mass}, not flagged, prefix))
    print('Stage83 scored', year, part, flush=True)
    return records, identity


def run_all():
    tasks = [(y, p, 4) for y in YEARS for p in range(4)]
    workers = max(1, min(len(tasks), os.cpu_count() or 1, 4))
    if workers == 1:
        return [year_task(*t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(year_task, *zip(*tasks)))


def build():
    spec = design()
    order = arms()
    results = run_all()
    records = {a: sorted([r for res in results for r in res[0][a]], key=lambda r: (r['year'], r['id'])) for a in order}
    identity = {a: max(res[1][a] for res in results) for a in order}
    return {'stage': 83, 'status': 'scored after the design freeze and amendment 1; no adoption', 'draws': spec['components']['draws'],
            'prefixDraws': spec['components']['prefixDraws'],
            'seatsByElection': {str(y): sum(r['year'] == y for r in records['control']) for y in YEARS},
            'flaggedSeatMaximumAbsoluteDifferenceFromControl': identity, 'records': records}


def main():
    args = arguments()
    verify()
    save('evaluation.json', build(), args.check)
    print('Stage83 scores ' + ('reproduced' if args.check else 'written'))


if __name__ == '__main__':
    main()
