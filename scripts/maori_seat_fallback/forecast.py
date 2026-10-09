"""2026 per-draw fallback for the four unpolled seats under arms F, FC and FP, and the reported (never adopted) sensitivities."""
import numpy as np
from scripts.maori_seat_layer.data import calibration_rows
from scripts.maori_seat_layer.simulate import current_polls
from scripts.maori_seat_calibration import model as model71, readout as readout71
from scripts.maori_seat_fallback import history, inputs2026, model
from scripts.maori_seat_fallback.common import read, SEATS, STAGE66, STAGE71, DESIGN

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
UNPOLLED = ('Waiariki', 'Ikaroa-Rāwhiti', 'Tāmaki Makaurau', 'Te Tai Tokerau')


def polled_layers(draws):
    """Stage66 control (C) and Stage71 inflated (P) simulations of the polled seats, exactly as Stage71 produced its forecast."""
    c71, stage66_seed = read(STAGE71 + '/design-contract.json'), read(STAGE66 + '/design-contract.json')['seed']
    rows = calibration_rows()
    units = model71.units_from_rows(rows, sorted({r['year'] for r in rows}))
    est = model71.fit_arm(units, False)
    unnamed = sorted(r['unnamedShare'] for r in rows)
    lam, _ = model71.bootstrap(units, False, c71['bootstrapReplicates'], np.random.default_rng(np.random.SeedSequence([c71['seed'], 2026, 1])))
    lam_draws = lam[np.random.default_rng(np.random.SeedSequence([c71['seed'], 2026, 3])).integers(0, len(lam), draws)]
    polls, _, _ = current_polls()
    return polls, {'C': readout71.simulate(polls, est, 1.0, 0.0, unnamed, stage66_seed, draws),
                   'P': readout71.simulate(polls, est, lam_draws, 0.0, unnamed, stage66_seed, draws)}


def polled_changes(polls, sim, res):
    """Draws of the realised MP-versus-LAB log-odds change since 2023 for each polled seat that qualifies by party label."""
    out = {}
    for seat, poll in polls.items():
        parties = [c['party'] for c in poll['candidates']]
        lo = history.prev_log_odds(res[2023][seat]['candidates'])
        if parties.count('MP') != 1 or parties.count('LAB') != 1 or lo is None:
            continue
        share = sim['seats'][seat]['share']
        out[seat] = np.log(share[:, parties.index('MP')]) - np.log(share[:, parties.index('LAB')]) - lo
    return out


def fallback_parameters(contract, res, draws):
    est = model.estimate(history.groups_for(history.contrast_rows(res), {2017, 2020, 2023}))
    pools = history.entrant_pools({2017, 2020, 2023}, res)
    s2, t2, z = model.parameter_draws(est, np.random.default_rng(np.random.SeedSequence([contract['seed'], 2026, 0])), draws)
    phi = np.random.default_rng(np.random.SeedSequence([contract['seed'], 2026, 2])).random(draws)
    return est, pools, s2, t2, z, phi


def simulate(contract, draws, res=None, layers=None, fallback=None):
    """Per-draw fallback for every unpolled seat. Returns {'z', 'arms': {arm: {seat: share}}, 'inputs', 'swing', 'estimate'}.

    The output per seat has the Stage66 shape (share array, candidate list; winner = argmax) so that the assembly can consume it.
    """
    res = res or history.results()
    polls, sims = layers or polled_layers(draws)
    est, pools, s2, t2, z, phi = fallback or fallback_parameters(contract, res, draws)
    slates = inputs2026.slates()
    inps = {seat: inputs2026.seat_inputs(seat, slates[seat], res) for seat in UNPOLLED}
    changes = {arm: polled_changes(polls, sims[key], res) for arm, key in (('FC', 'C'), ('FP', 'P'))}

    def shifted(arm, exclude=()):
        used = sorted(s for s in changes[arm] if s not in exclude)
        xbar = np.mean([changes[arm][s] for s in used], axis=0)
        u, kappa = model.posterior_shift(xbar, s2, t2, len(used), z)
        return u, {'seats': used, 'meanKappa': float(kappa.mean()), 'xbarMean': float(xbar.mean()), 'xbarSd': float(xbar.std())}

    def seats(u, phi_use):
        out = {}
        for seat in UNPOLLED:
            rng = np.random.default_rng(np.random.SeedSequence([contract['seed'], 2026, 10 + SEATS.index(seat)]))
            out[seat] = model.simulate_seat(inps[seat], s2, u, pools, rng, phi_use if inps[seat]['split'] else None)
        return out

    arms, swing = {'F': seats(np.sqrt(t2) * z, phi)}, {}
    for arm in ('FC', 'FP'):
        u, swing[arm] = shifted(arm)
        arms[arm] = seats(u, phi)
    sens = {}
    for arm in ('F', 'FC', 'FP'):
        for value in contract['phi']['sensitivityFixed']:
            u = np.sqrt(t2) * z if arm == 'F' else shifted(arm)[0]
            sens['%s, phi %.1f' % (arm, value)] = (arm, {'Te Tai Tokerau': seats(u, np.full(draws, value))['Te Tai Tokerau']})
    for arm in ('FC', 'FP'):
        u, info = shifted(arm, exclude=('Te Tai Tonga',))
        sens[arm + ', swing without Te Tai Tonga'] = (arm, seats(u, phi))
        swing[arm + ' without Te Tai Tonga'] = info
    return {'z': z, 'arms': arms, 'inputs': inps, 'swing': swing, 'estimate': est, 'pools': pools, 'sensitivities': sens, 'polls': polls, 'polledSims': sims}


