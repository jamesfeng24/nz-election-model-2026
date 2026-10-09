"""Stage81 closed-vector backtest of the four local party transforms on the Stage5 general-seat records.

Everything is computed on the persistent-party composition: source, national and actual shares are restricted to the
transition's parties and renormalised, each arm maps (p, P0, P1) to a closed vector, and errors are in percentage points.
"""
import collections
import numpy as np
from .common import read, RECORDS, ARMS, PROFILE, EPSILON
from .transforms import swing


def load(source, target):
    """{'parties', 'seats', 'p_lower', 'p_upper', 'actual', 'P0', 'P1', 'rawP0', 'rawP1', 'votes'} for one transition."""
    by_seat = collections.defaultdict(dict)
    for r in read(RECORDS)['records']:
        if (r['sourceYear'], r['targetYear']) == (source, target) and r['electorateType'] == 'general':
            by_seat[r['electorateId']][r['canonicalPartyId']] = r
    parties = sorted(set().union(*[set(v) for v in by_seat.values()]))
    seats = sorted(by_seat)
    if any(len(by_seat[s]) != len(parties) for s in seats):
        raise ValueError(f'{source}-{target}: a seat lacks a persistent party record')
    grid = lambda key: np.array([[by_seat[s][q][key] for q in parties] for s in seats])
    raw0 = np.array([by_seat[seats[0]][q]['sourceNationalShare'] for q in parties])
    raw1 = np.array([by_seat[seats[0]][q]['targetNationalShare'] for q in parties])
    for s in seats:
        same = all(by_seat[s][q]['sourceNationalShare'] == raw0[i] and by_seat[s][q]['targetNationalShare'] == raw1[i] for i, q in enumerate(parties))
        if not same:
            raise ValueError('national shares differ between seats')
    close = lambda x: x / x.sum(axis=-1, keepdims=True)
    return {'parties': parties, 'seats': seats, 'names': [by_seat[s][parties[0]]['electorateName'] for s in seats],
            'p_lower': close(grid('sourceLocalShareLower')), 'p_upper': close(grid('sourceLocalShareUpper')),
            'actual': close(grid('actualTargetShare')), 'P0': close(raw0), 'P1': close(raw1), 'rawP0': raw0, 'rawP1': raw1,
            'votes': grid('actualTargetPartyVotes'), 'exact': bool(np.all(grid('sourceLocalShareLower') == grid('sourceLocalShareUpper')))}


def predictions(data, bound, arms=ARMS):
    p = data['p_' + bound]
    return {a: swing(a, p, data['P0'], data['P1']) for a in arms}


def clr(x):
    star = (x + EPSILON) / (1 + x.shape[-1] * EPSILON)
    logs = np.log(star)
    return logs - logs.mean(axis=-1, keepdims=True)


def column(data, code):
    return data['parties'].index(code)


def seat_errors(data, pred, bound):
    """Per-seat arrays for one arm: margin error (signed, pp), minor-party absolute errors, CLR second moment."""
    n, l = column(data, 'nationalparty'), column(data, 'labourparty')
    a = data['actual']
    margin = 100 * ((pred[:, n] - pred[:, l]) - (a[:, n] - a[:, l]))
    abs_party = 100 * np.abs(pred - a)
    clr_sq = ((clr(a) - clr(pred)) ** 2).sum(axis=1) / pred.shape[1]
    return {'margin': margin, 'absParty': abs_party, 'clrSq': clr_sq}


def minor_columns(data):
    """Persistent parties other than National and Labour with national share >= 1% in either election."""
    keep = (np.maximum(data['rawP0'], data['rawP1']) >= 0.01)
    return [i for i, q in enumerate(data['parties']) if keep[i] and q not in ('nationalparty', 'labourparty')]


def tercile_bias(margin_signed, source_margin):
    order = np.argsort(source_margin, kind='stable')
    return [float(margin_signed[idx].mean()) for idx in np.array_split(order, 3)]


