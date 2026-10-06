"""Apply the frozen Stage60 decision rule; rule, margins and thresholds live in design-contract.json."""
import math
import numpy as np
from .common import PREFIX, YEARS, SCALES, ATTRIBUTION, STAGE48_FIT, STAGE48_EVALUATION, read, save, verify, arguments, design, arms
from .summary import by_population
from scripts.uncertainty.construction import scale_for

DECISION_YEARS = (2017, 2020, 2023)


def compare(summary, x, y, rule, records):
    """Stage48 IMPROVES quantities for arm x against arm y on the decision seats."""
    pop = summary['decisionSeats']
    levels = rule['intervalScoreLevels']
    delta_crps = pop[x]['majorCRPSPP'] - pop[y]['majorCRPSPP']
    delta_is = float(np.mean([pop[x]['majorIntervals'][str(l)]['intervalScorePP'] - pop[y]['majorIntervals'][str(l)]['intervalScorePP'] for l in levels]))
    guard = {str(l): {'coverageArm': pop[x]['majorIntervals'][str(l)]['coverage'], 'coverageControl': pop[y]['majorIntervals'][str(l)]['coverage'],
                      'passed': abs(pop[x]['majorIntervals'][str(l)]['coverage'] - l / 100)
                                <= abs(pop[y]['majorIntervals'][str(l)]['coverage'] - l / 100) + rule['coverageGuardAbsolute']} for l in levels}
    folds = {str(e): summary[str(e)][x]['majorCRPSPP'] - summary[str(e)][y]['majorCRPSPP'] for e in DECISION_YEARS}
    chosen = [i for i, r in enumerate(records[x]) if r['year'] != 2014]
    prefix = float(np.mean([records[x][i]['majorCRPSPrefix'] - records[y][i]['majorCRPSPrefix'] for i in chosen]))
    return {'deltaMajorCRPSPP': float(delta_crps), 'relativeDeltaMajorCRPS': float(delta_crps / pop[y]['majorCRPSPP']),
            'deltaMajorIntervalScorePP': delta_is, 'coverageGuard': guard,
            'deltaEnergyPP': float(pop[x]['energyPP'] - pop[y]['energyPP']), 'foldDeltaMajorCRPSPP': folds,
            'foldsNegative': int(sum(v < 0 for v in folds.values())),
            'resolution': {'prefixDraws': rule['resolutionPrefixDraws'], 'deltaAtPrefixPP': prefix, 'differencePP': abs(prefix - delta_crps),
                           'passed': abs(prefix - delta_crps) <= rule['resolutionTolerancePP']}}


def classify(c, rule, doubling_passed):
    material = rule['crpsMaterialityPP']
    resolved = c['resolution']['passed'] and doubling_passed
    if (resolved and c['deltaMajorCRPSPP'] <= -material and c['deltaMajorIntervalScorePP'] <= 0
            and all(g['passed'] for g in c['coverageGuard'].values()) and c['deltaEnergyPP'] <= rule['energyGuardPP']
            and c['foldsNegative'] >= rule['minimumFoldsNegative']):
        return 'IMPROVES'
    if resolved and c['deltaMajorCRPSPP'] >= material:
        return 'WORSE'
    if resolved and abs(c['deltaMajorCRPSPP']) < material:
        return 'NEGLIGIBLE'
    return 'MIXED'


def coverage_floor(summary, arm, floor):
    """Per election and level the arm's pooled N/L coverage against min(nominal - margin, control - alreadyUndercovering)."""
    rows, passed = {}, True
    for e in floor['elections']:
        for l in floor['levels']:
            nominal = l / 100
            control = summary[str(e)]['control']['majorIntervals'][str(l)]['coverage']
            value = summary[str(e)][arm]['majorIntervals'][str(l)]['coverage']
            threshold = min(nominal - floor['nominalMargin'], control - floor['alreadyUndercoveringMargin'])
            ok = bool(value >= threshold - 1e-12)
            passed = passed and ok
            rows[f'{e}:{l}'] = {'coverage': value, 'controlCoverage': control, 'threshold': threshold, 'passed': ok}
    return {'passed': passed, 'rows': rows}


