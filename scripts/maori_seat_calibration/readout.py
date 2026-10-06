"""2026 readout of the three polled seats under control, inflation and era-bias arms (Stage66 simulation layout, per-draw parameters)."""
import numpy as np
from scripts.maori_seat_layer.common import SEATS, group
from scripts.maori_seat_layer.simulate import summarise


def base_draws(seed, est, tau_dof, draws):
    """Stage66's stream order: sigma^2 chi-square, tau^2 chi-square (only when tau^2 > 0 in the control), shared normal."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, 0]))
    g1 = rng.chisquare(est['sigma2Dof'], draws)
    g2 = rng.chisquare(tau_dof, draws) if est['tau2'] > 0 else None
    return g1, g2, rng.standard_normal(draws)


def simulate(polls, est, lam, bias, unnamed, seed, draws, tau_dof=4):
    """lam: scalar or per-draw multiplier of sigma^2 and tau^2; bias: constant Maori Party shift."""
    g1, g2, z = base_draws(seed, est, tau_dof, draws)
    s2 = est['sigma2'] * est['sigma2Dof'] / g1 * lam
    t2 = est['tau2'] * tau_dof / g2 * lam if g2 is not None else np.zeros(draws)
    u = np.sqrt(t2) * z
    unnamed = np.asarray(unnamed, float)
    out = {'z': z, 'seats': {}}
    for seat, poll in polls.items():
        rng = np.random.default_rng(np.random.SeedSequence([seed, 1 + SEATS.index(seat)]))
        cands = poll['candidates']
        q = np.array([c['pollPercent'] for c in cands], float)
        q = q / q.sum()
        k = len(cands)
        mp = np.array([group(c['party']) == 'MP' for c in cands], float)
        logits = np.log(q)[None, :] + np.sqrt(s2)[:, None] * rng.standard_normal((draws, k)) + (bias + u)[:, None] * mp[None, :]
        logits -= logits.max(axis=1, keepdims=True)
        share = np.exp(logits)
        share /= share.sum(axis=1, keepdims=True)
        rng.integers(0, len(unnamed), draws)  # keep the Stage66 stream layout; the unnamed remainder is not needed for winners
        out['seats'][seat] = {'share': share, 'winner': np.argmax(share, axis=1), 'poll': poll}
    return out


def describe(sim, draws, control=None):
    summary = summarise(sim, draws)
    for seat, v in summary['seats'].items():
        for i, c in enumerate(v['candidates']):
            q = c['shareQuantiles']
            c['share90Width'] = q['0.95'] - q['0.05']
            if control is not None:
                ref = control['seats'][seat]['candidates'][i]
                c['winProbabilityChangeVsControl'] = c['winProbability'] - ref['winProbability']
                c['share90WidthChangeVsControl'] = c['share90Width'] - ref['shareQuantiles']['0.95'] + ref['shareQuantiles']['0.05']
    if control is not None:
        summary['maxWinProbabilityChangeBySeat'] = {s: max(abs(c['winProbabilityChangeVsControl']) for c in v['candidates']) for s, v in summary['seats'].items()}
        summary['flaggedShiftOver0.10'] = sorted(s for s, x in summary['maxWinProbabilityChangeBySeat'].items() if x > 0.10)
    return summary
