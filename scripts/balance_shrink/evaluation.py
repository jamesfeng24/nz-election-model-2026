"""Score the Stage60 arms on identical common-stream candidate-layer records; no adoption."""
import os
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty.metrics import crps
from scripts.uncertainty_revision.coordinates import partition
from scripts.uncertainty_tails.metrics import record
from scripts.uncertainty_expectation.simulation import component
from scripts.balance_scale.simulate import scaled, prefix_metrics, draw_gaps, major_columns
from scripts.balance_scale.evaluation import representative_ids, doubling
from .common import PREFIX, INVENTORY, SCALES, YEARS, LEVELS, read, save, verify, arguments, design, arms


def candidate_rows(year):
    """General-electorate candidate records only: Maori electorates are modelled separately, excluded by electorate type."""
    rows = [r for r in read(INVENTORY)['candidateRecords'] if r['targetYear'] == year]
    if any(r['scope'] != 'general' for r in rows):
        raise ValueError('Stage60 excludes every non-general electorate by electorate type')
    return sorted(rows, key=lambda r: r['targetElectorateId'])


def lean(row, rec, extra):
    """Only the National/Labour coordinates, the complete-vector energy and the resolution prefix are kept."""
    n, l, _ = partition(row['groups'])
    pick = lambda values: [float(values[n[0]]), float(values[l[0]])]
    out = {'id': row['targetElectorateId'], 'year': row['targetYear'], 'crpsPP': pick(rec['crpsPP']), 'energyPP': float(rec['energyPP']),
           'intervals': {str(level): {'covered': [bool(rec[f'interval{level}']['covered'][i]) for i in (n[0], l[0])],
                                       'widths': pick(rec[f'interval{level}']['widths']), 'scores': pick(rec[f'interval{level}']['scores'])}
                         for level in LEVELS}}
    out.update(extra)
    return out


def seat(row, fit, multipliers, count, resolution, doubling_counts):
    banks, records, rep = {}, {}, {}
    point = np.asarray(row['mean'])
    major = major_columns(row)
    actual = 100 * np.asarray(row['actual'])
    for arm, multiplier in multipliers.items():
        q, _ = component(row, scaled(fit, multiplier), count)
        banks[arm] = q
        extra = {'multiplier': float(multiplier),
                 'majorCRPSPrefix': float(np.mean(crps(100 * q[:resolution][:, major], actual[major]))),
                 'finiteMeanDeviationPP': float(np.max(np.abs(100 * (q.mean(axis=0) - point))))}
        records[arm] = lean(row, record(row, q, point), extra)
        if doubling_counts:
            rep[arm] = prefix_metrics(row, q, point, doubling_counts)
    return records, draw_gaps(row, banks), rep


def year_task(year):
    spec = design()
    fits = read(PREFIX + '/fit.json')['folds'][str(year)]['multipliers']
    rows = candidate_rows(year)
    fit = scale_for(read(SCALES), 'candidate', year)['scales']
    ids = set(representative_ids(rows))
    order = arms()
    records, gaps, doubling_entries = {a: [] for a in order}, [], []
    for row in rows:
        cid = row['targetElectorateId']
        found, gap, rep = seat(row, fit, {a: fits[a] for a in order}, spec['components']['draws'],
                               spec['decision']['improves']['resolutionPrefixDraws'], spec['components']['doubling'] if cid in ids else None)
        for a in order:
            records[a].append(found[a])
        gaps.append({'id': cid, **gap})
        if rep:
            doubling_entries.append(rep)
    print('Stage60 scored', year, flush=True)
    return records, gaps, doubling_entries


def run_all():
    items = list(YEARS)
    workers = max(1, min(len(items), os.cpu_count() or 1, 4))
    if workers == 1:
        return dict(zip(items, [year_task(y) for y in items]))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return dict(zip(items, pool.map(year_task, items)))


def build():
    spec = design()
    order = arms()
    results = run_all()
    records = {a: [x for y in YEARS for x in results[y][0][a]] for a in order}
    gaps = [g for y in YEARS for g in results[y][1]]
    entries = [e for y in YEARS for e in results[y][2]]
    precision = doubling(entries, spec['components']['doubling'], spec['decision']['improves']['doublingGatesPP'], order)
    return {'stage': 60, 'status': 'scored after the design freeze; no adoption', 'draws': spec['components']['draws'],
            'seatsByElection': {str(y): len(results[y][0][order[0]]) for y in YEARS},
            'excludedByElectorateType': {'maori': 0, 'rule': 'every candidate record must have scope general; none other is present in the Stage44 inventory'},
            'records': records, 'drawGaps': gaps,
            'maximumDrawGapAcrossArms': max(max(g[a]['otherMaxAbs'], g[a]['majorMassMaxAbs']) for g in gaps for a in order[1:]),
            'maximumFiniteMeanDeviationPP': {a: max(x['finiteMeanDeviationPP'] for x in records[a]) for a in order},
            'representativeDoubling': precision}


def main():
    args = arguments()
    verify()
    save('evaluation.json', build(), args.check)
    print('Stage60 scores complete' if not args.check else 'Stage60 scores reproduced')


if __name__ == '__main__':
    main()
