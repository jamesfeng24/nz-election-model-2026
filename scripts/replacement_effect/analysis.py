"""Fold-trained replacement arms, candidate-layer scoring and descriptive inference (frozen design)."""
import numpy as np
from scipy.stats import norm
from scripts.balance_scale.data import environments
from scripts.balance_scale.fit import location
from scripts.uncertainty_revision.coordinates import partition
from .common import ARMS, FOLD_YEARS, INVENTORY, design, read
from .sample import SAMPLES, select

PP = 100.0


def fit_folds(table, name):
    """Earlier-target-only fits: K constant, P partial transfer with rho in [0, 1], T/C parameter free."""
    folds = {}
    for year in FOLD_YEARS:
        train = select(table, name, below=year)
        old = np.array([r['RoldFraction'] for r in train])
        new = np.array([r['RnewFraction'] for r in train])
        var = float(np.var(old))
        raw_slope = float(np.cov(old, new, bias=True)[0, 1] / var) if var > 0 else 0.0
        rho = min(1.0, max(0.0, raw_slope))
        folds[year] = {'trainingTargetYears': sorted({r['targetYear'] for r in train}), 'trainingSeats': len(train),
                       'K': {'a': float(new.mean())},
                       'P': {'a': float(new.mean() - rho * old.mean()), 'rho': rho, 'unconstrainedSlope': raw_slope,
                             'atBound': bool(raw_slope < 0 or raw_slope > 1)}}
    return folds


def predicted_r(arm, fold, r_old, mu):
    if arm == 'C':
        return mu
    if arm == 'K':
        return fold['K']['a']
    if arm == 'P':
        return fold['P']['a'] + fold['P']['rho'] * r_old
    return r_old


def crps(y, mu, sd):
    z = (y - mu) / sd
    return sd * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1 / np.sqrt(np.pi))


def layer_seats(table, name, env):
    """Affected seats: scored replaced N/L candidates whose control R is exactly neutral (counted exclusions)."""
    records = {r['targetElectorateId']: r for r in read(INVENTORY)['candidateRecords']}
    seats, excluded = {}, {'notInLayer': 0, 'notNationalOrLabour': 0, 'ownRHistory': 0}
    for r in select(table, name):
        if r['targetYear'] not in FOLD_YEARS:
            continue
        found = [(rec, i) for rec in records.values() if r['targetOccurrenceId'] in rec['ids']
                 for i in [rec['ids'].index(r['targetOccurrenceId'])]]
        if not found:
            excluded['notInLayer'] += 1
            continue
        rec, i = found[0]
        n, l, _ = partition(rec['groups'])
        if i not in (n[0], l[0]):
            excluded['notNationalOrLabour'] += 1
            continue
        feature = rec['features'][i]
        if feature['centered'][1] != 0.0 or feature['supportedMass']['R'] != 0:
            excluded['ownRHistory'] += 1
            continue
        seat = seats.setdefault(rec['targetElectorateId'], {'record': rec, 'year': r['targetYear'], 'replaced': []})
        seat['replaced'].append({'index': i, 'rOld': r['RoldFraction'], 'rNew': r['RnewFraction'], 'key': r['key']})
    index = {cid: k for y in FOLD_YEARS for k, cid in enumerate(env[y]['ids'])}
    return seats, excluded, index


