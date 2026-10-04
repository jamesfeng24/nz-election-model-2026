"""Deterministic complete local/candidate transforms; no random draw or fit."""
import numpy as np
from decimal import Decimal, localcontext
from functools import lru_cache
from scripts.models.complete_party_vector.construction import construct_vector
from scripts.checkpoints.joint_candidate_share.kernel import centered, METHODS
from .adapter import simplexes


def source_affinities(party_row, categories, roster):
    ids = [c['categoryId'] for c in roster]
    keys = {c['categoryId']: c['targetPartyKey'] for c in categories if c['relationship'] != 'exit'}
    if set(ids) != set(keys) or any(keys[c['categoryId']] != c['ballotGroupKey'] for c in roster):
        raise ValueError('National/local category roster mismatch')
    source = {r['categoryId']: r for r in party_row['sourceCategories']}
    if len(source) != len(party_row['sourceCategories']):
        raise ValueError('Duplicate source category')
    _, states = construct_vector(categories, source, {cid: 1 / len(ids) for cid in ids})
    return np.array([states[cid]['affinity'] for cid in ids]), states


def local_vectors(fine_draws, affinities):
    x = simplexes(fine_draws)
    a = np.asarray(affinities, dtype=float)
    if a.shape != (x.shape[1],) or not np.isfinite(a).all() or (a < 0).any():
        raise ValueError('Missing/invalid affinity')
    masses = x * a
    total = masses.sum(axis=1)
    if not np.isfinite(total).all() or np.any(total <= 0):
        raise ValueError('No supported local party mass')
    return simplexes(masses / total[:, None])


def candidate_vectors(local, destinations, exponents, kappa):
    x = simplexes(local)
    dest = np.asarray(destinations)
    z = np.asarray(exponents, dtype=float)
    if dest.ndim != 1 or not len(dest) or not np.issubdtype(dest.dtype, np.integer) or z.shape != dest.shape:
        raise ValueError('Invalid candidate destinations/features')
    mapped = dest[dest >= 0]
    if len(set(mapped.tolist())) != len(mapped) or (dest < -1).any() or (dest >= x.shape[1]).any():
        raise ValueError('Duplicate/missing mapped candidate party')
    if not np.isfinite(z).all() or not np.isfinite(kappa) or not .0001 <= kappa <= .1:
        raise ValueError('Invalid fixed parameters/exponents')
    p = np.zeros((len(x), len(dest)))
    p[:, dest >= 0] = x[:, mapped]
    weights = (p + kappa) * exponent_weights(tuple(float(v) for v in z))
    return simplexes(weights / weights.sum(axis=1, keepdims=True))


@lru_cache(maxsize=512)
def exponent_weights(exponents):
    """One portable scalar exponential per fixed feature state, never per draw."""
    with localcontext() as context:
        context.prec = 50
        z = [Decimal(str(v)) for v in exponents]
        highest = max(z)
        return np.array([float((v - highest).exp()) for v in z])


def prepare_seat(row, case, method):
    if method not in METHODS:
        raise ValueError('Unknown frozen candidate restriction')
    params = case['fits'][method]['parameters']
    names = METHODS[method]
    if params['status'] != 'fitted' or set(params['coefficients']) != set(names) or any(abs(v) > 4 or not np.isfinite(v) for v in params['coefficients'].values()):
        raise ValueError('Wrong/invalid saved restriction')
    if list(params['theta']) != [params['coefficients'][n] for n in names]:
        raise ValueError('Saved feature coefficient order changed')
    group_ids = {r['ballotGroupKey']: i for i, r in enumerate(case['roster'])}
    destinations, exponents = [], []
    ids = [c['targetOccurrenceId'] for c in row['candidates']]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError('Duplicate/incomplete candidate slate')
    for c in row['candidates']:
        group = c['partyBallotGroupKey']
        if group is None:
            if not c['mappingStatus'].startswith('verified_no_party_group_'):
                raise ValueError('Missing group is not affirmative no-group')
            destinations.append(-1)
        else:
            if group not in group_ids:
                raise ValueError('Standing group absent from complete local vector')
            destinations.append(group_ids[group])
        exponents.append(sum(params['coefficients'][n] * centered(c, n, case['trainingOnlyMeans'], 'broad', 'printed') for n in names))
    return np.array(destinations, dtype=int), np.array(exponents), params['kappa']


def propagate(fine_draws, affinities, destinations, exponents, kappa, batch_size=256):
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError('Invalid batch size')
    x = simplexes(fine_draws)
    return np.concatenate([candidate_vectors(local_vectors(x[i:i + batch_size], affinities), destinations, exponents, kappa)
                           for i in range(0, len(x), batch_size)], axis=0)
