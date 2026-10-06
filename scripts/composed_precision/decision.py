"""Apply the frozen precision rules to the stored blocks; the rules and thresholds live in design-contract.json."""
import math
import numpy as np
from scipy.stats import t as student
from scripts.balance_scale.evaluation import doubling
from .common import PREFIX, RESTRICTIONS, YEARS, read, save, verify, arguments, design

# frozen quantity -> (field of the control record, key in the ladder/chain metrics)
QUANTITIES = {'mean': ('meanPP', 'meansPP'), 'rbMean': ('rbMeanPP', None), 'crps': ('crpsPP', 'crps'), 'energy': ('energyPP', 'energy'),
              'width50': ('width50', 'width50'), 'width80': ('width80', 'width80'), 'width90': ('width90', 'width90')}
COMPARISONS = {'constant_vs_control': ('constant', 'control'), 'conditional_vs_constant': ('conditional', 'constant'),
               'conditional_vs_control': ('conditional', 'control')}


def blocks_of(seat, shared, total):
    """Control records of blocks 0..total-1 (the shared all-seat blocks, then the representative-only blocks)."""
    out = [seat['blocks'][str(b)]['control'] for b in range(shared)]
    out += [seat['representativeBlocks'][str(b)] for b in range(shared, total)] if 'representativeBlocks' in seat else []
    return out


def spread(values):
    """Sample sd (ddof 1) across blocks, per column."""
    return np.std(np.atleast_2d(np.asarray(values, float).reshape(len(values), -1)), axis=0, ddof=1)


def summary(x):
    x = np.asarray(x, float)
    return {'max': float(x.max()), 'median': float(np.median(x)), 'count': int(x.size)}


def cap_for(gates, name):
    return gates['mean'] if name == 'rbMean' else gates[name]


def next_power_of_two(x, minimum):
    return int(max(minimum, 2 ** math.ceil(math.log2(max(x, 1.)))))


def mcse(ev, spec):
    """s512 across blocks for every quantity, representatives (8 blocks) and all seats (4 blocks)."""
    shared, total = spec['blocks']['allSeats'], spec['blocks']['representatives']
    result = {}
    for name, (field, _) in QUANTITIES.items():
        reps, every = [], []
        for seat in ev['seats'].values():
            series = blocks_of(seat, shared, shared)
            every.append(spread([b[field] for b in series]))
            if 'representativeBlocks' in seat:
                reps.append(spread([b[field] for b in blocks_of(seat, shared, total)]))
        result[name] = {'representatives': {'blocks': total, **summary(np.concatenate(reps))},
                        'allSeats': {'blocks': shared, **summary(np.concatenate(every))}}
    return result


def requirement(stats, spec):
    rule, gates = spec['requirement'], spec['gatesPP']
    base = spec['blockDraws']
    out = {}
    for name in rule['quantities']:
        s, cap = stats[name]['representatives']['max'], cap_for(gates, name)
        raw = base * (rule['sigmaMultiple'] * s / cap) ** 2
        out[name] = {'capPP': cap, 'maxS512PP': s, 'requiredDraws': next_power_of_two(raw, base) if rule['powerOfTwo'] else raw,
                     'unroundedDraws': float(raw), 'ratioAt4096': float(rule['sigmaMultiple'] * s * math.sqrt(base / 4096) / cap),
                     'seatDrawsFor71Seats': int(next_power_of_two(raw, base) * 71),
                     'statisticAlternativeToStage47Gate': name == 'rbMean'}
    return out


def gate(ev, spec):
    entries = [{'control': r['ladder']} for r in ev['representatives'].values()]
    rounds = doubling(entries, spec['ladder'], spec['gatesPP'], ('control',))['control']
    last = rounds[-1]
    return {'rounds': rounds, 'lastDoubling': {'earlier': last['earlier'], 'later': last['later']},
            'lastDoublingRatioToCap': {k: v / spec['gatesPP'][k] for k, v in last['changesPP'].items()},
            'verdict': 'CAPS_MET_AT_CACHED_BANK' if last['allPassed'] else 'CAPS_NOT_ATTAINABLE_WITHIN_CACHED_BANK'}


def scaling(ev, spec, gate_result, stats):
    """Observed last-doubling change over the i.i.d. prediction s512 / sqrt(pool / block); diagnostic only."""
    factor = math.sqrt(spec['blockDraws'] / spec['ladder'][-1])
    mapping = {'mean': 'mean', 'crps': 'crps', 'energy': 'energy', 'width50': 'width50', 'width80': 'width80', 'width90': 'width90'}
    last = gate_result['rounds'][-1]['changesPP']
    return {k: float(last[k] / (stats[k]['representatives']['max'] * factor)) for k in mapping}