def score_name(table, name, folds):
    env = environments()
    seats, excluded, index = layer_seats(table, name, env)
    rows = []
    for cid, seat in sorted(seats.items()):
        year, rec = seat['year'], seat['record']
        e = env[year]
        k = index[cid]
        n, l, _ = partition(rec['groups'])
        mean = np.array(rec['mean'])
        if abs(mean.sum() - 1) > 1e-9 or abs(e['p'][k] - mean[n[0]] / (mean[n[0]] + mean[l[0]])) > 1e-12:
            raise ValueError('Layer mean does not reproduce the Stage48 balance mean: ' + cid)
        theta, mu = rec['parameters']['coefficients']['R'], rec['trainingOnlyMeans']['R']
        total = float(np.hypot(e['seat'], e['shared']))
        actual = np.array(rec['actual'])
        row = {'seat': cid, 'year': year, 'replacedKeys': [r['key'] for r in seat['replaced']], 'thetaR': theta, 'muR': mu,
               'v': float(e['v'][k]), 'totalSd': total, 'arms': {}}
        for arm in ARMS:
            shift = np.zeros(len(mean))
            rhat = {}
            for r in seat['replaced']:
                rhat[r['index']] = predicted_r(arm, folds[year], r['rOld'], mu)
                shift[r['index']] = theta * (rhat[r['index']] - mu)
            q = mean * np.exp(shift)
            q = q / q.sum()
            p = float(q[n[0]] / (q[n[0]] + q[l[0]]))
            loc = float(location(np.array([p]), np.array([total]))[0][0])
            z = (row['v'] - loc) / total
            replaced_share_error = [abs(q[r['index']] - actual[r['index']]) * PP for r in seat['replaced']]
            replaced_share_signed = [(q[r['index']] - actual[r['index']]) * PP for r in seat['replaced']]
            row['arms'][arm] = {'p': p, 'location': loc, 'maxAbsLogWeightShift': float(np.max(np.abs(shift))),
                                'crps': float(crps(row['v'], loc, total)), 'sqError': float((row['v'] - loc) ** 2),
                                'nlpd': float(0.5 * np.log(2 * np.pi * total ** 2) + 0.5 * z * z), 'z2': float(z * z),
                                'replacedShareAbsErrorPP': replaced_share_error, 'replacedShareSignedErrorPP': replaced_share_signed,
                                'marginAbsErrorPP': float(abs((q[n[0]] - q[l[0]]) - (actual[n[0]] - actual[l[0]])) * PP),
                                'rHatPP': {str(i): v * PP for i, v in rhat.items()}}
        rows.append(row)
    return rows, excluded


def bootstrap_upper(diffs, years, spec):
    rng = np.random.default_rng(spec['seed'])
    diffs, years = np.asarray(diffs), np.asarray(years)
    groups = [np.flatnonzero(years == y) for y in sorted(set(years.tolist()))]
    draws = []
    for _ in range(spec['draws']):
        picks = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        draws.append(diffs[picks].mean())
    low, high = np.quantile(draws, [(1 - spec['level']) / 2 + 0.0, 1 - (1 - spec['level']) / 2])
    return float(low), float(high)


def compare(rows, x, y, rule):
    """Decision quantities for arm x versus arm y on the affected seats."""
    d_crps = np.array([r['arms'][x]['crps'] - r['arms'][y]['crps'] for r in rows])
    d_mse = np.array([r['arms'][x]['sqError'] - r['arms'][y]['sqError'] for r in rows])
    d_nlpd = np.array([r['arms'][x]['nlpd'] - r['arms'][y]['nlpd'] for r in rows])
    years = [r['year'] for r in rows]
    base = float(np.mean([r['arms']['C']['crps'] for r in rows]))
    by_year = {y: float(d_crps[[i for i, v in enumerate(years) if v == y]].mean()) for y in sorted(set(years))}
    low, high = bootstrap_upper(d_crps, years, rule['bootstrap'])
    relative = float(d_crps.mean() / base)
    t = rule['relativeCrpsThreshold']
    if len(rows) < rule['minimumAffectedSeats']:
        label = 'INSUFFICIENT'
    elif relative >= t:
        label = 'WORSE'
    elif abs(relative) < t:
        label = 'NEGLIGIBLE'
    elif d_mse.mean() <= 0 and sum(v < 0 for v in by_year.values()) >= 2 and high < 0:
        label = 'IMPROVES'
    else:
        label = 'MIXED'
    equal_election = float(np.mean(list(by_year.values())))
    return {'comparison': f'{x} vs {y}', 'affectedSeats': len(rows), 'meanDeltaCrps': float(d_crps.mean()),
            'relativeDeltaCrps': relative, 'controlMeanCrps': base, 'equalElectionMeanDeltaCrps': equal_election,
            'deltaCrpsByElection': {str(k): v for k, v in by_year.items()},
            'bootstrap90Interval': [low, high], 'meanDeltaMse': float(d_mse.mean()), 'meanDeltaNlpd': float(d_nlpd.mean()),
            'label': label}


