"""Stage87: the 2026 layer noise groups are independent when paired by row, at production size.

Separately scrambled Sobol engines share their coarse structure row by row (the leading output bits of every
dimension are fixed by the low bits of the row index), so the pre-fix construction gave row-paired correlations
above 0.9. The grouped bank now permutes each non-shared group's rows independently."""
import itertools
import unittest
import numpy as np
from scipy.stats import norm, qmc
from scripts.nowcast_assembly import streams
from scripts.nowcast_assembly.common import namespace_seed
from scripts.uncertainty_tails.integration import open_unit

NAMESPACE = 'nz-nowcast-2026'
ROWS = 65536  # production size: 4,096 national draws x 16 layer replicates
SEATS = ('e01', 'e02', 'e03')
LAYERS = ('party', 'candidate')


def names():
    shared = [f'{layer}:2026:shared:{key}' for layer in LAYERS for key in ('balance', 'mass', 'within:a', 'within:b', 'within:c')]
    seat = [f'{layer}:2026:seat:{s}:{key}' for layer in LAYERS for s in SEATS for key in ('balance', 'mass', 'within:a', 'within:b', 'within:c')]
    return shared + seat


def cross_correlations(columns):
    """Largest |row-paired correlation| of normal scores, and of their squares, between columns of different groups."""
    worst = {'linear': 0.0, 'square': 0.0}
    for (_, a), (_, b) in itertools.combinations(columns.items(), 2):
        za = (a - a.mean(0)) / a.std(0)
        zb = (b - b.mean(0)) / b.std(0)
        worst['linear'] = max(worst['linear'], float(np.abs(za.T @ zb / len(za)).max()))
        qa, qb = za ** 2, zb ** 2
        qa, qb = (qa - qa.mean(0)) / qa.std(0), (qb - qb.mean(0)) / qb.std(0)
        worst['square'] = max(worst['square'], float(np.abs(qa.T @ qb / len(qa)).max()))
    return worst


class GroupIndependence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = names()
        bank = streams.GroupedBank(cls.names, ROWS, NAMESPACE)
        cls.columns = {}
        for group in bank.members:
            cls.columns[group] = norm.ppf(bank.block(group))
        cls.bank = bank

    def test_groups_are_the_registered_ones(self):
        self.assertEqual(set(self.bank.members), {'shared'} | {f'{l}:{s}' for l in LAYERS for s in SEATS})

    def test_row_paired_correlation_between_groups_is_noise_level(self):
        # iid expectation is 1/sqrt(ROWS) = 0.0039; the largest of the 5 x 5 x 36 = 900 pairs stays under 4.5 sd
        worst = cross_correlations(self.columns)
        limit = 4.5 / np.sqrt(ROWS)
        self.assertLess(worst['linear'], limit)
        self.assertLess(worst['square'], limit)

    def test_every_column_is_still_evenly_spread(self):
        for group, block in self.columns.items():
            u = norm.cdf(block)
            counts = np.stack([np.histogram(u[:, j], bins=256, range=(0, 1))[0] for j in range(u.shape[1])])
            self.assertLessEqual(np.abs(counts - ROWS / 256).max(), 2, group)

    def test_dimensions_of_one_group_stay_uncorrelated(self):
        for group, block in self.columns.items():
            c = np.corrcoef(block.T) - np.eye(block.shape[1])
            self.assertLess(np.abs(c).max(), 4.5 / np.sqrt(ROWS), group)

    def test_deterministic_and_group_blocks_do_not_depend_on_what_else_is_asked(self):
        again = streams.GroupedBank(self.names, ROWS, NAMESPACE)
        only = again.block('candidate:e03')
        self.assertTrue(np.array_equal(norm.ppf(only), self.columns['candidate:e03']))
        other_namespace = streams.GroupedBank(self.names, ROWS, NAMESPACE + 'x').block('candidate:e03')
        self.assertFalse(np.array_equal(only, other_namespace))

    def test_shared_group_keeps_its_natural_sobol_order(self):
        dims = len(self.bank.members['shared'])
        natural = open_unit(qmc.Sobol(dims, scramble=True, bits=30, seed=namespace_seed(NAMESPACE, 'layers:shared')).random_base2(16))
        self.assertTrue(np.array_equal(self.bank.block('shared'), natural))

    def test_the_unpermuted_construction_is_detected(self):
        """Negative control: separately scrambled engines paired by row fail the same check."""
        raw = {g: norm.ppf(open_unit(qmc.Sobol(len(m), scramble=True, bits=30, seed=namespace_seed(NAMESPACE, 'layers:' + g))
                                     .random_base2(16)))
               for g, m in self.bank.members.items()}
        self.assertGreater(cross_correlations(raw)['linear'], 0.5)


if __name__ == '__main__':
    unittest.main()
