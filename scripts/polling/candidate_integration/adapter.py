"""Raw gauss joint output to complete historical ballot-category scenarios."""
from math import fsum
import numpy as np
from .common import EXTERNAL, read, sha


def simplexes(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or not x.shape[0] or not x.shape[1] or not np.isfinite(x).all() or (x < 0).any():
        raise ValueError('Invalid joint simplex array')
    if not np.allclose(x.sum(axis=1), 1., atol=1e-12, rtol=0):
        raise ValueError('Incomplete joint simplex array')
    return x


def allocate_draws(draws, raw_categories, roster, weights, explicit_mapping):
    x = simplexes(draws)
    if x.shape[1] != len(raw_categories) or len(set(raw_categories)) != len(raw_categories) or raw_categories.count('Other') != 1:
        raise ValueError('Incomplete/duplicate raw national categories')
    ids = [c['categoryId'] for c in roster]
    if len(set(ids)) != len(ids) or len({c['ballotGroupKey'] for c in roster}) != len(ids):
        raise ValueError('Duplicate category or ballot group')
    if set(explicit_mapping) != set(raw_categories) - {'Other'} or len(set(explicit_mapping.values())) != len(explicit_mapping):
        raise ValueError('Unknown/duplicate explicit category')
    fractions = {r['categoryId']: r['allocationFraction'] for r in weights}
    explicit = set(explicit_mapping.values())
    if len(fractions) != len(weights) or explicit & set(fractions) or set(ids) != explicit | set(fractions):
        raise ValueError('Missing/duplicated allocation or explicit destination')
    if fractions and (any(not np.isfinite(v) or v < 0 for v in fractions.values()) or abs(fsum(fractions.values()) - 1) > 1e-12):
        raise ValueError('Invalid Other fractions')
    other = x[:, raw_categories.index('Other')]
    if not fractions and np.any(other != 0):
        raise ValueError('Unresolved positive Other without recipient')
    out = np.empty((len(x), len(ids)))
    for label, cid in explicit_mapping.items():
        out[:, ids.index(cid)] = x[:, raw_categories.index(label)]
    for cid, fraction in fractions.items():
        out[:, ids.index(cid)] = other * fraction
    simplexes(out)
    if fractions and not np.allclose(out[:, [ids.index(cid) for cid in fractions]].sum(axis=1), other, atol=1e-12, rtol=0):
        raise ValueError('Other conservation failure')
    return out


def read_case(case):
    year = case['year']
    metadata = read(EXTERNAL / f'fits/{year}/attempt1.json')
    path = EXTERNAL / f'fits/{year}/attempt1.npz'
    if metadata['signature'] != case['nationalSignature'] or metadata['drawIds'] != case['nationalDrawIds'] or sha(path) != metadata['npzSha256']:
        raise ValueError('Changed raw national forecast/signature')
    with np.load(path, allow_pickle=False) as archive:
        chain = archive['electionDay']
        if list(chain.shape) != case['chainShape']:
            raise ValueError('National chain shape changed')
        x = chain.reshape(-1, chain.shape[-1])
    if len(x) != len(case['nationalDrawIds']) or len(set(case['nationalDrawIds'])) != len(x):
        raise ValueError('Invalid shared draw identity')
    return simplexes(x)
