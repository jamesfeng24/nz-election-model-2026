"""Held-out scoring of the no-poll fallback arms F, FC and FP, the pooled metrics, the paired bootstrap and the frozen finding rules."""
import itertools
import math
import numpy as np
from scripts.maori_seat_layer.data import calibration_rows
from scripts.maori_seat_calibration import score as score71
from scripts.maori_seat_fallback import history, model
from scripts.maori_seat_fallback.common import SEATS

ARMS = ('F', 'FC', 'FP')
POLLED = {'FC': 'C', 'FP': 'P'}
SCHEME_IDS = {'chronological': 1, 'leaveOneElectionOut': 2}
LEVELS = (0.5, 0.8, 0.9)


def folds(contract, scheme):
    return {int(e): {'fallbackYears': contract['schemes'][scheme][e], 'pollYears': contract['pollTrainingYears'][scheme][e]}
            for e in contract['schemes'][scheme]}


def eligible_polled(rows, res, e):
    """Historical polls of election e with one MP and one LAB candidate whose seat also had exactly one of each last time."""
    out = {}
    for i, r in enumerate(rows):
        if r['year'] != e or r['contrastD'] is None:
            continue
        lo = history.prev_log_odds(res[history.prev_year(e)][r['seat']]['candidates'])
        if lo is not None:
            out[r['seat']] = {'index': i, 'row': r, 'prevLogOdds': lo}
    return out


def polled_changes(rows, res, ests, e, scheme_id, n_train, draws, seed):
    """Per polled-layer arm (C, P) and eligible polled seat: draws of the realised MP-versus-LAB log-odds change since last election."""
    out = {}
    elig = eligible_polled(rows, res, e)
    for arm in ('C', 'P'):
        rng = np.random.default_rng(np.random.SeedSequence([seed, e, scheme_id, 300]))
        base = (rng, rng.chisquare(ests['C']['sigma2Dof'], draws), rng.chisquare(n_train, draws), rng.standard_normal(draws))
        lam_rng = np.random.default_rng(np.random.SeedSequence([seed, e, scheme_id, 301]))
        s2, t2, z = score71.arm_draws(arm, ests[arm], base, n_train, lam_rng, draws)
        u = np.sqrt(t2) * z
        per = {}
        for seat, info in elig.items():
            cands = info['row']['candidates']
            prng = np.random.default_rng(np.random.SeedSequence([seed, e, scheme_id, 400 + info['index']]))
            logits = np.log([c['pollClosed'] for c in cands])[None, :] + np.sqrt(s2)[:, None] * prng.standard_normal((draws, len(cands)))
            mp, lab = [c['group'] for c in cands].index('MP'), [c['party'] for c in cands].index('LAB')
            logits[:, mp] += u
            per[seat] = logits[:, mp] - logits[:, lab] - info['prevLogOdds']
        out[arm] = per
    return out


def contest_record(share, actual, new_cands, prev_lo, floor, kinds=None):
    """Numeric scores of one contest: winner probabilities, favourite, share coverage and the contrast coverage."""
    draws, k = share.shape
    prob = np.bincount(np.argmax(share, axis=1), minlength=k) / draws
    onehot = np.zeros(k)
    onehot[actual] = 1.0
    fav = int(np.argmax(prob))
    rec = {'probActual': float(prob[actual]), 'logScore': math.log(max(float(prob[actual]), floor)), 'brierMulti': float(((prob - onehot) ** 2).sum()),
           'favouriteProb': float(prob[fav]), 'favouriteWon': float(fav == actual), 'shareCover': {}, 'kinds': kinds}
    actual_share = np.array([c['share'] for c in new_cands])
    for lv in LEVELS:
        lo, hi = np.quantile(share, [(1 - lv) / 2, (1 + lv) / 2], axis=0)
        rec['shareCover'][str(lv)] = [float(a <= x <= b) for a, x, b in zip(lo, actual_share, hi)]
    parties = [c['party'] for c in new_cands]
    if parties.count('MP') == 1 and parties.count('LAB') == 1 and prev_lo is not None:
        i, j = parties.index('MP'), parties.index('LAB')
        tiny = 1e-300
        d = np.log(np.maximum(share[:, i], tiny)) - np.log(np.maximum(share[:, j], tiny)) - prev_lo
        actual_d = math.log(actual_share[i] / actual_share[j]) - prev_lo
        rec['contrastCover'] = {str(lv): float(np.quantile(d, (1 - lv) / 2) <= actual_d <= np.quantile(d, (1 + lv) / 2)) for lv in LEVELS}
    return rec


