"""Deterministic summaries of the saved Stage62 draws (numpy only; no inference, no JAX). Internal outputs."""
import argparse
import json
import numpy as np
from .common import OUT, EXT, ARMS, DATASET_OF, ENV_CHECK, CODES, read, save

ORDER = ['A', 'A2', 'B1', 'B2', 'E', 'T']
QS = (.05, .25, .5, .75, .95)
MAJOR = ('NAT', 'LAB')
FORBIDDEN = ('probab', 'seat', 'winner', 'bloc', 'coalition', 'government')


def accepted(arm, base=None):
    root = OUT if base is None else base
    for attempt in (1, 2):
        p = root / f'fits/{arm}/attempt{attempt}.json'
        if p.exists():
            rec = read(p)
            if rec['status'] == 'accepted':
                return rec, root / f'fits/{arm}/attempt{attempt}.npz'
    return None, None


def pp(x):
    return 100 * np.asarray(x, float)


def state_summary(x, codes):
    """x: (draws, K) shares; summary in percentage points."""
    d = pp(x)
    out = {}
    for k, c in enumerate(codes):
        q = np.quantile(d[:, k], QS)
        out[c] = {'mean': float(d[:, k].mean()), 'sd': float(d[:, k].std(ddof=1)), 'q05': float(q[0]), 'q25': float(q[1]), 'q50': float(q[2]), 'q75': float(q[3]), 'q95': float(q[4])}
    return out


def margin_summary(x, codes):
    m = pp(x)[:, codes.index('NAT')] - pp(x)[:, codes.index('LAB')]
    q = np.quantile(m, QS)
    return {'mean': float(m.mean()), 'sd': float(m.std(ddof=1)), 'q05': float(q[0]), 'q50': float(q[2]), 'q95': float(q[4])}


def softmax(v):
    v = v - v.max(-1, keepdims=True)
    e = np.exp(v)
    return e / e.sum(-1, keepdims=True)


def house_effects(offsets, pi_last, names, codes):
    """Poll-share shift (pp) of each 2026-cycle pollster relative to the equal-weight mean offset, at the last-data state."""
    delta = offsets.astype(float)
    log_pi = np.log(np.maximum(pi_last, 1e-300))[:, None, :]
    share = softmax(log_pi + delta)
    ref = softmax(log_pi + delta.mean(1, keepdims=True))
    eff = 100 * (share - ref)
    rel = delta - delta.mean(1, keepdims=True)
    out = {}
    for j, name in enumerate(names):
        out[name] = {}
        for k, c in enumerate(codes):
            e = eff[:, j, k]; q = np.quantile(e, (.05, .95)); r = rel[:, j, k]
            out[name][c] = {'effectPP': {'mean': float(e.mean()), 'sd': float(e.std(ddof=1)), 'q05': float(q[0]), 'q95': float(q[1])},
                            'offsetLogit': {'mean': float(r.mean()), 'sd': float(r.std(ddof=1))}}
    return out


def flat(a):
    a = np.asarray(a)
    return a.reshape((-1,) + a.shape[2:])


