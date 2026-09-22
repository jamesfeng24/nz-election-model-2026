"""Common boundary contract rejects corrupted globally coupled bounds."""
import copy
import json
import unittest
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.contract import audit_scope


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope=json.loads((ROOT/'data/processed/boundaries/2011-2014/crosswalk.json').read_bytes())['scopes']['maori']

    def test_real_maori_network_and_unchanged_seats(self):
        self.assertEqual(audit_scope(self.scope)['controlsSatisfied'],7)
        unchanged=[t for t in self.scope['targets'] if t['officialChangeStatus']=='unchanged']
        self.assertEqual(len(unchanged),5)
        self.assertTrue(all(t['unchangedMembershipStatus']=='identity' for t in unchanged))

    def test_wrong_weight_control_and_duplicate_identity_fail(self):
        for kind in ['weight','control','duplicate']:
            s=copy.deepcopy(self.scope)
            if kind=='weight':s['edges'][0]['weightLower']['numerator']+=1
            elif kind=='control':s['targets'][0]['populationControl']+=1
            else:s['sources'].append(copy.deepcopy(s['sources'][0]))
            with self.assertRaises(ValueError):audit_scope(s)