def average(recs):
    """Mean of numeric contest records over swing subsets (the expected score under a random qualifying subset)."""
    if len(recs) == 1:
        return recs[0]
    out = {k: float(np.mean([r[k] for r in recs])) for k in ('probActual', 'logScore', 'brierMulti', 'favouriteProb', 'favouriteWon')}
    out['shareCover'] = {lv: [float(x) for x in np.mean([r['shareCover'][lv] for r in recs], axis=0)] for lv in recs[0]['shareCover']}
    out['kinds'] = recs[0]['kinds']
    if 'contrastCover' in recs[0]:
        out['contrastCover'] = {lv: float(np.mean([r['contrastCover'][lv] for r in recs])) for lv in recs[0]['contrastCover']}
    return out


def score_fold(res, rows, contract, scheme, e, spec, replicates, seed, draws):
    """Score arms F, FC and FP on every seat of election e. Returns (fit record, {arm: [contest records]})."""
    scheme_id = SCHEME_IDS[scheme]
    contrast = history.contrast_rows(res)
    est = model.estimate(history.groups_for(contrast, set(spec['fallbackYears'])))
    pools = history.entrant_pools(set(spec['fallbackYears']), res)
    ests71 = score71.fold_fits(rows, spec['pollYears'], replicates, seed, scheme_id, e)
    changes = polled_changes(rows, res, ests71, e, scheme_id, len(spec['pollYears']), draws, seed)
    brng = np.random.default_rng(np.random.SeedSequence([seed, scheme_id, e, 0]))
    s2, t2, z = model.parameter_draws(est, brng, draws)
    floor, k_sub = contract['winnerLogScoreFloor'], contract['swingSubsetSize']
    prev = res[history.prev_year(e)]
    records = {a: [] for a in ARMS}
    kappas = {a: [] for a in ('FC', 'FP')}
    for seat in SEATS:
        new_cands = res[e][seat]['candidates']
        inp = history.build_inputs(prev[seat]['candidates'], new_cands)
        actual = [c['name'] for c in new_cands].index(res[e][seat]['winner'])
        prev_lo = history.prev_log_odds(prev[seat]['candidates'])
        kinds = [('mp-lab' if c['party'] in ('MP', 'LAB') else 'matched-other' if inp['base'][i] is not None else 'entrant') for i, c in enumerate(new_cands)]

        def run(u):
            rng = np.random.default_rng(np.random.SeedSequence([seed, scheme_id, e, 1 + SEATS.index(seat)]))
            return contest_record(model.simulate_seat(inp, s2, u, pools, rng), actual, new_cands, prev_lo, floor, kinds)
        f_rec = run(np.sqrt(t2) * z)
        records['F'].append(dict(f_rec, year=e, seat=seat))
        for arm in ('FC', 'FP'):
            others = sorted(s for s in changes[POLLED[arm]] if s != seat)
            subsets = list(itertools.combinations(others, min(k_sub, len(others)))) if others else []
            if not subsets:
                records[arm].append(dict(f_rec, year=e, seat=seat))
                continue
            recs = []
            for sub in subsets:
                xbar = np.mean([changes[POLLED[arm]][s] for s in sub], axis=0)
                u, kappa = model.posterior_shift(xbar, s2, t2, len(sub), z)
                kappas[arm].append(float(kappa.mean()))
                recs.append(run(u))
            records[arm].append(dict(average(recs), year=e, seat=seat, subsets=len(subsets)))
    fit = {'fallback': dict(est, trainYears=spec['fallbackYears']), 'pollTrainYears': spec['pollYears'],
           'eligiblePolledSeats': sorted(eligible_polled(rows, res, e)), 'meanKappa': {a: (float(np.mean(v)) if v else None) for a, v in kappas.items()},
           'lambdaInterval': ests71['P']['lambdaInterval']}
    return fit, records


def score_scheme(res, contract, scheme, replicates, seed, draws):
    rows = calibration_rows()
    fits, records = {}, {a: [] for a in ARMS}
    for e, spec in folds(contract, scheme).items():
        fit, recs = score_fold(res, rows, contract, scheme, e, spec, replicates, seed, draws)
        fits[e] = fit
        for a in ARMS:
            records[a].extend(recs[a])
    return fits, records