def layer_share(ev, spec):
    """Variance share of layer-only scrambles of national block 0 relative to the block-to-block variance."""
    shared, total = spec['blocks']['allSeats'], spec['blocks']['representatives']
    result = {}
    for name, (field, _) in QUANTITIES.items():
        layer, whole = [], []
        for seat in ev['seats'].values():
            if 'layerOnly' not in seat:
                continue
            first = seat['blocks']['0']['control']
            scrambles = [first] + [seat['layerOnly'][str(s)] for s in spec['layerOnly']['scrambleIndices']]
            layer.append(spread([b[field] for b in scrambles]) ** 2)
            whole.append(spread([b[field] for b in blocks_of(seat, shared, total)]) ** 2)
        layer, whole = np.concatenate(layer), np.concatenate(whole)
        keep = whole > 0
        ratio = np.clip(layer[keep] / whole[keep], 0, 1)
        result[name] = {'pooledLayerShareOfVariance': float(min(1., layer.sum() / whole.sum())),
                        'medianLayerShare': float(np.median(ratio)), 'maxLayerShare': float(ratio.max())}
    return result


def chain_split(ev, spec):
    """Multi-chain bound on the 4,096 estimate relative to the cached chains (reportedOnly)."""
    gates = spec['gatesPP']
    result = {}
    for name, (field, key) in QUANTITIES.items():
        if key is None:
            continue
        bounds = []
        for seat in ev['representatives'].values():
            series = [seat['chains'][str(c)][key] for c in range(1, spec['chainSplit']['chains'] + 1)]
            bounds.append(spread(series) / math.sqrt(spec['chainSplit']['chains']))
        bounds = np.concatenate(bounds)
        cap = gates[name]
        result[name] = {'maxBoundPP': float(bounds.max()), 'medianBoundPP': float(np.median(bounds)),
                        'threeBoundOverCap': float(3 * bounds.max() / cap)}
    return result


def pooled_deltas(seats, x, y, block, years=None):
    sel = [s for s in seats.values() if years is None or s['year'] in years]
    crps = np.mean([s['blocks'][block][x]['majorCRPSPP'] - s['blocks'][block][y]['majorCRPSPP'] for s in sel])
    score = np.mean([np.mean(np.array(s['blocks'][block][x]['intervalScorePP']) - np.array(s['blocks'][block][y]['intervalScorePP'])) for s in sel])
    energy = np.mean([s['blocks'][block][x]['energyPP'] - s['blocks'][block][y]['energyPP'] for s in sel])
    return float(crps), float(score), float(energy)


def state(interval, materiality):
    low, high = interval
    if high <= -materiality or low >= materiality:
        return 'SETTLED_MATERIAL'
    if high < 0 or low > 0:
        return 'SETTLED_SIGN'
    return 'UNRESOLVED'


def estimate(values, spec):
    values = np.asarray(values, float)
    n = len(values)
    mean, sd = float(values.mean()), float(values.std(ddof=1))
    half = float(student.ppf(0.5 + spec['settled']['confidence'] / 2, n - 1) * sd / math.sqrt(n))
    interval = (mean - half, mean + half)
    return {'blockValues': [float(v) for v in values], 'mean': mean, 'sdAcrossBlocks': sd, 'standardError': sd / math.sqrt(n),
            'interval95': [interval[0], interval[1]], 'state': state(interval, spec['settled']['materialityCRPSPP']),
            'stage48BlockZeroValue': float(values[0]),
            'blockZeroZScore': float((values[0] - mean) / sd) if sd > 0 else None}


def settled(ev, spec):
    blocks = [str(b) for b in range(spec['blocks']['allSeats'])]
    out = {}
    for name, (x, y) in COMPARISONS.items():
        entry = {}
        per_block = [pooled_deltas(ev['seats'], x, y, b) for b in blocks]
        for i, quantity in enumerate(('deltaMajorCRPSPP', 'deltaMajorIntervalScorePP', 'deltaEnergyPP')):
            entry[quantity] = estimate([v[i] for v in per_block], spec)
        entry['byElection'] = {str(year): estimate([pooled_deltas(ev['seats'], x, y, b, (year,))[0] for b in blocks], spec) for year in YEARS}
        entry['decidingComparison'] = name in spec['settled']['comparisons']
        out[name] = entry
    return out


