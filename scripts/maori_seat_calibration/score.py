"""Held-out scoring of arms C, P and PB, the pooled metrics, the paired bootstrap and the frozen finding rule."""
import math
import numpy as np
from scripts.maori_seat_calibration import model
from scripts.maori_seat_calibration.common import era

ARMS = ('C', 'P', 'PB')
SCHEME_IDS = {'chronological': 1, 'leaveOneElectionOut': 2}
LEVELS = (0.5, 0.8, 0.9)


def training_sets(rows, scheme):
    years = sorted({r['year'] for r in rows})
    if scheme == 'chronological':
        return {e: [y for y in years if y < e] for e in years[1:]}
    return {e: [y for y in years if y != e] for e in years}


def fold_fits(rows, train_years, replicates, seed, scheme_id, e):
    """Per-arm estimates, correction bootstrap and held-out era bias for one training set."""
    units = model.units_from_rows(rows, train_years)
    out = {}
    held_era = era(next(r['pollster'] for r in rows if r['year'] == e))
    for arm in ARMS:
        with_bias = arm == 'PB'
        est = model.fit_arm(units, with_bias)
        rng = np.random.default_rng(np.random.SeedSequence([seed, e, scheme_id, 100 + ARMS.index(arm)]))
        lam, skipped = model.bootstrap(units, with_bias, replicates, rng)
        est.update({'bootstrapSkipped': skipped, 'bootstrapReplicates': replicates, 'lambdaInterval': model.interval(lam) if len(lam) else None,
                    'lambdaReplicates': lam, 'heldOutBias': model.era_bias_for(units, held_era) if with_bias else 0.0, 'trainElections': list(train_years)})
        out[arm] = est
    return out


