"""Block streams for the composed precision study; block 0 is exactly the Stage47/Stage48 frame."""
import contextlib
from functools import lru_cache
import numpy as np
from scipy.stats import qmc
from scripts.uncertainty.construction import national_case
from scripts.uncertainty_tails import streams as base
from scripts.uncertainty_tails.integration import open_unit
from .common import INVENTORY, read

BLOCK = 512
POOL = 4096


def seed(year, scramble):
    return 460046 + year + 1000 * scramble


@lru_cache(maxsize=None)
def block_uniforms(year, count, scramble):
    """The Stage46 key registry and Sobol construction with only the scramble seed substituted."""
    inventory = read(INVENTORY)
    rows = [r for key in ('partyRecords', 'candidateRecords') for r in inventory[key] if r['targetYear'] == year]
    names = base.registry(rows)
    if count & (count - 1):
        raise ValueError('Simulation count must be power of two')
    return names, open_unit(qmc.Sobol(len(names), scramble=True, bits=30, seed=seed(year, scramble)).random_base2(int(np.log2(count))))


@contextlib.contextmanager
def scrambled(index):
    """Every caller of the Stage46 ``noise`` reads ``uniforms`` through its module, so one substitution
    reaches the Stage47 inversion and the Stage48 rebalance without copying either."""
    original = base.uniforms
    base.uniforms = lambda year, count: block_uniforms(year, count, index)
    try:
        yield
    finally:
        base.uniforms = original


def national_block(year, party, block, size=BLOCK):
    """National draws and cached draw ids of block ``block`` of the Stage47 order of the balanced 4,096 subset."""
    draws, ids, _ = national_case(year, party['ids'], POOL)
    order = base.permutation(POOL, f'national:{year}')[block * size:(block + 1) * size]
    return draws[order], [ids[int(i)] for i in order]


def chain_of(draw_id):
    """Chain number of a cached draw id such as ``gauss-2017-attempt1-chain3-draw0012``."""
    return int(draw_id.split('-chain')[1].split('-')[0])


def pool_order(year, party):
    """Pool positions of every block in order, for the disjointness check."""
    return [base.permutation(POOL, f'national:{year}')[b * BLOCK:(b + 1) * BLOCK] for b in range(POOL // BLOCK)]