def finding(results, rule):
    kc, pk, pc = results['K vs C']['label'], results['P vs K']['label'], results['P vs C']['label']
    if 'INSUFFICIENT' in (kc, pc):
        return 'insufficient_sample'
    if pc == 'IMPROVES' and pk == 'IMPROVES':
        return 'partial_transfer'
    if kc == 'IMPROVES' and pk != 'IMPROVES':
        return 'constant_shift_only'
    if kc in ('NEGLIGIBLE', 'WORSE') and pc in ('NEGLIGIBLE', 'WORSE'):
        return 'neutral_adequate'
    return 'mixed_report_to_james'


def supporting(rows):
    out = {}
    for arm in ARMS:
        shares = [e for r in rows for e in r['arms'][arm]['replacedShareAbsErrorPP']]
        out[arm] = {'meanCrps': float(np.mean([r['arms'][arm]['crps'] for r in rows])),
                    'meanSquaredBalanceError': float(np.mean([r['arms'][arm]['sqError'] for r in rows])),
                    'meanNlpd': float(np.mean([r['arms'][arm]['nlpd'] for r in rows])),
                    'meanSquaredStandardisedResidual': float(np.mean([r['arms'][arm]['z2'] for r in rows])),
                    'replacedCandidateShareMaePP': float(np.mean(shares)),
                    'replacedCandidateShareMeanSignedErrorPP_predictedMinusActual_contextOnly':
                        float(np.mean([e for r in rows for e in r['arms'][arm]['replacedShareSignedErrorPP']])),
                    'marginMaePP': float(np.mean([r['arms'][arm]['marginAbsErrorPP'] for r in rows])),
                    'maxAbsLogWeightShift': float(max(r['arms'][arm]['maxAbsLogWeightShift'] for r in rows))}
    return out


def r_unit_errors(table, name, folds):
    """Out-of-fold squared error of the R prediction, all sample rows of each fold year (not only layer seats)."""
    mu = {}
    for rec in read(INVENTORY)['candidateRecords']:
        mu.setdefault(rec['targetYear'], set()).add(rec['trainingOnlyMeans']['R'])
    out = {}
    for year in FOLD_YEARS:
        if len(mu[year]) != 1:
            raise ValueError('Fold mean R is not constant within a target year')
        m = next(iter(mu[year]))
        rows = [r for r in select(table, name) if r['targetYear'] == year]
        new = np.array([r['RnewFraction'] for r in rows])
        out[str(year)] = {'seats': len(rows), 'muRPP': m * PP, 'meanRnewPP': float(new.mean() * PP),
                          'meanRnewMinusMuPP': float((new - m).mean() * PP),
                          'rmsePP': {arm: float(np.sqrt(np.mean([(predicted_r(arm, folds[year], r['RoldFraction'], m)
                                                                  - r['RnewFraction']) ** 2 for r in rows])) * PP)
                                     for arm in ARMS}}
    return out


def run_sample(table, name):
    folds = fit_folds(table, name)
    rows, excluded = score_name(table, name, folds)
    rule = design()['decisionRule']
    results = {c: compare(rows, *c.split(' vs '), rule) for c in ('K vs C', 'P vs K', 'P vs C', 'T vs C')}
    return {'sample': name, 'seatsInSample': len(select(table, name)), 'folds': {str(k): v for k, v in folds.items()},
            'layerExclusions': excluded, 'affectedSeats': len(rows),
            'affectedSeatsByElection': {str(y): sum(r['year'] == y for r in rows) for y in FOLD_YEARS},
            'comparisons': results, 'finding': finding(results, rule), 'supporting': supporting(rows),
            'rUnitOutOfFold': r_unit_errors(table, name, folds), 'seatScores': rows}


