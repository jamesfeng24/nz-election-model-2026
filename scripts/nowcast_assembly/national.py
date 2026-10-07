"""National adapter: the configured latent-state draws (D106) mapped to 2026 party groups.

Only `lastDataSupport` is read. `electionDay` is never loaded, and a config that names it fails. National
uncertainty enters once, through the draw row: every seat and the MMP party vote read the same row.
"""
import numpy as np
from .common import ROOT, OTHER, read, require, permutation, file_sha256


def sibling(source):
    require(source.endswith('.npz'), 'national source must be a saved .npz draw file')
    return source[:-4] + '.json'


def load(config, count):
    """Return (shares[count, G], drawIds[count], groups[G]) for the configured national state."""
    national = config['national']
    key = national['stateKey']
    require(key == 'lastDataSupport', 'the nowcast reads lastDataSupport only (D106)')
    require(key not in national['forbiddenStateKeys'] and 'electionDay' in national['forbiddenStateKeys'],
            'election-week draws must be forbidden for the nowcast')
    meta = read(sibling(national['source']))
    require(meta.get('status') == 'accepted', 'national fit is not accepted')
    require(meta['signature']['cutoff'] == national['dataCutoff'], 'national fit cutoff differs from config dataCutoff')
    require(file_sha256(national['source']) == meta['npzSha256'], 'national draw file hash differs from its record')
    with np.load(ROOT / national['source']) as bank:
        draws = np.asarray(bank[key], dtype=float)
    categories = meta['parties']
    mapping = national['categoryMap']
    require(set(mapping) == set(categories) and len(set(mapping.values())) == len(mapping),
            'categoryMap must map every national category to a distinct 2026 group')
    require(OTHER in mapping.values(), 'the Other category must map to the national other bucket')
    draws = draws.reshape(-1, len(categories))
    ids = meta['drawIds']
    require(len(ids) == len(draws) == len(set(ids)), 'national draw ids are missing or duplicated')
    require(np.isfinite(draws).all() and (draws >= 0).all() and np.allclose(draws.sum(axis=1), 1, atol=1e-9),
            'national draws are not finite simplexes')
    require(isinstance(count, int) and 0 < count <= len(draws) and not count & (count - 1),
            f'draw count must be a power of two no larger than {len(draws)}')
    order = permutation(len(draws), config['simulation']['seedNamespace'], 'national')[:count]
    groups = [mapping[c] for c in categories]
    return draws[order], [ids[int(i)] for i in order], groups
