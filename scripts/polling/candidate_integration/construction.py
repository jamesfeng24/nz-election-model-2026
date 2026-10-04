"""Cached joint-draw integration, sealed independently of held-out evaluation."""
import argparse
from collections import Counter
import numpy as np
from scripts.polling.category_interface.common import portable_gzip
from .common import *
from .adapter import read_case, allocate_draws
from .propagation import source_affinities, prepare_seat, propagate, candidate_vectors, local_vectors

CODE = ['scripts/polling/candidate_integration/' + n + '.py' for n in ('common', 'inventory', 'adapter', 'propagation', 'construction')]


def signature(batch_size):
    return sha_value({'sources': read(OUT / 'input-contract.json'), 'specification': sha(OUT / 'specification.json'),
                     'inventory': sha(OUT / 'inventory.json'), 'code': {p: sha(ROOT / p) for p in CODE}, 'batchSize': batch_size})


def sha_value(value):
    from hashlib import sha256
    return sha256(encode(value)).hexdigest()


def reproduction(case, row, party_row, categories, saved):
    a, _ = source_affinities(party_row, categories, case['roster'])
    scenario = {c['categoryId']: c['suppliedTargetNationalShare'] for c in categories if c['relationship'] != 'exit'}
    national = np.array([[scenario[c['categoryId']] for c in case['roster']]])
    gaps = {}
    for method in METHODS:
        dest, z, kappa = prepare_seat(row, case, method)
        q = propagate(national, a, dest, z, kappa)[0]
        reference = next(p for p in saved['predictions'][method] if p['targetElectorateId'] == row['targetElectorateId'])['candidateShares']
        ids = [c['targetOccurrenceId'] for c in row['candidates']]
        if set(ids) != set(reference):
            raise ValueError('Saved conditional prediction slate mismatch')
        gap = max(abs(v - reference[cid]) for cid, v in zip(ids, q))
        if gap > 1e-12:
            raise ValueError('Saved Stage33 conditional reproduction failed')
        gaps[method] = gap
    return gaps


def store_draws(name, payload, check=False):
    """Large deterministic transforms remain local; archived seeds/inputs recreate them."""
    import hashlib
    raw = portable_gzip(encode(payload))
    path = ROOT / '.cache/stage39/candidate-draws' / name
    if check:
        if path.exists() and path.read_bytes() != raw:
            raise ValueError('Changed cached candidate vectors')
    else:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
            'storage': 'local reproducible deterministic transforms; national archives/fits and summaries committed'}


