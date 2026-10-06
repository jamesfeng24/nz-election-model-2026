"""Stage61 arithmetic: per-component seat ratios, shared checks, PIT coverage, stored-interval coverage, width mapping.

Everything is read from frozen Stage44 to Stage47 artifacts. Nothing is refit, rescaled or simulated.
"""
import numpy as np
from hashlib import sha256
from scipy.special import expit, logit, roots_hermitenorm
from scipy.stats import chi2, norm
from scripts.uncertainty_revision.coordinates import coordinates, partition
from scripts.uncertainty_revision.estimation import labels
from .common import ATTRIBUTION, EVALUATION, INVENTORY, SCALES, design, read

NODES, WEIGHTS = roots_hermitenorm(81)
WEIGHTS = WEIGHTS / np.sqrt(2 * np.pi)
LAYER_KEY = {'local_party': 'partyRecords', 'candidate': 'candidateRecords'}
SCALAR = ('balance', 'mass')
LEVELS = (0.5, 0.8, 0.9)
EDGES = np.array([0.05, 0.10, 0.25, 0.75, 0.90, 0.95])


def rng_for(*labels):
    seed = int.from_bytes(sha256('|'.join(map(str, (design()['statistics']['bootstrap']['seed'],) + labels)).encode()).digest()[:8], 'big')
    return np.random.default_rng(seed)


def location(p, sd):
    """Gaussian logistic location l with E[expit(l + sd Z)] = p (the operational conditional-mean location)."""
    p, sd = np.asarray(p, float), np.asarray(sd, float)
    loc = logit(p)
    for _ in range(100):
        q = expit(loc[:, None] + sd[:, None] * NODES[None, :])
        step = np.clip((q @ WEIGHTS - p) / ((q * (1 - q)) @ WEIGHTS), -1, 1)
        loc = loc - step
        if np.max(np.abs(step)) < 1e-15:
            break
    q = expit(loc[:, None] + sd[:, None] * NODES[None, :])
    if np.max(np.abs(q @ WEIGHTS - p)) > 1e-12:
        raise ValueError('Location did not converge')
    return loc


def fold(scales, layer, year):
    return next(f for f in scales['folds'][layer] if f['targetYear'] == year)


def scalar_frame(layer):
    """Per election: ids, location-adjusted and raw residuals for balance and mass; skipped records are counted."""
    inventory, scales = read(INVENTORY), read(SCALES)
    rows = inventory[LAYER_KEY[layer]]
    if any(r['scope'] != 'general' for r in rows):
        raise ValueError('Stage61 scores general electorates only')
    result, skipped = {}, {}
    for year in sorted({int(r['targetYear']) for r in rows}):
        f = fold(scales, layer, year)
        entry = {'status': f['status'], 'ids': {}, 'e': {}, 'eRaw': {}, 'sd': {}}
        for comp in SCALAR:
            ids, p, v, raw = [], [], [], []
            for row in (r for r in rows if int(r['targetYear']) == year):
                mean, actual, groups = np.array(row['mean']), np.array(row['actual']), row['groups']
                n, l, other = partition(groups)
                obs, mu = coordinates(actual, groups), coordinates(mean, groups)
                if comp == 'balance':
                    ok = bool(n and l) and obs['balance'] is not None and mu['balance'] is not None
                    prob = mean[n[0]] / (mean[n[0]] + mean[l[0]]) if ok else None
                else:
                    ok = bool((n or l) and other) and obs['mass'] is not None and mu['mass'] is not None
                    prob = mean[n + l].sum() if ok else None
                if not ok or not 0 < prob < 1:
                    skipped.setdefault((year, comp), []).append(row['targetElectorateId'])
                    continue
                ids.append(row['targetElectorateId']); p.append(prob); v.append(float(obs[comp])); raw.append(float(obs[comp] - mu[comp]))
            sd = f['scales'][comp]
            total = float(np.hypot(sd['shared'], sd['seat']))
            entry['ids'][comp] = ids
            entry['e'][comp] = np.array(v) - location(np.array(p), np.full(len(p), total))
            entry['eRaw'][comp] = np.array(raw)
            entry['sd'][comp] = {'shared': sd['shared'], 'seat': sd['seat'], 'total': total}
        result[year] = entry
    return result, {f'{y}.{c}': ids for (y, c), ids in skipped.items()}