def summarise(data, pred, bound, large_move=1.5, quartile=0.75):
    """Metrics M1 to M5 and D1 for one arm, one transition, one source-bound choice."""
    err = seat_errors(data, pred, bound)
    n, l = column(data, 'nationalparty'), column(data, 'labourparty')
    a, p = data['actual'], data['p_' + bound]
    minors = minor_columns(data)
    abs_party = err['absParty']
    votes = data['votes']
    out = {'M1': {'mae': float(np.abs(err['margin']).mean()), 'bias': float(err['margin'].mean()),
                  'biasByTercileOfPreviousMargin': tercile_bias(err['margin'], p[:, n] - p[:, l])},
           'M2': {'macroMinorMae': float(abs_party[:, minors].mean(axis=0).mean()),
                  'byParty': {data['parties'][i]: float(abs_party[:, i].mean()) for i in minors}},
           'M3': {'leadCallAgreement': float(np.mean(np.sign(pred[:, n] - pred[:, l]) == np.sign(a[:, n] - a[:, l]))),
                  'nationalAheadPredicted': int((pred[:, n] > pred[:, l]).sum()), 'nationalAheadActual': int((a[:, n] > a[:, l]).sum()),
                  'countError': int((pred[:, n] > pred[:, l]).sum() - (a[:, n] > a[:, l]).sum())},
           'M4': {'macroPartyMae': float(abs_party.mean(axis=0).mean()), 'rmse': float(np.sqrt((abs_party ** 2).mean())),
                  'voteWeightedMae': float((abs_party * votes).sum() / votes.sum())},
           'M5': {'clrMeanSquaredPerCategory': float(err['clrSq'].mean())}}
    movers = np.abs(np.log(data['rawP1'] / data['rawP0'])) >= np.log(large_move)
    d1 = {}
    for i, q in enumerate(data['parties']):
        if movers[i]:
            strong = p[:, i] >= np.quantile(p[:, i], quartile)
            signed = 100 * (pred[strong, i] - a[strong, i])
            d1[q] = {'nationalChange': float(data['rawP1'][i] / data['rawP0'][i]), 'seats': int(strong.sum()),
                     'meanSignedErrorPP': float(signed.mean()), 'maePP': float(np.abs(signed).mean())}
    out['D1'] = d1
    return out


def per_seat_losses(data, pred, bound):
    err = seat_errors(data, pred, bound)
    return {'M1': np.abs(err['margin']), 'M2': err['absParty'][:, minor_columns(data)].mean(axis=1)}


def score_transition(source, target, arms=ARMS, profile=True):
    data = load(source, target)
    bounds = ('lower', 'upper') if not data['exact'] else ('lower',)
    result = {'sourceYear': source, 'targetYear': target, 'seats': len(data['seats']), 'parties': data['parties'],
              'exactSource': data['exact'], 'nationalShares': {q: [float(data['rawP0'][i]), float(data['rawP1'][i])] for i, q in enumerate(data['parties'])},
              'minorParties': [data['parties'][i] for i in minor_columns(data)], 'bounds': {}}
    for bound in bounds:
        preds = predictions(data, bound, arms)
        block = {'arms': {a: summarise(data, preds[a], bound) for a in arms}}
        if profile:
            theta = {name: swing(spec, data['p_' + bound], data['P0'], data['P1']) for name, spec in PROFILE if name not in arms}
            theta.update({name: preds[name] for name, spec in PROFILE if name in arms})
            block['profile'] = {name: {'M1': summarise(data, theta[name], bound)['M1']['mae'],
                                       'M2': summarise(data, theta[name], bound)['M2']['macroMinorMae']} for name, _ in PROFILE}
        result['bounds'][bound] = block
    return result, data


def bootstrap(losses, resamples, seed, metric, a, b):
    """Paired seat bootstrap of (loss_a - loss_b) pooled as the mean over the transitions in `losses`."""
    rng = np.random.default_rng(seed)
    diffs = []
    for key in sorted(losses):
        d = losses[key][a][metric] - losses[key][b][metric]
        idx = rng.integers(0, len(d), size=(resamples, len(d)))
        diffs.append(d[idx].mean(axis=1))
    pooled = np.mean(diffs, axis=0)
    return {'meanDifference': float(np.mean([losses[k][a][metric].mean() - losses[k][b][metric].mean() for k in losses])),
            'q05': float(np.quantile(pooled, .05)), 'q95': float(np.quantile(pooled, .95))}
