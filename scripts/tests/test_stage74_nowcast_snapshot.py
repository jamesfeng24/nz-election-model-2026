"""Stage74: the Python share summaries and the SYNTHETIC bank fixture read by the TypeScript contract test."""
import unittest
import numpy as np
from scripts.nowcast_assembly import fixture, summaries
from scripts.nowcast_assembly.common import read


class Summaries(unittest.TestCase):
    def test_nested_intervals_share_one_median_and_match_numpy(self):
        q = np.random.default_rng(1).dirichlet([2, 3, 5], 1000)
        out = summaries.share_summaries(['a', 'b', 'c'], q)
        for i, c in enumerate(out):
            self.assertEqual({v['median'] for v in c['intervals']}, {float(np.quantile(q[:, i], 0.5))})
            self.assertAlmostEqual(c['intervals'][1]['lower'], float(np.quantile(q[:, i], 0.1)), places=15)
            self.assertAlmostEqual(c['mean'], float(q[:, i].mean()), places=15)


class Fixture(unittest.TestCase):
    def test_fixture_is_labelled_synthetic_and_complete(self):
        bank = read(fixture.OUTPUT)
        self.assertEqual(bank['provenance'], 'synthetic-fixture')
        self.assertTrue(bank['label'].startswith('SYNTHETIC FIXTURE'))
        self.assertEqual(bank['draws'], fixture.COUNT)
        self.assertTrue(all(s['status'] == 'simulated' for s in bank['seats']))
        self.assertTrue(all(c['candidateId'].startswith('synthetic-') for c in bank['directory']['candidates']))


if __name__ == '__main__':
    unittest.main()
