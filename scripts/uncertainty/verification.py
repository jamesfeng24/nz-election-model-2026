"""Independent scalar log coordinates and QR-based uncertainty arithmetic audit."""
from math import exp, fsum, log, sqrt
import hashlib

import numpy as np

from .common import PREFIX, ROOT, arguments, digest, read, save, verify

TOLERANCE = 1e-10


def coordinates(values, epsilon):
    """Compute CLR directly; its common zero-replacement denominator cancels."""
    if not values or any(not np.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid independent residual vector')
    logs = [log(v + epsilon) for v in values]
    center = fsum(logs) / len(logs)
    return np.array([v - center for v in logs])


def residual(row, epsilon):
    return coordinates(row['actual'], epsilon) - coordinates(row['mean'], epsilon)


def contrasts(count):
    """Construct orthonormal Helmert columns explicitly, without scipy helper."""
    result = np.zeros((count, count - 1))
    for column in range(count - 1):
        denominator = sqrt((column + 1) * (column + 2))
        result[:column + 1, column] = 1 / denominator
        result[column + 1, column] = -(column + 1) / denominator
    return result


def category_design(groups, labels):
    matrix = np.array([[float(group == label) for label in labels] for group in groups])
    return matrix - np.sum(matrix, axis=0) / len(groups)


def environment(rows, labels, epsilon):
    contrast = contrasts(len(labels))
    x, y = [], []
    for row in rows:
        weight = sqrt(len(row['ids']))
        x.extend(category_design(row['groups'], labels) @ contrast / weight)
        y.extend(residual(row, epsilon) / weight)
    x, y = np.asarray(x), np.asarray(y)
    singular = np.linalg.svd(x, compute_uv=False)
    rank = int(np.sum(singular > max(1e-12, singular[0] * 1e-10)))
    identifiable = singular[-1] > singular[0] * 1e-10 and singular[-1] > 1e-12
    if identifiable:
        orthogonal, triangular = np.linalg.qr(x, mode='reduced')
        coefficients = np.linalg.solve(triangular, orthogonal.T @ y)
        effects = contrast @ coefficients
        shared = fsum(float(v) ** 2 for v in effects) / (len(labels) - 1)
    else:
        effects = np.zeros(len(labels))
        shared = None
    seat = []
    for row in rows:
        remainder = residual(row, epsilon) - category_design(row['groups'], labels) @ effects
        seat.append(fsum(float(v) ** 2 for v in remainder) / (len(remainder) - 1))
    return {'rank': rank, 'identifiable': bool(identifiable), 'effects': effects,
            'shared': shared, 'seat': fsum(seat) / len(seat)}


def verify_fit(rows, layer, target_year, saved, spec):
    eligible = [r for r in rows if target_year is None or r['targetYear'] < target_year]
    years = sorted({r['targetYear'] for r in eligible})
    if saved['trainingYears'] != years or saved['trainingIds'] != [r['targetElectorateId'] for r in eligible]:
        raise ValueError('Independent chronology membership mismatch')
    moments = []
    gap, identities = 0., 0
    for year in years:
        rows_year = [r for r in eligible if r['targetYear'] == year]
        calculated = environment(rows_year, spec['sharedClasses'][layer], spec['zeroReplacement'])
        recorded = next(m for m in saved['moments'] if m['targetYear'] == year)
        if calculated['rank'] != recorded['sharedRank'] or calculated['identifiable'] != recorded['sharedIdentifiable']:
            raise ValueError('Independent rank audit mismatch')
        for name, value in zip(spec['sharedClasses'][layer], calculated['effects']):
            gap = max(gap, abs(float(value) - recorded['classEffects'][name]))
            identities += 1
        for name, key in (('shared', 'sharedSecondMoment'), ('seat', 'seatSecondMoment')):
            value = calculated[name]
            if (value is None) != (recorded[key] is None):
                raise ValueError('Independent missing shared moment mismatch')
            if value is not None:
                gap = max(gap, abs(value - recorded[key]))
                identities += 1
        moments.append(calculated)
    for name in ('shared', 'seat'):
        values = [m[name] for m in moments if m[name] is not None]
        weight = spec['priorPseudoEnvironments']
        scale = sqrt((fsum(values) + weight * spec['priorScales'][layer][name] ** 2) / (len(values) + weight))
        gap = max(gap, abs(scale - saved['scales'][name]))
        identities += 1
    if gap > TOLERANCE:
        raise ValueError('Independent moment/scale disagreement')
    return identities, gap


def compare(actual, recorded, tolerance=TOLERANCE):
    a, b = np.asarray(actual, dtype=float), np.asarray(recorded, dtype=float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Independent arithmetic shape/finite failure')
    difference = float(np.max(np.abs(a - b))) if a.size else 0.
    if difference > tolerance:
        raise ValueError('Independent simulation/score arithmetic disagreement: ' + str(difference))
    return difference


def bank(key, draws, seed):
    value = int.from_bytes(hashlib.sha256(f'{seed}:{key}'.encode()).digest()[:16], 'big')
    half = np.random.Generator(np.random.PCG64(value)).standard_normal(draws // 2)
    return np.array([v for pair in zip(half, -half) for v in pair])


def noise_bank(row, scales, draws, spec, stress=False):
    prefix = f'{row["layer"]}:{row["targetYear"]}'
    shared = [bank(prefix + ':shared:' + group, draws, spec['seed']) for group in row['groups']]
    seat = [bank(prefix + ':seat:' + row['targetElectorateId'] + ':' + cid, draws, spec['seed']) for cid in row['ids']]
    multiplier = sqrt(spec['transportStressCandidateSeatVarianceMultiplier']) if stress and row['layer'] == 'candidate' and row['geography'] != 'exact' else 1.
    values = np.array([scales['shared'] * s + scales['seat'] * multiplier * t for s, t in zip(shared, seat)]).T
    return values - values.mean(axis=1, keepdims=True)


def adjusted(base, noise, offset):
    b = np.asarray(base, dtype=float)
    if b.ndim == 1:
        b = np.broadcast_to(b, noise.shape)
    result = []
    for values, perturbation in zip(b, noise):
        centered = perturbation + np.asarray(offset)
        highest = float(max(centered))
        masses = [float(v) * exp(float(z) - highest) for v, z in zip(values, centered)]
        total = fsum(masses)
        result.append([v / total for v in masses])
    return np.array(result)


def candidate_vectors(local, party, candidate):
    groups = {g: i for i, g in enumerate(party['ballotGroupKeys'])}
    features = candidate['features']
    coefficients = candidate['parameters']['theta']
    floor = candidate['parameters']['kappa']
    exponent = [fsum(t * z for t, z in zip(coefficients, c['centered'])) for c in features]
    highest = max(exponent)
    output = []
    for row in local:
        masses = [(floor + (0 if c['group'] is None else row[groups[c['group']]])) * exp(z - highest) for c, z in zip(features, exponent)]
        total = fsum(masses)
        output.append([v / total for v in masses])
    return np.array(output)


def national_draws(case, parties, spec):
    data = read(f'data/processed/polling/candidate-integration/national/{case["year"]}-recent_report_prior.json.gz')
    chains, per_chain = data['fineChainShape'][:2]
    order = np.random.Generator(np.random.PCG64(spec['seed'])).permutation(per_chain)
    indices = [chain * per_chain + position for position in order[:spec['draws'] // chains] for chain in range(chains)]
    columns = [data['categories'].index(cid) for cid in parties['ids']]
    x = np.asarray(data['arrays'])[indices][:, columns]
    ids = [data['drawIds'][i] for i in indices]
    if len(set(ids)) != len(ids) or spec['draws'] % chains or any(sum(i // per_chain == chain for i in indices) != spec['draws'] // chains for chain in range(chains)):
        raise ValueError('Independent national balance/identity failure')
    return x, ids


def quantile(values, probability):
    ordered = sorted(float(v) for v in values)
    position = (len(ordered) - 1) * probability
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (position - lo) * (ordered[hi] - ordered[lo])


def crps_scalar(values, outcome):
    """Explicit empirical pair distances, not the principal sorted shortcut."""
    x = np.asarray(values)
    distances = np.abs(x[:, None] - x[None, :])
    return fsum(abs(float(v) - outcome) for v in values) / len(values) - float(distances.sum()) / (2 * len(values) ** 2)


def proper_scores(draws, row, recorded, spec):
    mean = [fsum(float(v) for v in draws[:, i]) / len(draws) for i in range(draws.shape[1])]
    errors = [100 * (m - a) for m, a in zip(mean, row['actual'])]
    gap = compare(mean, recorded['simulatedMean'])
    gap = max(gap, compare(errors, recorded['errorPP']))
    gap = max(gap, compare([fsum(abs(e) for e in errors) / len(errors), fsum(e * e for e in errors) / len(errors), fsum(errors) / len(errors)],
                          [recorded['maePP'], recorded['msePP2'], recorded['biasPP']]))
    for i, outcome in enumerate(row['actual']):
        values = [100 * float(v) for v in draws[:, i]]
        truth = 100 * outcome
        gap = max(gap, compare(crps_scalar(values, truth), recorded['crpsPP'][i]))
        for level, key in ((.5, 'interval50'), (.9, 'interval90')):
            alpha = 1 - level
            lower, upper = quantile(values, alpha / 2), quantile(values, 1 - alpha / 2)
            score = upper - lower + 2 / alpha * (max(lower - truth, 0) + max(truth - upper, 0))
            gap = max(gap, compare([lower, upper, upper - lower, score],
                [recorded[key]['lower'][i], recorded[key]['upper'][i], recorded[key]['widths'][i], recorded[key]['scores'][i]]))
            if (lower <= truth <= upper) != recorded[key]['covered'][i]:
                raise ValueError('Independent interval inclusion mismatch')
    selected = 100 * draws[:spec['energyDraws']]
    actual = [100 * v for v in row['actual']]
    def distance(x, y):
        return sqrt(fsum((float(a) - float(b)) ** 2 for a, b in zip(x, y)))
    first = fsum(distance(x, actual) for x in selected) / len(selected)
    second = fsum(distance(x, y) for x in selected for y in selected) / (2 * len(selected) ** 2)
    gap = max(gap, compare(first - second, recorded['energyPP']))
    return gap


def simulation_checks(inventory, spec):
    if not (ROOT / PREFIX / 'construction.json').exists() or not (ROOT / PREFIX / 'evaluation.json').exists():
        return {'status': 'pending construction/evaluation archives'}
    construction = read(PREFIX + '/construction.json')
    evaluation = {c['id']: c for c in read(PREFIX + '/evaluation.json')['cases']}
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    candidates = {r['targetElectorateId']: r for r in inventory['candidateRecords']}
    gap, vectors, score_vectors, composed, national_cases = 0., 0, 0, 0, 0
    mean_preservation_gap = 0.
    for case in construction['cases']:
        if digest(case['drawCache']['path']) != case['drawCache']['sha256']:
            raise ValueError('Independent cache checksum mismatch')
        cache = read(case['drawCache']['path'])
        if len(cache['drawIds']) != spec['draws'] or len(set(cache['drawIds'])) != spec['draws']:
            raise ValueError('Independent draw identity failure')
        for value in cache['vectors'].values():
            q = np.asarray(value)
            if not np.isfinite(q).all() or np.any(q < 0) or np.max(np.abs(q.sum(axis=1) - 1)) > spec['simplexTolerance']:
                raise ValueError('Independent archived simplex failure')
            vectors += len(q)
        records = sorted(case['records'], key=lambda r: r['id'])
        chosen = (records[0], records[-1])
        scored = {r['id']: r for r in evaluation[case['id']]['records']}
        if case['layer'] == 'composed':
            national, ids = national_draws(case, parties[chosen[0]['id']], spec)
            if cache['drawIds'] != ids:
                raise ValueError('Cached shared national IDs differ from balanced raw selection')
            national_cases += 1
        for record in chosen:
            cid = record['id']
            row = parties[cid] if case['layer'] == 'local_party' else candidates[cid]
            q = np.asarray(cache['vectors'][cid])
            metadata = record['metadata']
            if case['layer'] == 'composed':
                party = parties[cid]
                unnormalized = national * np.asarray(party['affinities'])
                deterministic = unnormalized / unnormalized.sum(axis=1, keepdims=True)
                local = adjusted(deterministic, noise_bank(party, case['partyScaleFit']['scales'], spec['draws'], spec), metadata['localLocation']['locationOffset'])
                base = candidate_vectors(local, party, row)
                control = candidate_vectors(deterministic, party, row)
                reconstructed = adjusted(base, noise_bank(row, case['candidateScaleFit']['scales'], spec['draws'], spec), metadata['candidateLocation']['locationOffset'])
                gap = max(gap, compare(control.mean(axis=0), metadata['deterministicNationalOnlyMean']))
                gap = max(gap, compare(base.mean(axis=0), metadata['candidateConditionalMeanAfterLocalUncertainty']))
                gap = max(gap, compare(100 * (base.mean(axis=0) - control.mean(axis=0)), metadata['nonlinearUpstreamMeanShiftPP']))
                gap = max(gap, compare(100 * (q.mean(axis=0) - base.mean(axis=0)), metadata['candidateAdjustmentMeanShiftPP']))
                gap = max(gap, compare(100 * (local.mean(axis=0) - deterministic.mean(axis=0)), metadata['localMarginalMeanShiftPP']))
                mean_preservation_gap = max(mean_preservation_gap, float(np.max(np.abs(local.mean(axis=0) - deterministic.mean(axis=0)))), float(np.max(np.abs(q.mean(axis=0) - base.mean(axis=0)))))
                composed += 1
            else:
                reconstructed = adjusted(row['mean'], noise_bank(row, case['scaleFit']['scales'], spec['draws'], spec), metadata['location']['locationOffset'])
                gap = max(gap, compare(100 * (q.mean(axis=0) - np.asarray(row['mean'])), metadata['expectedShareShiftPP']))
                mean_preservation_gap = max(mean_preservation_gap, float(np.max(np.abs(q.mean(axis=0) - np.asarray(row['mean'])))))
            gap = max(gap, compare(reconstructed, q), compare(q.mean(axis=0), metadata['simulatedMean']))
            gap = max(gap, proper_scores(q, row, scored[cid], spec))
            score_vectors += 1
        summary = evaluation[case['id']]['summary']
        all_records = list(scored.values())
        gap = max(gap, compare([fsum(r['maePP'] for r in all_records) / len(all_records), sqrt(fsum(r['msePP2'] for r in all_records) / len(all_records))],
                              [summary['contestEqualMAEPP'], summary['contestEqualRMSEPP']]))
        flat_errors = [e for r in all_records for e in r['errorPP']]
        gap = max(gap, compare([fsum(abs(e) for e in flat_errors) / len(flat_errors),
            sqrt(fsum(e * e for e in flat_errors) / len(flat_errors)),
            fsum(fsum(r['crpsPP']) / len(r['ids']) for r in all_records) / len(all_records),
            fsum(r['energyPP'] for r in all_records) / len(all_records)],
            [summary['candidateCategoryEqualMAEPP'], summary['candidateCategoryEqualRMSEPP'],
             summary['contestEqualCRPSPP'], summary['energyPP']]))
        for key in ('interval50', 'interval90'):
            covered = [v for r in all_records for v in r[key]['covered']]
            if summary[key]['covered'] != sum(covered) or summary[key]['total'] != len(covered):
                raise ValueError('Independent summary interval counts mismatch')
            gap = max(gap, compare([sum(covered) / len(covered),
                fsum(fsum(r[key]['scores']) / len(r['ids']) for r in all_records) / len(all_records),
                fsum(fsum(r[key]['widths']) / len(r['ids']) for r in all_records) / len(all_records)],
                [summary[key]['coverage'], summary[key]['contestEqualScorePP'], summary[key]['contestEqualWidthPP']]))
    if mean_preservation_gap > spec['meanTolerance'] + 1e-14:
        raise ValueError('Independent mean preservation exceeds frozen tolerance')
    return {'status': 'verified', 'archivedSimplexDrawVectors': vectors,
            'representativePredictionAndScoreVectors': score_vectors, 'composedJensenIdentities': composed,
            'balancedRawNationalCases': national_cases, 'energyAllPairDrawCap': spec['energyDraws'],
            'crpsAllPairDrawCap': spec['draws'], 'maximumArithmeticDifferenceRounded12Decimals': round(gap, 12),
            'meanPreservationWithinFrozenTolerance': True,
            'independentScoringMethods': ['all-pair empirical CRPS', 'scalar all-pair Euclidean energy',
                'manual linear quantiles and proper interval score', 'fsum contest metrics'],
            'means': 'finite-bank marginal preservation; composed nonlinear local-input shift separately verified'}


def build():
    inventory = read(PREFIX + '/inventory.json')
    scales = read(PREFIX + '/scales.json')
    spec = read(PREFIX + '/specification.json')
    identities, gap, fits = 0, 0., 0
    residual_coordinates = 0
    for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords')):
        rows = inventory[key]
        for row in rows:
            value = residual(row, spec['zeroReplacement'])
            if abs(fsum(float(v) for v in value)) > TOLERANCE:
                raise ValueError('Independent CLR conservation mismatch')
            residual_coordinates += len(value)
        for saved in scales['folds'][layer] + [scales['descriptive'][layer]]:
            n, difference = verify_fit(rows, layer, saved['targetYear'], saved, spec)
            identities += n
            gap = max(gap, difference)
            fits += 1
    return {'stage': 44, 'independentMethods': ['scalar CLR logs with fsum',
                'explicit Helmert coordinates', 'QR rather than normal-equation solve',
                'equal-election prior-shrunk second moments'],
            'residualVectors': len(inventory['partyRecords']) + len(inventory['candidateRecords']),
            'residualCoordinates': residual_coordinates, 'chronologicalAndDescriptiveFits': fits,
            'momentAndScaleIdentities': identities, 'tolerance': TOLERANCE,
            'maximumDifferenceRounded12Decimals': round(gap, 12),
            'allChecksPassed': True, 'historicalMeanFittingPerformed': False,
            'simulationAndScoreChecks': simulation_checks(inventory, spec)}


def main():
    args = arguments()
    verify()
    value = build()
    save('independent-verification.json', value, args.check)
    print('Stage44 independent moments/scales verified', value['momentAndScaleIdentities'])


if __name__ == '__main__':
    main()