def metrics(recs):
    n = len(recs)
    p = np.array([r['favouriteProb'] for r in recs])
    y = np.array([r['favouriteWon'] for r in recs])
    var = float((p * (1 - p)).sum())
    out = {'contests': n, 'meanProbabilityOfWinner': float(np.mean([r['probActual'] for r in recs])),
           'meanLogScoreWinner': float(np.mean([r['logScore'] for r in recs])), 'brierMulti': float(np.mean([r['brierMulti'] for r in recs])),
           'meanFavouriteProbability': float(p.mean()), 'favouriteWinRate': float(y.mean()),
           'calibrationZ': float((y - p).sum() / math.sqrt(var)) if var > 0 else None}
    out['shareCoverage'] = {str(lv): float(np.mean([c for r in recs for c in r['shareCover'][str(lv)]])) for lv in LEVELS}
    out['shareObservations'] = int(sum(len(r['shareCover']['0.5']) for r in recs))
    con = [r for r in recs if 'contrastCover' in r]
    out['contrastCoverage'] = {str(lv): (float(np.mean([r['contrastCover'][str(lv)] for r in con])) if con else None) for lv in LEVELS}
    out['contrastContests'] = len(con)
    out['coverageDeviation'] = float(np.mean([abs(out['shareCoverage'][str(lv)] - lv) for lv in LEVELS]))
    out['coverageBias'] = float(np.mean([out['shareCoverage'][str(lv)] - lv for lv in LEVELS]))
    out['shareCoverageByCandidateKind'] = {kind: {'observations': int(sum(k == kind for r in recs for k in r['kinds'])),
                                                  **{str(lv): float(np.mean([c for r in recs for c, k in zip(r['shareCover'][str(lv)], r['kinds']) if k == kind]))
                                                     for lv in LEVELS}}
                                           for kind in ('mp-lab', 'matched-other', 'entrant') if any(k == kind for r in recs for k in r['kinds'])}
    return out


def by_year(recs, year):
    return [r for r in recs if r['year'] == year]


def paired_bootstrap(recs_a, recs_b, resamples, seed):
    """Paired contest-level bootstrap of mean(b) - mean(a) for the winner log score and the multi Brier score; ignores within-election dependence."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, 9]))
    n = len(recs_a)
    dl = np.array([b['logScore'] - a['logScore'] for a, b in zip(recs_a, recs_b)])
    db = np.array([b['brierMulti'] - a['brierMulti'] for a, b in zip(recs_a, recs_b)])
    idx = rng.integers(0, n, (resamples, n))
    ll, bb = dl[idx].mean(axis=1), db[idx].mean(axis=1)
    return {'logScoreDifference': float(dl.mean()), 'logScoreInterval90': [float(np.quantile(ll, 0.05)), float(np.quantile(ll, 0.95))],
            'brierDifference': float(db.mean()), 'brierInterval90': [float(np.quantile(bb, 0.05)), float(np.quantile(bb, 0.95))]}


def swing_rule(f, x, fold_f, fold_x, cmp, min_folds):
    """Rule 1 for one swing arm against F: swing_helps, swing_hurts or mixed_report_to_james, with the evidence qualifier."""
    better_log, better_brier = x['meanLogScoreWinner'] > f['meanLogScoreWinner'], x['brierMulti'] < f['brierMulti']
    worse_log, worse_brier = x['meanLogScoreWinner'] < f['meanLogScoreWinner'], x['brierMulti'] > f['brierMulti']
    folds_better = sum(1 for e in fold_f if fold_x[e]['meanLogScoreWinner'] > fold_f[e]['meanLogScoreWinner'])
    if better_log and better_brier and folds_better >= min_folds:
        cls = 'swing_helps'
    elif worse_log and worse_brier:
        cls = 'swing_hurts'
    else:
        cls = 'mixed_report_to_james'
    lo, hi = cmp['logScoreInterval90']
    return {'class': cls, 'foldsLogScoreBetter': folds_better, 'evidenceQualifier': 'clear' if (lo > 0 or hi < 0) else 'weak'}


def registration(fc_class, fp_class):
    """Registered fallback from the two swing classes: the FC-to-FP range, F alone, or nothing until James has been asked."""
    classes = {fc_class, fp_class}
    if 'mixed_report_to_james' in classes or len(classes) > 1:
        return 'none_report_to_james'
    return 'F' if classes == {'swing_hurts'} else 'FC_to_FP'


def calibration_class(m, z_limit, deviation_max):
    """Rule 2: calibrated, overconfident or underconfident from the favourite z and the share-coverage deviation."""
    z = m['calibrationZ']
    if z is not None and abs(z) <= z_limit and m['coverageDeviation'] <= deviation_max:
        return 'calibrated'
    if (z is not None and z < -z_limit) or m['coverageBias'] < -deviation_max:
        return 'overconfident'
    return 'underconfident'
