"""2026 layer noise: the Stage46 key structure over a 2026 key registry, generated per key group.

The frozen historical registry (built from the Stage44 inventory) has no 2026 rows and is never edited. Every
Stage46 `noise` caller reads `uniforms` through its module, so one substitution reaches the Stage47 inversion
unchanged (the Stage63 composed-precision precedent).

Keys are grouped: all `shared` keys (common to every seat of a layer, so each row is one simulated election) form one
scrambled Sobol bank, and each seat-layer's own keys form another, seeded from `simulation.seedNamespace` and the
group name. Columns are generated only when a seat asks for them, so memory stays bounded at production size
(65,536 rows) instead of one joint bank of every key.
"""
import contextlib
import numpy as np
from scipy.stats import qmc
from scripts.uncertainty_tails import streams as base
from scripts.uncertainty_tails.integration import open_unit
from .common import YEAR, require, namespace_seed


def group_of(name):
    """`shared` for shared keys; `<layer>:<seat>` for a seat's own keys."""
    parts = name.split(':')
    return 'shared' if parts[2] == 'shared' else f'{parts[0]}:{parts[3]}'


class GroupedBank:
    """A (count, len(names)) uniform matrix whose columns come from per-group scrambled Sobol banks."""

    def __init__(self, names, count, namespace):
        require(count and not count & (count - 1), 'draw count must be a power of two')
        self.count, self.namespace = count, namespace
        self.position = {}
        self.members = {}
        for i, name in enumerate(names):
            group = group_of(name)
            self.position[i] = (group, len(self.members.setdefault(group, [])))
            self.members[group].append(name)
        self.cache = {}

    def block(self, group):
        if group not in self.cache:
            if len(self.cache) > 4:  # keep the shared bank and the seats in use; seats are processed in turn
                for key in [k for k in self.cache if k != 'shared'][:-2]:
                    del self.cache[key]
            dims = len(self.members[group])
            sobol = qmc.Sobol(dims, scramble=True, bits=30, seed=namespace_seed(self.namespace, 'layers:' + group))
            self.cache[group] = open_unit(sobol.random_base2(int(np.log2(self.count))))
        return self.cache[group]

    def __getitem__(self, key):
        rows, column = key
        require(rows == slice(None), 'only whole columns are read')
        group, j = self.position[int(column)]
        return self.block(group)[:, j]


@contextlib.contextmanager
def substituted(rows, count, namespace):
    names = base.registry(rows)
    values = GroupedBank(names, count, namespace)
    original = base.uniforms

    def uniforms(year, requested):
        require(year == YEAR and requested == count, 'only the registered 2026 stream is available here')
        return names, values

    base.uniforms = uniforms
    try:
        yield names
    finally:
        base.uniforms = original
