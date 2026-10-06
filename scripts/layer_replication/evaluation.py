"""Simulate the layer replicates and reduce them to the frozen per-seat records (no thresholds are applied here)."""
import os
import pickle
import platform
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import scipy
from scripts.composed_precision.evaluation import year_inputs
from scripts.composed_precision.stream import block_uniforms, national_block, POOL
from .common import PREFIX, QUANTITIES, VECTOR, STAGE54_EVALUATION, YEARS, equivalent, read, save, verify, arguments, design
from .simulate import bank_metrics, replicate_bank, reused_solves

BLOCK = 512
HARNESS_REPLICATES = (0, 8, 9, 10)  # replicate 0 is Stage54 block 0; 8, 9, 10 are its layer-only scrambles
STAGE54_NAMES = {'meansPP': 'meanPP', 'crps': 'crpsPP', 'energy': 'energyPP', 'width50': 'width50', 'width80': 'width80',
                 'width90': 'width90', 'win': 'win'}


def seat_row(year, cid):
    ctx = year_inputs(year)
    return ctx, next(r for r in ctx['rows'] if r['targetElectorateId'] == cid)


def populations():
    """(kind, year, id, replicates, chunk size) for the nine representatives and the nine panel seats."""
    spec = design()
    reps, panel = spec['populations']['representatives'], spec['populations']['winPanel']
    items = []
    for year in YEARS:
        ctx = year_inputs(year)
        items += [('rep', year, r['targetElectorateId'], reps['replicates'], reps['chunkReplicates'])
                  for r in ctx['rows'] if r['targetElectorateId'] in ctx['reps']]
    items += [('panel', int(cid.split('-')[2]), cid, panel['replicates'], panel['replicates']) for cid in panel['seats']]
    return items


def task(item):
    """``compute`` with an optional resume directory (``STAGE63_SCRATCH``, outside the repository, local convenience only):
    a finished task is stored byte-exactly and reloaded, so an interrupted local run continues; the result is identical."""
    scratch = os.environ.get('STAGE63_SCRATCH')
    if not scratch:
        return compute(item)
    path = os.path.join(scratch, '-'.join(str(v) for v in item) + '.pickle')
    if os.path.exists(path):
        with open(path, 'rb') as handle:
            return pickle.load(handle)
    result = compute(item)
    os.makedirs(scratch, exist_ok=True)
    with open(path + '.part', 'wb') as handle:
        pickle.dump(result, handle)
    os.replace(path + '.part', path)
    return result


def compute(item):
    """One chunk of consecutive replicates of one seat on the whole national pool; independent of worker count."""
    kind, year, cid, first, count = item
    ctx, row = seat_row(year, cid)
    national, _ = national_block(year, ctx['first'], 0, POOL)
    banks, cpu = {}, []
    control = None
    with reused_solves() as solves:
        for r in range(first, first + count):
            start = time.process_time()
            q, control = replicate_bank(row, ctx['parties'][cid], national, ctx['pfit'], ctx['fit'], r)
            cpu.append(time.process_time() - start)
            banks[r] = q
            block_uniforms.cache_clear()  # each 4,096-point replicate stream is 48 MB and is never reused; memory only
    print('Stage63', kind, cid, first, flush=True)
    return item, banks, control, {'replicateCPUSeconds': cpu, 'solveCacheHits': solves['hits'], 'solveCacheMisses': solves['misses']}


def run_all():
    items = []
    for kind, year, cid, replicates, chunk in populations():
        items += [(kind, year, cid, s, chunk) for s in range(0, replicates, chunk)]
    items.sort(key=lambda i: (i[0] != 'rep', i[1], i[2], i[3]))
    workers = max(1, min(len(items), os.cpu_count() or 1, 4))
    if workers == 1:
        results = [task(i) for i in items]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(task, items, chunksize=1))
    return results


def union(row, banks, control, replicates, low, high):
    """Metrics of the bank formed by the given replicates over national positions [low, high)."""
    q = np.concatenate([banks[r][low:high] for r in replicates])
    return bank_metrics(row, q, control[low:high].mean(axis=0))


def spread(records):
    """Sample sd (ddof 1) over banks of every gate quantity."""
    return {k: (np.std([r[k] for r in records], axis=0, ddof=1).tolist() if k != 'energy' else float(np.std([r[k] for r in records], ddof=1)))
            for k in (*QUANTITIES, 'win')}