def arm_summary(arm):
    rec, npz = accepted(arm)
    if rec is None:
        return {'arm': arm, 'status': 'not_accepted'}
    inv = read(OUT / 'inventory.json')['arms'][DATASET_OF[arm]]
    codes = inv['codes']
    with np.load(npz, allow_pickle=False) as a:
        last = flat(a['lastDataSupport']); elec = flat(a['electionDay'])
        off = flat(a['houseOffset2026']); hyper = {k: flat(a[k]).astype(float) for k in ('sigma', 'kappa', 'house_cycle_sd', 'industry_start_sd', 'industry_end_sd', 'designEffect', 'industryStart2026', 'industryEnd2026')}
        path_mean = a['pathMean']; path_q = a['pathQuantiles']
    def ms(x):
        x = np.asarray(x, float)
        return {'mean': float(x.mean()), 'sd': float(x.std(ddof=1))}
    weeks = read(OUT / 'fits' / arm / ('attempt%d.json' % rec['attempt'])) and None
    return {'arm': arm, 'status': 'accepted', 'attempt': rec['attempt'], 'draws': int(last.shape[0]), 'dataset': inv['fingerprint'], 'polls2026': inv['polls2026'],
            'lastDataWeek': inv['lastDataWeek'], 'targetWeek': inv['targetWeek'], 'codes': codes,
            'lastData': state_summary(last, codes), 'electionWeek': state_summary(elec, codes),
            'marginNatMinusLabLastData': margin_summary(last, codes), 'marginNatMinusLabElectionWeek': margin_summary(elec, codes),
            'houseEffects': house_effects(off, last, rec['pollsters2026'], codes),
            'hyperparameters': {'sigma': [ms(hyper['sigma'][:, k]) for k in range(hyper['sigma'].shape[1])], 'kappa': ms(hyper['kappa']),
                                'houseCycleSd': ms(hyper['house_cycle_sd']), 'industryStartSd': ms(hyper['industry_start_sd']), 'industryEndSd': ms(hyper['industry_end_sd']),
                                'industryEnd2026Logit': {c: ms(hyper['industryEnd2026'][:, k]) for k, c in enumerate(codes)},
                                'designEffect': {n: ms(hyper['designEffect'][:, i]) for i, n in enumerate(inv['pollsters'])}},
            'pathWeeklyPP': {'q': [None], 'note': 'see pathMean'} if False else {'weeksFromLastCompletedElection': None},
            'convergence': {k: rec['diagnostics'][k] for k in ('passed', 'maxRhat', 'minBulkESS', 'minTailESS', 'divergences', 'treeDepthContacts', 'energyBFMI', 'meanAccept')},
            'runtimeSeconds': rec['runtimeSeconds']}


def path_block(arm):
    rec, npz = accepted(arm)
    if rec is None:
        return None
    with np.load(npz, allow_pickle=False) as a:
        pm = 100 * a['pathMean']; q = 100 * a['pathQuantiles']
    return {'meanPP': pm.round(4).tolist(), 'q05PP': q[..., 0].round(4).tolist(), 'q95PP': q[..., 4].round(4).tolist()}


def recent_poll_mean(n_recent=5):
    inv = read(OUT / 'inventory.json')['arms']['A']
    meta = json.loads((OUT / 'datasets/A.json').read_text())
    with np.load(OUT / 'datasets/A.npz', allow_pickle=False) as d:
        y, n, mask, cyc = d['y'], d['n'], d['mask'], d['cycle_idx']
    last = inv['cycles'].index(2026)
    idx = [i for i in range(len(n)) if cyc[i] == last]
    idx.sort(key=lambda i: (meta['mid_dates'][i], i))
    take = idx[-n_recent:]
    codes = inv['codes']
    share = np.where(mask[take][:, :-1], y[take][:, :-1] / n[take][:, None], np.nan)
    mean = np.nanmean(share, axis=0)
    return {'polls': [meta['poll_ids'][i] for i in take], 'meanPP': {c: float(100 * m) for c, m in zip(codes[:-1], mean)}}


def compare(summaries):
    a = summaries['A']
    out = {}
    for arm, s in summaries.items():
        if arm == 'A' or s['status'] != 'accepted':
            continue
        out[arm] = {'states': {}, 'flags': []}
        for state, key in (('lastData', 'lastData'), ('electionWeek', 'electionWeek')):
            rows = {}
            for c in a['codes']:
                x, y = s[key][c], a[key][c]
                width = (x['q95'] - x['q05']) / (y['q95'] - y['q05'])
                rows[c] = {'deltaMeanPP': x['mean'] - y['mean'], 'deltaMeanInSdA': (x['mean'] - y['mean']) / y['sd'], 'sdRatio': x['sd'] / y['sd'], 'width90Ratio': width}
                if c in MAJOR and (abs(rows[c]['deltaMeanPP']) >= 1.0 or not .80 <= width <= 1.25):
                    out[arm]['flags'].append({'state': state, 'category': c, 'deltaMeanPP': rows[c]['deltaMeanPP'], 'width90Ratio': width})
            mk = 'marginNatMinusLab' + ('LastData' if state == 'lastData' else 'ElectionWeek')
            rows['NAT-LAB margin'] = {'deltaMeanPP': s[mk]['mean'] - a[mk]['mean'], 'sdRatio': s[mk]['sd'] / a[mk]['sd']}
            out[arm]['states'][state] = rows
        out[arm]['material'] = bool(out[arm]['flags'])
    return out


