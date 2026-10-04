"""Conserve each archived draw under two fixed conditional Other allocations."""
from math import fsum
from .common import CORE, NATIONAL, simplex, read, save


def allocate(vector, categories, fine, weights):
    if len(vector) != len(categories) or len(set(categories)) != len(categories) or categories.count('OTH') != 1:
        raise ValueError('Incomplete/duplicate national schema')
    simplex(vector)
    if any(p not in CORE and p != 'OTH' for p in categories):
        raise ValueError('Unknown explicit national category')
    ids = [r['categoryId'] for r in fine]
    if len(set(ids)) != len(ids) or len({r['ballotGroupKey'] for r in fine}) != len(fine):
        raise ValueError('Duplicate fine roster')
    explicit = {CORE[p]: v for p, v in zip(categories, vector) if p != 'OTH'}
    if len(explicit) != len(categories) - 1:
        raise ValueError('Duplicate explicit category')
    other = vector[categories.index('OTH')]
    fractions = {r['categoryId']: r['allocationFraction'] for r in weights}
    if len(fractions) != len(weights) or set(fractions) & set(explicit) or set(ids) != set(fractions) | set(explicit):
        raise ValueError('Incomplete or overlapping allocation')
    if not fractions:
        if other != 0:
            raise ValueError('Positive unresolved Other without recipient')
    else:
        simplex(list(fractions.values()))
    result = [explicit[cid] if cid in explicit else other * fractions[cid] for cid in ids]
    simplex(result)
    if abs(fsum(result[ids.index(cid)] for cid in fractions) - other) > 1e-12:
        raise ValueError('Other conservation failed')
    return result


def summary(vectors, fine, weights, coarse, categories):
    means = [fsum(v[j] for v in vectors) / len(vectors) for j in range(len(fine))]
    other = fsum(v[categories.index('OTH')] for v in coarse) / len(coarse)
    by_basis = {}
    for r in weights:
        by_basis[r['basis']] = by_basis.get(r['basis'], 0) + other * r['allocationFraction']
    return {'expectedShares': means, 'allocatedOtherMean': other, 'allocatedMassByBasis': by_basis,
            'unresolvedRemainder': 0., 'drawCount': len(vectors),
            'uncertainty': 'conditional fixed allocation; scenario sensitivity is not a fine-party posterior'}


def run(inventory, check=False):
    benchmarks = {c['id']: c for c in read(NATIONAL / 'benchmark.json')['cases']}
    rows = []
    for case in inventory['cases']:
        fit = read(NATIONAL / case['archivePath'])
        fine = case['roster']
        policies = {}
        for policy in ('recent_report_prior', 'prior_only'):
            systems = {}
            for system in ('model', 'average'):
                info = case['systems'][system]
                weights, cats = info['weights'][policy], info['categories']
                if system == 'model':
                    if fit['categories'] != cats:
                        raise ValueError('Archived category disagreement')
                    arrays = {name: fit['draws'][name] for name in ('current', 'electionDay')}
                else:
                    b = benchmarks[case['id']]
                    if b['categories'] != cats or b['status'] != 'constructed':
                        raise ValueError('Missing independent benchmark')
                    arrays = {'point': [b['shares']]}
                outputs, summaries = {}, {}
                for name, coarse in arrays.items():
                    outputs[name] = [allocate(v, cats, fine, weights) for v in coarse]
                    summaries[name] = summary(outputs[name], fine, weights, coarse, cats)
                path = 'allocations/' + case['id'] + '-' + policy + '-' + system + '.json.gz'
                payload = {'id': case['id'], 'system': system, 'policy': policy, 'categories': [r['categoryId'] for r in fine],
                           'ballotGroupKeys': [r['ballotGroupKey'] for r in fine], 'arrays': outputs,
                           'drawNamespace': case['drawNamespace'] if system == 'model' else None,
                           'drawIds': fit['draws']['drawIds'] if system == 'model' else None,
                           'sourceArchive': case['archivePath'] if system == 'model' else 'benchmark.json',
                           'informationFlags': ['retrospective_roster', 'inferred_publication_admitted', 'conditional_other_allocation', 'no_recalibration'],
                           'cutoff': case['cutoff'], 'horizonDays': case['horizonDays'], 'summaries': summaries}
                save(path, payload, check)
                systems[system] = {'path': path, 'summaries': summaries}
            policies[policy] = systems
        differences = {}
        for system in ('model', 'average'):
            name = 'electionDay' if system == 'model' else 'point'
            a = policies['recent_report_prior'][system]['summaries'][name]['expectedShares']
            b = policies['prior_only'][system]['summaries'][name]['expectedShares']
            differences[system] = {'totalVariationPP': 50 * fsum(abs(x-y) for x,y in zip(a,b)),
                                   'maximumCategoryDifferencePP': 100 * max(abs(x-y) for x,y in zip(a,b))}
        rows.append({'id': case['id'], 'fineCategories': [r['categoryId'] for r in fine], 'policies': policies, 'policyDifference': differences})
    result = {'stage': 37, 'cases': rows, 'candidatePredictionsProduced': False, 'operationalSelection': None}
    save('allocation-manifest.json', result, check)
    return result
