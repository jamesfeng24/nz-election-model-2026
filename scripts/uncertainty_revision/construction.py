"""Resumable sealed forecasts and fixed numerical convergence, no mean fitting."""
import json
import hashlib
from pathlib import Path
import numpy as np
from scripts.uncertainty.construction import national_case, scale_for
from scripts.uncertainty.simulation import component as original_component, compose as original_compose
from scripts.uncertainty.metrics import crps
from .common import ROOT, PREFIX, OLD, read, save, verify, arguments, signature, digest, encode, equivalent
from .simulation import component, compose


def inputs():
    inventory = read(OLD + '/inventory.json')
    return inventory, read(PREFIX + '/scales.json'), read(OLD + '/scales.json')


def cases(inventory):
    result = []
    for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords')):
        for year in sorted({r['targetYear'] for r in inventory[key]}):
            result.append((layer, year, sorted([r for r in inventory[key] if r['targetYear'] == year], key=lambda r: r['targetElectorateId'])))
    for year in (2017, 2020, 2023):
        result.append(('composed', year, sorted([r for r in inventory['candidateRecords'] if r['targetYear'] == year], key=lambda r: r['targetElectorateId'])))
    return result


def simulate(row, layer, policy, draws, revised, old, party=None, national=None):
    scales = revised if policy == 'revised' else old
    if layer != 'composed':
        fit = scale_for(scales, layer, row['targetYear'])
        q, metadata = (component if policy == 'revised' else original_component)(row, fit['scales'], draws)
    else:
        year = row['targetYear']
        p = scale_for(scales, 'local_party', year)['scales']
        c = scale_for(scales, 'candidate', year)['scales']
        q, metadata = (compose if policy == 'revised' else original_compose)(party, row, national, p, c)
    return q, metadata


def cache_paths(case_id, draws, kind):
    folder = ROOT / '.cache/stage45' / signature()
    path = folder / f'{kind}-{case_id.replace(":", "-")}-{draws}'
    return path.with_suffix('.npz'), path.with_suffix('.json')


def restore(case_id, draws, kind):
    archive, manifest = cache_paths(case_id, draws, kind)
    if not manifest.exists():
        return None
    value = json.loads(manifest.read_text())
    if value['signature'] != signature() or value['draws'] != draws or value['id'] != case_id:
        raise ValueError('Incompatible exact-signature cache')
    if digest(str(archive.relative_to(ROOT))) != value['drawCache']['sha256']:
        raise ValueError('Corrupt Stage45 cache')
    return value


def seal(case_id, draws, kind, vectors, metadata):
    archive, manifest = cache_paths(case_id, draws, kind)
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        with np.load(archive, allow_pickle=False) as cached:
            if set(cached.files) != set(vectors) or any(not np.allclose(cached[k], vectors[k], rtol=0, atol=1e-10) for k in vectors):
                raise ValueError('Changed deterministic cached draws')
    else:
        temporary = archive.with_suffix('.temporary.npz')
        np.savez_compressed(temporary, **vectors)
        temporary.replace(archive)
    value = {'id': case_id, 'draws': draws, 'signature': signature(), **metadata,
             'drawCache': {'path': str(archive.relative_to(ROOT)), 'sha256': digest(str(archive.relative_to(ROOT)))}}
    manifest.write_bytes(encode(value))
    return value


def arrays(case):
    runtime = restore(case['id'], case['draws'], case['kind'])
    if runtime is None or not equivalent(case, runtime):
        raise ValueError('Run compatible construction first')
    return np.load(ROOT / runtime['drawCache']['path'], allow_pickle=False)


def case_build(layer, year, rows, draws, kind, revised, old, parties, regenerate=False):
    case_id = f'{layer}:{year}'
    restored = None if regenerate else restore(case_id, draws, kind)
    if restored is not None:
        return restored
    vectors, records, national_ids, provenance = {}, [], None, None
    national = None
    if layer == 'composed':
        national, national_ids, provenance = national_case(year, parties[rows[0]['targetElectorateId']]['ids'], draws)
    for row in rows:
        record = {'id': row['targetElectorateId'], 'metadata': {}}
        for policy in ('revised', 'unchanged_stage44'):
            q, metadata = simulate(row, layer, policy, draws, revised, old, parties.get(row['targetElectorateId']), national)
            vectors[policy + ':' + row['targetElectorateId']] = q
            record['metadata'][policy] = metadata
        records.append(record)
    value = seal(case_id, draws, kind, vectors,
                 {'kind': kind, 'layer': layer, 'year': year, 'records': records,
                  'nationalDrawIds': national_ids, 'nationalProvenance': provenance,
                  'outcomesConsumed': False, 'meanRefitting': False})
    print('Sealed', kind, case_id, draws, len(rows), flush=True)
    return value


def monitored(case, rows):
    result = {}
    with arrays(case) as bank:
        for policy in ('revised', 'unchanged_stage44'):
            values = []
            for row in rows:
                q = bank[policy + ':' + row['targetElectorateId']]
                values.append({'id': row['targetElectorateId'], 'meanPP': (100 * q.mean(axis=0)).tolist(),
                               'crpsPP': crps(100 * q, 100 * np.array(row['actual'])).tolist(),
                               'width90PP': (100 * (np.quantile(q, .95, axis=0) - np.quantile(q, .05, axis=0))).tolist()})
            result[policy] = values
    return result


def convergence(regenerate=False):
    inventory, revised, old = inputs()
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    spec = read(PREFIX + '/specification.json')
    previous, rounds, selected, passed = None, [], None, False
    for draws in spec['drawCounts']:
        current = {}
        for layer, year, rows in cases(inventory):
            chosen = [rows[i] for i in sorted({0, len(rows) // 2, len(rows) - 1})]
            case = case_build(layer, year, chosen, draws, 'precision', revised, old, parties, regenerate)
            current[case['id']] = monitored(case, chosen)
        changes = {}
        if previous is not None:
            for field in ('meanPP', 'crpsPP', 'width90PP'):
                changes[field] = max(abs(a - b) for cid in current for policy in current[cid]
                    for now, earlier in zip(current[cid][policy], previous[cid][policy])
                    for a, b in zip(now[field], earlier[field]))
            gate = spec['convergence']
            passed = (changes['meanPP'] <= gate['maximumMeanChangePP'] and
                      changes['crpsPP'] <= gate['maximumCRPSChangePP'] and
                      changes['width90PP'] <= gate['maximum90WidthChangePP'])
        rounds.append({'draws': draws, 'changes': changes, 'passed': passed, 'monitored': current})
        selected = draws
        if passed:
            break
        previous = current
    return {'stage': 45, 'selectedDraws': selected, 'converged': passed,
            'capReached': selected == spec['capDraws'], 'rounds': rounds,
            'status': 'fixed_precision_gate_passed' if passed else 'cap_used_precision_gate_unmet',
            'action': 'no further count or tolerance change; report limited precision'}


def build(regenerate=False):
    inventory, revised, old = inputs()
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    precision = convergence(regenerate)
    save('convergence.json', precision, regenerate)
    draws = precision['selectedDraws']
    completed = [case_build(layer, year, rows, draws, 'full', revised, old, parties, regenerate)
                 for layer, year, rows in cases(inventory)]
    return {'stage': 45, 'signature': signature(), 'draws': draws,
            'precisionStatus': precision['status'], 'cases': completed,
            'predictionsSealedBeforeEvaluation': True, 'operationalSelection': None}


def main():
    args = arguments(); verify(); save('construction.json', build(args.check), args.check)
    print('Stage45 draws sealed; no mean coefficients fitted')


if __name__ == '__main__':
    main()
