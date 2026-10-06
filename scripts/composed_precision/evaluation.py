"""Simulate the composed blocks: harness check, per-block lean records, nested ladder, chain split."""
import math
import os
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scripts.balance_scale.evaluation import multipliers_for, representative_ids
from scripts.balance_scale.simulate import national_inputs
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty_tails import streams as base
from scripts.uncertainty_tails.metrics import record
from .common import (INVENTORY, SCALES, STAGE48_FIT, STAGE48_EVALUATION, RESTRICTIONS, YEARS,
                     read, save, verify, arguments, design)
from .simulate import composed_bank, summarize_bank, LEVELS
from .stream import BLOCK, POOL, block_uniforms, national_block, chain_of, pool_order


def gap(a, b):
    """Largest absolute difference over matching numeric leaves; a structural mismatch is infinite."""
    if isinstance(a, dict):
        return max([gap(v, b[k]) if k in b else math.inf for k, v in a.items()] or [0.])
    if isinstance(a, (list, tuple)):
        return max([gap(x, y) for x, y in zip(a, b)] + [0. if len(a) == len(b) else math.inf])
    if isinstance(a, bool) or isinstance(b, bool):
        return 0. if a == b else 1.
    if isinstance(a, (int, float)):
        return abs(a - b)
    return 0. if a == b else math.inf


def year_inputs(year):
    inventory, scales, fits = read(INVENTORY), read(SCALES), read(STAGE48_FIT)
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    rows = sorted([r for r in inventory['candidateRecords'] if r['targetYear'] == year], key=lambda r: r['targetElectorateId'])
    return {'rows': rows, 'parties': parties, 'pfit': scale_for(scales, 'local_party', year)['scales'],
            'fit': scale_for(scales, 'candidate', year)['scales'], 'mult': multipliers_for(fits, year),
            'first': parties[rows[0]['targetElectorateId']], 'reps': set(representative_ids(rows)),
            'edge': {rows[0]['targetElectorateId'], rows[-1]['targetElectorateId']}}


def task(item):
    """One national block with one layer scramble over a seat population; independent of worker count."""
    kind, year, index = item
    ctx = year_inputs(year)
    block, scramble = (0, index) if kind == 'layer' else (index, index)
    national, draw_ids = national_block(year, ctx['first'], block)
    everything = kind == 'all'
    stage48 = None
    if everything and index == 0:
        stored = read(STAGE48_EVALUATION)['composed']['records']
        stage48 = {r: {x['id']: x for x in stored[r]} for r in RESTRICTIONS}
    seats = {}
    for row in ctx['rows']:
        cid = row['targetElectorateId']
        if not everything and cid not in ctx['reps']:
            continue
        restrictions = RESTRICTIONS if everything else RESTRICTIONS[:1]
        banks, control_input, rb, checks = composed_bank(row, ctx['parties'][cid], national, ctx['pfit'], ctx['fit'], ctx['mult'](cid),
                                                         scramble, restrictions, check_full=everything and index == 1 and cid in ctx['edge'])
        point = control_input.mean(axis=0)
        lean, harness = {}, {}
        for r in restrictions:
            lean[r], compacted = summarize_bank(row, banks[r], point, rb if r == 'control' else None)
            if stage48:
                harness[r] = gap(compacted, stage48[r][cid])
        seat = {'lean': lean, 'checks': checks, 'harness': harness or None}
        if cid in ctx['reps']:
            seat['bank'] = {'q': banks['control'], 'controlInput': control_input, 'ids': draw_ids}
        seats[cid] = seat
    print('Stage54', kind, year, index, flush=True)
    return item, seats


def run_all():
    spec = design()
    shared, total = spec['blocks']['allSeats'], spec['blocks']['representatives']
    items = ([('all', y, b) for y in YEARS for b in range(shared)]
             + [('rep', y, b) for y in YEARS for b in range(shared, total)]
             + [('layer', y, s) for y in YEARS for s in spec['layerOnly']['scrambleIndices']])
    workers = max(1, min(len(items), os.cpu_count() or 1, 4))
    if workers == 1:
        results = [task(i) for i in items]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(task, items, chunksize=1))
    return dict(results)