def seat_entry(kind, row, banks, control, spec, stage54):
    count = len(banks)
    sizes = [m for m in spec['arms']['nested'] if m < count]
    entry = {'kind': kind, 'year': row['targetYear'], 'ids': row['ids'], 'groups': row['groups'], 'replicates': count,
             'groupBanks': {str(m): [union(row, banks, control, range(g * m, (g + 1) * m), 0, POOL) for g in range(count // m)] for m in sizes},
             'full': union(row, banks, control, range(count), 0, POOL)}
    entry['blocks'] = []
    for b in range(POOL // BLOCK):
        low, high = b * BLOCK, (b + 1) * BLOCK
        single = [union(row, banks, control, [r], low, high) for r in range(count)]
        entry['blocks'].append({'pooled': union(row, banks, control, range(count), low, high), 'layerSd': spread(single)})
    if kind == 'rep':
        arms = [m for m in spec['gateAnationalDoubling']['arms'] if m <= count]
        entry['nationalDoubling'] = {str(m): {str(n): union(row, banks, control, range(m), 0, n)
                                               for n in spec['gateAnationalDoubling']['nationalCounts']} for m in arms}
    entry['harness'] = harness(row, banks, control, stage54)
    return entry


def gap(mine, theirs):
    worst = 0.
    for k, name in STAGE54_NAMES.items():
        a, b = np.atleast_1d(mine[k]), np.atleast_1d(theirs[name])
        worst = max(worst, float(np.max(np.abs(a - b))) if a.shape == b.shape else float('inf'))
    return worst


def harness(row, banks, control, stage54):
    """First 512 positions of replicate 0, and of 8, 9, 10 for the representatives, against the Stage54 records."""
    seat = stage54[row['targetElectorateId']]
    out = {}
    for r in HARNESS_REPLICATES:
        if r not in banks:
            continue
        theirs = seat['blocks']['0']['control'] if r == 0 else seat['layerOnly'][str(r)]
        out[str(r)] = gap(union(row, banks, control, [r], 0, BLOCK), theirs)
    return out


def build():
    spec = design()
    stage54 = read(STAGE54_EVALUATION)['seats']
    gathered = {}
    timing = []
    for item, banks, control, clock in run_all():
        kind, year, cid, first, count = item
        entry = gathered.setdefault(cid, {'kind': kind, 'year': year, 'banks': {}, 'control': control})
        entry['banks'].update(banks)
        timing.append({'kind': kind, 'id': cid, 'firstReplicate': first, 'replicates': count, **clock})
    seats = {}
    for cid, g in sorted(gathered.items()):
        _, row = seat_row(g['year'], cid)
        seats[cid] = seat_entry(g['kind'], row, g['banks'], g['control'], spec, stage54)
    runtime = {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__, 'processors': os.cpu_count(),
               'note': 'process CPU seconds per replicate bank (4,096 draws); the first replicate of each task also pays the one-off local-layer solves; hardware dependent'}
    return ({'stage': 63, 'status': 'scored after the design freeze; no adoption, no change of any default', 'seats': seats},
            {'stage': 63, 'runtime': runtime, 'tasks': sorted(timing, key=lambda t: (t['id'], t['firstReplicate']))})


SAMPLE = {'rep': (62, 2), 'panel': (6, 2)}  # two consecutive replicates at the top of every seat's range, first and count


def sample_check():
    """Bounded replay for hosted CI: regenerate two replicate banks of every seat (uncached start, deterministic, independent of
    the worker count) and compare each with its stored single-replicate record. The complete replay is ``--check --full``."""
    stored = read(PREFIX + '/evaluation.json')['seats']
    items = [(kind, year, cid, *SAMPLE[kind]) for kind, year, cid, _, _ in populations()]
    workers = max(1, min(len(items), os.cpu_count() or 1, 4))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(task, items, chunksize=1))
    for (kind, year, cid, first, count), banks, control, _ in results:
        _, row = seat_row(year, cid)
        for r in banks:
            if not equivalent(stored[cid]['groupBanks']['1'][r], union(row, banks, control, [r], 0, POOL)):
                raise ValueError(f'Stale Stage63 replicate {cid} {r}')
    return len(items) * SAMPLE['rep'][1]


def main():
    args = arguments()
    verify()
    if args.check and not args.full:
        print(f'Stage63 sampled replay reproduced {sample_check()} replicate banks (complete replay: --check --full)')
        return
    evaluation, timing = build()
    save('evaluation.json', evaluation, args.check)
    save('timing.json', timing, args.check, structure_only=True)
    print('Stage63 replicates complete' if not args.check else 'Stage63 replicates reproduced')


if __name__ == '__main__':
    main()
