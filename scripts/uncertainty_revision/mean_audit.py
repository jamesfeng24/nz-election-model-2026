"""Outcome-free conditional response, remainder distortion and shared effects."""
import hashlib
import numpy as np
from scipy.special import ndtri, softmax
from scipy.stats import qmc
from scripts.uncertainty.construction import national_case, scale_for
from scripts.polling.candidate_integration.propagation import local_vectors, candidate_vectors
from scripts.uncertainty.simulation import candidate_inputs, compose as old_compose
from .simulation import compose
from .coordinates import partition
from .estimation import labels
from .construction import arrays
from .common import PREFIX, OLD, read, save, verify, arguments


def integration_noise(row, scales, policy):
    if policy == 'unchanged_stage44':
        tags = row['groups']; options = list(range(len(tags)))
        shared_scale, seat_scale = scales['shared'], scales['seat']
    else:
        options = partition(row['groups'])[2]
        all_tags = labels(row); tags = [all_tags[i] for i in options]
        shared_scale, seat_scale = scales['within']['shared'], scales['within']['seat']
    unique = sorted(set(tags))
    seed = int.from_bytes(hashlib.sha256(('stage45:conditional-audit:' + row['targetElectorateId'] + policy).encode()).digest()[:4], 'big')
    uniform = qmc.Sobol(len(unique) + len(options), scramble=True, seed=seed).random_base2(11)
    z = ndtri(uniform)
    eta = np.column_stack([shared_scale * z[:, unique.index(tag)] + seat_scale * z[:, len(unique) + i]
                           for i, tag in enumerate(tags)])
    return eta - eta.mean(axis=1, keepdims=True)


def conditional_expectation(base, row, scales, metadata, policy):
    base = np.asarray(base)
    eta = integration_noise(row, scales, policy)
    if policy == 'unchanged_stage44':
        logbase = np.full(len(base), -np.inf)
        np.log(base, out=logbase, where=base > 0)
        return softmax(logbase + metadata['locationOffset'] + eta, axis=1).mean(axis=0)
    n, l, other = partition(row['groups'])
    result = base.copy()
    if other:
        logbase = np.full(len(other), -np.inf)
        np.log(base[other], out=logbase, where=base[other] > 0)
        offsets = metadata['withinLocation']['locationOffset']
        within = softmax(logbase + offsets + eta, axis=1).mean(axis=0)
        result[other] = np.sum(base[other]) * within
    return result