def metrics(row, q, point):
    """The six frozen gate quantities of one bank, per candidate."""
    rec = record(row, q, point)
    return {'meansPP': [float(100 * v) for v in rec['simulatedMean']], 'crps': [float(v) for v in rec['crpsPP']],
            'energy': float(rec['energyPP']), **{f'width{v}': [float(x) for x in rec[f'interval{v}']['widths']] for v in LEVELS}}


def representative_analysis(results, ctxs):
    """Nested union ladder and chain split from the stored control banks of the eight pool blocks."""
    out = {}
    spec = design()
    shared, total = spec['blocks']['allSeats'], spec['blocks']['representatives']
    for year in YEARS:
        ctx = ctxs[year]
        for row in ctx['rows']:
            cid = row['targetElectorateId']
            if cid not in ctx['reps']:
                continue
            banks = [results[('all' if b < shared else 'rep', year, b)][cid]['bank'] for b in range(total)]
            ladder = {}
            for count in spec['ladder']:
                used = banks[:count // BLOCK]
                q = np.concatenate([b['q'] for b in used])
                point = np.concatenate([b['controlInput'] for b in used]).mean(axis=0)
                ladder[str(count)] = metrics(row, q, point)
            q = np.concatenate([b['q'] for b in banks])
            ci = np.concatenate([b['controlInput'] for b in banks])
            chains = np.array([chain_of(i) for b in banks for i in b['ids']])
            split = {}
            for c in sorted(set(chains.tolist())):
                keep = chains == c
                split[str(c)] = {'draws': int(keep.sum()), **metrics(row, q[keep], ci[keep].mean(axis=0))}
            out[cid] = {'year': year, 'ids': row['ids'], 'ladder': ladder, 'chains': split}
    return out


def harness_summary(results, ctxs):
    worst = {r: 0. for r in RESTRICTIONS}
    for (kind, year, index), seats in results.items():
        if kind == 'all' and index == 0:
            for seat in seats.values():
                for r in RESTRICTIONS:
                    worst[r] = max(worst[r], seat['harness'][r])
    streams = {}
    for year in YEARS:
        first = ctxs[year]['first']
        original = base.uniforms(year, BLOCK)
        mine = block_uniforms(year, BLOCK, 0)
        national, _ = national_block(year, first, 0)
        order = pool_order(year, first)
        streams[str(year)] = {'uniformNamesEqual': original[0] == mine[0],
                              'uniformMaxAbsDifference': float(np.max(np.abs(original[1] - mine[1]))),
                              'nationalBlock0MaxAbsDifference': float(np.max(np.abs(national_inputs(year, first, BLOCK) - national))),
                              'blocksDisjointAndCoverPool': bool(sorted(np.concatenate(order).tolist()) == list(range(POOL))),
                              'scramble1DiffersFromBlock0': bool(np.max(np.abs(block_uniforms(year, BLOCK, 1)[1] - mine[1])) > 0.01)}
    checks = [v for seats in results.values() for s in seats.values() for v in s['checks'].values()]
    return {'stage48Block0MaxAbsDifference': worst, 'streams': streams,
            'fullInvertVersusRebalanceMaxAbs': max(checks) if checks else None, 'fullInvertChecks': len(checks)}


def build():
    spec = design()
    shared, total = spec['blocks']['allSeats'], spec['blocks']['representatives']
    results = run_all()
    ctxs = {y: year_inputs(y) for y in YEARS}
    seats = {}
    for year in YEARS:
        for row in ctxs[year]['rows']:
            cid = row['targetElectorateId']
            blocks = {str(b): results[('all', year, b)][cid]['lean'] for b in range(shared)}
            entry = {'year': year, 'ids': row['ids'], 'groups': row['groups'], 'blocks': blocks}
            if cid in ctxs[year]['reps']:
                entry['representativeBlocks'] = {str(b): results[('rep', year, b)][cid]['lean']['control'] for b in range(shared, total)}
                entry['layerOnly'] = {str(s): results[('layer', year, s)][cid]['lean']['control'] for s in spec['layerOnly']['scrambleIndices']}
            seats[cid] = entry
    return {'stage': 54, 'status': 'scored after the design freeze; no adoption, no change of any default',
            'harness': harness_summary(results, ctxs), 'seats': seats,
            'representatives': representative_analysis(results, ctxs)}


def main():
    args = arguments()
    verify()
    save('evaluation.json', build(), args.check)
    print('Stage54 composed blocks complete' if not args.check else 'Stage54 composed blocks reproduced')


if __name__ == '__main__':
    main()
