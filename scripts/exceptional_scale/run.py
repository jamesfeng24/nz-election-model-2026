"""Diagnostic only: do frozen exceptional-uncertainty flags support separate ordinary/exceptional balance scales?

python -m scripts.exceptional_scale.run [--check]

Consumes the Stage48 candidate N/L balance observations, frozen means and frozen fold scales unchanged, and the
Stage48 Gaussian balance likelihood (shared election effect plus seat effect). Nothing is adopted: no operational
scale, forecast, mean or interface changes. See docs/exceptional-scale-diagnostic.md.
"""
import argparse

import numpy as np
from scipy.optimize import minimize
from scipy.stats import chi2

from scripts.balance_scale.common import HETEROGENEITY, equivalent, read
from scripts.balance_scale.data import YEARS, environments
from scripts.balance_scale.fit import environment_value, location
from scripts.uncertainty_revision.common import ROOT, encode

OUTPUT = 'data/processed/exceptional-scale/summary.json'

# TEMPORARY DEVELOPMENT DIAGNOSTIC INPUT, NOT AN OPERATIONAL DATA INTERFACE.
# Frozen YES set of the 2026-10-06 read-only historical audit (exceptional ex-ante uncertainty at the voting-open
# cutoff). Classified before any residual was joined and fixed here: never edit it in response to these results.
FROZEN_YES = {
    2014: ('Epsom', 'Ōhāriu', 'Rodney', 'Papakura', 'Napier', 'New Lynn', 'East Coast Bays', 'Pakuranga'),
    2017: ('Ōhāriu', 'Epsom', 'Northland', 'Mt Albert', 'Helensville', 'Clutha-Southland'),
    2020: ('Mt Albert', 'Papakura', 'Auckland Central', 'Epsom', 'Northland', 'Botany', 'Rangitata', 'Southland',
           'Palmerston North', 'Dunedin'),
    2023: ('Auckland Central', 'Wellington Central', 'Rongotai', 'Tāmaki', 'Epsom', 'Mt Albert', 'Remutaka', 'Botany',
           'Tauranga', 'Napier', 'Hamilton West', 'East Coast', 'Mt Roskill', 'Ilam'),
}
BANDS = ((1.5, None), (1.25, 1.5), (1.0, 1.25), (0.75, 1.0), (0.5, 0.75), (0.0, 0.5))
BOUND = float(np.log(16))
DRAWS, SEED = 400, 20261006
Z90 = 1.6448536269514722


def data():
    """Per-election arrays with the frozen flag; residuals use the control (frozen-scale) Gaussian location."""
    env = environments()
    het = {r['id']: r for r in read(HETEROGENEITY)['records']}
    out = {}
    for year in YEARS:
        e = env[year]
        names = [het[i]['name'] for i in e['ids']]
        missing = set(FROZEN_YES[year]) - set(names)
        if missing:
            raise ValueError(f'Frozen flag not in {year} universe: {sorted(missing)}')
        yes = np.array([n in FROZEN_YES[year] for n in names], float)
        total = np.hypot(e['seat'], e['shared'])
        loc, _ = location(e['p'], np.full(len(e['p']), total))
        out[year] = {'names': names, 'p': e['p'], 'v': e['v'], 'yes': yes, 'seat': e['seat'], 'shared': e['shared'],
                     'z': (e['v'] - loc) / total,
                     'auditZ': np.array([abs(het[i]['balanceSeatResidual']) for i in e['ids']]) / e['seat']}
    return out


def nll(theta, envs, index=None):
    """Summed (not per-seat) negative log likelihood; seat sd = frozen seat * exp(a + b * yes)."""
    value, grad = 0., np.zeros(3)
    for year, e in envs.items():
        i = slice(None) if index is None else index[year]
        features = np.column_stack((e['yes'][i], np.zeros(len(e['p'][i]))))
        v, g = environment_value(np.asarray(theta, float), e['p'][i], e['v'][i], features, e['seat'], e['shared'])
        n = len(e['p'][i])
        value += n * v; grad += n * g
    return value, grad