def conditional_records():
    inventory = read(OLD + '/inventory.json')
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    candidates = {r['targetElectorateId']: r for r in inventory['candidateRecords']}
    revised, old = read(PREFIX + '/scales.json'), read(OLD + '/scales.json')
    construction = read(PREFIX + '/construction.json')
    results = []
    for case in construction['cases']:
        if case['layer'] != 'composed':
            continue
        records = case['records']
        selected = [records[i] for i in sorted({0, len(records) // 2, len(records) - 1})]
        first_party = parties[selected[0]['id']]
        national, _, _ = national_case(case['year'], first_party['ids'], case['draws'])
        national_n = first_party['groups'].index('national')
        national_order = np.argsort(national[:, national_n], kind='stable')
        scenarios = [int(national_order[i]) for i in (0, len(national) // 2, len(national) - 1)]
        for item in selected:
            party, candidate = parties[item['id']], candidates[item['id']]
            local = local_vectors(national[scenarios], party['affinities'])
            destination, exponent, floor = candidate_inputs(candidate, party)
            candidate_base = candidate_vectors(local, destination, exponent, floor)
            for policy, scales in (('revised', revised), ('unchanged_stage44', old)):
                for layer, row, bases, location_name in (
                        ('local_party', party, local, 'localLocation'),
                        ('candidate', candidate, candidate_base, 'candidateLocation')):
                    fit = scale_for(scales, layer, case['year'])
                    location = item['metadata'][policy][location_name]
                    for index, base in zip(scenarios, bases):
                        expected = conditional_expectation(base, row, fit['scales'], location, policy)
                        results.append({'policy': policy, 'layer': layer, 'year': case['year'],
                                        'seat': row['targetElectorateId'], 'nationalIndex': index,
                                        'base': base.tolist(), 'expected': expected.tolist(),
                                        'groups': row['groups'], 'conditionalShiftPP': (100 * (expected - base)).tolist(),
                                        'integration': 'GH conditional major expectation; independent scrambled Sobol2048 remainder' if policy == 'revised' else 'independent scrambled Sobol2048 full CLR expectation'})
    return results


def synthetic_records():
    results = []
    revised, old = read(PREFIX + '/scales.json'), read(OLD + '/scales.json')
    inv = read(OLD + '/inventory.json')
    for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords')):
        template = next(r for r in inv[key] if r['targetYear'] == 2023)
        # Frozen input-only shifts of both major mass and balance; no target outcomes.
        bases = []
        for n, l in ((.65, .25), (.40, .45), (.20, .60)):
            row = np.array(template['mean'])
            ni, li, other = partition(template['groups'])
            row[ni[0]], row[li[0]] = n, l
            row[other] *= (1 - n - l) / row[other].sum()
            bases.append(row)
        base = np.tile(bases, (1366, 1))[:4096]
        for policy, scales in (('revised', revised), ('unchanged_stage44', old)):
            fitted = scale_for(scales, layer, 2023)['scales']
            if policy == 'revised':
                from .simulation import noise
                from .coordinates import inverse
                eta, total = noise(template, fitted, len(base))
                _, metadata = inverse(base, template['groups'], eta, total)
            else:
                from scripts.uncertainty.streams import noise
                from scripts.uncertainty.transforms import preserve_mean
                _, metadata = preserve_mean(base, noise(template, fitted, len(base)))
            for vector in bases:
                expected = conditional_expectation(vector, template, fitted, metadata, policy)
                results.append({'syntheticOnly': True, 'layer': layer, 'policy': policy,
                                'base': vector.tolist(), 'expected': expected.tolist(), 'groups': template['groups'],
                                'conditionalShiftPP': (100 * (expected - vector)).tolist()})
    return results


def dependence():
    inv = read(OLD + '/inventory.json')
    lookup = {r['targetElectorateId']: r for key in ('partyRecords', 'candidateRecords') for r in inv[key]}
    # Party and candidate IDs overlap; choose layer-specific dictionaries below.
    records = []
    for case in read(PREFIX + '/construction.json')['cases']:
        if case['layer'] == 'composed':
            continue
        rows = inv['partyRecords' if case['layer'] == 'local_party' else 'candidateRecords']
        lookup = {r['targetElectorateId']: r for r in rows}
        first, last = case['records'][0], case['records'][-1]
        with arrays(case) as bank:
            for policy in ('revised', 'unchanged_stage44'):
                ratios = []
                for item in (first, last):
                    row = lookup[item['id']]
                    n, l, _ = partition(row['groups'])
                    q = bank[policy + ':' + row['targetElectorateId']]
                    ratios.append(np.log(q[:, n[0]]) - np.log(q[:, l[0]]))
                scales = read((PREFIX if policy == 'revised' else OLD) + '/scales.json')
                fit = scale_for(scales, case['layer'], case['year'])['scales']
                f = fit['balance'] if policy == 'revised' else fit
                variance_factor = 1 if policy == 'revised' else 2
                records.append({'case': case['id'], 'policy': policy, 'seats': [first['id'], last['id']],
                                'sharedLogRatioVariance': variance_factor * f['shared'] ** 2,
                                'seatLogRatioVariance': variance_factor * f['seat'] ** 2,
                                'theoreticalCrossSeatCorrelation': f['shared'] ** 2 / (f['shared'] ** 2 + f['seat'] ** 2),
                                'empiricalCrossSeatLogRatioCorrelation': float(np.corrcoef(ratios)[0, 1])})
    return records


def build():
    return {'stage': 45, 'conditionalResponseRecords': conditional_records(),
            'syntheticConditionalResponses': synthetic_records(), 'sharedDependence': dependence(),
            'outcomesConsumed': False,
            'limitation': 'minor conditional allocations retain finite-bank marginal approximation; Sobol audit is numerical, not calibrated error bound'}


def main():
    args = arguments(); verify(); save('mean-audit.json', build(), args.check)
    print('Stage45 conditional response and shared dependence audited without outcomes')


if __name__ == '__main__':
    main()