def within_frame(layer):
    """Per election: per-seat Stage45 seat moment sum(left^2)/(K-1), left = e - (b - mean b), from the saved class effects.

    e is the raw within-remainder residual and b the saved full-panel class effects of that election, exactly the
    definition in scripts/uncertainty_revision/estimation.py (amendment A1 to the frozen design).
    """
    effects = {m['year']: m['moments']['within']['classEffects'] for m in read(SCALES)['descriptive'][layer]['moments']}
    result = {}
    for row in read(INVENTORY)[LAYER_KEY[layer]]:
        year = int(row['targetYear'])
        actual, mean = coordinates(np.array(row['actual']), row['groups']), coordinates(np.array(row['mean']), row['groups'])
        if actual['within'] is None:
            continue
        other = partition(row['groups'])[2]
        tags = [labels(row)[i] for i in other]
        e = actual['within'] - mean['within']
        b = np.array([effects[year][t] for t in tags])
        left = e - (b - b.mean())
        result.setdefault(year, []).append(float(np.sum(left * left) / (len(e) - 1)))
    return {y: np.array(v) for y, v in sorted(result.items())}


def pooled(values_by_year, years):
    return float(np.mean([values_by_year[y] for y in years]))


def seat_ratio(e, h_removed=True):
    return float(np.mean((e - e.mean()) ** 2))


def bootstrap_scale(frame, comp, years, boot, label):
    """Per-election point ratio and bootstrap draws of the seat ratio, pooled equal-election over `years`."""
    draws, point = {}, {}
    for y in frame:
        e = frame[y]['e'][comp]
        seat = frame[y]['sd'][comp]['seat']
        point[y] = seat_ratio(e) / seat ** 2
        idx = rng_for('scale', comp, y, label).integers(0, len(e), (boot['draws'], len(e)))
        s = e[idx]
        draws[y] = ((s - s.mean(axis=1, keepdims=True)) ** 2).mean(axis=1) / seat ** 2
    return point, draws


def interval(draws, level):
    lo, hi = np.percentile(draws, [50 * (1 - level), 50 * (1 + level)])
    return [float(lo), float(hi)]


def verdict_scale(R, ci, rules):
    if ci[1] < 1 and R <= 0.95:
        return 'conservative'
    if ci[0] > 1 and R >= 1.05:
        return 'too_tight'
    return 'calibrated'


def scale_block(point, draws, years, boot, rules):
    ratio = pooled(point, years)
    pooled_draws = np.mean([draws[y] for y in years], axis=0)
    r_draws = np.sqrt(pooled_draws)
    R = float(np.sqrt(ratio))
    ci = interval(r_draws, boot['level'])
    return {'pooledRatio': ratio, 'R': R, 'RInterval90': ci, 'verdict': verdict_scale(R, ci, rules),
            'perElectionRatio': {str(y): float(point[y]) for y in sorted(point)},
            'perElectionRatioInterval90': {str(y): interval(draws[y], boot['level']) for y in sorted(draws)},
            'postHocElectionHeterogeneity': {
                'note': 'post hoc, not part of the frozen verdict: how consistent the pooled R is across the estimated-fold elections',
                'electionsBelowOne': int(sum(point[y] < 1 for y in years)), 'electionsScored': len(years),
                'minRatio': float(min(point[y] for y in years)), 'maxRatio': float(max(point[y] for y in years)),
                'leaveOneElectionOutR': {str(y): float(np.sqrt(np.mean([point[k] for k in years if k != y]))) for y in years}}}


def pit_block(frame, comp, years, boot):
    """Total-law PIT: central coverage per election and pooled, bootstrap interval, ten-bin histogram."""
    out = {'perElection': {}, 'pooled': {}, 'histogram': {}}
    z = {y: frame[y]['e'][comp] / frame[y]['sd'][comp]['total'] for y in frame}
    cut = [norm.ppf((1 + c) / 2) for c in LEVELS]
    cover = {y: np.array([np.abs(z[y]) <= q for q in cut], float) for y in frame}
    draws = {}
    for y in frame:
        idx = rng_for('pit', comp, y).integers(0, len(z[y]), (boot['draws'], len(z[y])))
        draws[y] = np.stack([cover[y][k][idx].mean(axis=1) for k in range(3)])
        out['perElection'][str(y)] = {'seats': int(len(z[y])), 'status': frame[y]['status'],
                                       'coverage': {str(c): float(cover[y][k].mean()) for k, c in enumerate(LEVELS)}}
    for name, ys in (('estimatedFolds', years), ('allFolds', sorted(frame))):
        stack = np.mean([draws[y] for y in ys], axis=0)
        out['pooled'][name] = {str(c): {'coverage': float(np.mean([cover[y][k].mean() for y in ys])),
                                         'interval90': interval(stack[k], boot['level'])} for k, c in enumerate(LEVELS)}
        u = norm.cdf(np.concatenate([z[y] for y in ys]))
        counts = np.histogram(u, bins=10, range=(0, 1))[0]
        expected = len(u) / 10
        stat = float(((counts - expected) ** 2 / expected).sum())
        out['histogram'][name] = {'counts': counts.tolist(), 'chiSquare9': stat, 'approximatePValueIgnoringSharedEffect': float(chi2.sf(stat, 9))}
    return out


