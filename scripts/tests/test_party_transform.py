import unittest
from scripts.models.party_vote_transform.formulas import transform,prediction_bounds,METHODS

class FormulaTests(unittest.TestCase):
    def test_prespecified_formulas(self):
        for method in METHODS:self.assertAlmostEqual(transform(method,.3,.2,.2)['prediction'],.3)
        self.assertAlmostEqual(transform('additive',.3,.2,.4)['prediction'],.5)
        self.assertAlmostEqual(transform('proportional',.3,.2,.4)['prediction'],.6)
        self.assertAlmostEqual(transform('log_odds',.3,.2,.4)['prediction'],8/15)
    def test_domains_clipping_and_zeros(self):
        for method in METHODS:
            for p in [0,.01,.5,.99,1]:self.assertTrue(0<=transform(method,p,.1,.9)['prediction']<=1)
            with self.assertRaises(ValueError):transform(method,.2,0,.2)
        self.assertTrue(transform('additive',.9,.1,.5)['clipped'])
        self.assertTrue(transform('proportional',.9,.1,.5)['clipped'])
        for method in ['proportional','log_odds']:self.assertEqual(transform(method,0,.1,.5)['prediction'],0)
    def test_bounds_and_corruption(self):
        for method in METHODS:
            r=prediction_bounds(method,.1,.4,.2,.3,.25)
            self.assertLessEqual(r['lower'],r['upper'])
            self.assertGreaterEqual(r['absoluteErrorUpper'],r['absoluteErrorLower'])
        with self.assertRaises(ValueError):prediction_bounds('additive',.4,.1,.2,.3,.2)
        with self.assertRaises(ValueError):prediction_bounds('additive',.1,.4,.2,.3,2)
