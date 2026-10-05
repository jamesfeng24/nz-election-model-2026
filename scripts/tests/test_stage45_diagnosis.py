"""Independent pre-scoring scale-allocation arithmetic fixtures."""
import math
import unittest

import numpy as np

from scripts.uncertainty_revision.diagnosis import (
    EPSILON, aggregate_value, contrast_covariance, pair_value,
    remainder_pair_moment, scalar_residual, scale_decomposition,
)


class ResidualDiagnosisTests(unittest.TestCase):
    def row(self):
        return {'groups': ['national', 'labour', 'other', 'other'],
                'actual': [.40, .35, .20, .05], 'mean': [.45, .30, .20, .05]}

    def test_national_labour_cancels_clr_centering(self):
        row = self.row()
        expected = math.log((.40+EPSILON)/(.35+EPSILON)) - math.log((.45+EPSILON)/(.30+EPSILON))
        self.assertAlmostEqual(pair_value(row), expected, places=14)
        self.assertAlmostEqual(sum(scalar_residual(row)), 0, places=14)

    def test_major_balance_variance_ignores_minor_count(self):
        scales = {'shared': .2, 'seat': .5}
        for k in (2, 4, 30):
            row = {'groups': ['national', 'labour']+['other']*(k-2)}
            a = np.array([1., -1.]+[0.]*(k-2))
            result = contrast_covariance(row, a, scales)
            self.assertAlmostEqual(result['sharedVariance'], .08)
            self.assertAlmostEqual(result['seatVariance'], .50)
            self.assertAlmostEqual(result['totalSD'], math.sqrt(.58))

    def test_same_group_remainder_shared_effect_cancels(self):
        result = contrast_covariance(self.row(), [0, 0, 1, -1], {'shared': .2, 'seat': .5})
        self.assertEqual(result['sharedVariance'], 0)
        self.assertAlmostEqual(result['seatVariance'], .5)

    def test_aggregate_uses_complete_remainder(self):
        row = self.row()
        expected = math.log((.75+2*EPSILON)/(.25+2*EPSILON)) - math.log((.75+2*EPSILON)/(.25+2*EPSILON))
        self.assertAlmostEqual(aggregate_value(row), expected)
        self.assertAlmostEqual(remainder_pair_moment(row), 0)

    def test_missing_major_does_not_manufacture_pair(self):
        row = self.row();row['groups'][1] = 'other'
        self.assertIsNone(pair_value(row))

    def test_prior_and_history_variance_add_without_sd_addition(self):
        fold = {'layer': 'local_party', 'targetYear': 2014, 'trainingYears': [2011],
                'moments': [{'sharedSecondMoment': .04, 'seatSecondMoment': .16}],
                'scales': {'shared': math.sqrt(.04), 'seat': math.sqrt(.2275)}}
        spec = {'priorPseudoEnvironments': 3,
                'priorScales': {'local_party': {'shared': .2, 'seat': .5}}}
        result = scale_decomposition(fold, spec)
        self.assertAlmostEqual(result['parts']['seat']['priorVarianceContribution'], .1875)
        self.assertAlmostEqual(result['parts']['seat']['historicalVarianceContribution'], .04)
        self.assertAlmostEqual(result['NLSD'], math.sqrt(2*(.04+.2275)))


if __name__ == '__main__':
    unittest.main()
