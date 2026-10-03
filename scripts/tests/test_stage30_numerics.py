"""Synthetic numerical fixtures; no historical result is altered."""
import unittest
from scripts.models.expanded_candidate_persistence.numerics import fit,mean_fit

class PersistenceNumerics(unittest.TestCase):
    def test_unrestricted_exact_line(self):
        f=fit([-0.2,0.0,0.2],[-0.5,0.1,0.7])
        self.assertEqual(f['status'],'available');self.assertAlmostEqual(f['alpha'],0.1);self.assertAlmostEqual(f['beta'],3)
    def test_tiny_sample_identifiable(self):
        self.assertEqual(fit([0,1],[3,2])['status'],'available')
    def test_variation_rank_and_empty(self):
        self.assertEqual(fit([1,1],[1,2])['reason'],'zero_predictor_variation')
        self.assertEqual(fit([],[])['status'],'abstain')
        self.assertEqual(fit([0,float('nan')],[1,2])['status'],'abstain')
    def test_mean_independent_of_slope(self):
        self.assertEqual(mean_fit([1,3])['mean'],2)
        self.assertEqual(mean_fit([])['status'],'abstain')
    def test_no_clipping(self):
        f=fit([0,1],[2,4]);self.assertAlmostEqual(f['alpha']+f['beta']*2,6)