def fit(envs, two_group, index=None):
    free = (True, two_group, False)
    result = minimize(lambda t: nll(t, envs, index), np.zeros(3), jac=True, method='L-BFGS-B',
                      bounds=[(-BOUND, BOUND) if f else (0., 0.) for f in free],
                      options={'ftol': 1e-13, 'gtol': 1e-9, 'maxiter': 1000})
    a, b = result.x[0], result.x[1]
    return {'ordinaryMultiplier': float(np.exp(a)), 'exceptionalMultiplier': float(np.exp(a + b)),
            'ratio': float(np.exp(b)), 'nll': float(result.fun), 'converged': bool(result.success),
            'boundContact': bool(np.any(np.abs(result.x[:2]) > BOUND - 1e-6))}


def describe(z):
    a = np.abs(z)
    if not len(a):
        return {'n': 0}
    q = np.quantile(a, [0.5, 0.8, 0.9, 0.95])
    return {'n': int(len(a)), 'rmsZ': float(np.sqrt(np.mean(z ** 2))), 'maeZ': float(a.mean()),
            'abs50': float(q[0]), 'abs80': float(q[1]), 'abs90': float(q[2]), 'abs95': float(q[3]),
            'shareAbove1': float(np.mean(a > 1)), 'shareAbove1645': float(np.mean(a > Z90)), 'countAbove2': int(np.sum(a > 2))}


def groups(envs, years):
    z = {g: np.concatenate([envs[y]['z'][envs[y]['yes'] == f] for y in years]) for g, f in (('yes', 1), ('no', 0))}
    return {'all': describe(np.concatenate([z['yes'], z['no']])), 'ordinary': describe(z['no']), 'exceptional': describe(z['yes'])}


def bands(envs, key):
    rows = []
    for lo, hi in BANDS:
        row = {'band': f'>={lo}' if hi is None else f'{lo}-<{hi}'}
        for g, f in (('exceptional', 1), ('ordinary', 0)):
            a = np.abs(np.concatenate([envs[y][key][envs[y]['yes'] == f] for y in YEARS]))
            k = int(np.sum((a >= lo) & (a < (np.inf if hi is None else hi))))
            row[g] = {'count': k, 'rate': k / len(a)}
        rows.append(row)
    return rows


def widths(envs, pooled, two):
    """Gaussian log-odds total sd (interval widths scale with it) per election; even-seat 90% width in N/(N+L) pp."""
    out = {}
    for y, e in envs.items():
        sd = {k: float(np.hypot(e['shared'], e['seat'] * m)) for k, m in
              (('frozen', 1.), ('pooledFit', pooled['ordinaryMultiplier']), ('ordinary', two['ordinaryMultiplier']),
               ('exceptional', two['exceptionalMultiplier']))}
        out[str(y)] = {'totalSD': sd, 'evenSeat90WidthPP': {k: 2 * Z90 * 25 * s for k, s in sd.items()},
                       'ordinaryVsFrozen': sd['ordinary'] / sd['frozen'], 'ordinaryVsPooledFit': sd['ordinary'] / sd['pooledFit'],
                       'exceptionalVsOrdinary': sd['exceptional'] / sd['ordinary']}
    return out