def env_check():
    rec, npz = accepted(ENV_CHECK)
    if rec is None:
        return {'status': 'not_accepted'}
    old = read(EXT / 'fits/2017/attempt1.json')
    with np.load(npz) as a, np.load(EXT / 'fits/2017/attempt1.npz') as b:
        new = flat(a['electionDay']); prev = flat(b['electionDay'])
    codes = old['parties']
    d = 100 * (new.mean(0) - prev.mean(0)); r = new.std(0, ddof=1) / prev.std(0, ddof=1)
    ok = bool(np.all(np.abs(d) <= .30) and np.all((r >= .85) & (r <= 1.15)))
    return {'status': 'pass' if ok else 'fail', 'criterion': 'every category election-week mean within 0.30 pp and sd ratio within [0.85, 1.15] of the committed Stage38 2017 fit',
            'parties': codes, 'deltaMeanPP': d.tolist(), 'sdRatio': r.tolist(), 'maxAbsDeltaMeanPP': float(np.abs(d).max()),
            'stage38Mean': prev.mean(0).tolist(), 'refitMean': new.mean(0).tolist(), 'stage38Platform': 'macOS 15.6 arm64, Python 3.12.2', 'refitDraws': int(new.shape[0])}


def close(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(b, (int, float)) and abs(a - b) <= tol * max(1., abs(a))
    return a == b


def scan(value, path=''):
    """No probability, seat, bloc or government field anywhere in the internal outputs."""
    if isinstance(value, dict):
        for k, v in value.items():
            if any(w in k.lower() for w in FORBIDDEN):
                raise ValueError('Forbidden output field ' + path + '/' + k)
            scan(v, path + '/' + k)
    elif isinstance(value, list):
        for v in value:
            scan(v, path)


def build(check=False):
    summaries = {}
    for arm in ORDER:
        s = arm_summary(arm); s.pop('pathWeeklyPP', None); summaries[arm] = s
        if s['status'] == 'accepted':
            s['pathWeekly'] = path_block(arm)
            rec, _ = accepted(arm)
            inv = read(OUT / 'fits' / arm / f"attempt{s['attempt']}.json")
        scan(s)
    comparison = {'reference': 'A', 'noiseFloorArm': 'A2', 'arms': compare(summaries), 'recentFivePolls': recent_poll_mean(),
                  'thresholds': {'deltaMeanPP': 1.0, 'width90RatioRange': [.8, 1.25], 'note': 'descriptive, not tuned; design section 7'}}
    a = summaries['A']
    if a['status'] == 'accepted':
        comparison['recentFivePolls']['deltaVersusALastDataPP'] = {c: a['lastData'][c]['mean'] - v for c, v in comparison['recentFivePolls']['meanPP'].items()}
    scan(comparison)
    for arm, s in summaries.items():
        save(f'summary/{arm}.json', s, False) if not check else compare_saved(f'summary/{arm}.json', s)
    save('summary/comparison.json', comparison, False) if not check else compare_saved('summary/comparison.json', comparison)
    ec = env_check()
    save('summary/environment-check.json', ec, False) if not check else compare_saved('summary/environment-check.json', ec)
    return summaries, comparison, ec


def compare_saved(path, value):
    if not close(read(OUT / path), json.loads(json.dumps(value))):
        raise ValueError('Summary does not reproduce from the saved draws: ' + path)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); build(p.parse_args().check)
