"""Stage78 estimation and per-draw simulation: Stage66 estimators with b = 0, carry-forward shares, entrants, split incumbent, swing posterior."""
import numpy as np
from scripts.maori_seat_layer.fit import sigma2 as stage66_sigma2, tau2 as stage66_tau2


def estimate(groups):
    """sigma^2 (within-election pooled variance of D over 2) and tau^2 (method of moments about zero), Stage66 code unchanged."""
    s2, dof = stage66_sigma2(groups)
    return {'sigma2': s2, 'sigma2Dof': dof, 'tau2': stage66_tau2(groups, s2, 0.0), 'elections': len(groups),
            'contrasts': sum(len(g) for g in groups.values())}


def parameter_draws(est, rng, draws):
    """Scaled inverse chi-square parameter draws for sigma^2 and tau^2 plus the shared standard normal (a zero tau^2 stays zero)."""
    s2 = est['sigma2'] * est['sigma2Dof'] / rng.chisquare(est['sigma2Dof'], draws)
    t2 = est['tau2'] * est['elections'] / rng.chisquare(est['elections'], draws) if est['tau2'] > 0 else np.zeros(draws)
    return s2, t2, rng.standard_normal(draws)


def posterior_shift(xbar, s2, t2, k, z):
    """Gaussian posterior draw of the shared shift given the mean change xbar of k exchangeable seats.

    x_j = u + eps_MP,j - eps_LAB,j, so xbar = u + e with Var(e) = 2 sigma^2 / k; u ~ N(0, tau^2).
    Returns (draw, kappa).
    """
    noise = 2.0 * s2 / k
    kappa = np.where(t2 > 0, t2 / (t2 + noise), 0.0)
    return kappa * xbar + np.sqrt(kappa * noise) * z, kappa


def simulate_seat(inp, s2, u, pools, rng, phi=None):
    """Closed-share draws (draws x K) for one seat.

    inp: history.build_inputs output; s2, u: per-draw noise variance and shared Maori Party-label shift;
    pools: {'established': [...], 'other': [...]} entrant shares; rng: this seat's stream. phi: per-draw split fraction.
    The stream is consumed identically for every arm: K normals and K uniforms per draw.
    """
    draws, k = len(s2), len(inp['names'])
    eps = rng.standard_normal((draws, k))
    pick = rng.random((draws, k))
    base = np.zeros((draws, k))
    for i in range(k):
        if inp['base'][i] is not None:
            base[:, i] = inp['base'][i]
    logits = base + np.sqrt(s2)[:, None] * eps
    for i, cls in enumerate(inp['entrant']):
        if cls is not None:
            pool = np.asarray(pools[cls], float)
            logits[:, i] = np.log(pool[np.minimum((pick[:, i] * len(pool)).astype(int), len(pool) - 1)])
    sp = inp['split']
    if sp is not None:
        if phi is None:
            raise ValueError('A split incumbent needs phi')
        phi = np.clip(np.asarray(phi, float), 1e-9, 1 - 1e-9)
        logits[:, sp['toIndex']] = sp['prevLog'] + np.log(phi) + np.sqrt(s2) * eps[:, sp['toIndex']]
        logits[:, sp['fromIndex']] = sp['prevLog'] + np.log1p(-phi) + np.sqrt(s2) * eps[:, sp['fromIndex']]
    logits = logits + u[:, None] * np.asarray(inp['mp'], float)[None, :]
    logits -= logits.max(axis=1, keepdims=True)
    share = np.exp(logits)
    share /= share.sum(axis=1, keepdims=True)
    return share