def build():
    envs = data()
    pooled, two = fit(envs, False), fit(envs, True)
    lr = 2 * (pooled['nll'] - two['nll'])
    perElection = {str(y): {'twoGroup': fit({y: envs[y]}, True), 'exceptionalN': int(envs[y]['yes'].sum())} for y in YEARS}
    loeo = {}
    for held in YEARS:
        train = {y: envs[y] for y in YEARS if y != held}
        f1, f2 = fit(train, False), fit(train, True)
        th1 = np.array([np.log(f1['ordinaryMultiplier']), 0., 0.])
        th2 = np.array([np.log(f2['ordinaryMultiplier']), np.log(f2['ratio']), 0.])
        n = len(envs[held]['p'])
        loeo[str(held)] = {'twoGroup': f2, 'pooled': f1,
                           'heldOutNllPerSeatTwoMinusPooled': (nll(th2, {held: envs[held]})[0] - nll(th1, {held: envs[held]})[0]) / n}
    ranked = sorted(((abs(envs[y]['z'][i]), y, i) for y in YEARS for i in np.flatnonzero(envs[y]['yes'])), reverse=True)
    top = {(y, i) for _, y, i in ranked[:5]}
    keep = {y: np.array([(y, i) not in top for i in range(len(envs[y]['p']))]) for y in YEARS}
    dropTop5 = fit(envs, True, keep)
    rng = np.random.default_rng(SEED)
    boot, perm = [], []
    for _ in range(DRAWS):
        idx = {y: rng.integers(0, len(envs[y]['p']), len(envs[y]['p'])) for y in YEARS}
        r = fit(envs, True, idx)
        boot.append((r['ordinaryMultiplier'], r['exceptionalMultiplier'], r['ratio'], fit(envs, False, idx)['ordinaryMultiplier']))
    for _ in range(DRAWS):
        shuffled = {y: dict(envs[y], yes=rng.permutation(envs[y]['yes'])) for y in YEARS}
        perm.append(fit(shuffled, True)['ratio'])
    boot = np.array(boot)
    interval = lambda c: [float(np.quantile(boot[:, c], 0.05)), float(np.quantile(boot[:, c], 0.95))]
    return {
        'diagnostic': 'exceptional-scale', 'adopted': False, 'operationalChange': False,
        'question': 'Do the frozen exceptional-uncertainty flags support a narrower ordinary and wider exceptional '
                    'candidate N/L balance seat scale?',
        'flags': {'frozenAudit': '2026-10-06 read-only historical audit; fixed before residuals were joined',
                  'exceptionalByElection': {str(y): len(FROZEN_YES[y]) for y in YEARS},
                  'exceptionalTotal': sum(len(v) for v in FROZEN_YES.values()), 'seats': sum(len(envs[y]['p']) for y in YEARS)},
        'residual': 'z = (v - l) / sqrt(shared^2 + seat^2): Stage48 balance observation v, control Gaussian location l, '
                    'frozen fold scales; includes the shared election effect',
        'descriptive': {'pooled': groups(envs, YEARS), 'byElection': {str(y): groups(envs, (y,)) for y in YEARS}},
        'bands': {'controlZ': bands(envs, 'z'),
                  'auditSeatZ': bands(envs, 'auditZ'),
                  'auditSeatZDefinition': '|balanceSeatResidual| / frozen seat sd (election mean removed with hindsight; '
                                          'the metric of the audit residual table)'},
        'likelihood': {'model': 'Stage48 Gaussian: Sigma_e = diag((seat_e m_i)^2) + shared_e^2 11^T, unchanged means; '
                                'm_i = exp(a + b * exceptional_i); summed seat likelihood over 2014-2023; unpenalised, in-sample',
                       'pooledOneScale': pooled, 'twoGroup': two, 'likelihoodRatio': lr, 'lrPValueChi2df1': float(chi2.sf(lr, 1)),
                       'perElection': perElection, 'leaveOneElectionOut': loeo, 'dropFiveLargestExceptional': dropTop5},
        'resampling': {'draws': DRAWS, 'seed': SEED,
                       'bootstrap': 'seats resampled with replacement within election, labels carried',
                       'ordinaryMultiplier90': interval(0), 'exceptionalMultiplier90': interval(1), 'ratio90': interval(2),
                       'pooledMultiplier90': interval(3), 'shareOrdinaryBelowPooled': float(np.mean(boot[:, 0] < boot[:, 3])),
                       'permutation': 'flags permuted within election, two-group refit',
                       'permutationShareRatioAtLeastObserved': float(np.mean(np.array(perm) >= two['ratio']))},
        'widths': widths(envs, pooled, two),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='recompute and compare with the saved summary')
    check = parser.parse_args().check
    summary = build()
    path = ROOT / OUTPUT
    if check:
        if not equivalent(read(OUTPUT), summary, tolerance=1e-6):
            raise SystemExit('Stale ' + OUTPUT)
        print('exceptional-scale summary matches')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode(summary))


if __name__ == '__main__':
    main()
