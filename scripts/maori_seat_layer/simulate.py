"""Per-draw Maori seat candidate shares and winners from current polls and the calibrated error model."""
import math
import numpy as np
from scripts.maori_seat_layer.common import read, SEATS, CURRENT_POLLS, fold, group

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def current_polls(path=CURRENT_POLLS):
    """Latest poll per seat by fieldwork end; earlier polls are returned separately so they are never silently dropped."""
    data = read(path)
    latest, superseded = {}, []
    for poll in sorted(data['polls'], key=lambda p: (p['fieldworkEnd'], p['id'])):
        if poll['seat'] not in SEATS:
            raise ValueError('Unknown Maori seat: ' + poll['seat'])
        if len(poll['candidates']) < 2:
            raise ValueError('A seat poll needs at least two candidates: ' + poll['id'])
        if len({fold(c['name']) for c in poll['candidates']}) != len(poll['candidates']):
            raise ValueError('Duplicate candidate in ' + poll['id'])
        if poll['seat'] in latest:
            superseded.append(latest[poll['seat']]['id'])
        latest[poll['seat']] = poll
    return latest, superseded, data


def scale_draws(rng, value, dof, draws):
    """Scaled inverse chi-square parameter draws; a zero estimate stays zero."""
    if value <= 0:
        return np.zeros(draws)
    return value * dof / rng.chisquare(dof, draws)


def simulate(polls, params, draws, seed, oth_sigma2=None):
    """Return per-seat arrays. polls: seat -> poll record; params: sigma2, sigma2Dof, tau2, tauDof, bias, unnamedShares."""
    base = np.random.default_rng(np.random.SeedSequence([seed, 0]))
    s2 = scale_draws(base, params['sigma2'], params['sigma2Dof'], draws)
    t2 = scale_draws(base, params['tau2'], params['tauDof'], draws)
    z = base.standard_normal(draws)
    u = np.sqrt(t2) * z
    unnamed = np.asarray(params['unnamedShares'], float)
    out = {'z': z, 'seats': {}}
    for seat, poll in polls.items():
        rng = np.random.default_rng(np.random.SeedSequence([seed, 1 + SEATS.index(seat)]))
        cands = poll['candidates']
        q = np.array([c['pollPercent'] for c in cands], float)
        q = q / q.sum()
        k = len(cands)
        sd = np.sqrt(s2)[:, None] * np.ones((1, k))
        if oth_sigma2 is not None:  # post-hoc sensitivity: wider noise for candidates outside the MP and LAB groups
            wide = np.array([group(c['party']) == 'OTH' for c in cands])
            sd[:, wide] = np.sqrt(np.maximum(s2, oth_sigma2))[:, None]
        mp = np.array([group(c['party']) == 'MP' for c in cands], float)
        logits = np.log(q)[None, :] + sd * rng.standard_normal((draws, k)) + (params['bias'] + u)[:, None] * mp[None, :]
        logits -= logits.max(axis=1, keepdims=True)
        share = np.exp(logits)
        share /= share.sum(axis=1, keepdims=True)
        w = unnamed[rng.integers(0, len(unnamed), draws)]
        out['seats'][seat] = {'share': share * (1.0 - w)[:, None], 'winner': np.argmax(share, axis=1), 'poll': poll}
    return out


def summarise(sim, draws):
    seats = {}
    for seat, s in sim['seats'].items():
        cands = s['poll']['candidates']
        win = np.bincount(s['winner'], minlength=len(cands)) / draws
        seats[seat] = {'pollId': s['poll']['id'], 'fieldworkEnd': s['poll']['fieldworkEnd'], 'candidates': [
            {'name': c['name'], 'party': c['party'], 'pollPercent': c['pollPercent'], 'winProbability': float(win[i]),
             'winProbabilityMonteCarloSE': float(math.sqrt(win[i] * (1 - win[i]) / draws)),
             'meanShare': float(s['share'][:, i].mean()),
             'shareQuantiles': {str(q): float(np.quantile(s['share'][:, i], q)) for q in QUANTILES}}
            for i, c in enumerate(cands)]}
    polled = list(sim['seats'])
    mp_wins = {seat: np.array([sim['seats'][seat]['poll']['candidates'][i]['party'] == 'MP' for i in sim['seats'][seat]['winner']]) for seat in polled}
    count = sum(mp_wins[s].astype(int) for s in polled)
    dist = np.bincount(count, minlength=len(polled) + 1) / draws
    p = [float(mp_wins[s].mean()) for s in polled]
    independent = np.array([1.0])
    for pi in p:
        independent = np.convolve(independent, [1 - pi, pi])
    return {'seats': seats, 'polledSeats': polled,
            'maoriPartyWinsAmongPolledSeats': {'distribution': [float(x) for x in dist], 'meanWins': float(count.mean()),
                                               'distributionIfIndependent': [float(x) for x in independent]}}