def shared_block(frame, comp, years):
    """h_Y^2 / (shared^2 + seat^2 / n) per election against the chi-square(E)/E reference band."""
    stat, signed = {}, {}
    for y in frame:
        e, sd = frame[y]['e'][comp], frame[y]['sd'][comp]
        stat[y] = float(e.mean() ** 2 / (sd['shared'] ** 2 + sd['seat'] ** 2 / len(e)))
        signed[y] = float(e.mean() / np.sqrt(sd['shared'] ** 2 + sd['seat'] ** 2 / len(e)))
    count = len(years)
    band = [float(chi2.ppf(q, count) / count) for q in (0.05, 0.95)]
    value = float(np.mean([stat[y] for y in years]))
    return {'perElectionStatistic': {str(y): stat[y] for y in sorted(stat)}, 'perElectionStandardisedEffect': {str(y): signed[y] for y in sorted(signed)},
            'pooledStatistic': value, 'referenceBand90': band, 'elections': count,
            'verdict': 'within_band' if band[0] <= value <= band[1] else 'outside_band'}


def descriptive_moments(layer, comp):
    return {m['year']: m['moments'][comp] for m in read(SCALES)['descriptive'][layer]['moments']}


def within_scale(layer, years, boot, rules):
    scales = read(SCALES)
    seats = within_frame(layer)
    point, draws = {}, {}
    for y, s in seats.items():
        sd = fold(scales, layer, y)['scales']['within']['seat']
        point[y] = float(np.nanmean(s)) / sd ** 2
        values = s[~np.isnan(s)]
        idx = rng_for('within', layer, y).integers(0, len(values), (boot['draws'], len(values)))
        draws[y] = values[idx].mean(axis=1) / sd ** 2
    block = scale_block(point, draws, years, boot, rules)
    moments = descriptive_moments(layer, 'within')
    block['stage45DescriptiveSeatMomentRatio'] = {str(y): float(moments[y]['seat'] / fold(scales, layer, y)['scales']['within']['seat'] ** 2) for y in sorted(point)}
    shared = {y: float(moments[y]['shared'] / fold(scales, layer, y)['scales']['within']['shared'] ** 2) for y in sorted(point)}
    block['stage45DescriptiveSharedMomentRatio'] = {str(y): v for y, v in shared.items()}
    block['sharedPooledRatioEstimatedFolds'] = float(np.mean([shared[y] for y in years]))
    return block


def moment_crosscheck(layer, frame):
    """Raw-basis seat/shared moments equal the saved Stage45 descriptive moments: a data-handling check."""
    out = {}
    for comp in SCALAR:
        moments = descriptive_moments(layer, comp)
        worst = 0.
        for y in frame:
            raw = frame[y]['eRaw'][comp]
            seat, shared = float(np.mean((raw - raw.mean()) ** 2)), float(raw.mean() ** 2)
            worst = max(worst, abs(seat - moments[y]['seat']) / moments[y]['seat'],
                        abs(shared - moments[y]['shared']) / max(moments[y]['shared'], 1e-12) if moments[y]['shared'] > 1e-6 else 0.)
        out[comp] = float(worst)
    return out


