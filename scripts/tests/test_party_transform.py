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

class IdentityTests(unittest.TestCase):
    def test_historical_identity_and_anti_leakage(self):
        import json
        from scripts.models.party_vote_transform.inputs import Inputs,continuity,DEST,allowed
        from scripts.transform.panel_config import canonical
        x=Inputs();e=x.elections();spec=json.loads((DEST/'specification.json').read_bytes());rows=continuity(e,spec['transitions'])
        self.assertEqual(sum(r['status']=='eligible' for r in rows),53)
        self.assertEqual(canonical('newconservative'),canonical('conservativeparty'))
        self.assertNotEqual(canonical('internetmana'),canonical('manamovement'))
        self.assertNotEqual(canonical('advance'),canonical('nzpublicparty'))
        self.assertTrue(all(r['source'] is None for r in rows if r['status']=='entrant'))
        self.assertTrue(all(r['target'] is None for r in rows if r['status']=='exit'))
        self.assertFalse(any('opportunity'==r['canonicalPartyId'] for r in rows))
        for path in ['data/processed/polls/2026.json','data/processed/candidates/2026.json','data/processed/boundaries/2023-2026/party-votes.json','data/processed/models/incumbency.json']:
            with self.assertRaises(ValueError):allowed(path)
        self.assertEqual(sum(t['primary'] for t in spec['transitions']),3)
        self.assertEqual(len(spec['transitions']),5)
