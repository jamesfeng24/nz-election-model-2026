"""Frozen Stage71 estimation: Stage66 sigma and tau, the penalty-free variance inflation, the leave-self-out pollster-era bias and the bootstrap."""
import math
import numpy as np
from scripts.maori_seat_layer.fit import sigma2 as stage66_sigma2
from scripts.maori_seat_calibration.common import era


def poll_vectors(row):
    """Reference-candidate-1 error contrasts x = A d, the Maori Party indicator contrast A m, and A A' for one poll."""
    d = np.array([math.log(c['resultClosed']) - math.log(c['pollClosed']) for c in row['candidates']])
    m = np.array([1.0 if c['group'] == 'MP' else 0.0 for c in row['candidates']])
    x, a = d[1:] - d[0], m[1:] - m[0]
    return x, a, np.eye(len(x)) + np.ones((len(x), len(x)))


def make_unit(year, pollster, rows):
    return {'year': year, 'era': era(pollster), 'polls': list(rows)}


def units_from_rows(rows, years):
    out = []
    for y in years:
        sel = [r for r in rows if r['year'] == y]
        out.append(make_unit(y, sel[0]['pollster'], sel))
    return out


def unit_mean(unit):
    d = [r['contrastD'] for r in unit['polls'] if r['contrastD'] is not None]
    return sum(d) / len(d) if d else None


def era_bias(units, i):
    """Equal-weight mean of the election means of D over the other source elections of the same pollster era; 0 when there is none."""
    me = units[i]
    means = {}
    for j, u in enumerate(units):
        if u['year'] != me['year'] and u['era'] == me['era'] and unit_mean(u) is not None:
            means.setdefault(u['year'], unit_mean(u))
    return sum(means.values()) / len(means) if means else 0.0


def era_bias_for(units, era_name):
    """Bias applied to a held-out election of the given era: mean of the training elections' means of that era."""
    means = [unit_mean(u) for u in units if u['era'] == era_name and unit_mean(u) is not None]
    return sum(means) / len(means) if means else 0.0


def estimate(units, with_bias):
    """Stage66 sigma^2 (within-election pooled / 2) and tau^2 (method of moments about the arm's bias) and the per-unit bias."""
    groups = {i: [r['contrastD'] for r in u['polls'] if r['contrastD'] is not None] for i, u in enumerate(units)}
    groups = {i: g for i, g in groups.items() if g}
    dof = sum(len(g) for g in groups.values()) - len(groups)
    if not groups or dof < 1:
        return None
    s2, dof = stage66_sigma2(groups)
    bias = [era_bias(units, i) if with_bias else 0.0 for i in range(len(units))]
    first = sum((sum(g) / len(g) - bias[i]) ** 2 for i, g in groups.items()) / len(groups)
    noise = sum(2.0 * s2 / len(g) for g in groups.values()) / len(groups)
    return {'sigma2': s2, 'sigma2Dof': dof, 'tau2': max(0.0, first - noise), 'bias': bias, 'elections': len(units)}


def lambda_hat(units, est):
    """Maximum-likelihood multiplier S / N of the covariance implied by (sigma^2, tau^2) over all named candidates."""
    S, N = 0.0, 0
    for i, u in enumerate(units):
        parts = [poll_vectors(r) for r in u['polls']]
        r = np.concatenate([x - est['bias'][i] * a for x, a, _ in parts])
        a_all = np.concatenate([a for _, a, _ in parts])
        sigma = est['tau2'] * np.outer(a_all, a_all)
        k = 0
        for x, a, aa in parts:
            sigma[k:k + len(x), k:k + len(x)] += est['sigma2'] * aa
            k += len(x)
        S += float(r @ np.linalg.solve(sigma, r))
        N += len(r)
    return S / N


def fit_arm(units, with_bias):
    est = estimate(units, with_bias)
    est['lambdaHat'] = lambda_hat(units, est)
    return est


def bootstrap(units, with_bias, replicates, rng):
    """Two-stage bootstrap (elections, then polls within) of the correction: returns replicate lambda-hats and the skip count."""
    lam, skipped = [], 0
    n = len(units)
    for _ in range(replicates):
        new = []
        for idx in rng.integers(0, n, n):
            polls = units[idx]['polls']
            pick = rng.integers(0, len(polls), len(polls))
            new.append({'year': units[idx]['year'], 'era': units[idx]['era'], 'polls': [polls[k] for k in pick]})
        est = estimate(new, with_bias)
        if est is None or est['sigma2'] <= 0:
            skipped += 1
            continue
        lam.append(lambda_hat(new, est))
    return np.array(lam), skipped


def interval(lam):
    return {'p05': float(np.quantile(lam, 0.05)), 'p50': float(np.quantile(lam, 0.5)), 'p95': float(np.quantile(lam, 0.95)), 'replicates': int(len(lam))}
