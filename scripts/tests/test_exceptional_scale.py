"""Exceptional-scale diagnostic: frozen flag set, likelihood reduction and saved-summary invariants (no regeneration)."""
import unittest

import numpy as np

from scripts.balance_scale.common import read
from scripts.exceptional_scale import run


class ExceptionalScale(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.envs = run.data()
        cls.summary = read(run.OUTPUT)

    def test_frozen_flags_match_the_audit_universe(self):
        self.assertEqual({y: len(v) for y, v in run.FROZEN_YES.items()}, {2014: 8, 2017: 6, 2020: 10, 2023: 14})
        self.assertEqual({y: int(e['yes'].sum()) for y, e in self.envs.items()}, {2014: 8, 2017: 6, 2020: 10, 2023: 14})
        self.assertEqual(sum(len(e['p']) for e in self.envs.values()), 257)

    def test_two_group_likelihood_reduces_to_one_scale_when_b_is_zero(self):
        theta = np.array([-0.2, 0., 0.])
        flat = {y: dict(e, yes=np.zeros_like(e['yes'])) for y, e in self.envs.items()}
        self.assertAlmostEqual(run.nll(theta, self.envs)[0], run.nll(theta, flat)[0], places=10)
        self.assertAlmostEqual(run.nll(np.array([-0.2, 0.4, 0.]), flat)[0], run.nll(theta, flat)[0], places=10)

    def test_gradient_matches_central_differences(self):
        theta, h = np.array([-0.3, 0.5, 0.]), 1e-6
        _, grad = run.nll(theta, self.envs)
        for k in (0, 1):
            step = np.eye(3)[k] * h
            numeric = (run.nll(theta + step, self.envs)[0] - run.nll(theta - step, self.envs)[0]) / (2 * h)
            self.assertAlmostEqual(grad[k], numeric, places=5)

    def test_saved_summary_invariants(self):
        s = self.summary
        self.assertFalse(s['adopted'])
        self.assertFalse(s['operationalChange'])
        self.assertEqual((s['flags']['exceptionalTotal'], s['flags']['seats']), (38, 257))
        for key in ('controlZ', 'auditSeatZ'):
            self.assertEqual(sum(r['exceptional']['count'] for r in s['bands'][key]), 38)
            self.assertEqual(sum(r['ordinary']['count'] for r in s['bands'][key]), 219)
        lik = s['likelihood']
        self.assertLessEqual(lik['twoGroup']['nll'], lik['pooledOneScale']['nll'])
        self.assertTrue(lik['twoGroup']['converged'] and not lik['twoGroup']['boundContact'])


if __name__ == '__main__':
    unittest.main()
