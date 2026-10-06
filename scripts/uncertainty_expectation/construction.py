"""Exact-signature, unscored numerical companions; cached controls stay untouched."""
import hashlib
import json
import sys
import numpy as np
import scipy
from scripts.uncertainty_revision.construction import cases
from scripts.uncertainty.construction import national_case, scale_for
from scripts.uncertainty_tails.streams import permutation
from scripts.uncertainty_tails.construction import arrays as control_arrays
from .common import ROOT, PREFIX, INVENTORY, SCALES, read, save, verify, arguments, digest, encode, equivalent
from .simulation import component, composed

PRODUCERS = ('common', 'integration', 'simulation', 'construction')


def signature():
    paths = ['scripts/uncertainty_expectation/'+p+'.py' for p in PRODUCERS]
    return hashlib.sha256(encode({'inputs': read(PREFIX+'/input-contract.json'),
        'contracts': {p: digest(PREFIX+'/'+p+'.json') for p in ('numerical-contract', 'companion-contract')},
        'code': {p: digest(p) for p in paths},
        'environment': {'python': list(sys.version_info[:2]), 'numpy': np.__version__,
                        'scipy': scipy.__version__, 'lock': digest('requirements-boundaries.txt')}})).hexdigest()


def paths(cid, count, kind):
    p = ROOT/'.cache/stage47'/signature()/f'{kind}-{cid.replace(":", "-")}-{count}'
    return p.with_suffix('.npz'), p.with_suffix('.json')


def restore(cid, count, kind):
    archive, manifest = paths(cid, count, kind)
    if not manifest.exists():
        return None
    value = json.loads(manifest.read_text())
    if value['signature'] != signature() or value['draws'] != count or value['id'] != cid:
        raise ValueError('Incompatible Stage47 cache')
    if digest(str(archive.relative_to(ROOT))) != value['drawCache']['sha256']:
        raise ValueError('Corrupt Stage47 cache')
    return value


def arrays(case):
    value = restore(case['id'], case['draws'], case['kind'])
    if value is None or not equivalent(value, case):
        raise ValueError('Construct compatible Stage47 bank first')
    return np.load(ROOT/value['drawCache']['path'], allow_pickle=False)


def seal(cid, count, kind, vectors, metadata):
    archive, manifest = paths(cid, count, kind)
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        with np.load(archive, allow_pickle=False) as old:
            if set(old.files) != set(vectors) or any(not np.allclose(old[k], vectors[k], rtol=0, atol=1e-10) for k in vectors):
                raise ValueError('Changed deterministic Stage47 draws')
    else:
        temporary = archive.with_suffix('.temporary.npz')
        np.savez_compressed(temporary, **vectors)
        temporary.replace(archive)
    result = {'id': cid, 'draws': count, 'kind': kind, 'signature': signature(), **metadata,
              'drawCache': {'path': str(archive.relative_to(ROOT)), 'sha256': digest(str(archive.relative_to(ROOT)))}}
    manifest.write_bytes(encode(result))
    return result


def national_inputs(year, party, count):
    base, ids, provenance = national_case(year, party['ids'], 4096)
    order = permutation(4096, f'national:{year}')[:count]
    return base[order], {'ids': [ids[int(i)] for i in order], 'baseIndices': order.tolist(),
                        'weight': 1/count, 'replicas': 1, 'provenance': provenance}


def control_case(cid):
    return next(c for c in read('data/processed/uncertainty-tails/construction.json')['cases'] if c['id'] == cid)


def paired_control(case):
    """Original Stage45-law control, same canonical streams/indices, no regeneration."""
    original = control_case(case['id'])
    if case['draws'] > original['draws']:
        raise ValueError('Control has fewer common draws')
    return control_arrays(original)


def case_build(layer, year, rows, count, kind, scales, parties, regenerate=False):
    cid = f'{layer}:{year}'
    restored = None if regenerate else restore(cid, count, kind)
    if restored is not None:
        if [r['id'] for r in restored['records']] != [r['targetElectorateId'] for r in rows]:
            raise ValueError('Cached membership changed')
        return restored
    national, ids = (national_inputs(year, parties[rows[0]['targetElectorateId']], count)
                     if layer == 'composed' else (None, None))
    vectors, records = {}, []
    for row in rows:
        fit = scale_for(scales, row['layer'], year)['scales']
        if layer == 'composed':
            party = parties[row['targetElectorateId']]
            pfit = scale_for(scales, 'local_party', year)['scales']
            q, meta = composed(party, row, national, pfit, fit)
        else:
            q, meta = component(row, fit, count)
        vectors['corrected:'+row['targetElectorateId']] = q
        records.append({'id': row['targetElectorateId'], 'metadata': meta})
    original = control_case(cid)
    result = seal(cid, count, kind, vectors, {'layer': layer, 'year': year, 'records': records,
        'nationalDrawIds': ids, 'controlReference': {'id': cid, 'signature': original['signature'],
            'drawCache': original['drawCache'], 'indices': f'first {count}; same stream prefix'},
        'outcomesConsumed': False, 'meanRefitting': False, 'scalesRefitted': False})
    print('Sealed Stage47', kind, cid, count, len(rows), flush=True)
    return result


def build(regenerate=False):
    inventory, scales = read(INVENTORY), read(SCALES)
    spec = read(PREFIX+'/companion-contract.json')
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    completed, representatives = [], []
    for layer, year, rows in cases(inventory):
        count = spec['composedDraws'] if layer == 'composed' else spec['componentDraws']
        completed.append(case_build(layer, year, rows, count, 'full', scales, parties, regenerate))
    for layer, year, rows in cases(inventory):
        if layer != 'composed':
            continue
        chosen = [rows[i] for i in sorted({0, len(rows)//2, len(rows)-1})]
        for count in (256, 512, 1024):
            representatives.append(case_build(layer, year, chosen, count, 'precision', scales, parties, regenerate))
    return {'stage': 47, 'signature': signature(), 'cases': completed, 'representatives': representatives,
            'predictionsSealedBeforeEvaluation': True, 'sameStatisticalLaw': 'Stage45 Gaussian',
            'operationalSelection': None, 'fullCheckMeaning': 'explicit complete Stage47 reconstruction, not cached verification'}


def main():
    args = arguments()
    verify()
    save('construction.json', build(args.check), args.check)


if __name__ == '__main__':
    main()