def layer_scale_audit(layer):
    contract = design()
    boot, rules = contract['statistics']['bootstrap'], contract['verdictRules']
    estimated = contract['scope']['estimatedFoldYears'][layer]
    frame, skipped = scalar_frame(layer)
    result = {'skippedRecords': skipped, 'momentCrosscheckMaxRelativeDifference': moment_crosscheck(layer, frame), 'components': {}}
    for comp in SCALAR:
        point, draws = bootstrap_scale(frame, comp, estimated, boot, layer)
        block = scale_block(point, draws, estimated, boot, rules)
        all_years = sorted(point)
        block['allFoldsPooledRatio'] = pooled(point, all_years)
        raw = {y: float(np.mean((frame[y]['eRaw'][comp] - frame[y]['eRaw'][comp].mean()) ** 2) / frame[y]['sd'][comp]['seat'] ** 2) for y in frame}
        block['rawBasisPooledRatioEstimatedFolds'] = pooled(raw, estimated)
        block['seatsPerElection'] = {str(y): len(frame[y]['e'][comp]) for y in sorted(frame)}
        block['scales'] = {str(y): frame[y]['sd'][comp] for y in sorted(frame)}
        block['pit'] = pit_block(frame, comp, estimated, boot)
        block['shared'] = shared_block(frame, comp, estimated)
        pit_c50 = block['pit']['pooled']['estimatedFolds']['0.5']['interval90']
        block['shapeFlag'] = ('centre_too_wide' if pit_c50[0] > 0.5 else 'centre_too_narrow' if pit_c50[1] < 0.5 else 'none')
        result['components'][comp] = block
    result['components']['within'] = within_scale(layer, estimated, boot, rules)
    result['components']['within']['shapeFlag'] = 'not_assessed_vector_component'
    return result


def stored_coverage(boot):
    """Stored Stage47 interval coverage by case and option group, with seat (contest) bootstrap and seven-bin PIT."""
    cases = read(EVALUATION)['cases']
    out = {}
    for case in cases:
        layer, year = case['layer'], int(case['year'])
        groups = {}
        for rec in case['methods']['corrected']['records']:
            actual = np.array(rec['actual']) * 100
            iv = {c: rec['interval' + c] for c in ('50', '80', '90')}
            lo, hi = [np.array(iv[c]['lower']) for c in ('90', '80', '50')], [np.array(iv[c]['upper']) for c in ('50', '80', '90')]
            bins = np.zeros(len(actual), int)
            bins += actual >= lo[0]; bins += actual >= lo[1]; bins += actual >= lo[2]
            bins += actual > hi[0]; bins += actual > hi[1]; bins += actual > hi[2]
            degenerate = (hi[2] - lo[0]) < 1e-12
            for j, g in enumerate(rec['groups']):
                key = g if g in ('national', 'labour') else 'other'
                entry = groups.setdefault(key, {'contest': [], 'cov': [], 'bin': [], 'degenerate': 0})
                if degenerate[j]:
                    entry['degenerate'] += 1
                    continue
                entry['contest'].append(rec['id'])
                entry['cov'].append([bool(iv[c]['covered'][j]) for c in ('50', '80', '90')])
                entry['bin'].append(int(bins[j]))
        out[(layer, year)] = groups
    return out


def stored_block(boot, estimated_by_layer):
    stored = stored_coverage(boot)
    result = {}
    for layer in ('local_party', 'candidate', 'composed'):
        years = sorted(y for (l, y) in stored if l == layer)
        est = [y for y in years if y in estimated_by_layer[layer]]
        for group in ('national', 'labour', 'other'):
            per, draws = {}, {}
            for y in years:
                e = stored[(layer, y)][group]
                contests = sorted(set(e['contest']))
                pos = {c: i for i, c in enumerate(contests)}
                cov = np.array(e['cov'], float)
                sums = np.zeros((len(contests), 3)); counts = np.zeros(len(contests))
                for c, row in zip(e['contest'], cov):
                    sums[pos[c]] += row; counts[pos[c]] += 1
                idx = rng_for('stored', layer, group, y).integers(0, len(contests), (boot['draws'], len(contests)))
                draws[y] = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)[:, None]
                per[y] = {'contests': len(contests), 'options': int(len(e['cov'])), 'degenerateIntervalsExcluded': e['degenerate'],
                          'coverage': {str(c): float(cov[:, k].mean()) for k, c in enumerate(LEVELS)},
                          'coverageInterval90': {str(c): interval(draws[y][:, k], boot['level']) for k, c in enumerate(LEVELS)}}
            pools = {}
            for name, ys in (('estimatedFolds', est), ('allYears', years)):
                stack = np.mean([draws[y] for y in ys], axis=0)
                bins = np.concatenate([np.array(stored[(layer, y)][group]['bin']) for y in ys])
                counts = np.bincount(bins, minlength=7)
                expected = np.array([.05, .05, .15, .5, .15, .05, .05]) * len(bins)
                stat = float(((counts - expected) ** 2 / expected).sum())
                ci80 = interval(stack[:, 1], boot['level'])
                pools[name] = {'years': ys, 'coverage': {str(c): float(np.mean([per[y]['coverage'][str(c)] for y in ys])) for c in LEVELS},
                               'coverageInterval90': {str(c): interval(stack[:, k], boot['level']) for k, c in enumerate(LEVELS)},
                               'verdict80': 'over_covers' if ci80[0] > 0.8 else 'under_covers' if ci80[1] < 0.8 else 'consistent',
                               'pitBins': counts.tolist(), 'expectedPitBins': expected.tolist(), 'chiSquare6': stat,
                               'approximatePValueIgnoringSharedEffect': float(chi2.sf(stat, 6))}
            result[f'{layer}.{group}'] = {'perElection': {str(y): per[y] for y in years}, 'pooled': pools}
    return result


