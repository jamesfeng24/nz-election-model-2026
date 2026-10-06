"""Frozen Stage66 estimation: sigma, tau, the registered bias-adoption rule, diagnostics and the leave-one-election-out backtest."""
import math
import numpy as np
from scripts.maori_seat_layer.common import read, DESIGN
from scripts.maori_seat_layer.data import calibration_rows


def by_election(rows):
    out = {}
    for r in rows:
        if r['contrastD'] is not None:
            out.setdefault(r['year'], []).append(r['contrastD'])
    return out


def sigma2(groups):
    """Within-election pooled variance of D divided by 2 (Var(D | e) = 2 sigma^2) and its degrees of freedom."""
    ss = sum(sum((d - sum(g) / len(g)) ** 2 for d in g) for g in groups.values())
    dof = sum(len(g) for g in groups.values()) - len(groups)
    return ss / dof / 2.0, dof


def tau2(groups, s2, b):
    means = [sum(g) / len(g) for g in groups.values()]
    first = sum((m - b) ** 2 for m in means) / len(means)
    noise = sum(2.0 * s2 / len(g) for g in groups.values()) / len(groups)
    return max(0.0, first - noise)


def bias_hat(groups):
    means = [sum(g) / len(g) for g in groups.values()]
    return sum(means) / len(means)


def mvn_logpdf(d, b, s2, t2):
    d = np.asarray(d, float)
    n = len(d)
    cov = 2.0 * s2 * np.eye(n) + t2 * np.ones((n, n))
    r = d - b
    sign, logdet = np.linalg.slogdet(cov)
    return -0.5 * (n * math.log(2 * math.pi) + logdet + r @ np.linalg.solve(cov, r))


def parameters(groups, b):
    s2, dof = sigma2(groups)
    return {'sigma2': s2, 'sigma2Dof': dof, 'tau2': tau2(groups, s2, b), 'bias': b}


def loeo_scores(groups, rule):
    """Total held-out log score of each election's D vector with b = 0 and with b = b_hat from the other elections."""
    out = {'zero': 0.0, 'estimated': 0.0, 'perElection': {}}
    for e, held in groups.items():
        train = {k: v for k, v in groups.items() if k != e}
        bh = bias_hat(train)
        p0, p1 = parameters(train, 0.0), parameters(train, bh)
        a, b = mvn_logpdf(held, 0.0, p0['sigma2'], p0['tau2']), mvn_logpdf(held, bh, p1['sigma2'], p1['tau2'])
        out['zero'] += a
        out['estimated'] += b
        out['perElection'][str(e)] = {'biasHatFromOthers': bh, 'logScoreZero': a, 'logScoreEstimated': b}
    out['improvementNats'] = out['estimated'] - out['zero']
    return out


def adopt_bias(groups, rule):
    bh = bias_hat(groups)
    scores = loeo_scores(groups, rule)
    same = sum(1 for g in groups.values() if (sum(g) / len(g)) * bh > 0)
    adopted = scores['improvementNats'] >= rule['loeoLogScoreImprovementNats'] and same >= rule['minimumSameSignElections']
    return {'biasHat': bh, 'loeo': scores, 'sameSignElections': same, 'adopted': bool(adopted)}


def other_contrast_ratio(rows, s2):
    """Second moment of log-odds errors against Labour for candidates in neither the MP nor the LAB group, versus 2 sigma^2."""
    f = []
    for r in rows:
        lab = next(c for c in r['candidates'] if c['party'] == 'LAB')
        for c in r['candidates']:
            if c['group'] == 'OTH':
                f.append(math.log(c['resultClosed'] / lab['resultClosed']) - math.log(c['pollClosed'] / lab['pollClosed']))
    return {'count': len(f), 'meanError': sum(f) / len(f), 'rms2': sum(x * x for x in f) / len(f), 'ratioTo2Sigma2': sum(x * x for x in f) / len(f) / (2 * s2)}


