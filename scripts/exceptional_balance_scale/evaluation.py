"""Score the Stage67 arms on Stage60's common-stream candidate-layer harness; only per-seat balance multipliers differ."""
import os
from concurrent.futures import ProcessPoolExecutor
from scripts.uncertainty.construction import scale_for
from scripts.balance_scale.evaluation import representative_ids, doubling
from scripts.balance_shrink.evaluation import candidate_rows, seat
from .common import PREFIX, YEARS, FLAG_SETS, read, save, verify, arguments, design, arms, flags, names

SCALES = 'data/processed/uncertainty-revision/scales.json'


def seat_multipliers(fold, flagged):
    """{arm: multiplier} for one seat; `flagged` maps arm to that seat's frozen flag."""
    out = {'control': 1.0, 'free': fold['free']}
    for arm in FLAG_SETS:
        out[arm] = fold[arm]['exceptionalMultiplier'] if flagged[arm] else fold[arm]['ordinaryMultiplier']
    out['twogroup_exc1'] = 1.0 if flagged['twogroup'] else fold['twogroup_exc1']['ordinaryMultiplier']
    return out


def year_task(year, only=None):
    spec = design()
    fold = read(PREFIX + '/fit.json')['folds'][str(year)]
    lookup = names()
    sets = {arm: flags(kind)[year] for arm, kind in FLAG_SETS.items()}
    rows = candidate_rows(year)
    if only is not None:
        rows = [r for r in rows if r['targetElectorateId'] in only]
    fit = scale_for(read(SCALES), 'candidate', year)['scales']
    ids = set(representative_ids(candidate_rows(year)))
    order = arms()
    records, gaps, entries = {a: [] for a in order}, [], []
    for row in rows:
        cid = row['targetElectorateId']
        flagged = {arm: lookup[cid] in sets[arm] for arm in FLAG_SETS}
        found, gap, rep = seat(row, fit, seat_multipliers(fold, flagged), spec['components']['draws'],
                               spec['decision']['improves']['resolutionPrefixDraws'],
                               spec['components']['doubling'] if cid in ids and only is None else None)
        for a in order:
            records[a].append({**found[a], 'name': lookup[cid], 'exceptional': flagged['twogroup'], 'exceptional17': flagged['twogroup17']})
        gaps.append({'id': cid, **gap})
        if rep:
            entries.append(rep)
    print('Stage67 scored', year, flush=True)
    return records, gaps, entries


def run_all():
    workers = max(1, min(len(YEARS), os.cpu_count() or 1, 4))
    if workers == 1:
        return dict(zip(YEARS, [year_task(y) for y in YEARS]))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return dict(zip(YEARS, pool.map(year_task, YEARS)))


def build():
    spec = design()
    order = arms()
    results = run_all()
    records = {a: [x for y in YEARS for x in results[y][0][a]] for a in order}
    gaps = [g for y in YEARS for g in results[y][1]]
    entries = [e for y in YEARS for e in results[y][2]]
    precision = doubling(entries, spec['components']['doubling'], spec['decision']['improves']['doublingGatesPP'], order)
    return {'stage': 67, 'status': 'scored after the design freeze; no adoption', 'draws': spec['components']['draws'],
            'seatsByElection': {str(y): len(results[y][0][order[0]]) for y in YEARS},
            'flaggedByElection': {arm: {str(y): sum(r['exceptional' if arm == 'twogroup' else 'exceptional17'] for r in results[y][0]['control'])
                                        for y in YEARS} for arm in FLAG_SETS},
            'records': records, 'drawGaps': gaps,
            'maximumDrawGapAcrossArms': max(max(g[a]['otherMaxAbs'], g[a]['majorMassMaxAbs']) for g in gaps for a in order[1:]),
            'maximumFiniteMeanDeviationPP': {a: max(x['finiteMeanDeviationPP'] for x in records[a]) for a in order},
            'representativeDoubling': precision}


def main():
    args = arguments()
    verify()
    save('evaluation.json', build(), args.check)
    print('Stage67 scores ' + ('reproduced' if args.check else 'written'))


if __name__ == '__main__':
    main()