def build(check=False, batch_size=256):
    inventory = read(OUT / 'inventory.json')
    design = read(DESIGN / 'inventory.json')
    rows = {r['targetElectorateId']: r for r in design['contestRecords']}
    party = read(PARTY / 'input-inventory.json')
    source = {r['targetElectorateId']: r for r in party['partyFrame']}
    categories = {r['targetYear']: r['categories'] for r in party['categoryRelationships']}
    saved = {f['targetYear']: f for f in read(CANDIDATE / 'construction.json')['folds'] if f['branch'] == 'primary'}
    checks = []
    for case in inventory['cases']:
        for cid in case['evaluationIds']:
            checks.append({'targetElectorateId': cid, 'maximumAbsoluteShareGap': reproduction(case, rows[cid], source[cid], categories[case['year']], saved[case['year']])})
    result = {'stage': 39, 'signature': signature(batch_size), 'cases': [], 'reproduction': checks,
              'uncertainty': 'national-input-only conditional; missing local/candidate/parameter/transport errors',
              'operationalSelection': None, 'heldoutOutcomesUsed': False}
    files = []
    for case in inventory['cases']:
        raw = read_case(case)
        for policy in POLICIES:
            fine = allocate_draws(raw, case['rawCategories'], case['roster'], case['weights'][policy], case['explicitMapping'])
            fine_name = f'national/{case["year"]}-{policy}.json.gz'
            save(fine_name, {'year': case['year'], 'policy': policy, 'cutoff': case['cutoff'], 'horizonDays': 56,
                            'system': 'external_gauss', 'version': case['nationalSignature']['pin'],
                            'categories': [r['categoryId'] for r in case['roster']],
                            'ballotGroupKeys': [r['ballotGroupKey'] for r in case['roster']],
                            'drawIds': case['nationalDrawIds'], 'sourceChainShape': case['chainShape'],
                            'fineChainShape': case['chainShape'][:2] + [len(case['roster'])],
                            'drawArrayShape': list(fine.shape), 'rawCategories': case['rawCategories'],
                            'explicitMapping': case['explicitMapping'],
                            'currentSupportField': case['currentSupportField'],
                            'forecastTarget': case['forecastTarget'], 'arrays': fine.tolist(),
                            'sourceAttribution': 'Arie/ariedotcodotnz nz-poll-of-polls; GPL-3.0-or-later; unchanged statistical code retained in Stage38 archive',
                            'availability': ['reconstructed_input_snapshot', 'inferred_publication', 'retrospective_roster', 'conditional_other_allocation']}, check)
            files.append(fine_name)
            records, abstentions = [], []
            candidate_draws = {m: {} for m in METHODS}
            for cid in case['evaluationIds']:
                row = rows[cid]
                try:
                    a, states = source_affinities(source[cid], categories[case['year']], case['roster'])
                    methods = {}
                    for method in METHODS:
                        dest, z, kappa = prepare_seat(row, case, method)
                        q = propagate(fine, a, dest, z, kappa, batch_size)
                        ids = [c['targetOccurrenceId'] for c in row['candidates']]
                        expected = q.mean(axis=0)
                        shortcut = propagate(fine.mean(axis=0, keepdims=True), a, dest, z, kappa)[0]
                        quantiles = np.quantile(q, [.05, .25, .75, .95], axis=0, method='linear')
                        methods[method] = {'candidateShares': dict(zip(ids, expected.tolist())),
                            'nationalInputOnlyConditionalIntervals': {c: {'50': [float(quantiles[1,j]), float(quantiles[2,j])], '90': [float(quantiles[0,j]), float(quantiles[3,j])]} for j,c in enumerate(ids)},
                            'meanInputShortcutMaximumGapPP': float(100 * np.max(np.abs(expected - shortcut))),
                            'fitId': case['fits'][method]['fitId']}
                        candidate_draws[method][cid] = {'candidateIds': ids, 'shares': q.tolist()}
                except ValueError as exc:
                    abstentions.append({'targetElectorateId': cid, 'reason': str(exc)})
                    for m in METHODS: candidate_draws[m].pop(cid, None)
                    continue
                records.append({'targetElectorateId': cid, 'originalFrame': row['originalFrame'], 'methods': methods,
                                'sourceAffinities': {c['categoryId']: float(v) for c,v in zip(case['roster'], a)}})
            if abstentions:
                raise ValueError('Unexpected integration construction failure: ' + str(abstentions))
            caches = {}
            for m in METHODS:
                payload = {'drawIds': case['nationalDrawIds'], 'year': case['year'], 'policy': policy, 'method': m, 'contests': candidate_draws[m]}
                caches[m] = store_draws(f'{case["year"]}-{policy}-{m}.json.gz', payload, check)
            other_mean = float(raw[:, case['rawCategories'].index('Other')].mean())
            mass = {}
            for w in case['weights'][policy]: mass[w['basis']] = mass.get(w['basis'], 0.) + other_mean * w['allocationFraction']
            result['cases'].append({'year': case['year'], 'policy': policy, 'expectedIds': case['evaluationIds'],
                'candidateIds': case['evaluationCandidateIds'], 'drawIdsReferenced': fine_name, 'drawsPerContest': len(fine),
                'records': records, 'abstentions': abstentions, 'nationalArtifact': fine_name, 'candidateDrawCaches': caches,
                'allocatedOtherMean': other_mean, 'allocatedMassByBasis': mass})
            print('Constructed', case['year'], policy, len(records), flush=True)
    save('construction.json', result, check)
    seal('construction', files + ['construction.json'], CODE, check)
    return result


def run(check=False, batch_size=256):
    verify_inputs()
    if not check and (OUT / 'construction.json').exists():
        saved = read(OUT / 'construction.json')
        if saved['signature'] == signature(batch_size):
            verify_phase('construction')
            for case in saved['cases']:
                for cache in case['candidateDrawCaches'].values():
                    path = ROOT / cache['path']
                    if path.exists() and sha(path) != cache['sha256']:
                        raise ValueError('Corrupted local candidate draw cache')
            print('Reusing exact construction cache; no inference or predictions rerun'); return saved
    return build(check, batch_size)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); p.add_argument('--batch-size', type=int, default=256)
    a = p.parse_args(); run(a.check, a.batch_size)