def ols(x, y, extra=None):
    cols = [np.ones(len(x)), x] + ([] if extra is None else [extra])
    design_matrix = np.column_stack(cols)
    beta = np.linalg.lstsq(design_matrix, y, rcond=None)[0]
    return beta


def slope_interval(old, new, years, seed=55, draws=2000):
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(years == y) for y in sorted(set(years.tolist()))]
    values = []
    for _ in range(draws):
        picks = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        if np.var(old[picks]) > 0:
            values.append(ols(old[picks], new[picks])[1])
    return [float(v) for v in np.quantile(values, [0.05, 0.95])]


def descriptive(table):
    primary = select(table, 'primary')
    old = np.array([r['RoldFraction'] for r in primary]) * PP
    new = np.array([r['RnewFraction'] for r in primary]) * PP
    years = np.array([r['targetYear'] for r in primary])
    beta = ols(old, new)
    pooled = {'seats': len(primary), 'meanRoldPP': float(old.mean()), 'meanRnewPP': float(new.mean()),
              'a_PP': float(beta[0]), 'rho': float(beta[1]), 'rho90Interval': slope_interval(old, new, years),
              'correlation': float(np.corrcoef(old, new)[0, 1])}
    per_pair = {}
    for pair in sorted({(r['sourceYear'], r['targetYear']) for r in primary}):
        sel = [i for i, r in enumerate(primary) if (r['sourceYear'], r['targetYear']) == pair]
        b = ols(old[sel], new[sel]) if len(sel) > 2 and np.var(old[sel]) > 0 else [None, None]
        per_pair[f'{pair[0]}-{pair[1]}'] = {'seats': len(sel), 'meanRoldPP': float(old[sel].mean()),
                                            'meanRnewPP': float(new[sel].mean()),
                                            'rho': None if b[1] is None else float(b[1])}
    continuation = select(table, 'continuationReference')
    c_old = np.array([r['RoldFraction'] for r in continuation]) * PP
    c_new = np.array([r['RnewFraction'] for r in continuation]) * PP
    c_beta = ols(c_old, c_new)
    cont = {'seats': len(continuation), 'meanRoldPP': float(c_old.mean()), 'meanRnewPP': float(c_new.mean()),
            'a_PP': float(c_beta[0]), 'rho': float(c_beta[1]),
            'rho90Interval': slope_interval(c_old, c_new, np.array([r['targetYear'] for r in continuation]))}
    by_type = {}
    for r in table:
        if r['relation'] == 'candidate_change' and r['scope'] == 'general' and r['RoldFraction'] is not None \
                and r['RnewFraction'] is not None:
            by_type.setdefault(r['transitionType'], []).append(r)
    strata = {k: {'seats': len(v), 'meanRoldPP': float(np.mean([x['RoldFraction'] for x in v]) * PP),
                  'meanRnewPP': float(np.mean([x['RnewFraction'] for x in v]) * PP)} for k, v in sorted(by_type.items())}
    return {'primaryPooled': pooled, 'primaryPerPair': per_pair, 'continuationReferenceGeneral': cont,
            'generalChangesByTransitionType': strata}


def s_overlap(table, env=None):
    """Slope of R_new on R_old with and without the outgoing seat-party split (layer zS) as a control."""
    records = {}
    for rec in read(INVENTORY)['candidateRecords']:
        for i, cid in enumerate(rec['ids']):
            records[cid] = (rec, i)
    rows = []
    for r in select(table, 'primary'):
        if r['targetOccurrenceId'] in records:
            rec, i = records[r['targetOccurrenceId']]
            f = rec['features'][i]
            if f['supportedMass']['S'] > 0:
                rows.append((r['RoldFraction'] * PP, r['RnewFraction'] * PP, f['centered'][0] * PP))
    arr = np.array(rows)
    old, new, zs = arr[:, 0], arr[:, 1], arr[:, 2]
    without = ols(old, new)
    with_s = ols(old, new, zs)
    return {'seats': len(rows), 'targetYears': '2014-2023 layer seats with supported S and a replaced N/L candidate',
            'correlationRoldZs': float(np.corrcoef(old, zs)[0, 1]), 'rhoWithoutS': float(without[1]),
            'rhoWithS': float(with_s[1]), 'gammaS': float(with_s[2]),
            'reading': 'descriptive: a fall in rho once the outgoing seat-party split is controlled indicates the seat-level '
                       'persistence S already carries'}