def long_horizon(rows, cut):
    groups = {}
    for r in rows:
        if r['contrastD'] is not None and r['horizonDays'] >= cut:
            groups.setdefault(r['year'], []).append(r['contrastD'])
    usable = {k: v for k, v in groups.items() if len(v) >= 2}
    if len(usable) < 2:
        return {'available': False, 'polls': sum(len(v) for v in groups.values())}
    b = 0.0
    p = parameters(usable, b)
    return {'available': True, 'polls': sum(len(v) for v in groups.values()), 'electionsUsed': sorted(usable), 'sigma2': p['sigma2'], 'sigma2Dof': p['sigma2Dof'], 'tau2': p['tau2']}


def backtest(rows, draws, seed):
    """Leave-one-election-out probability that the poll leader wins, with b = 0 and with b = b_hat from the other elections."""
    groups = by_election(rows)
    result = {'polls': []}
    for e in sorted(groups):
        train = {k: v for k, v in groups.items() if k != e}
        bh = bias_hat(train)
        for arm, b in (('zero', 0.0), ('estimated', bh)):
            p = parameters(train, b)
            rng = np.random.default_rng(np.random.SeedSequence([seed, e, 0 if arm == 'zero' else 1]))
            s2 = p['sigma2'] * p['sigma2Dof'] / rng.chisquare(p['sigma2Dof'], draws)
            t2 = p['tau2'] * len(train) / rng.chisquare(len(train), draws) if p['tau2'] > 0 else np.zeros(draws)
            u = np.sqrt(t2) * rng.standard_normal(draws)
            for r in (x for x in rows if x['year'] == e):
                cands = r['candidates']
                logits = np.log([c['pollClosed'] for c in cands])[None, :] + np.sqrt(s2)[:, None] * rng.standard_normal((draws, len(cands)))
                logits = logits + (b + u)[:, None] * np.array([c['group'] == 'MP' for c in cands], float)[None, :]
                win = np.argmax(logits, axis=1)
                names = [c['name'] for c in cands]
                prob = np.bincount(win, minlength=len(cands)) / draws
                result['polls'].append({'id': r['id'], 'arm': arm, 'pollLeaderWinProbability': float(prob[names.index(r['pollLeader'])]),
                                        'actualWinnerProbability': float(prob[names.index(r['actualWinner'])]), 'leaderWon': r['leaderWon']})
    for arm in ('zero', 'estimated'):
        sel = [p for p in result['polls'] if p['arm'] == arm]
        result[arm] = {'polls': len(sel), 'meanPredictedLeaderWin': sum(p['pollLeaderWinProbability'] for p in sel) / len(sel),
                       'observedLeaderWinRate': sum(p['leaderWon'] for p in sel) / len(sel),
                       'brierLeaderWins': sum((p['pollLeaderWinProbability'] - p['leaderWon']) ** 2 for p in sel) / len(sel),
                       'meanLogScoreActualWinner': sum(math.log(max(p['actualWinnerProbability'], 1e-4)) for p in sel) / len(sel)}
    return result


def fit():
    contract = read(DESIGN)
    rows = calibration_rows()
    groups = by_election(rows)
    rule = contract['biasAdoption']
    adoption = adopt_bias(groups, rule)
    b = adoption['biasHat'] if adoption['adopted'] else 0.0
    params = parameters(groups, b)
    means = {str(e): {'n': len(g), 'meanD': sum(g) / len(g), 'sdD': math.sqrt(sum((d - sum(g) / len(g)) ** 2 for d in g) / (len(g) - 1))} for e, g in groups.items()}
    fitted = {'rows': len(rows), 'contrastPolls': sum(len(g) for g in groups.values()), 'electionMeans': means,
              'sigma': math.sqrt(params['sigma2']), 'tau': math.sqrt(params['tau2']), **params, 'biasAdoption': adoption,
              'otherContrasts': other_contrast_ratio(rows, params['sigma2']),
              'unnamedShares': sorted(r['unnamedShare'] for r in rows),
              'horizon': {'cutDays': contract['diagnostics']['horizonCutDays'], 'longHorizonFit': long_horizon(rows, contract['diagnostics']['horizonCutDays']),
                          'pollHorizonDays': sorted(r['horizonDays'] for r in rows)},
              'backtest': backtest(rows, 20000, contract['seed'])}
    return {'schemaVersion': 1, 'fit': fitted}, rows