def seat_deltas(records, arm, other):
    return np.array([np.mean(a['crpsPP']) - np.mean(b['crpsPP']) for a, b in zip(records[arm], records[other]) if a['year'] != 2014])


def bootstrap_indices(records, spec):
    """One shared index set for every comparison: seats resampled within election."""
    rng = np.random.default_rng(spec['seed'])
    sizes = [sum(1 for r in records['control'] if r['year'] == y) for y in DECISION_YEARS]
    return [rng.integers(0, n, (spec['draws'], n)) for n in sizes], sizes


def bootstrap_interval(delta, indices, sizes, spec):
    start, means = 0, []
    parts = []
    for idx, n in zip(indices, sizes):
        parts.append(delta[start:start + n][idx])
        start += n
    pooled = np.concatenate(parts, axis=1).mean(axis=1)
    lo = (1 - spec['level']) / 2
    return [float(np.quantile(pooled, lo)), float(np.quantile(pooled, 1 - lo))]


def ablation_widths():
    """National and Labour full-90 widths per Stage47 ablation seat under full and no_candidate_balance policies."""
    out = []
    for r in read(ATTRIBUTION)['records']:
        out.append({'id': r['id'], 'year': r['year'],
                    **{label: {p: r['policies'][p]['widths'][label]['intervals']['90']['widthPP'] for p in ('full', 'no_candidate_balance')}
                       for label in ('national', 'labour')}})
    return out


def width_at(entry, label, multiplier, share):
    """Approximate composed full-90 width when the balance variance is scaled (see the design's composed-width arithmetic)."""
    full, rest = entry[label]['full'], entry[label]['no_candidate_balance']
    g = share * multiplier ** 2 + (1 - share)
    return math.sqrt(rest ** 2 + (full ** 2 - rest ** 2) * g)


def composed_implication(fits, arm_names):
    scales, entries = read(SCALES), ablation_widths()
    rows = {}
    for arm in arm_names:
        rows[arm] = {}
        for form in ('seatOnly', 'allBalance'):
            for label in ('national', 'labour'):
                widths = []
                for e in entries:
                    balance = scale_for(scales, 'candidate', e['year'])['scales']['balance']
                    share = balance['seat'] ** 2 / (balance['seat'] ** 2 + balance['shared'] ** 2) if form == 'seatOnly' else 1.0
                    multiplier = (fits['descriptive2026Refit']['fit']['multiplier'] if arm == 'free2026Refit'
                                  else fits['folds'][str(e['year'])]['multipliers'][arm])
                    widths.append(width_at(e, label, multiplier, share))
                rows[arm][f'{form}:{label}'] = float(np.mean(widths))
    base = {k: v for k, v in rows['control'].items()}
    for arm in arm_names:
        rows[arm] = {k: {'widthPP': v, 'changeRelativeToControl': v / base[k] - 1} for k, v in rows[arm].items()}
    return rows


def sanity_check(fits):
    """Same arithmetic with Stage48's penalised multipliers against Stage48's composed K-versus-control National width change."""
    stage48 = read(STAGE48_EVALUATION)['composed']['summary']['fittedFolds']
    control = stage48['control']['national']['intervals']['90']['widthPP']
    penalised = stage48['constant']['national']['intervals']['90']['widthPP']
    predicted = composed_implication(fits, ['control', 'penalised'])
    return {'stage48ComposedNationalFull90': {'control': control, 'constant': penalised, 'change': penalised / control - 1},
            'arithmeticSeatOnlyChange': predicted['penalised']['seatOnly:national']['changeRelativeToControl'],
            'arithmeticAllBalanceChange': predicted['penalised']['allBalance:national']['changeRelativeToControl'],
            'status': 'sanity check only: composed bank has 512 draws and unmet precision gates; arithmetic uses nine ablation seats'}


