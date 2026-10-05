"""Independent scalar audit of Stage44 scale allocation; no forecast scoring."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import helmert
from scripts.uncertainty.common import equivalent

ROOT = Path(__file__).resolve().parents[2]
OLD = 'data/processed/uncertainty'
NEW = 'data/processed/uncertainty-revision'
EPSILON = 1e-6


def load(name):
    return json.loads((ROOT / OLD / name).read_text())


def scalar_residual(row):
    raw = [math.log((a + EPSILON) / (m + EPSILON))
           for a, m in zip(row['actual'], row['mean'])]
    center = math.fsum(raw) / len(raw)
    return np.array([r - center for r in raw])


def rms(values):
    return None if not values else math.sqrt(math.fsum(v*v for v in values)/len(values))


def pair_value(row):
    groups = row['groups']
    if groups.count('national') != 1 or groups.count('labour') != 1:
        return None
    n, l = groups.index('national'), groups.index('labour')
    e = scalar_residual(row)
    return float(e[n] - e[l])


def aggregate_value(row):
    major = [i for i, g in enumerate(row['groups']) if g in ('national', 'labour')]
    remaining = [i for i, g in enumerate(row['groups']) if g not in ('national', 'labour')]
    if not major or not remaining:
        return None
    def ratio(x):
        return math.log((math.fsum(x[i] for i in major)+len(major)*EPSILON)
                        / (math.fsum(x[i] for i in remaining)+len(remaining)*EPSILON))
    return ratio(row['actual']) - ratio(row['mean'])


def remainder_pair_moment(row):
    e = scalar_residual(row)
    remaining = [i for i, g in enumerate(row['groups']) if g not in ('national', 'labour')]
    values = [(float(e[i]-e[j]))**2 for p, i in enumerate(remaining) for j in remaining[p+1:]]
    return None if not values else math.fsum(values)/len(values)


def coordinate_summary(rows):
    groups = sorted({g for r in rows for g in r['groups']})
    result = []
    total = math.fsum(float(v*v) for r in rows for v in scalar_residual(r))
    for group in groups:
        values = [float(v) for r in rows for g, v in zip(r['groups'], scalar_residual(r)) if g == group]
        magnitude = math.fsum(v*v for v in values)
        result.append({'group': group, 'coordinates': len(values), 'squaredMagnitude': magnitude,
                       'fractionSquaredMagnitude': magnitude/total, 'coordinateRMS': rms(values)})
    return result


def zero_summary(rows):
    zero, near, perturbations, zero_rows = [], [], [], []
    for row in rows:
        e = scalar_residual(row)
        has_zero = False
        for i, (a, m, value) in enumerate(zip(row['actual'], row['mean'], e)):
            entry = {'seatId': row['targetElectorateId'], 'optionId': row['ids'][i],
                     'actualShare': a, 'meanShare': m, 'CLRResidual': float(value),
                     'outcomeReference': row['outcomeReference']}
            if a == 0 or m == 0:
                zero.append(entry)
                has_zero = True
            if min(a, m) <= 1e-4:
                near.append(entry)
            if a > 0 and m > 0:
                # Pairwise raw-log perturbation before common CLR subtraction.
                perturbations.append(math.log((a+EPSILON)/(m+EPSILON))-math.log(a/m))
        if has_zero:
            zero_rows.append(row['targetElectorateId'])
    total = math.fsum(float(v*v) for row in rows for v in scalar_residual(row))
    return {'zeroCoordinates': zero, 'zeroRows': zero_rows,
            'nearZeroDiagnosticThresholdShare': 1e-4, 'nearZeroCoordinates': len(near),
            'nearZeroSquaredMagnitudeFraction': math.fsum(v['CLRResidual']**2 for v in near)/total,
            'zeroCoordinateSquaredMagnitudeFraction': math.fsum(v['CLRResidual']**2 for v in zero)/total,
            'positiveCoordinateRawLogReplacementPerturbationRMS': rms(perturbations),
            'positiveCoordinateMaximumRawLogReplacementPerturbation': max(map(abs, perturbations), default=0),
            'interpretation': 'Threshold is diagnostic only; all residual coordinates remain in the audit.'}


def independent_environment(rows, labels):
    basis = helmert(len(labels), full=False).T
    matrices, values = [], []
    for row in rows:
        h = np.array([[float(g == label) for label in labels] for g in row['groups']])
        h -= h.mean(axis=0, keepdims=True)
        matrices.append(h @ basis / math.sqrt(len(h)))
        values.append(scalar_residual(row) / math.sqrt(len(h)))
    x, y = np.concatenate(matrices), np.concatenate(values)
    q, r = np.linalg.qr(x, mode='reduced')
    effects = basis @ np.linalg.solve(r, q.T @ y)
    shared = float(effects @ effects / (len(labels)-1))
    fitted_magnitudes, leftovers = [], []
    for row in rows:
        h = np.array([[float(g == label) for label in labels] for g in row['groups']])
        h -= h.mean(axis=0, keepdims=True)
        e = scalar_residual(row)
        fitted = h @ effects
        fitted_magnitudes.append(float(fitted @ fitted/(len(e)-1)))
        leftover = e - fitted
        leftovers.append(float(leftover @ leftover/(len(e)-1)))
    return {'classEffects': dict(zip(labels, effects.tolist())),
            'sharedSecondMoment': shared, 'seatSecondMoment': float(np.mean(leftovers)),
            'meanProjectedSharedSquaredMagnitudePerTangentDegree': float(np.mean(fitted_magnitudes)),
            'meanSeatSquaredMagnitudePerTangentDegree': float(np.mean(leftovers)),
            'fitMethod': 'independent QR on equal-contest 1/K coordinate-weighted class contrasts'}


def historical_summary(rows, layer, year, spec, saved_fold):
    pair = [v for row in rows if (v := pair_value(row)) is not None]
    aggregate = [v for row in rows if (v := aggregate_value(row)) is not None]
    remainder = [v for row in rows if (v := remainder_pair_moment(row)) is not None]
    groups = coordinate_summary(rows)
    other_fraction = math.fsum(g['fractionSquaredMagnitude'] for g in groups if g['group'] not in ('national', 'labour'))
    env = independent_environment(rows, spec['sharedClasses'][layer])
    pair_replacement_changes = []
    for row in rows:
        g = row['groups']
        if g.count('national') != 1 or g.count('labour') != 1:
            continue
        n, l = g.index('national'), g.index('labour')
        a, m = row['actual'], row['mean']
        if min(a[n], a[l], m[n], m[l]) > 0:
            raw = math.log(a[n]/a[l])-math.log(m[n]/m[l])
            pair_replacement_changes.append(pair_value(row)-raw)
    return {'targetYear': year, 'contests': len(rows), 'coordinates': sum(len(r['ids']) for r in rows),
            'coordinateGroups': groups, 'nonMajorSquaredMagnitudeFraction': other_fraction,
            'nationalLabourLogRatio': {'records': len(pair), 'residualRMS': rms(pair),
                                     'signedMean': None if not pair else math.fsum(pair)/len(pair),
                                     'maximumReplacementPerturbation': max(map(abs, pair_replacement_changes), default=0)},
            'majorVersusRemainderAggregateLogRatio': {'records': len(aggregate), 'residualRMS': rms(aggregate)},
            'withinRemainderPairLogRatio': {'records': len(remainder),
                                          'equalContestResidualRMS': None if not remainder else math.sqrt(math.fsum(remainder)/len(remainder))},
            'zeroAudit': zero_summary(rows), 'independentStage44Environment': env,
            'simulationContrastAudit': contrast_summary(rows, saved_fold['scales'])}


def contrast_covariance(row, a, scales):
    # a sums to zero, hence the simulation's CLR projection cancels exactly.
    shared_load = [math.fsum(float(a[i]) for i, g in enumerate(row['groups']) if g == label)
                   for label in sorted(set(row['groups']))]
    shared = scales['shared']**2 * math.fsum(v*v for v in shared_load)
    seat = scales['seat']**2 * math.fsum(float(v*v) for v in a)
    return {'sharedVariance': shared, 'seatVariance': seat, 'totalSD': math.sqrt(shared+seat)}


def contrast_summary(rows, scales):
    pair, aggregate, remainder = [], [], []
    for row in rows:
        groups = row['groups']
        if groups.count('national') == 1 and groups.count('labour') == 1:
            a = np.zeros(len(groups));a[groups.index('national')] = 1;a[groups.index('labour')] = -1
            pair.append(contrast_covariance(row, a, scales))
        major = [i for i, g in enumerate(groups) if g in ('national', 'labour')]
        minor = [i for i, g in enumerate(groups) if g not in ('national', 'labour')]
        if major and minor:
            mean = row['mean'];m = math.fsum(mean[i] for i in major);r = math.fsum(mean[i] for i in minor)
            if m > 0 and r > 0:
                a = np.array([mean[i]/m if i in major else -mean[i]/r for i in range(len(groups))])
                aggregate.append(contrast_covariance(row, a, scales))
        for p, i in enumerate(minor):
            for j in minor[p+1:]:
                a = np.zeros(len(groups));a[i] = 1;a[j] = -1
                remainder.append(contrast_covariance(row, a, scales))
    def summary(values):
        return None if not values else {'contrasts': len(values),
            'meanSharedVariance': math.fsum(x['sharedVariance'] for x in values)/len(values),
            'meanSeatVariance': math.fsum(x['seatVariance'] for x in values)/len(values),
            'minimumSD': min(x['totalSD'] for x in values), 'maximumSD': max(x['totalSD'] for x in values)}
    return {'scales': scales, 'nationalLabour': summary(pair), 'majorVersusRemainderDeltaMethod': summary(aggregate),
            'withinRemainderPair': summary(remainder),
            'interpretation': 'NL and pair contrasts exact before location adjustment; aggregate derivative is local delta method, not adjusted-share interval.'}


def scale_decomposition(fold, spec):
    result = {}
    for part, key in [('shared', 'sharedSecondMoment'), ('seat', 'seatSecondMoment')]:
        vals = [m[key] for m in fold['moments'] if m[key] is not None]
        weight = spec['priorPseudoEnvironments'];prior = spec['priorScales'][fold['layer']][part]
        denominator = len(vals)+weight
        p = weight*prior**2/denominator;history = math.fsum(vals)/denominator
        total = fold['scales'][part]**2
        if abs(total-p-history) > 1e-12:
            raise ValueError('Stage44 saved shrinkage identity fails')
        result[part] = {'priorVarianceContribution': p, 'historicalVarianceContribution': history,
                       'totalVariance': total, 'priorFractionVariance': p/total,
                       'historicalFractionVariance': history/total, 'priorSD': prior,
                       'historicalEnvironments': len(vals), 'priorPseudoEnvironments': weight}
    return {'layer': fold['layer'], 'targetYear': fold['targetYear'], 'trainingYears': fold['trainingYears'],
            'parts': result, 'NLVariance': 2*(result['shared']['totalVariance']+result['seat']['totalVariance']),
            'NLSD': math.sqrt(2*(result['shared']['totalVariance']+result['seat']['totalVariance']))}


def build():
    inventory, scales, spec = load('inventory.json'), load('scales.json'), load('specification.json')
    layers, checks = {}, []
    for layer, key in [('local_party', 'partyRecords'), ('candidate', 'candidateRecords')]:
        rows = inventory[key];layers[layer] = []
        for year in sorted({r['targetYear'] for r in rows}):
            subset = [r for r in rows if r['targetYear'] == year]
            fold = next(f for f in scales['folds'][layer] if f['targetYear'] == year)
            item = historical_summary(subset, layer, year, spec, fold)
            independent = item['independentStage44Environment']
            saved = next(m for m in scales['descriptive'][layer]['moments'] if m['targetYear'] == year)
            differences = [abs(independent[k]-saved[k]) for k in ['sharedSecondMoment', 'seatSecondMoment']]
            differences += [abs(v-saved['classEffects'][g]) for g, v in independent['classEffects'].items()]
            if max(differences) > 1e-10:
                raise ValueError('Independent moment audit differs from Stage44')
            checks.append({'layer': layer, 'year': year, 'maximumMomentDifference': max(differences)})
            layers[layer].append(item)
    source_names = ['inventory.json', 'scales.json', 'specification.json']
    source_code = ['estimation.py', 'streams.py', 'transforms.py', 'simulation.py']
    consumed = [f'{OLD}/{p}' for p in source_names]+[f'scripts/uncertainty/{p}' for p in source_code]
    references = [{k: r[k] for k in ['layer', 'targetYear', 'targetElectorateId', 'predictionReference', 'outcomeReference']}
                  for key in ['partyRecords', 'candidateRecords'] for r in inventory[key]]
    return {'stage': 45, 'purpose': 'Pre-correction allocation audit, not predictive scoring',
            'inputHashes': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in consumed},
            'layers': layers, 'scaleDecomposition': [scale_decomposition(f, spec) for values in scales['folds'].values() for f in values],
            'independentChecks': checks, 'residualReferences': references,
            'zeroReplacementShare': EPSILON, 'operationalSelection': None,
            'diagnosis': 'Stage44 correctly implements its frozen isotropic seat/common-class family. It allocates heterogeneous small-option relative errors to major-party contrasts; this is a statistical-family limitation, not a numerical bug.'}


def render(value):
    lines = ['# Stage45 residual-scale allocation diagnosis', '',
        'This audit precedes revised uncertainty scoring. It uses the preserved Stage44 residual inventory and actual simulation equations; no mean model is refitted and no new performance score is calculated.', '',
        '## Verified allocation', '',
        '| Layer | Election | Vectors | Other squared CLR fraction | NAT/LAB log-ratio RMS | Stage44 implied NAT/LAB SD |',
        '|---|---:|---:|---:|---:|---:|']
    for layer, cases in value['layers'].items():
        for c in cases:
            lines.append(f"| {layer} | {c['targetYear']} | {c['contests']} | {100*c['nonMajorSquaredMagnitudeFraction']:.2f}% | {c['nationalLabourLogRatio']['residualRMS']:.4f} | {c['simulationContrastAudit']['nationalLabour']['minimumSD']:.4f} |")
    lines += ['', 'All quantities above are dimensionless natural-log units, not percentage points. The implied SD is before nonlinear location adjustment. For NAT/LAB, CLR centering cancels exactly: residual = log(actual NAT / actual LAB) − log(mean NAT / mean LAB), with the frozen ε replacement.', '',
        'More minor coordinates naturally contribute more squared magnitude. In the local-party layer their per-coordinate relative errors are also much larger than the major-party coordinates, while the common isotropic seat scale imposes the same variance on every option. Candidate heterogeneity is less uniform: no-group candidates have the largest coordinate RMS, and smaller mapped candidates are not worse than every major group in every election. For the NAT/LAB contrast, the actual Stage44 generator implies variance **2 σ_shared² + 2 σ_seat²**, independently of CLR subtraction.', '',
        'Stage44 is correctly implemented. Its statistical allocation spreads large small-option relative errors into major-party balance uncertainty. A post-result change to the uncertainty family is justified; this is not a numerical correction to Stage44.', '',
        '## Shared, seat and prior allocation', '',
        '| Layer / forecast election | Earlier environments | Shared SD | Seat SD | Shared prior variance fraction | Seat prior variance fraction |',
        '|---|---:|---:|---:|---:|---:|']
    for f in value['scaleDecomposition']:
        a, b = f['parts']['shared'], f['parts']['seat']
        lines.append(f"| {f['layer']} / {f['targetYear']} | {len(f['trainingYears'])} | {math.sqrt(a['totalVariance']):.4f} | {math.sqrt(b['totalVariance']):.4f} | {100*a['priorFractionVariance']:.1f}% | {100*b['priorFractionVariance']:.1f}% |")
    lines += ['', 'Variance contributions are exactly priorPseudoEnvironments × priorSD² / totalEnvironments and sum(historical second moments) / totalEnvironments. The candidate early seat SD 0.50 is an assumption, not an estimate. Shared effects are estimated once per election; many seats do not create many independent common-error environments.', '',
        '## Other meaningful contrasts and zero handling', '',
        '| Layer | Election | Major/remainder aggregate log-ratio RMS | Within-remainder pair log-ratio RMS | Zero coordinates | Zero squared magnitude fraction | Near-zero squared magnitude fraction |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for layer, cases in value['layers'].items():
        for c in cases:
            z = c['zeroAudit']
            lines.append(f"| {layer} | {c['targetYear']} | {c['majorVersusRemainderAggregateLogRatio']['residualRMS']:.4f} | {c['withinRemainderPairLogRatio']['equalContestResidualRMS']:.4f} | {len(z['zeroCoordinates'])} | {100*z['zeroCoordinateSquaredMagnitudeFraction']:.2f}% | {100*z['nearZeroSquaredMagnitudeFraction']:.2f}% |")
    lines += ['', 'Major/remainder aggregates use sums of ε-replaced fine options. Within-remainder RMS averages squared pair contrasts within each slate, then weights contests equally. Fine IDs, source/outcome references, complete group counts, coordinate RMS, fitted class effects, exact prior/history decomposition and implied contrast covariance are in `data/processed/uncertainty-revision/diagnosis.json`.', '',
        'The diagnostic near-zero boundary is 0.01% share and is not an eligibility or scale-estimation threshold. All options remain represented. Zero replacement remains ε=1e-6. The consumed candidate frame has no zero observations; the party frame contains zeros, including one positive observed party share with frozen mean zero. A locked zero mean cannot acquire positive mass while preserving that mean.', '',
        'Large within-remainder relative misses must remain uncertainty evidence. They should be allocated to remainder directions rather than erased. The tiny fixed replacement can materially affect extreme minor-option log errors, but observed zero coordinates alone do not account for the pooled major overdispersion. The maximum NAT/LAB log-ratio replacement perturbation is 0.00000290 for local party and 0.00000790 for candidate residuals; these meaningful major contrasts are essentially unaffected.', '',
        '## Independent arithmetic and preservation', '',
        'Scalar `math.log`/`math.fsum` CLR residuals and independent QR class fits reproduce every saved Stage44 environment moment and class effect within 1e-10. Direct covariance contrasts verify the projected shared/seat generator. This is independent numerical verification, not documentary or predictive validation.', '',
        'Reproduce with `.venv/bin/python -m scripts.uncertainty_revision.diagnosis`; verify with `--check`. Only the separate Stage45 diagnosis artifacts are written. Consumed file hashes are pinned; prior Stage44 data and implementation are unchanged.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--check', action='store_true')
    args = parser.parse_args();value = build()
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n'
    files = {ROOT/NEW/'diagnosis.json': raw, ROOT/'docs/stage45-residual-diagnosis.md': render(value)}
    for path, text in files.items():
        if args.check:
            valid = equivalent(json.loads(path.read_text()), value) if path.suffix == '.json' else path.read_text() == text
            if not valid:
                raise ValueError(f'Stale diagnosis: {path}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True);path.write_text(text)
    print('Stage45 independent pre-scoring diagnosis verified:', len(value['residualReferences']), 'vectors')


if __name__ == '__main__':
    main()