def summarise_seat(inp, share, draws):
    win = np.argmax(share, axis=1)
    prob = np.bincount(win, minlength=len(inp['names'])) / draws
    cands = []
    for i, name in enumerate(inp['names']):
        base = inp['base'][i]
        cands.append({'name': name, 'party': inp['codes'][i], 'carriedForwardShare': (float(np.exp(base)) if base is not None else None),
                      'entrantPool': inp['entrant'][i], 'winProbability': float(prob[i]),
                      'winProbabilityMonteCarloSE': float(np.sqrt(prob[i] * (1 - prob[i]) / draws)), 'meanShare': float(share[:, i].mean()),
                      'shareQuantiles': {str(q): float(np.quantile(share[:, i], q)) for q in QUANTILES}})
    by_code = {}
    for code in sorted(set(inp['codes'])):
        by_code[code] = float(sum(prob[i] for i, c in enumerate(inp['codes']) if c == code))
    return {'candidates': cands, 'winProbabilityByPartyCode': by_code}


def win_counts(sim, arm, draws):
    """Distributions of Maori Party-label (MP) wins among the four unpolled seats and, for FC and FP, among all seven seats."""
    codes = {seat: np.array(sim['inputs'][seat]['codes']) for seat in UNPOLLED}
    mp_unpolled = sum((codes[s][np.argmax(sim['arms'][arm][s], axis=1)] == 'MP').astype(int) for s in UNPOLLED)
    out = {'unpolled': {'distribution': [float(x) for x in np.bincount(mp_unpolled, minlength=5) / draws], 'mean': float(mp_unpolled.mean())}}
    ttt = (codes['Te Tai Tokerau'][np.argmax(sim['arms'][arm]['Te Tai Tokerau'], axis=1)] == 'TTT')
    out['teTaiTokerauPartyWinsTeTaiTokerau'] = float(ttt.mean())
    if arm in ('FC', 'FP'):
        layer = sim['polledSims']['C' if arm == 'FC' else 'P']
        polled = sum((np.array([c['party'] == 'MP' for c in layer['seats'][s]['poll']['candidates']])[layer['seats'][s]['winner']]).astype(int)
                     for s in layer['seats'])
        total = mp_unpolled + polled
        out['allSeven'] = {'distribution': [float(x) for x in np.bincount(total, minlength=8) / draws], 'mean': float(total.mean()),
                           'polledSeatsMean': float(polled.mean())}
    return out


def build(contract, draws=None):
    draws = draws or contract['readoutDraws']
    sim = simulate(contract, draws)
    out = {'draws': draws, 'seed': contract['seed'], 'unpolledSeats': list(UNPOLLED), 'fallbackEstimate': sim['estimate'],
           'entrantPoolSizes': {k: len(v) for k, v in sim['pools'].items()}, 'swing': sim['swing'], 'arms': {}, 'sensitivities': {}}
    for arm, seats in sim['arms'].items():
        out['arms'][arm] = {'seats': {s: summarise_seat(sim['inputs'][s], sh, draws) for s, sh in seats.items()}, 'winCounts': win_counts(sim, arm, draws)}
    for name, (arm, seats) in sim['sensitivities'].items():
        summaries, shifts = {}, {}
        for s, sh in seats.items():
            summaries[s] = summarise_seat(sim['inputs'][s], sh, draws)
            ref = out['arms'][arm]['seats'][s]['candidates']
            shifts[s] = max(abs(a['winProbability'] - b['winProbability']) for a, b in zip(summaries[s]['candidates'], ref))
        out['sensitivities'][name] = {'against': arm, 'seats': summaries, 'maxWinProbabilityShiftBySeat': shifts,
                                      'flaggedShiftOver0.10': sorted(s for s, x in shifts.items() if x > read(DESIGN)['flagShift'])}
    return out, sim