def choose(qualifying, decision_summary, rule, order, interval):
    """Best qualifier, within-noise set and the least aggressive within noise; `interval(a, best)` is the bootstrap interval of a minus best."""
    selection = {'qualifying': list(qualifying), 'best': None, 'withinNoise': {}, 'recommended': None, 'descriptiveAlternative': None}
    if not qualifying:
        return selection
    major = lambda a: decision_summary[a]['majorCRPSPP']
    aggressiveness = lambda a: decision_summary[a]['meanMultiplier']
    best = min(qualifying, key=lambda a: (major(a), order.index(a)))
    selection['best'] = best
    for a in qualifying:
        bounds = [0., 0.] if a == best else interval(a, best)
        selection['withinNoise'][a] = {'intervalOfArmMinusBest': bounds, 'withinNoise': bool(bounds[0] <= 0.)}
    near = [a for a in qualifying if selection['withinNoise'][a]['withinNoise']]
    selection['recommended'] = max(near, key=lambda a: (aggressiveness(a), -order.index(a)))
    close = [a for a in qualifying if major(a) - major(best) <= rule['improves']['crpsMaterialityPP']]
    selection['descriptiveAlternative'] = max(close, key=lambda a: (aggressiveness(a), -order.index(a)))
    return selection


def build():
    spec = design()
    rule = spec['decision']
    evaluation = read(PREFIX + '/evaluation.json')
    fits = read(PREFIX + '/fit.json')
    records = evaluation['records']
    summary = by_population(records)
    order = arms()
    candidate_arms = spec['candidateArms']
    doubling = evaluation['representativeDoubling']
    doubling_passed = {a: all(x['allPassed'] for x in doubling[a]) for a in order}
    comparisons, floors, classes = {}, {}, {}
    for a in order[1:]:
        c = compare(summary, a, 'control', rule['improves'], records)
        c['classification'] = classify(c, rule['improves'], doubling_passed[a])
        comparisons[a], classes[a] = c, c['classification']
        floors[a] = coverage_floor(summary, a, rule['coverageFloor'])
    qualifying = [a for a in candidate_arms if classes[a] == 'IMPROVES' and floors[a]['passed']]
    improving = [a for a in candidate_arms if classes[a] == 'IMPROVES']
    indices, sizes = bootstrap_indices(records, rule['selection']['bootstrap'])
    selection = choose(qualifying, summary['decisionSeats'], rule, order,
                       lambda a, b: bootstrap_interval(seat_deltas(records, a, b), indices, sizes, rule['selection']['bootstrap']))
    if qualifying:
        finding = f'recommend_{selection["recommended"]}_for_james_signoff'
    elif improving:
        finding = 'floor_blocked_report_to_james'
    else:
        finding = 'no_arm_qualifies_keep_corrected_control'
    free_2026 = fits['descriptive2026Refit']['fit']['multiplier']
    all_arms = [a for a in order]
    result = {'stage': 60, 'rule': rule, 'finding': finding, 'operationalAdoption': None, 'classification': classes,
              'doublingGatesPassed': doubling_passed, 'comparisons': comparisons, 'coverageFloor': floors, 'selection': selection,
              'recommendedArmIsLeaveFutureOut': None if selection['recommended'] is None else selection['recommended'] == 'free',
              'free2026RefitMultiplier': free_2026, 'summary': summary,
              'composedWidthImplication': composed_implication(fits, [*all_arms, 'free2026Refit']), 'composedWidthSanityCheck': sanity_check(fits),
              'allSeatsDeltaMajorCRPSPP': {a: summary['allSeats'][a]['majorCRPSPP'] - summary['allSeats']['control']['majorCRPSPP'] for a in order[1:]},
              'numerical': {'doublingAllPassed': doubling_passed, 'maximumDrawGapAcrossArms': evaluation['maximumDrawGapAcrossArms'],
                            'maximumFiniteMeanDeviationPP': evaluation['maximumFiniteMeanDeviationPP'],
                            'doublingLastChangesPP': {a: doubling[a][-1]['changesPP'] for a in order}}}
    return result


def main():
    args = arguments()
    verify()
    save('decision.json', build(), args.check)
    print('Stage60 frozen decision rule applied' if not args.check else 'Stage60 decision reproduced')


if __name__ == '__main__':
    main()