def win_probability(ev, spec):
    blocks = [str(b) for b in range(spec['blocks']['allSeats'])]
    low, high = spec['winProbability']['inclusionRange']
    numerator = denominator = 0.
    own, mean_p = [], []
    for seat in ev['seats'].values():
        series = np.array([seat['blocks'][b]['control']['win'] for b in blocks])
        p, s = series.mean(axis=0), spread(series)
        own.append(s)
        keep = (p >= low) & (p <= high)
        numerator += float(np.sum(spec['blockDraws'] * s[keep] ** 2))
        denominator += float(np.sum(p[keep] * (1 - p[keep])))
        mean_p.append(p)
    design_effect = numerator / denominator
    own = np.concatenate(own)
    rows = {}
    for target in spec['winProbability']['targetStandardErrors']:
        need = design_effect * 0.25 / target ** 2
        rows[str(target)] = {'drawsForStandardErrorAtHalf': float(need), 'powerOfTwoDraws': next_power_of_two(need, spec['blockDraws'])}
    standard_error = lambda n: float(math.sqrt(design_effect * 0.25 / n))
    result = {'designEffect': design_effect, 'includedCandidateProbabilities': int(sum(((p >= low) & (p <= high)).sum() for p in mean_p)),
              'perSeatS512': summary(own), 'standardErrorAtHalf': {str(n): standard_error(n) for n in (512, 2048, 4096)},
              'requiredDraws': rows, 'differences': {}}
    for name in ('constant_vs_control', 'conditional_vs_constant'):
        x, y = COMPARISONS[name]
        mean_diff, se_diff = [], []
        for seat in ev['seats'].values():
            d = np.array([seat['blocks'][b][x]['majorWin'][0] - seat['blocks'][b][y]['majorWin'][0] for b in blocks])
            mean_diff.append(d.mean())
            se_diff.append(d.std(ddof=1) / math.sqrt(len(d)))
        mean_diff, se_diff = np.array(mean_diff), np.array(se_diff)
        critical = float(student.ppf(0.5 + spec['settled']['confidence'] / 2, len(blocks) - 1))
        moved = np.abs(mean_diff) > 0
        result['differences'][name] = {'seats': len(mean_diff), 'seatsWithAnyChange': int(moved.sum()),
                                       'seatsResolved': int(np.sum(np.abs(mean_diff) > critical * se_diff)),
                                       'seatsMovedAtLeastOnePointUnresolved': int(np.sum((np.abs(mean_diff) >= 0.01) & (np.abs(mean_diff) <= critical * se_diff))),
                                       'maxAbsMeanDifference': float(np.abs(mean_diff).max()), 'medianStandardError': float(np.median(se_diff)),
                                       'maxStandardError': float(se_diff.max())}
    return result


def harness_verdict(ev, spec):
    h = ev['harness']
    tol = spec['tolerance']
    ok = (all(v <= tol['stage48Block0'] for v in h['stage48Block0MaxAbsDifference'].values())
          and all(s['uniformNamesEqual'] and s['uniformMaxAbsDifference'] <= tol['blockZeroStream']
                  and s['nationalBlock0MaxAbsDifference'] <= tol['blockZeroStream'] and s['blocksDisjointAndCoverPool']
                  and s['scramble1DiffersFromBlock0'] for s in h['streams'].values())
          and (h['fullInvertVersusRebalanceMaxAbs'] or 0.) <= tol['independentRecompute'])
    return {'verdict': 'MATCHES_STAGE48' if ok else 'STOP', **{k: h[k] for k in ('stage48Block0MaxAbsDifference', 'fullInvertVersusRebalanceMaxAbs')}}


def build():
    spec, ev = design(), read(PREFIX + '/evaluation.json')
    harness = harness_verdict(ev, spec)
    result = {'stage': 54, 'harness': harness, 'operationalAdoption': None}
    if harness['verdict'] != 'MATCHES_STAGE48':
        return result
    stats = mcse(ev, spec)
    g = gate(ev, spec)
    result.update({'gate': g, 'scalingDiagnostic': scaling(ev, spec, g, stats), 'mcse': stats, 'requirement': requirement(stats, spec),
                   'layerShare': layer_share(ev, spec), 'chainSplit': chain_split(ev, spec), 'settled': settled(ev, spec),
                   'winProbability': win_probability(ev, spec), 'gateVerdict': g['verdict']})
    return result


def main():
    args = arguments()
    verify()
    save('decision.json', build(), args.check)
    print('Stage54 frozen precision rules applied' if not args.check else 'Stage54 decision reproduced')


if __name__ == '__main__':
    main()
