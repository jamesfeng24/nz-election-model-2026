"""Stage68 descriptive swing check: frozen stop rule, arithmetic and sealed summary."""
import unittest
import numpy as np
from scripts.balance_scale.common import equivalent
from scripts.shared_split_swing import run
from scripts.uncertainty_revision.common import read


class SharedSplitSwing(unittest.TestCase):
    def test_contract_is_frozen(self):
        rule = run.design()['stopRule']
        self.assertEqual((rule['signsAgreeRequired'], rule['loeoRmsRatioMaximum'], rule['leaveFutureOutYears']), (4, 0.75, [2020, 2023]))
        self.assertIsNone(run.design()['operationalAdoption'])

    def test_through_origin_beta(self):
        x, y = np.array([1., -2.]), np.array([-0.5, 1.])
        self.assertAlmostEqual(run.beta(x, y), 0.5)

    def test_summary_reproduces(self):
        saved = read(run.PREFIX + '/summary.json')
        self.assertTrue(equivalent(saved, run.build(), 1e-10))
        self.assertIn(saved['finding'], run.design()['stopRule']['findings'])
        for v in saved['byElection'].values():
            self.assertLess(abs(v['sharedShift'] - v['heterogeneityElectionMean']), 0.05)


if __name__ == '__main__':
    unittest.main()