def ablation_widths():
    records = read(ATTRIBUTION)['records']
    policies = sorted(records[0]['policies'])
    widths = {p: float(np.mean([r['policies'][p]['widths']['national']['intervals']['90']['seatMeanWidthDistribution']['quantilesPP']['50']
                                for r in records])) for p in policies}
    return widths


def width_at(full, without, m):
    return float(np.sqrt(full ** 2 - (1 - m ** 2) * (full ** 2 - without ** 2)))


def narrowing(scale_results, shared_stats):
    contract = design()
    widths, mapping = ablation_widths(), contract['narrowingTarget']['ablationMap']
    full = widths['full']
    rows = {}
    for key, policy in mapping.items():
        layer, part = key.split('.')
        without = widths[policy]
        if part == 'shared':
            comps = {c: shared_stats[layer][c] for c in SCALAR}
            entries = {'multiplier': float(np.sqrt(np.mean(list(comps.values())))), 'rankable': False,
                       'reason': 'shared part rests on four or five election replications and is never ranked'}
            m_point = entries['multiplier'] if entries['multiplier'] < 1 else 1.0
            entries['widthAtPoint'] = width_at(full, without, m_point)
            entries['cutPercentAtPoint'] = 100 * (1 - entries['widthAtPoint'] / full)
            rows[key] = entries
            continue
        if key == 'local_party.seat':
            comps = scale_results['local_party']['components']
            rs = [comps[c]['R'] for c in ('balance', 'mass', 'within')]
            uppers = [comps[c]['RInterval90'][1] for c in ('balance', 'mass', 'within')]
            all_conservative = all(comps[c]['verdict'] == 'conservative' for c in ('balance', 'mass', 'within'))
            lo, hi = min(rs), max(rs)
            rows[key] = {'bracketR': [lo, hi], 'rankable': all_conservative,
                         'widthAtLowestR': width_at(full, without, min(lo, 1.)), 'widthAtHighestR': width_at(full, without, min(hi, 1.)),
                         'cutPercentRange': [100 * (1 - width_at(full, without, min(lo, 1.)) / full), 100 * (1 - width_at(full, without, min(hi, 1.)) / full)],
                         'cutPercentAtPoint': 100 * (1 - width_at(full, without, min(hi, 1.)) / full),
                         'cutPercentAtIntervalUpper': 100 * (1 - width_at(full, without, min(max(uppers), 1.)) / full),
                         'reason': 'three local coordinates share one ablation policy; the point cut uses the highest R'}
            continue
        comp = key.split('.')[1]
        block = scale_results[layer]['components'][comp]
        m_point, m_upper = min(block['R'], 1.), min(block['RInterval90'][1], 1.)
        rows[key] = {'R': block['R'], 'RInterval90': block['RInterval90'], 'verdict': block['verdict'], 'rankable': block['verdict'] == 'conservative',
                     'widthAtPoint': width_at(full, without, m_point), 'widthAtIntervalUpper': width_at(full, without, m_upper),
                     'cutPercentAtPoint': 100 * (1 - width_at(full, without, m_point) / full),
                     'cutPercentAtIntervalUpper': 100 * (1 - width_at(full, without, m_upper) / full)}
    ranked = sorted((k for k, v in rows.items() if v['rankable']), key=lambda k: -rows[k]['cutPercentAtPoint'])
    return {'ablationMeanWidthsNationalComposed90PP': widths, 'rows': rows, 'rankingAll': ranked,
            'rankingExcludingCandidateBalance': [k for k in ranked if k != 'candidate.balance'],
            'arithmetic': contract['narrowingTarget']['arithmetic'],
            'caveat': 'nine-seat ablation; widths are not additive variance shares; indicative only'}