def materiality(rows_primary):
    thetas = [r['thetaR'] for r in rows_primary]
    totals = [r['totalSd'] for r in rows_primary]
    return {'meanThetaR': float(np.mean(thetas)), 'balanceLocationShiftPer1ppR': float(np.mean(thetas) * 0.01),
            'medianTotalSd': float(np.median(totals)),
            'ratio': float(np.mean(thetas) * 0.01 / np.median(totals)),
            'reading': 'approximate log-ratio location change from a 1pp change in the incoming candidate R, against the '
                       'frozen balance total scale'}


def fold_means():
    mu = {}
    for rec in read(INVENTORY)['candidateRecords']:
        mu.setdefault(rec['targetYear'], set()).add(rec['trainingOnlyMeans']['R'])
    for year in FOLD_YEARS:
        if len(mu[year]) != 1:
            raise ValueError('Fold mean R is not constant within a target year')
    return {year: next(iter(mu[year])) for year in FOLD_YEARS}


def neutrality(table, name='primary'):
    """Questions 1 and 2: mean R_new minus the neutral centring mu_f on the scored target years."""
    mu = fold_means()
    rows = [r for r in select(table, name) if r['targetYear'] in FOLD_YEARS]
    gap = np.array([(r['RnewFraction'] - mu[r['targetYear']]) * PP for r in rows])
    years = np.array([r['targetYear'] for r in rows])
    rng = np.random.default_rng(55)
    groups = [np.flatnonzero(years == y) for y in FOLD_YEARS]
    draws = [gap[np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])].mean() for _ in range(2000)]
    low, high = np.quantile(draws, [0.05, 0.95])
    return {'sample': name, 'seats': len(rows), 'meanRnewMinusMuPP': float(gap.mean()),
            'bootstrap90IntervalPP': [float(low), float(high)], 'sdPP': float(gap.std(ddof=1)),
            'byTargetYear': {str(y): float(gap[years == y].mean()) for y in FOLD_YEARS},
            'reading': 'mu_f is the fold training mean of supported R that the layer uses as neutral; 0 on this scale means '
                       'neutral is right on average'}


def standardised_context(rows):
    """Not pre-registered context: mean squared standardised control residual, affected seats versus all layer seats."""
    env = environments()
    everything = [float(((e['v'][k] - location(np.array([e['p'][k]]), np.array([np.hypot(e['seat'], e['shared'])]))[0][0])
                         / np.hypot(e['seat'], e['shared'])) ** 2)
                  for y in FOLD_YEARS for e in [env[y]] for k in range(len(e['ids']))]
    affected = np.array([r['arms']['C']['z2'] for r in rows])
    years = np.array([r['year'] for r in rows])
    rng = np.random.default_rng(55)
    groups = [np.flatnonzero(years == y) for y in FOLD_YEARS]
    draws = [affected[np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])].mean() for _ in range(2000)]
    return {'allLayerSeats2017To2023': len(everything), 'meanSquaredStandardisedControlResidualAll': float(np.mean(everything)),
            'affectedSeats': len(rows), 'meanSquaredStandardisedControlResidualAffected': float(affected.mean()),
            'affectedBootstrap90Interval': [float(v) for v in np.quantile(draws, [0.05, 0.95])],
            'reading': 'descriptive context only (not a pre-registered decision quantity): compare with the affected-seat value '
                       'in scores.json to see whether replacement seats are unusually over- or under-dispersed'}