def draw_base(seed, e, scheme_id, est_c, n_train, draws):
    """Common random numbers: Stage66's stream order (sigma^2 chi-square, tau^2 chi-square, shared normal) for every arm of a fold."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, e, 0 if scheme_id == 2 else 10 + scheme_id]))
    g1 = rng.chisquare(est_c['sigma2Dof'], draws)
    g2 = rng.chisquare(n_train, draws)
    z = rng.standard_normal(draws)
    return rng, g1, g2, z


def arm_draws(arm, est, base, n_train, lam_rng, draws):
    _, g1, g2, z = base
    lam = np.ones(draws)
    if arm != 'C':
        lam = est['lambdaReplicates'][lam_rng.integers(0, len(est['lambdaReplicates']), draws)]
    s2 = est['sigma2'] * est['sigma2Dof'] / g1 * lam
    t2 = (est['tau2'] * n_train / g2 * lam) if est['tau2'] > 0 else np.zeros(draws)
    return s2, t2, z


def predict_polls(rows_e, s2, t2, z, bias, rng, draws):
    """Per held-out poll: winner probabilities, closed-share quantiles and the Maori Party-versus-Labour contrast draws."""
    out = []
    sd, u = np.sqrt(s2), np.sqrt(t2) * z
    for r in rows_e:
        cands = r['candidates']
        logits = np.log([c['pollClosed'] for c in cands])[None, :] + sd[:, None] * rng.standard_normal((draws, len(cands)))
        mp = np.array([c['group'] == 'MP' for c in cands], float)
        logits = logits + (bias + u)[:, None] * mp[None, :]
        win = np.argmax(logits, axis=1)
        prob = np.bincount(win, minlength=len(cands)) / draws
        shifted = logits - logits.max(axis=1, keepdims=True)
        share = np.exp(shifted)
        share /= share.sum(axis=1, keepdims=True)
        names = [c['name'] for c in cands]
        rec = {'id': r['id'], 'year': r['year'], 'prob': prob, 'names': names, 'leader': r['pollLeader'], 'winner': r['actualWinner'], 'leaderWon': r['leaderWon']}
        cover = {}
        for lv in LEVELS:
            lo, hi = np.quantile(share, [(1 - lv) / 2, (1 + lv) / 2], axis=0)
            cover[lv] = [bool(lo[k] <= c['resultClosed'] <= hi[k]) for k, c in enumerate(cands)]
        rec['shareCover'] = cover
        if r['contrastD'] is not None:
            i = [c['group'] for c in cands].index('MP')
            j = [c['party'] for c in cands].index('LAB')
            dpred = logits[:, i] - logits[:, j] - (math.log(cands[i]['pollClosed']) - math.log(cands[j]['pollClosed']))
            rec['contrastCover'] = {lv: bool(np.quantile(dpred, (1 - lv) / 2) <= r['contrastD'] <= np.quantile(dpred, (1 + lv) / 2)) for lv in LEVELS}
        out.append(rec)
    return out


def poll_record(rec, floor):
    names = rec['names']
    p_leader, p_win = float(rec['prob'][names.index(rec['leader'])]), float(rec['prob'][names.index(rec['winner'])])
    y = 1.0 if rec['leaderWon'] else 0.0
    onehot = np.array([1.0 if n == rec['winner'] else 0.0 for n in names])
    out = {'id': rec['id'], 'year': rec['year'], 'leaderWinProbability': p_leader, 'leaderWon': bool(rec['leaderWon']),
           'actualWinnerProbability': p_win, 'logScoreWinner': math.log(max(p_win, floor)),
           'brierLeader': (p_leader - y) ** 2, 'brierMulti': float(((rec['prob'] - onehot) ** 2).sum()),
           'shareCover': {str(lv): rec['shareCover'][lv] for lv in LEVELS}}
    if 'contrastCover' in rec:
        out['contrastCover'] = {str(lv): rec['contrastCover'][lv] for lv in LEVELS}
    return out


def score_scheme(rows, scheme, draws, replicates, seed, floor):
    """Score every arm on every held-out election of a scheme. Returns (fits, poll records by arm)."""
    fits, records = {}, {a: [] for a in ARMS}
    scheme_id = SCHEME_IDS[scheme]
    for e, train in training_sets(rows, scheme).items():
        ests = fold_fits(rows, train, replicates, seed, scheme_id, e)
        held = [r for r in rows if r['year'] == e]
        fits[e] = {a: {k: v for k, v in est.items() if k != 'lambdaReplicates'} for a, est in ests.items()}
        for a in ARMS:
            base = draw_base(seed, e, scheme_id, ests['C'], len(train), draws)  # identical draws for every arm (common random numbers)
            lam_rng = np.random.default_rng(np.random.SeedSequence([seed, e, scheme_id, 7]))
            s2, t2, z = arm_draws(a, ests[a], base, len(train), lam_rng, draws)
            recs = predict_polls(held, s2, t2, z, ests[a]['heldOutBias'], base[0], draws)
            records[a].extend(poll_record(r, floor) for r in recs)
    return fits, records


def metrics(recs):
    n = len(recs)
    p = np.array([r['leaderWinProbability'] for r in recs])
    y = np.array([1.0 if r['leaderWon'] else 0.0 for r in recs])
    var = float((p * (1 - p)).sum())
    out = {'polls': n, 'meanPredictedLeaderWin': float(p.mean()), 'observedLeaderWinRate': float(y.mean()), 'leaderWins': int(y.sum()),
           'calibrationZ': float((y - p).sum() / math.sqrt(var)) if var > 0 else None,
           'brierLeader': float(np.mean([r['brierLeader'] for r in recs])), 'brierMulti': float(np.mean([r['brierMulti'] for r in recs])),
           'meanLogScoreWinner': float(np.mean([r['logScoreWinner'] for r in recs]))}
    out['shareCoverage'] = {str(lv): float(np.mean([c for r in recs for c in r['shareCover'][str(lv)]])) for lv in LEVELS}
    out['shareObservations'] = int(sum(len(r['shareCover']['0.5']) for r in recs))
    con = [r for r in recs if 'contrastCover' in r]
    out['contrastCoverage'] = {str(lv): (float(np.mean([r['contrastCover'][str(lv)] for r in con])) if con else None) for lv in LEVELS}
    out['contrastPolls'] = len(con)
    out['coverageDeviation'] = float(np.mean([abs(out['shareCoverage'][str(lv)] - lv) for lv in LEVELS]))
    bands = {}
    for lo, hi in ((0.0, 0.7), (0.7, 0.9), (0.9, 1.0001)):
        sel = [r for r in recs if lo <= r['leaderWinProbability'] < hi]
        bands['%.1f-%.1f' % (lo, min(hi, 1.0))] = {'polls': len(sel), 'meanPredicted': float(np.mean([r['leaderWinProbability'] for r in sel])) if sel else None,
                                                   'observed': float(np.mean([1.0 if r['leaderWon'] else 0.0 for r in sel])) if sel else None}
    out['bands'] = bands
    return out


def paired_bootstrap(recs_a, recs_b, resamples, seed):
    """Paired poll-level bootstrap of mean(b) - mean(a) for Brier (leader) and the winner log score; ignores within-election dependence."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, 9]))
    n = len(recs_a)
    db = np.array([b['brierLeader'] - a['brierLeader'] for a, b in zip(recs_a, recs_b)])
    dl = np.array([b['logScoreWinner'] - a['logScoreWinner'] for a, b in zip(recs_a, recs_b)])
    idx = rng.integers(0, n, (resamples, n))
    bb, ll = db[idx].mean(axis=1), dl[idx].mean(axis=1)
    return {'brierDifference': float(db.mean()), 'brierInterval90': [float(np.quantile(bb, 0.05)), float(np.quantile(bb, 0.95))],
            'logScoreDifference': float(dl.mean()), 'logScoreInterval90': [float(np.quantile(ll, 0.05)), float(np.quantile(ll, 0.95))]}


