"""Dated estimate from the saved draws (numpy only). Same quantities as the Stage62 arm A summary; internal, no probability fields."""
import numpy as np
from scripts.polling.live_fit.summarize import state_summary, margin_summary, house_effects, flat, scan, close
from .common import ESTIMATE_SHIFT_PP, read

CONVERGENCE = ('passed', 'maxRhat', 'minBulkESS', 'minTailESS', 'divergences', 'treeDepthContacts', 'energyBFMI', 'meanAccept')


def summarize(npz_path, fit_rec, inv):
    codes = inv['codes']
    with np.load(npz_path, allow_pickle=False) as a:
        if 'electionDay' in a.files:
            raise ValueError('The nowcast archive must not carry election-week draws (D106)')
        last = flat(a['lastDataSupport']); off = flat(a['houseOffset2026'])
        pm = 100 * a['pathMean']; q = 100 * a['pathQuantiles']
    out = {'codes': codes, 'draws': int(last.shape[0]), 'lastData': state_summary(last, codes),
           'marginNatMinusLabLastData': margin_summary(last, codes),
           'houseEffects': house_effects(off, last, fit_rec['pollsters2026'], codes),
           'pathWeekly': {'meanPP': pm.round(4).tolist(), 'q05PP': q[..., 0].round(4).tolist(), 'q95PP': q[..., 4].round(4).tolist()},
           'convergence': {k: fit_rec['diagnostics'][k] for k in CONVERGENCE}}
    scan(out)
    return out


def previous_summary(path):
    """The previous published estimate (Stage62 arm A summary or the previous weekly estimate): same field names by construction."""
    p = read(path)
    return {'lastData': p['lastData'], 'marginNatMinusLabLastData': p['marginNatMinusLabLastData'],
            'lastDataWeek': p.get('lastDataWeek'), 'polls2026': p.get('polls2026')}


def compare(cur, prev, label):
    deltas = {c: cur['lastData'][c]['mean'] - prev['lastData'][c]['mean'] for c in cur['codes'] if c in prev['lastData']}
    margin = cur['marginNatMinusLabLastData']['mean'] - prev['marginNatMinusLabLastData']['mean']
    flags = [{'kind': 'estimate_shift', 'category': c, 'deltaMeanPP': round(deltas[c], 3),
              'action': 'last-data mean moved by at least 1 pp against the previous published estimate; review the new rows and house effects'}
             for c in ('NAT', 'LAB') if abs(deltas[c]) >= ESTIMATE_SHIFT_PP]
    return {'previous': label, 'previousLastDataWeek': prev['lastDataWeek'], 'previousPolls2026': prev['polls2026'], 'deltaLastDataMeanPP': deltas,
            'deltaMarginNatMinusLabPP': margin, 'noiseFloorPP': 0.1,
            'note': 'Stage62 seed replicate: Monte Carlo noise floor about 0.1 pp'}, flags
