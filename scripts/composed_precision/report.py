"""Reproducible Stage54 findings document; every number is read from the decision file."""
from .common import ROOT, PREFIX, arguments, read, verify, design

DOC = 'docs/stage54-composed-precision-findings.md'
NAMES = {'mean': 'simulated mean', 'rbMean': 'Rao-Blackwell mean (alternative statistic)', 'crps': 'CRPS', 'energy': 'energy score',
         'width50': '50% width', 'width80': '80% width', 'width90': '90% width'}
COMPARISONS = (('constant_vs_control', 'K vs C'), ('conditional_vs_constant', 'F vs K'), ('conditional_vs_control', 'F vs C'))


def table(header, rows):
    return ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join('---' for _ in header) + ' |',
            *['| ' + ' | '.join(str(v) for v in r) + ' |' for r in rows], '']


def f(x, digits=3):
    return f'{x:.{digits}f}'


def build():
    spec, d = design(), read(PREFIX + '/decision.json')
    if d['harness']['verdict'] != 'MATCHES_STAGE48':
        raise ValueError('Stage54 harness did not match Stage48')
    gate, req, mcse, layer, chain = d['gate'], d['requirement'], d['mcse'], d['layerShare'], d['chainSplit']
    caps = spec['gatesPP']
    last = gate['rounds'][-1]
    failing = [k for k, v in gate['lastDoublingRatioToCap'].items() if v > 1]
    out = ['# Stage54: composed Monte Carlo precision, findings', '',
           'Pre-registered design: [stage54-composed-precision-design.md](stage54-composed-precision-design.md), frozen before any block other than the Stage47/Stage48 frame was simulated. '
           'Machine contract: [design-contract.json](../data/processed/composed-precision/design-contract.json). All figures are percentage points unless stated; no model default, scale, law or Stage47/Stage48 result is changed.', '',
           '## Finding under the frozen rules', '',
           f'**{d["gateVerdict"]}.** The frozen composed caps are not met even when the whole cached 4,096-draw national subset is used '
           f'(last doubling 2,048 to 4,096 exceeds the cap for {", ".join(failing)}). The i.i.d. scaling prediction holds (observed last-doubling change over predicted: '
           + ', '.join(f'{k} {f(v, 2)}' for k, v in d['scalingDiagnostic'].items()) + '), so this is ordinary Monte Carlo noise at a draw count that is too small for 0.05pp caps, not a harness defect. '
           'Paired composed differences and seat-win probabilities, however, are bounded well enough to be settled or quantified (below), so the failed gate limits absolute composed levels, not the Stage48 supporting comparison.', '',
           '## Harness', '',
           f'Block 0 equals the Stage47/Stage48 composed frame exactly: maximum absolute difference to Stage48\'s stored composed records is {d["harness"]["stage48Block0MaxAbsDifference"]["control"]:.1e} (control), '
           f'{d["harness"]["stage48Block0MaxAbsDifference"]["constant"]:.1e} (K), {d["harness"]["stage48Block0MaxAbsDifference"]["conditional"]:.1e} (F) over all 193 seats. The substituted Sobol stream equals the Stage46 stream exactly for scramble 0, the eight national blocks are disjoint and cover the cached 4,096 subset, and the reused-remainder rebalance equals a full re-inversion (maximum {d["harness"]["fullInvertVersusRebalanceMaxAbs"]:.1e}).', '',
           '## Frozen gate ladder (control, 9 representative seats)', '',
           'Nested union banks of 1, 2, 4, 8 blocks; maximum change over representative seats and candidates at each doubling, against the frozen caps.', '']
    rows = []
    for r in gate['rounds']:
        c = r['changesPP']
        rows.append([f'{r["earlier"]} to {r["later"]}'] + [f(c[k], 3) + ('' if r['passed'][k] else ' (fail)') for k in ('mean', 'crps', 'energy', 'width50', 'width80', 'width90')])
    rows.append(['Cap'] + [str(caps[k]) for k in ('mean', 'crps', 'energy', 'width50', 'width80', 'width90')])
    out += table(['Doubling', 'mean', 'CRPS', 'energy', 'width50', 'width80', 'width90'], rows)
    out += ['The Stage47/48 first doubling (512 to 1,024) used different national subsets and scrambles here, so its numbers differ from Stage47\'s 0.561/0.233/0.212/2.255; the failure and its size are the same.', '',
            '## Where the error comes from and what would be needed', '',
            's512 is the sd of a 512-draw composed bank across blocks (representatives: 8 blocks, 80 seat-candidates; all seats: 4 blocks). The layer share is the variance share left when only the layer stream is re-scrambled on the same 512 national draws '
            '(pooled over representative seat-candidates; above 1.0 is clipped). The chain bound is the multi-chain sd of the 4,096 estimate over the four cached chains (reported only; 3 degrees of freedom, maximum over 80 seat-candidates, so biased high). '
            'Required draws apply the frozen 3-sigma rule to the worst representative seat-candidate (`N` is the larger bank of the doubling).', '']
    rows = []
    for k in ('mean', 'rbMean', 'crps', 'energy', 'width50', 'width80', 'width90'):
        cb = chain.get(k)
        rows.append([NAMES[k], caps['mean'] if k == 'rbMean' else caps[k], f(mcse[k]['representatives']['max'], 3), f(mcse[k]['representatives']['median'], 3),
                     f(mcse[k]['allSeats']['max'], 3), f(layer[k]['pooledLayerShareOfVariance'], 2), f(cb['maxBoundPP'], 3) if cb else 'n/a',
                     f"{req[k]['requiredDraws']:,}", f(req[k]['ratioAt4096'], 2)])
    out += table(['Quantity', 'Cap', 's512 max (reps)', 's512 median (reps)', 's512 max (all seats)', 'Layer share', 'Chain bound at 4,096', 'Required draws', '3 sigma / cap at 4,096'], rows)
    worst = max(req[k]['requiredDraws'] for k in ('mean', 'crps', 'energy', 'width50', 'width80', 'width90'))
    out += [f'The frozen caps need between {min(req[k]["requiredDraws"] for k in ("mean", "crps", "energy", "width50", "width80", "width90")):,} and {worst:,} composed draws under the 3-sigma rule, '
            f'that is up to {worst * 71:,} seat-draws for a 71-seat slate. At about 14 ms per draw per seat for the unchanged Stage47 conditional-location solves (one pre-freeze timing, not an artifact) the largest requirement is of order {worst * 71 * 0.014 / 3600:,.0f} CPU hours, so the caps are out of reach for the current numerics at any feasible bank size rather than merely above 4,096. '
            f'The cached national bank holds 8,000 draws (4,096 balanced subset used), so the national dimension cannot be enlarged without a new fit.', '',
            'Layer noise dominates the widths, CRPS and energy variance (layer share '
            + ', '.join(f'{NAMES[k]} {f(layer[k]["pooledLayerShareOfVariance"], 2)}' for k in ('crps', 'energy', 'width90'))
            + '), while the simulated mean is split (' + f(layer['mean']['pooledLayerShareOfVariance'], 2) + ') and the Rao-Blackwell mean is mostly national ('
            + f(1 - layer['rbMean']['pooledLayerShareOfVariance'], 2) + '). So extra layer draws on fixed national draws could in principle remove most of the score and width noise without a new national fit; whether that is affordable is a question about the conditional-location solves and was not tested here.', '',
            '## Are the composed differences settled?', '',
            'Blocks 0 to 3 (4 blocks of 512 draws, 193 seats); estimate is the block mean, SE the sd over blocks divided by 2, 95% t interval with 3 degrees of freedom. Negative favours the first restriction. Stage48\'s own composed value is block 0.', '']
    rows = []
    for key, label in COMPARISONS:
        s = d['settled'][key]
        e = s['deltaMajorCRPSPP']
        rows.append([label, f(e['stage48BlockZeroValue'], 4), f(e['mean'], 4), f(e['standardError'], 4), f'[{f(e["interval95"][0], 4)}, {f(e["interval95"][1], 4)}]', e['state'],
                     f(s['deltaMajorIntervalScorePP']['mean'], 4) + ' (' + s['deltaMajorIntervalScorePP']['state'] + ')',
                     f(s['deltaEnergyPP']['mean'], 4) + ' (' + s['deltaEnergyPP']['state'] + ')'])
    out += table(['Comparison', 'Stage48 block 0', 'Delta major CRPS (4-block mean)', 'SE', '95% interval', 'State', 'Delta interval score', 'Delta energy'], rows)
    rows = []
    for key, label in COMPARISONS:
        s = d['settled'][key]['byElection']
        rows.append([label] + [f'{f(s[y]["mean"], 4)} ({s[y]["state"]})' for y in ('2017', '2020', '2023')])
    out += table(['Delta major CRPS by election', '2017', '2020', '2023'], rows)
    out += ['The paired composed differences are tiny relative to their noise because both restrictions share every draw except the N/L split. The sign agreement that Stage48 could only report as unresolved is settled for K vs C and F vs C pooled and in 2020 and 2023; 2017 is flat at about zero (K and F do not differ from C there). F vs K is settled in sign but immaterial (about 0.0003pp). This labels Stage48\'s supporting check only; its decision and finding are unchanged.', '',
            '## Seat-win probabilities (control, all 193 seats)', '']
    w = d['winProbability']
    out += [f'Design effect D = {f(w["designEffect"], 3)} over {w["includedCandidateProbabilities"]} seat-candidate probabilities in [0.05, 0.95] (D below 1: the scrambled layer stream beats an i.i.d. binomial bank). Largest per-seat sd across 512-draw blocks {f(w["perSeatS512"]["max"], 4)}.', '']
    out += table(['Draws N', 'SE of a probability of 0.5'], [[n, f(v, 4)] for n, v in w['standardErrorAtHalf'].items()])
    out += ['Draws for SE(0.5) <= 0.01: ' + f'{w["requiredDraws"]["0.01"]["powerOfTwoDraws"]:,}' + '; for <= 0.005: ' + f'{w["requiredDraws"]["0.005"]["powerOfTwoDraws"]:,}' + ' (power of two). These are arithmetic bounds relative to the cached national draws; no probability-release threshold is set here (open decision for James).', '']
    rows = []
    for key, label in COMPARISONS[:2]:
        s = w['differences'][key]
        rows.append([label, s['seatsWithAnyChange'], s['seatsResolved'], s['seatsMovedAtLeastOnePointUnresolved'], f(s['maxAbsMeanDifference'], 4), f(s['medianStandardError'], 4), f(s['maxStandardError'], 4)])
    out += table(['Leading-candidate win probability, National', 'Seats changed', 'Seats resolved (95%)', 'Moved 1pt or more, unresolved', 'Max abs mean difference', 'Median SE', 'Max SE'], rows)
    out += ['K moves no seat\'s National win probability by as much as one percentage point, so the Stage48 narrowing is invisible in seat-win probabilities at this precision.', '',
            '## Limits', '',
            '- Blocks are sampled without replacement from a 4,096 pool, so s512 is up to a factor sqrt(7/8) below an i.i.d. sd; this is recorded, not corrected. Block sds have 3 (all seats) or 7 (representatives) degrees of freedom and maxima over seat-candidates are biased high; the 3-sigma requirement is deliberately conservative.',
            '- Precision here is relative to the cached national draws. The chain bound at 4,096 draws is larger than the pool-subsampling bound (s512 over sqrt(8)) for the mean, CRPS and energy, which would mean the four cached chains disagree by more than i.i.d. subsampling implies; with 3 degrees of freedom this is suggestive only, and no composed simulation improves the effective size of the national bank.',
            '- Representative seats are the Stage47/48 first, middle and last of each election, not the worst-precision seats; the all-seat s512 maxima are larger for every quantity.',
            '- Horizon (56 days versus about 32 at publication), prior/parameter uncertainty and omitted uncertainty are outside this stage, and no calibration claim is made.', '',
            '## Recommendation', '',
            '1. **Record the bound; change nothing operational.** Composed absolute levels (means, CRPS, widths, energy) must carry the s512 table above and must not be called settled at a 0.05pp scale; composed paired differences and seat-win probabilities can be reported with the SEs above. The frozen caps stay as they are.',
            '2. **Treat the layer share as the lever, not more national draws.** If composed precision of scores or widths matters for a later stage, the separately authorised engineering question is the cost of the conditional-location solves under layer replication on the fixed 4,096 national draws (or a verified cheaper solver), with the same caps. Not started here.',
            '3. **Item 4 is resolved as a bound.** Stage48\'s composed supporting check is settled in sign and size; the composed-precision limit no longer qualifies it. The probability-release policy remains open.', '']
    return '\n'.join(out) + '\n'


def main():
    args = arguments()
    verify()
    text = build()
    path = ROOT / DOC
    if args.check:
        if not path.exists() or path.read_text() != text:
            raise ValueError('Stale Stage54 findings document')
    else:
        path.write_text(text)


if __name__ == '__main__':
    main()