def classify(c, p, fold_c, fold_p, fits, skip_limit, z_limit, min_folds):
    """Frozen finding rule for P against C. c, p: pooled metrics; fold_c, fold_p: metrics by fold year; fits: per-fold P fit records."""
    informative = [e for e in (2020, 2023) if e in fits]
    excludes = []
    for e in informative:
        iv = fits[e]['P']['lambdaInterval']
        skipped = fits[e]['P']['bootstrapSkipped'] / fits[e]['P']['bootstrapReplicates']
        excludes.append(bool(iv is not None and skipped <= skip_limit and (iv['p05'] > 1 or iv['p95'] < 1)))
    if not any(excludes):
        return 'insufficient_data'
    better_brier, better_log = p['brierLeader'] < c['brierLeader'], p['meanLogScoreWinner'] > c['meanLogScoreWinner']
    if better_brier != better_log:
        return 'mixed_report_to_james'
    if not better_brier:
        return 'not_helpful'
    folds_better = sum(1 for e in fold_c if fold_p[e]['brierLeader'] < fold_c[e]['brierLeader'])
    restored = (folds_better >= min_folds and p['calibrationZ'] is not None and abs(p['calibrationZ']) <= z_limit
                and p['coverageDeviation'] <= c['coverageDeviation'])
    return 'restored' if restored else 'improves_not_restored'


def reproduce_stage66_control(rows, seed, draws, floor):
    """Arm C under leave-one-election-out with Stage66's seed and draw order: must equal the stored Stage66 backtest ('zero' arm)."""
    recs = []
    for e, train in training_sets(rows, 'leaveOneElectionOut').items():
        est = model.fit_arm(model.units_from_rows(rows, train), False)
        base = draw_base(seed, e, SCHEME_IDS['leaveOneElectionOut'], est, len(train), draws)
        s2, t2, z = arm_draws('C', est, base, len(train), None, draws)
        held = [r for r in rows if r['year'] == e]
        recs.extend(poll_record(r, floor) for r in predict_polls(held, s2, t2, z, 0.0, base[0], draws))
    m = metrics(recs)
    return {'meanPredictedLeaderWin': m['meanPredictedLeaderWin'], 'observedLeaderWinRate': m['observedLeaderWinRate'], 'brierLeaderWins': m['brierLeader'], 'meanLogScoreActualWinner': m['meanLogScoreWinner']}
