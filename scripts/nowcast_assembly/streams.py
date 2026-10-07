"""2026 layer noise: the Stage46 key structure and Sobol construction over a 2026 key registry.

The frozen historical registry (built from the Stage44 inventory) has no 2026 rows and is never edited. Every
Stage46 `noise` caller reads `uniforms` through its module, so one substitution reaches the Stage47 inversion
unchanged (the Stage63 composed-precision precedent). Shared keys are common to all seats of a layer, so each draw
row is one simulated election.
"""
import contextlib
import numpy as np
from scipy.stats import qmc
from scripts.uncertainty_tails import streams as base
from scripts.uncertainty_tails.integration import open_unit
from .common import YEAR, require, namespace_seed


def bank(rows, count, namespace):
    names = base.registry(rows)
    require(count and not count & (count - 1), 'draw count must be a power of two')
    sobol = qmc.Sobol(len(names), scramble=True, bits=30, seed=namespace_seed(namespace, 'layers'))
    return names, open_unit(sobol.random_base2(int(np.log2(count))))


@contextlib.contextmanager
def substituted(rows, count, namespace):
    names, values = bank(rows, count, namespace)
    original = base.uniforms

    def uniforms(year, requested):
        require(year == YEAR and requested == count, 'only the registered 2026 stream is available here')
        return names, values

    base.uniforms = uniforms
    try:
        yield names
    finally:
        base.uniforms = original
